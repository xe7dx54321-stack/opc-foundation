"""GitHub Issues connector via GitHub REST Search API.

Supports optional GITHUB_TOKEN for higher rate limits.
"""
from __future__ import annotations

import os
from typing import Any

import httpx

from ...run.id_generator import new_id
from ...run.run_context import RunContext
from ...run.time_utils import utcnow_iso
from ...signals.dedupe import hash_url, hash_text
from ...signals.raw_signal_schema import RawSignal
from ..source_schema import FetchResult, SourceDefinition, SourceQuery

_GH_SEARCH = "https://api.github.com/search/issues"


class GitHubIssuesConnector:
    """Search GitHub Issues/PRs matching a query."""

    connector_id = "github_issues"

    def __init__(self, timeout: int = 20, _http_client: httpx.Client | None = None) -> None:
        self._timeout = timeout
        self._http_client = _http_client

    def _headers(self) -> dict[str, str]:
        token = os.environ.get("GITHUB_TOKEN")
        h: dict[str, str] = {"Accept": "application/vnd.github+json"}
        if token:
            h["Authorization"] = f"Bearer {token}"
        return h

    def _get(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        headers = self._headers()
        if self._http_client is not None:
            resp = self._http_client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            return resp.json()
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.get(url, params=params, headers=headers)
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

        q = f"{search_query} is:issue"

        try:
            data = self._get(
                _GH_SEARCH,
                {"q": q, "per_page": min(query.max_items, 100), "sort": "updated"},
            )
            items: list[dict[str, Any]] = data.get("items", [])
        except Exception as exc:
            errors.append(f"GitHub Issues fetch error: {exc}")
            return FetchResult(
                source_id=source.source_id,
                connector=self.connector_id,
                errors=errors,
                fetched_at=utcnow_iso(),
            )

        now = utcnow_iso()
        for item in items[: query.max_items]:
            title = item.get("title") or ""
            body = item.get("body") or ""
            text = f"{title}\n\n{body}".strip() or title or item.get("html_url", "")
            url = item.get("html_url", "")
            labels = [lbl.get("name", "") for lbl in item.get("labels", [])]

            sig = RawSignal(
                signal_id=new_id("sig_"),
                source_id=source.source_id,
                source_type=source.source_type,
                source_name=source.source_name,
                source_url=url,
                title=title,
                raw_text=text,
                author_or_org=item.get("user", {}).get("login"),
                published_at=item.get("created_at"),
                fetched_at=now,
                collection_query=search_query,
                collector=self.connector_id,
                url_hash=hash_url(url) if url else None,
                content_hash=hash_text(text),
                metadata={
                    "state": item.get("state"),
                    "comments": item.get("comments"),
                    "labels": labels,
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
