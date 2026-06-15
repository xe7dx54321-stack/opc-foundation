"""Core source data contracts."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from ..signals.raw_signal_schema import RawSignal


class SourceQuery(BaseModel):
    query_id: str
    source_id: str
    query: str | None = None
    url: str | None = None
    tags: list[str] = []
    max_items: int = 50
    metadata: dict[str, Any] = {}


class SourceDefinition(BaseModel):
    source_id: str
    source_name: str
    source_type: str

    connector: str
    enabled: bool = True

    base_url: str | None = None
    requires_api_key: bool = False
    api_key_env: str | None = None

    default_queries: list[str] = []
    tags: list[str] = []

    trust_weight: float = 0.5
    notes: str | None = None

    metadata: dict[str, Any] = {}


class FetchResult(BaseModel):
    source_id: str
    connector: str

    raw_signals: list[RawSignal] = []
    errors: list[str] = []
    warnings: list[str] = []

    fetched_at: str
    metadata: dict[str, Any] = {}
