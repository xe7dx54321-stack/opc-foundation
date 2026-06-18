"""GitHub Issues connector via GitHub REST Search API.

Supports optional GITHUB_TOKEN for higher rate limits.
Preserves rate-limit headers in FetchResult metadata.
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
from ..http_utils import http_get_with_retry, HTTPFetchError, classify_http_error
from ..source_schema import FetchResult, SourceDefinition, SourceQuery

_GH_SEARCH = "https://api.github.com/search/issues"


class GitHubIssuesConnector:
    """Search GitHub Issues/PRs matching a query."""

    connector_id = "github_issues"

    def __init__(
        self,
        timeout: int = 15,
        max_retries: int = 2,
        _http_client: httpx.Client | None = None,
    ) -> None:
        self._timeout = timeout
        self._max_retries = max_retries
        self._http_client = _http_client

    def _headers(self) -> dict[str, str]:
        token = os.environ.get("GITHUB_TOKEN")
        h: dict[str, str] = {"Accept": "application/vnd.github+json"}
        if token:
            h["Authorization"] = f"Bearer {token}"
        return h

    def _fetch_raw(
        self, q: str, max_items: int
    ) -> tuple[dict[str, Any] | None, list[HTTPFetchError], dict[str, str]]:
        """Return (json_data, errors, response_headers_subset)."""
        headers = self._headers()
        rate_headers: dict[str, str] = {}

        # We need response headers for rate-limit info, so use httpx directly
        # but wrap in our retry/error logic.
        last_resp: httpx.Response | None = None
        import time

        for attempt in range(self._max_retries + 1):
            try:
                if self._http_client is not None:
                    resp = self._http_client.get(
                        _GH_SEARCH,
                        params={"q": q, "per_page": min(max_items, 100), "sort": "updated"},
                        headers=headers,
                    )
                else:
                    with httpx.Client(timeout=self._timeout) as client:
                        resp = client.get(
                            _GH_SEARCH,
                            params={"q": q, "per_page": min(max_items, 100), "sort": "updated"},
                            headers=headers,
                        )
                last_resp = resp
                rate_headers = {
                    k: v
                    for k, v in resp.headers.items()
                    if "rate" in k.lower() or "x-ratelimit" in k.lower()
                }
                if resp.status_code in (403, 429):
                    err_type = "rate_limit" if resp.status_code == 429 else "access_denied"
                    fe = HTTPFetchError(
                        status_code=resp.status_code,
                        error_type=err_type,
                        message=f"HTTP {resp.status_code} from GitHub Search API",
                    )
                    if resp.status_code == 403 or attempt >= self._max_retries:
                        return None, [fe], rate_headers
                    time.sleep(1.5 ** attempt)
                    continue
                resp.raise_for_status()
                return resp.json(), [], rate_headers
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
                code = getattr(getattr(exc, "response", None), "status_code", None)
                fe = HTTPFetchError(
                    status_code=code,
                    error_type=classify_http_error(exc, code),
                    message=str(exc),
                )
                if attempt < self._max_retries:
                    time.sleep(1.5 ** attempt)
                else:
                    return None, [fe], rate_headers
            except Exception as exc:
                return None, [HTTPFetchError(error_type="unknown", message=str(exc))], rate_headers

        return None, [], rate_headers

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
            warnings.append("GitHub Issues connector: no query provided – returning empty result")
            return FetchResult(
                source_id=source.source_id,
                connector=self.connector_id,
                warnings=warnings,
                fetched_at=now,
            )

        q = f"{search_query} is:issue"
        data, fetch_errors, rate_headers = self._fetch_raw(q, query.max_items)

        for fe in fetch_errors:
            if fe.error_type in ("rate_limit", "access_denied"):
                warnings.append(f"GitHub [{fe.error_type}] {fe.message}")
            else:
                errors.append(f"GitHub fetch error [{fe.error_type}]: {fe.message}")

        if data is None:
            return FetchResult(
                source_id=source.source_id,
                connector=self.connector_id,
                errors=errors,
                warnings=warnings,
                fetched_at=now,
                metadata={"rate_limit_headers": rate_headers},
            )

        items: list[dict[str, Any]] = data.get("items", [])

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
                    "github_issue_id": item.get("id"),
                    "rate_limit_remaining": rate_headers.get("x-ratelimit-remaining"),
                    "rate_limit_reset": rate_headers.get("x-ratelimit-reset"),
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
            metadata={"rate_limit_headers": rate_headers},
        )