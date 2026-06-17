"""Convenience search runner: registry + normalizer combined."""
from __future__ import annotations
from .search_schema import SearchQuery, SearchRunResult
from .search_provider_registry import SearchProviderRegistry
from .search_result_normalizer import normalize_results


def run_search(
    query: str,
    provider: str | None = None,
    max_results: int = 5,
    normalize: bool = True,
    registry: SearchProviderRegistry | None = None,
) -> SearchRunResult:
    """One-call search: pick provider, search, normalize, return."""
    reg = registry or SearchProviderRegistry.from_env()
    sq = SearchQuery(query=query, provider=provider, max_results=max_results)
    result = reg.search(sq, provider_name=provider)
    if normalize and result.results:
        result.results = normalize_results(result.results)
    return result