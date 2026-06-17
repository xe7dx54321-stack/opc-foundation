"""Test BraveClient with mocked HTTP."""
import os
import pytest
from unittest.mock import MagicMock, patch
import httpx
from opc_foundation.search.brave_client import BraveClient
from opc_foundation.search.search_schema import SearchQuery

_MOCK_BRAVE_RESPONSE = {
    "web": {
        "results": [
            {"title": "Research Automation", "url": "https://automate.io/research",
             "description": "Automate research workflows."},
            {"title": "AI Tools 2026", "url": "https://aitools.io/2026",
             "description": "Best AI tools."},
        ]
    }
}


def _mock_http(status=200, json_data=None):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = json_data or _MOCK_BRAVE_RESPONSE
    resp.raise_for_status = MagicMock()
    client = MagicMock()
    client.get.return_value = resp
    return client


def test_unavailable_without_key():
    os.environ.pop("BRAVE_SEARCH_API_KEY", None)
    c = BraveClient(api_key="")
    assert not c.is_available()


def test_available_with_key():
    c = BraveClient(api_key="fake-brave-key")
    assert c.is_available()


def test_search_returns_results():
    c = BraveClient(api_key="fake", _http_client=_mock_http())
    q = SearchQuery(query="AI tools", max_results=5)
    result = c.search(q)
    assert result.provider == "brave"
    assert len(result.results) == 2
    assert result.errors == []


def test_search_without_key_returns_error():
    c = BraveClient(api_key="")
    result = c.search(SearchQuery(query="test"))
    assert len(result.errors) > 0


def test_network_error_does_not_raise():
    mock_client = MagicMock()
    mock_client.get.side_effect = httpx.NetworkError("down")
    c = BraveClient(api_key="fake", _http_client=mock_client, max_retries=0)
    result = c.search(SearchQuery(query="test"))
    assert len(result.errors) > 0