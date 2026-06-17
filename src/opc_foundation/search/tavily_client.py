"""Tavily Search API client."""
from __future__ import annotations
import os
from typing import Any
import httpx
from ..run.id_generator import new_id
from ..run.time_utils import utcnow_iso
from ..sources.http_utils import http_get_with_retry
from .search_schema import SearchQuery, SearchResult, SearchRunResult
from .search_result_normalizer import extract_domain

_TAVILY_URL = "https://api.tavily.com/search"


class TavilyClient:
    provider_name = "tavily"

    def __init__(
        self,
        api_key: str | None = None,
        timeout: int = 20,
        max_retries: int = 2,
        _http_client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("TAVILY_API_KEY", "")
        self._timeout = timeout
        self._max_retries = max_retries
        self._http_client = _http_client

    def is_available(self) -> bool:
        return bool(self._api_key)

    def _post(self, payload: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        errors: list[str] = []
        import time
        for attempt in range(self._max_retries + 1):
            try:
                if self._http_client is not None:
                    resp = self._http_client.post(_TAVILY_URL, json=payload)
                else:
                    with httpx.Client(timeout=self._timeout) as client:
                        resp = client.post(_TAVILY_URL, json=payload)
                if resp.status_code == 401:
                    errors.append("Tavily: invalid API key (401)")
                    return None, errors
                if resp.status_code == 429:
                    errors.append("Tavily: rate limit (429)")
                    if attempt < self._max_retries:
                        time.sleep(1.5 ** attempt)
                        continue
                    return None, errors
                resp.raise_for_status()
                return resp.json(), []
            except httpx.TimeoutException:
                errors.append(f"Tavily: timeout (attempt {attempt+1})")
                if attempt < self._max_retries:
                    time.sleep(1.5 ** attempt)
            except Exception as exc:
                errors.append(f"Tavily: error: {exc}")
                return None, errors
        return None, errors

    def search(self, query: SearchQuery) -> SearchRunResult:
        started = utcnow_iso()
        run_id = new_id("sr_")

        if not self.is_available():
            return SearchRunResult(
                run_id=run_id, provider=self.provider_name, query=query.query,
                errors=["Tavily not available: TAVILY_API_KEY not set"],
                started_at=started, finished_at=utcnow_iso(),
            )

        payload: dict[str, Any] = {
            "api_key": self._api_key,
            "query": query.query,
            "max_results": query.max_results,
            "search_depth": "basic",
        }
        if query.freshness_days:
            payload["days"] = query.freshness_days

        data, errors = self._post(payload)
        results: list[SearchResult] = []

        if data:
            raw_results = data.get("results") or []
            for rank, item in enumerate(raw_results[: query.max_results], start=1):
                url = item.get("url", "")
                results.append(SearchResult(
                    result_id=new_id("r_"),
                    provider=self.provider_name,
                    query=query.query,
                    title=item.get("title"),
                    url=url,
                    snippet=item.get("content") or item.get("snippet"),
                    published_at=item.get("published_date"),
                    rank=rank,
                    result_domain=extract_domain(url),
                    raw_provider_payload=item,
                    fetched_at=utcnow_iso(),
                ))

        return SearchRunResult(
            run_id=run_id, provider=self.provider_name, query=query.query,
            results=results, errors=errors,
            started_at=started, finished_at=utcnow_iso(),
        )