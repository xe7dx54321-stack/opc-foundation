"""Structured LLM runner (Pydantic model output)."""
from __future__ import annotations

import json
from typing import Type, TypeVar

from pydantic import BaseModel

from .client_base import LLMClientBase, LLMRequest, LLMMessage

T = TypeVar("T", bound=BaseModel)


class StructuredRunner:
    """Run an LLM request and parse the response into a Pydantic model."""

    def __init__(self, client: LLMClientBase) -> None:
        self._client = client

    def run(self, request: LLMRequest, model_cls: Type[T]) -> T:
        response = self._client.complete(request)
        data = json.loads(response.text)
        return model_cls.model_validate(data)
