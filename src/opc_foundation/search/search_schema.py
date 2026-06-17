"""Search query and result schemas."""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel


class SearchQuery(BaseModel):
    query: str
    provider: str | None = None
    max_results: int = 5
    locale: str | None = None
    freshness_days: int | None = None
    metadata: dict[str, Any] = {}


class SearchResult(BaseModel):
    result_id: str
    provider: str
    query: str

    title: str | None = None
    url: str
    snippet: str | None = None
    published_at: str | None = None
    rank: int

    result_domain: str | None = None
    raw_provider_payload: dict[str, Any] = {}

    fetched_at: str
    metadata: dict[str, Any] = {}


class SearchRunResult(BaseModel):
    run_id: str
    provider: str
    query: str

    results: list[SearchResult] = []
    errors: list[str] = []
    warnings: list[str] = []

    started_at: str
    finished_at: str | None = None
    metadata: dict[str, Any] = {}