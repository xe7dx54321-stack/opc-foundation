"""Manual URL batch connector – hardened for robustness."""
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
from ...web.url_validator import validate_url, URLValidationError
from ..source_schema import FetchResult, SourceDefinition, SourceQuery


class ManualUrlConnector:
    """Fetch and extract text from a CSV list of URLs."""

    connector_id = "manual_url"

    def __init__(self, extractor: URLTextExtractor | None = None) -> None:
        self._extractor = extractor

    def fetch(
        self,
        query: SourceQuery,
        source: SourceDefinition,
        context: RunContext,
    ) -> FetchResult:
        errors: list[str] = []
        warnings: list[str] = []
        raw_signals: list[RawSignal] = []
        now = utcnow_iso()

        csv_path = query.url or query.metadata.get("csv_path")

        if not csv_path:
            warnings.append("ManualURL connector: no csv_path provided – returning empty result")
            return FetchResult(
                source_id=source.source_id,
                connector=self.connector_id,
                warnings=warnings,
                fetched_at=now,
            )

        if not Path(str(csv_path)).exists():
            errors.append(f"ManualURL connector: CSV not found: {csv_path}")
            return FetchResult(
                source_id=source.source_id,
                connector=self.connector_id,
                errors=errors,
                fetched_at=now,
            )

        rows = CsvStore.load_csv_dicts(csv_path)

        for row_idx, row in enumerate(rows[: query.max_items]):
            url = (row.get("url") or "").strip()
            if not url:
                warnings.append(f"Row {row_idx}: missing url – skipping")
                continue

            title = row.get("title") or None
            source_type = row.get("source_type") or source.source_type
            source_name = row.get("source_name") or source.source_name
            collection_query = row.get("collection_query") or query.query
            notes = row.get("notes") or None

            # 校验 URL 安全性（SSRF 防护）
            try:
                validate_url(url)
            except URLValidationError as exc:
                errors.append(f"Row {row_idx} [{url}]: URL validation failed: {exc}")
                continue

            text = ""
            if self._extractor is not None:
                try:
                    page: ExtractedPage = self._extractor.extract(url)
                    text = page.text
                    if not title:
                        title = page.title
                    for err in page.errors:
                        errors.append(f"Row {row_idx} [{url}]: {err}")
                except Exception as exc:
                    errors.append(f"Row {row_idx} [{url}]: extractor error: {exc}")

            # Fallback chain: extractor text -> notes -> url
            if not text.strip():
                text = notes or url

            sig = RawSignal(
                signal_id=new_id("sig_"),
                source_id=source.source_id,
                source_type=source_type,
                source_name=source_name,
                source_url=url,
                source_note=notes,
                title=title,
                raw_text=text,
                fetched_at=now,
                collection_query=collection_query,
                collector=self.connector_id,
                url_hash=hash_url(url),
                content_hash=hash_text(text),
                metadata={"csv_row_index": row_idx},
            )
            raw_signals.append(sig)

        return FetchResult(
            source_id=source.source_id,
            connector=self.connector_id,
            raw_signals=raw_signals,
            errors=errors,
            warnings=warnings,
            fetched_at=now,
        )