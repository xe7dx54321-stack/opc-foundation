"""Prompt version metadata."""
from __future__ import annotations

from pydantic import BaseModel


class PromptMetadata(BaseModel):
    prompt_id: str
    version: str
    description: str | None = None
    model_hint: str | None = None
    tags: list[str] = []
