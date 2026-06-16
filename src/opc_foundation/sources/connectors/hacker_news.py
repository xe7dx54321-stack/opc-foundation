"""Hacker News connector via Algolia Search API.

No API key required. Uses: https://hn.algolia.com/api/v1/search
"""
from __future__ import annotations

from typing import Any

import httpx

from ...run.id_generator import new_id
from ...run.run_context import RunContext
from ...run.time_utils import utcnow_iso
from ...signals.dedupe import hash_url, hash_text
from ...signals.raw_signal_schema import RawSignal
from ..http_utils import http_get_with_retry
from ..source_schema import FetchResult, SourceDefinition, SourceQuery

_ALGOLIA_SEARCH = "https://hn.algolia.com/api/v1/search"


class HackerNewsConnector:
    """Fetch HN stories matching a query via Algolia Search API."""

    connector_id = "hacker_news"

    def __init__(
        self,
        timeout: int = 15,
        max_retries: int = 2,
        _http_client: httpx.Client | None = None,
    ) -> None:
        self._timeout = timeout
        self._max_retries = max_retries
        self._http_client = _http_client

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

        search_query = (query.query or "").strip()
        if not search_query:
            warnings.append("HN connector: no query provided – returning empty result")
            return FetchResult(
                source_id=source.source_id,
                connector=self.connector_id,
                warnings=warnings,
                fetched_at=now,
            )

        data, fetch_errors = http_get_with_retry(
            _ALGOLIA_SEARCH,
            params={
                "query": search_query,
                "hitsPerPage": min(query.max_items, 50),
                "tags": "story",
            },
            timeout=self._timeout,
            max_retries=self._max_retries,
            http_client=self._http_client,
        )

        for fe in fetch_errors:
            if fe.error_type in ("rate_limit", "access_denied"):
                warnings.append(f"HN [{fe.error_type}] {fe.message}")
            else:
                errors.append(f"HN fetch error [{fe.error_type}]: {fe.message}")

        if data is None:
            return FetchResult(
                source_id=source.source_id,
                connector=self.connector_id,
                errors=errors,
                warnings=warnings,
                fetched_at=now,
            )

        hits: list[dict[str, Any]] = data.get("hits", [])

        for hit in hits[: query.max_items]:
            text = (
                hit.get("story_text")
                or hit.get("comment_text")
                or hit.get("title")
                or ""
            )
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
                    "item_id": hit.get("objectID"),
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
            warnings=warnings,
            fetched_at=now,
        )