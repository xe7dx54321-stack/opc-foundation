"""Anthropic Messages API client."""
from __future__ import annotations

import os
from typing import Any

import httpx

from .client_base import LLMClientBase, LLMRequest, LLMResponse

_ANTHROPIC_API = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_VERSION = "2023-06-01"


class AnthropicCompatibleClient(LLMClientBase):
    """Chat completions via Anthropic Messages API."""

    def __init__(
        self,
        api_key: str | None = None,
        timeout: int = 60,
        _http_client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._timeout = timeout
        self._http_client = _http_client

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": _ANTHROPIC_VERSION,
            "Content-Type": "application/json",
        }
        if self._http_client is not None:
            resp = self._http_client.post(_ANTHROPIC_API, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(_ANTHROPIC_API, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()

    def complete(self, request: LLMRequest) -> LLMResponse:
        system_msgs = [m for m in request.messages if m.role == "system"]
        user_msgs = [m for m in request.messages if m.role != "system"]
        payload: dict[str, Any] = {
            "model": request.model,
            "messages": [{"role": m.role, "content": m.content} for m in user_msgs],
            "max_tokens": request.max_tokens,
        }
        if system_msgs:
            payload["system"] = system_msgs[0].content
        raw = self._post(payload)
        text = ""
        for block in raw.get("content", []):
            if block.get("type") == "text":
                text += block.get("text", "")
        return LLMResponse(
            text=text,
            raw=raw,
            model=raw.get("model"),
            usage=raw.get("usage", {}),
        )
