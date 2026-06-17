"""Test SearchProviderRegistry."""
import os
import pytest
from unittest.mock import MagicMock
from opc_foundation.search import SearchProviderRegistry, SearchQuery, SearchRunResult
from opc_foundation.run.time_utils import utcnow_iso


def _fake_client(name, available=True, results=None):
    client = MagicMock()
    client.provider_name = name
    client.is_available.return_value = available
    client.search.return_value = SearchRunResult(
        run_id="r1", provider=name, query="test",
        results=results or [], started_at=utcnow_iso()
    )
    return client


def test_preferred_provider_priority():
    brave = _fake_client("brave", available=True)
    tavily = _fake_client("tavily", available=True)
    reg = SearchProviderRegistry({"brave": brave, "tavily": tavily})
    preferred = reg.get_preferred_provider()
    assert preferred.provider_name == "tavily"


def test_no_provider_available_returns_error():
    reg = SearchProviderRegistry({})
    q = SearchQuery(query="test")
    result = reg.search(q)
    assert len(result.errors) > 0
    assert "No search provider" in result.errors[0]


def test_named_provider_not_registered_returns_error():
    reg = SearchProviderRegistry({})
    q = SearchQuery(query="test")
    result = reg.search(q, provider_name="tavily")
    assert len(result.errors) > 0


def test_from_env_no_keys():
    for k in ["TAVILY_API_KEY", "BRAVE_SEARCH_API_KEY"]:
        os.environ.pop(k, None)
    reg = SearchProviderRegistry.from_env()
    assert reg.get_preferred_provider() is None


def test_from_env_with_tavily():
    os.environ["TAVILY_API_KEY"] = "fake"
    try:
        reg = SearchProviderRegistry.from_env()
        assert "tavily" in reg.available_providers()
    finally:
        os.environ.pop("TAVILY_API_KEY", None)


def test_search_uses_preferred():
    client = _fake_client("tavily")
    reg = SearchProviderRegistry({"tavily": client})
    q = SearchQuery(query="test")
    result = reg.search(q)
    assert result.provider == "tavily"
    client.search.assert_called_once()