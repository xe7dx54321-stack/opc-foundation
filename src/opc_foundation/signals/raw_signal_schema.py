"""RawSignal – the canonical cross-project signal contract."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, model_validator


class RawSignal(BaseModel):
    signal_id: str

    source_id: str
    source_type: str
    source_name: str | None = None

    source_url: str | None = None
    source_note: str | None = None

    title: str | None = None
    raw_text: str

    language: str | None = None
    published_at: str | None = None
    fetched_at: str

    author_or_org: str | None = None

    collection_query: str | None = None
    collector: str | None = None

    metadata: dict[str, Any] = {}

    content_hash: str | None = None
    url_hash: str | None = None

    @model_validator(mode="after")
    def check_source_url_or_note(self) -> "RawSignal":
        if not self.source_url and not self.source_note:
            raise ValueError("At least one of source_url or source_note must be set.")
        if not self.raw_text:
            raise ValueError("raw_text must not be empty.")
        return self
