"""Hardened StructuredRunner with JSON extraction, repair, and retry."""
from __future__ import annotations

import json
import re
from typing import Any, Type, TypeVar

from pydantic import BaseModel, ValidationError

from .client_base import LLMClientBase, LLMRequest

T = TypeVar("T", bound=BaseModel)


class StructuredRunResult(BaseModel):
    success: bool
    parsed: Any | None = None
    raw_text: str
    errors: list[str] = []
    retries: int = 0
    cache_hit: bool = False
    metadata: dict[str, Any] = {}


def _extract_json_text(text: str) -> str:
    """Strip markdown fences and trim to the outermost JSON object/array."""
    # Remove ```json ... ``` or ``` ... ``` fences
    fenced = re.sub(r"```(?:json)?\s*", "", text)
    fenced = fenced.replace("```", "")

    # Trim to first { or [ and last } or ]
    start = min(
        (fenced.find("{") if "{" in fenced else len(fenced)),
        (fenced.find("[") if "[" in fenced else len(fenced)),
    )
    end_brace = fenced.rfind("}")
    end_bracket = fenced.rfind("]")
    end = max(end_brace, end_bracket)

    if start <= end:
        return fenced[start : end + 1]
    return fenced.strip()


def _try_parse(text: str) -> tuple[Any, str | None]:
    """Attempt JSON parse; return (data, error_msg)."""
    try:
        return json.loads(text), None
    except json.JSONDecodeError as exc:
        return None, str(exc)


class StructuredRunner:
    """Run an LLM request and parse the response into a Pydantic model.

    Features:
    - JSON fence extraction (strips ```json ... ```)
    - Lightweight JSON repair (trim surrounding text)
    - Pydantic validation with retry
    - Returns StructuredRunResult (never raises on parse failure)
    """

    def __init__(self, client: LLMClientBase, max_retries: int = 1) -> None:
        self._client = client
        self._max_retries = max_retries

    def run_safe(
        self,
        request: LLMRequest,
        model_cls: Type[T],
    ) -> StructuredRunResult:
        """Run and parse, returning StructuredRunResult (never raises)."""
        raw_text = ""
        errors: list[str] = []
        retries = 0

        try:
            response = self._client.complete(request)
            raw_text = response.text
        except Exception as exc:
            return StructuredRunResult(
                success=False,
                raw_text="",
                errors=[f"LLM call failed: {exc}"],
            )

        for attempt in range(self._max_retries + 1):
            if attempt > 0:
                retries += 1
                errors.append(f"Retrying parse (attempt {attempt + 1})")

            extracted = _extract_json_text(raw_text)
            data, parse_err = _try_parse(extracted)

            if data is None:
                errors.append(f"JSON parse error: {parse_err}")
                continue

            try:
                parsed = model_cls.model_validate(data)
                return StructuredRunResult(
                    success=True,
                    parsed=parsed,
                    raw_text=raw_text,
                    errors=errors,
                    retries=retries,
                )
            except ValidationError as exc:
                errors.append(f"Pydantic validation error: {exc}")

        return StructuredRunResult(
            success=False,
            parsed=None,
            raw_text=raw_text,
            errors=errors,
            retries=retries,
        )

    def run(self, request: LLMRequest, model_cls: Type[T]) -> T:
        """Run and parse; raises ValueError on failure (original contract)."""
        result = self.run_safe(request, model_cls)
        if not result.success or result.parsed is None:
            raise ValueError(
                f"StructuredRunner failed: {result.errors}"
            )
        return result.parsed  # type: ignore[return-value]