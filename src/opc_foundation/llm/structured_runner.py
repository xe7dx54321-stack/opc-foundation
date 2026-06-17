"""Hardened StructuredRunner with JSON extraction, repair, and retry.

功能说明：
    StructuredRunner 负责：
    1. 调用 LLM 获取文本响应
    2. 从响应中提取 JSON（剥离 markdown 围栏）
    3. 用 Pydantic 模型校验 JSON
    4. 如果解析/校验失败，重新调用 LLM 并重试

    run_safe() 永不抛异常，返回 StructuredRunResult。
    run() 在失败时抛 ValueError（保持原始契约）。
"""
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
    """从 LLM 响应文本中提取 JSON 字符串。

    剥离 ```json ... ``` 或 ``` ... ``` 围栏，
    然后裁剪到最外层的 { } 或 [ ]。

    参数：
        text: LLM 返回的原始文本

    返回：
        提取后的 JSON 字符串
    """
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
    """尝试 JSON 解析。

    参数：
        text: 待解析的 JSON 字符串

    返回：
        (data, error_msg)：成功时 data 是解析后的对象，error_msg 为 None；
        失败时 data 为 None，error_msg 是错误信息。
    """
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
    - Retry re-calls the LLM (not just re-parses the same text)
    - Returns StructuredRunResult (never raises on parse failure)

    参数：
        client: LLM 客户端（实现 LLMClientBase 接口）
        max_retries: 最大重试次数（默认 1，即最多调用 LLM 2 次）
    """

    def __init__(self, client: LLMClientBase, max_retries: int = 1) -> None:
        self._client = client
        self._max_retries = max_retries

    def run_safe(
        self,
        request: LLMRequest,
        model_cls: Type[T],
    ) -> StructuredRunResult:
        """运行 LLM 请求并解析响应，返回 StructuredRunResult（永不抛异常）。

        参数：
            request: LLM 请求对象
            model_cls: 目标 Pydantic 模型类

        返回：
            StructuredRunResult：包含 success、parsed、raw_text、errors、retries 等字段。
            重试时会重新调用 LLM（而非只重新解析同一段文本）。
        """
        raw_text = ""
        errors: list[str] = []
        retries = 0

        for attempt in range(self._max_retries + 1):
            if attempt > 0:
                retries += 1
                errors.append(f"Retrying (attempt {attempt + 1})")

            # 每次尝试都重新调用 LLM
            try:
                response = self._client.complete(request)
                raw_text = response.text
            except Exception as exc:
                errors.append(f"LLM call failed: {exc}")
                if attempt < self._max_retries:
                    continue
                return StructuredRunResult(
                    success=False,
                    raw_text=raw_text,
                    errors=errors,
                    retries=retries,
                )

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
        """运行并解析；失败时抛 ValueError（保持原始契约）。

        参数：
            request: LLM 请求对象
            model_cls: 目标 Pydantic 模型类

        返回：
            解析后的 Pydantic 模型实例

        异常：
            ValueError: 当解析或校验失败时抛出
        """
        result = self.run_safe(request, model_cls)
        if not result.success or result.parsed is None:
            raise ValueError(
                f"StructuredRunner failed: {result.errors}"
            )
        return result.parsed  # type: ignore[return-value]
