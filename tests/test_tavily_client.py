"""Test TavilyClient with mocked HTTP."""
import os
import pytest
from unittest.mock import MagicMock, patch
from opc_foundation.search.tavily_client import TavilyClient
from opc_foundation.search.search_schema import SearchQuery

_MOCK_RESPONSE = {
    "results": [
        {"title": "AI Research Tool", "url": "https://aitool.example.io/review",
         "content": "A great tool for research.", "published_date": None},
        {"title": "Research Automation", "url": "https://automate.io/research",
         "content": "Automate your research workflow.", "published_date": "2026-01-01"},
    ]
}


def _mock_http(status=200, json_data=None):
    mock_resp = MagicMock()
    mock_resp.status_code = status
    mock_resp.json.return_value = json_data or _MOCK_RESPONSE
    mock_resp.raise_for_status = MagicMock()
    client = MagicMock()
    client.post.return_value = mock_resp
    return client


def test_unavailable_without_key():
    os.environ.pop("TAVILY_API_KEY", None)
    c = TavilyClient(api_key="")
    assert not c.is_available()


def test_available_with_key():
    c = TavilyClient(api_key="fake-key")
    assert c.is_available()


def test_search_returns_run_result():
    c = TavilyClient(api_key="fake", _http_client=_mock_http())
    q = SearchQuery(query="AI tools", max_results=5)
    result = c.search(q)
    assert result.provider == "tavily"
    assert len(result.results) == 2
    assert result.results[0].title == "AI Research Tool"
    assert result.errors == []


def test_search_respects_max_results():
    c = TavilyClient(api_key="fake", _http_client=_mock_http())
    q = SearchQuery(query="test", max_results=1)
    result = c.search(q)
    assert len(result.results) <= 1


def test_search_without_key_returns_error():
    c = TavilyClient(api_key="")
    q = SearchQuery(query="test")
    result = c.search(q)
    assert len(result.errors) > 0
    assert "TAVILY_API_KEY" in result.errors[0]


def test_search_401_returns_error():
    c = TavilyClient(api_key="bad", _http_client=_mock_http(status=401))
    q = SearchQuery(query="test")
    result = c.search(q)
    assert any("401" in e or "invalid" in e.lower() for e in result.errors)


def test_network_error_does_not_raise():
    mock_client = MagicMock()
    import httpx
    mock_client.post.side_effect = httpx.NetworkError("connection refused")
    c = TavilyClient(api_key="fake", _http_client=mock_client, max_retries=0)
    q = SearchQuery(query="test")
    result = c.search(q)
    assert len(result.errors) > 0
    assert len(result.results) == 0