"""Hacker News connector via Algolia Search API.

No API key required. Uses: http://hn.algolia.com/api/v1/search
"""
from __future__ import annotations

from typing import Any

import httpx

from ...run.id_generator import new_id
from ...run.run_context import RunContext
from ...run.time_utils import utcnow_iso
from ...signals.dedupe import hash_url, hash_text
from ...signals.raw_signal_schema import RawSignal
from ..source_schema import FetchResult, SourceDefinition, SourceQuery

_ALGOLIA_SEARCH = "https://hn.algolia.com/api/v1/search"


class HackerNewsConnector:
    """Fetch HN stories/comments matching a query via Algolia."""

    connector_id = "hacker_news"

    def __init__(self, timeout: int = 20, _http_client: httpx.Client | None = None) -> None:
        self._timeout = timeout
        self._http_client = _http_client

    def _get(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        if self._http_client is not None:
            resp = self._http_client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()

    def fetch(
        self,
        query: SourceQuery,
        source: SourceDefinition,
        context: RunContext,
    ) -> FetchResult:
        errors: list[str] = []
        raw_signals: list[RawSignal] = []

        search_query = query.query or ""
        if not search_query:
            return FetchResult(
                source_id=source.source_id,
                connector=self.connector_id,
                errors=["No query provided"],
                fetched_at=utcnow_iso(),
            )

        try:
            data = self._get(
                _ALGOLIA_SEARCH,
                {
                    "query": search_query,
                    "hitsPerPage": min(query.max_items, 50),
                    "tags": "story",
                },
            )
            hits: list[dict[str, Any]] = data.get("hits", [])
        except Exception as exc:
            errors.append(f"HN fetch error: {exc}")
            return FetchResult(
                source_id=source.source_id,
                connector=self.connector_id,
                errors=errors,
                fetched_at=utcnow_iso(),
            )

        now = utcnow_iso()
        for hit in hits[: query.max_items]:
            text = hit.get("story_text") or hit.get("comment_text") or hit.get("title") or ""
            title = hit.get("title")
            url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"

            if not text.strip():
                text = title or url

            sig = RawSignal(
                signal_id=new_id("sig_"),
                source_id=source.source_id,
                source_type=source.source_type,
                source_name=source.source_name,
                source_url=url,
                title=title,
                raw_text=text,
                author_or_org=hit.get("author"),
                published_at=hit.get("created_at"),
                fetched_at=now,
                collection_query=search_query,
                collector=self.connector_id,
                url_hash=hash_url(url),
                content_hash=hash_text(text),
                metadata={
                    "objectID": hit.get("objectID"),
                    "num_comments": hit.get("num_comments"),
                    "points": hit.get("points"),
                },
            )
            raw_signals.append(sig)

        return FetchResult(
            source_id=source.source_id,
            connector=self.connector_id,
            raw_signals=raw_signals,
            errors=errors,
            fetched_at=now,
        )
