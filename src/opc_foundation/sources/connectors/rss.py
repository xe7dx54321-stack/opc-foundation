"""RSS connector via feedparser."""
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
        raw_signals: list[RawSignal] = []

        feed_url = query.url or source.base_url or query.metadata.get("feed_url")
        if not feed_url:
            return FetchResult(
                source_id=source.source_id,
                connector=self.connector_id,
                errors=["No feed_url provided (set query.url or source.base_url)"],
                fetched_at=utcnow_iso(),
            )

        try:
            parsed = feedparser.parse(feed_url)
            if parsed.get("bozo") and not parsed.get("entries"):
                errors.append(f"Feed parse warning: {parsed.get('bozo_exception')}")
        except Exception as exc:
            errors.append(f"RSS fetch error: {exc}")
            return FetchResult(
                source_id=source.source_id,
                connector=self.connector_id,
                errors=errors,
                fetched_at=utcnow_iso(),
            )

        feed_title: str = parsed.get("feed", {}).get("title", source.source_name or "")
        now = utcnow_iso()

        entries = parsed.get("entries", [])[: query.max_items]
        for entry in entries:
            title = entry.get("title") or ""
            summary = entry.get("summary") or ""
            link = entry.get("link") or ""
            published = entry.get("published") or entry.get("updated") or ""
            text = f"{title}\n\n{summary}".strip() or link

            sig = RawSignal(
                signal_id=new_id("sig_"),
                source_id=source.source_id,
                source_type=source.source_type,
                source_name=feed_title or source.source_name,
                source_url=link or None,
                source_note=feed_url if not link else None,
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
            fetched_at=now,
        )
