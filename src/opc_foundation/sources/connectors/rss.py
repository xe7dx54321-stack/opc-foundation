"""RSS connector via feedparser – hardened for robustness."""
from __future__ import annotations

from typing import Any

import feedparser

from ...run.id_generator import new_id
from ...run.run_context import RunContext
from ...run.time_utils import utcnow_iso
from ...signals.dedupe import hash_url, hash_text
from ...signals.raw_signal_schema import RawSignal
from ..source_schema import FetchResult, SourceDefinition, SourceQuery


class RssConnector:
    """Fetch entries from an RSS/Atom feed."""

    connector_id = "rss"

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

        feed_url = (
            query.url
            or source.base_url
            or query.metadata.get("feed_url")
        )
        if not feed_url:
            warnings.append("RSS connector: no feed_url provided – returning empty result")
            return FetchResult(
                source_id=source.source_id,
                connector=self.connector_id,
                warnings=warnings,
                fetched_at=now,
            )

        try:
            parsed = feedparser.parse(feed_url)
            if parsed.get("bozo"):
                bozo_exc = parsed.get("bozo_exception")
                if bozo_exc:
                    warnings.append(f"RSS bozo warning: {bozo_exc}")
            if not parsed.get("entries"):
                if parsed.get("bozo"):
                    errors.append(f"RSS feed parse failed (no entries): {feed_url}")
                # Empty feed is not a failure
        except Exception as exc:
            errors.append(f"RSS fetch error: {exc}")
            return FetchResult(
                source_id=source.source_id,
                connector=self.connector_id,
                errors=errors,
                warnings=warnings,
                fetched_at=now,
            )

        feed_title: str = parsed.get("feed", {}).get("title") or source.source_name or ""
        entries = list(parsed.get("entries", []))[: query.max_items]

        for entry in entries:
            title = entry.get("title") or ""
            # Fallback chain: summary -> description -> title
            summary = (
                entry.get("summary")
                or entry.get("description")
                or title
            )
            link = entry.get("link") or ""
            published = entry.get("published") or entry.get("updated") or ""
            text = f"{title}\n\n{summary}".strip() if summary else (title or link)

            # source_note acts as fallback when link is missing
            source_note = feed_url if not link else None

            sig = RawSignal(
                signal_id=new_id("sig_"),
                source_id=source.source_id,
                source_type=source.source_type,
                source_name=feed_title or source.source_name,
                source_url=link or None,
                source_note=source_note,
                title=title or None,
                raw_text=text,
                published_at=published or None,
                fetched_at=now,
                collection_query=query.query,
                collector=self.connector_id,
                url_hash=hash_url(link) if link else None,
                content_hash=hash_text(text),
                metadata={"feed_url": feed_url},
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