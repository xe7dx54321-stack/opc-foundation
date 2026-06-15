"""LLM data contracts and abstract base."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class LLMMessage(BaseModel):
    role: str
    content: str


class LLMRequest(BaseModel):
    model: str
    messages: list[LLMMessage]
    temperature: float = 0.0
    max_tokens: int = 4000
    metadata: dict[str, Any] = {}


class LLMResponse(BaseModel):
    text: str
    raw: dict[str, Any] = {}
    model: str | None = None
    usage: dict[str, Any] = {}


class LLMClientBase(ABC):
    """Abstract base for LLM provider clients."""

    @abstractmethod
    def complete(self, request: LLMRequest) -> LLMResponse:
        ...
