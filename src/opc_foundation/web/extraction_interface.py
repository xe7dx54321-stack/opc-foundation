"""Unified web extraction interface – wraps TrafilaturaExtractor by default.

Downstream projects may substitute their own adapter (Firecrawl, Crawl4AI, etc.)
by passing an object that implements extract(url) -> ExtractedPage.
"""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel
from ..run.time_utils import utcnow_iso


class WebExtractionRequest(BaseModel):
    url: str
    preferred_output: str = "text"  # text | markdown | html
    timeout_seconds: int = 20
    metadata: dict[str, Any] = {}


class WebExtractionResult(BaseModel):
    url: str
    success: bool
    title: str | None = None
    text: str | None = None
    markdown: str | None = None
    html: str | None = None

    text_chars: int = 0
    extractor: str = "trafilatura"
    errors: list[str] = []
    warnings: list[str] = []

    fetched_at: str = ""
    metadata: dict[str, Any] = {}

    def model_post_init(self, __context: Any) -> None:
        if not self.fetched_at:
            self.fetched_at = utcnow_iso()
        if self.text:
            self.text_chars = len(self.text)


def extract_page(
    request: WebExtractionRequest,
    adapter=None,
) -> WebExtractionResult:
    """Extract a web page using the given adapter (default: TrafilaturaExtractor).

    Never raises – errors are returned in WebExtractionResult.errors.
    """
    if adapter is None:
        from .trafilatura_extractor import TrafilaturaExtractor
        adapter = TrafilaturaExtractor(timeout=request.timeout_seconds)

    try:
        page = adapter.extract(request.url)
        text = page.text or ""
        return WebExtractionResult(
            url=request.url,
            success=bool(text.strip()),
            title=page.title,
            text=text or None,
            text_chars=len(text),
            extractor=type(adapter).__name__,
            errors=list(page.errors) if page.errors else [],
            fetched_at=utcnow_iso(),
        )
    except Exception as exc:
        return WebExtractionResult(
            url=request.url,
            success=False,
            extractor=type(adapter).__name__ if adapter else "unknown",
            errors=[f"Extraction failed: {exc}"],
            fetched_at=utcnow_iso(),
        )