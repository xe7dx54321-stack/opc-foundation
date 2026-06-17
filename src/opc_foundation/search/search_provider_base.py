"""SearchProviderClient protocol."""
from __future__ import annotations
from typing import Protocol, runtime_checkable
from .search_schema import SearchQuery, SearchRunResult


@runtime_checkable
class SearchProviderClient(Protocol):
    provider_name: str

    def is_available(self) -> bool: ...
    def search(self, query: SearchQuery) -> SearchRunResult: ...