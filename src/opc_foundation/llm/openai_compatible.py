"""OpenAI-compatible LLM client (works with OpenAI, Together, Groq, etc.)."""
from __future__ import annotations

import os
from typing import Any

import httpx

from .client_base import LLMClientBase, LLMRequest, LLMResponse


class OpenAICompatibleClient(LLMClientBase):
    """Chat completions via any OpenAI-compatible API."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.openai.com/v1",
        timeout: int = 60,
        _http_client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._http_client = _http_client

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self._base_url}/chat/completions"
        if self._http_client is not None:
            resp = self._http_client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()

    def complete(self, request: LLMRequest) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": request.model,
            "messages": [m.model_dump() for m in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        raw = self._post(payload)
        text = raw.get("choices", [{}])[0].get("message", {}).get("content", "")
        return LLMResponse(
            text=text,
            raw=raw,
            model=raw.get("model"),
            usage=raw.get("usage", {}),
        )
