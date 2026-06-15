"""URLTextExtractor protocol and ExtractedPage schema."""
from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel

from ..run.time_utils import utcnow_iso


class ExtractedPage(BaseModel):
    url: str
    title: str | None = None
    text: str = ""
    metadata: dict[str, Any] = {}
    fetched_at: str = ""
    errors: list[str] = []

    def model_post_init(self, __context: Any) -> None:
        if not self.fetched_at:
            self.fetched_at = utcnow_iso()


class URLTextExtractor(Protocol):
    """Protocol for URL text extraction backends."""

    def extract(self, url: str) -> ExtractedPage:
        ...
