"""Trafilatura-based URL text extractor."""
from __future__ import annotations

import trafilatura

from .url_text_extractor import ExtractedPage
from ..run.time_utils import utcnow_iso


class TrafilaturaExtractor:
    """Extracts page text via trafilatura."""

    def __init__(self, timeout: int = 30, favor_recall: bool = True) -> None:
        self.timeout = timeout
        self.favor_recall = favor_recall

    def extract(self, url: str) -> ExtractedPage:
        errors: list[str] = []
        title: str | None = None
        text = ""
        try:
            downloaded = trafilatura.fetch_url(url)
            if downloaded is None:
                errors.append(f"Failed to download: {url}")
                return ExtractedPage(url=url, text="", errors=errors, fetched_at=utcnow_iso())

            metadata = trafilatura.extract_metadata(downloaded)
            if metadata:
                title = metadata.title

            text = trafilatura.extract(
                downloaded,
                favor_recall=self.favor_recall,
                include_comments=False,
                include_tables=True,
            ) or ""

            if not text.strip():
                errors.append(f"No text extracted from: {url}")
        except Exception as exc:
            errors.append(f"Extraction error for {url}: {exc}")
            text = ""

        return ExtractedPage(
            url=url,
            title=title,
            text=text,
            errors=errors,
            fetched_at=utcnow_iso(),
        )
