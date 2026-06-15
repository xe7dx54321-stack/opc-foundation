"""Manual URL batch connector.

Reads a CSV with columns: url, source_type, source_name, title, collection_query, notes
Extracts text from each URL using the provided extractor and returns RawSignal objects.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ...run.id_generator import new_id
from ...run.run_context import RunContext
from ...run.time_utils import utcnow_iso
from ...signals.dedupe import hash_url, hash_text
from ...signals.raw_signal_schema import RawSignal
from ...storage.csv_store import CsvStore
from ...web.url_text_extractor import URLTextExtractor, ExtractedPage
from ..source_schema import FetchResult, SourceDefinition, SourceQuery


class ManualUrlConnector:
    """Fetches and extracts text from a CSV list of URLs."""

    connector_id = "manual_url"

    def __init__(self, extractor: URLTextExtractor | None = None) -> None:
        self._extractor = extractor

    def fetch(
        self,
        query: SourceQuery,
        source: SourceDefinition,
        context: RunContext,
    ) -> FetchResult:
        csv_path = query.url or query.metadata.get("csv_path")
        errors: list[str] = []
        raw_signals: list[RawSignal] = []

        if not csv_path or not Path(str(csv_path)).exists():
            return FetchResult(
                source_id=source.source_id,
                connector=self.connector_id,
                raw_signals=[],
                errors=[f"CSV path not found: {csv_path}"],
                fetched_at=utcnow_iso(),
            )

        rows = CsvStore.load_csv_dicts(csv_path)

        for i, row in enumerate(rows[: query.max_items]):
            url = (row.get("url") or "").strip()
            if not url:
                errors.append(f"Row {i}: missing url")
                continue

            title = row.get("title") or None
            source_type = row.get("source_type") or source.source_type
            source_name = row.get("source_name") or source.source_name
            collection_query = row.get("collection_query") or query.query
            notes = row.get("notes") or None

            text = ""
            page_errors: list[str] = []
            if self._extractor is not None:
                try:
                    page: ExtractedPage = self._extractor.extract(url)
                    text = page.text
                    if not title:
                        title = page.title
                    page_errors = page.errors
                except Exception as exc:
                    page_errors = [f"extractor error for {url}: {exc}"]
            else:
                text = notes or url

            if not text.strip():
                text = notes or url

            errors.extend(page_errors)

            sig = RawSignal(
                signal_id=new_id("sig_"),
                source_id=source.source_id,
                source_type=source_type,
                source_name=source_name,
                source_url=url,
                source_note=notes,
                title=title,
                raw_text=text,
                fetched_at=utcnow_iso(),
                collection_query=collection_query,
                collector=self.connector_id,
                url_hash=hash_url(url),
                content_hash=hash_text(text),
            )
            raw_signals.append(sig)

        return FetchResult(
            source_id=source.source_id,
            connector=self.connector_id,
            raw_signals=raw_signals,
            errors=errors,
            fetched_at=utcnow_iso(),
        )
