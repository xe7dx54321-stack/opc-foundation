"""Test HackerNews connector with mocked HTTP."""
from unittest.mock import MagicMock
import httpx
import pytest
from opc_foundation.sources.connectors.hacker_news import HackerNewsConnector
from opc_foundation.sources.source_schema import SourceQuery, SourceDefinition
from opc_foundation.run.run_context import RunContext


def _make_mock_client(hits):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"hits": hits}
    mock_resp.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.get.return_value = mock_resp
    return mock_client


def _source():
    return SourceDefinition(
        source_id="hn", source_name="HN", source_type="community_discussion", connector="hacker_news"
    )


def _ctx():
    return RunContext(pipeline_name="test")


SAMPLE_HITS = [
    {
        "objectID": "12345",
        "title": "Show HN: AI tool",
        "url": "https://example.com/ai-tool",
        "author": "alice",
        "created_at": "2026-01-01T00:00:00Z",
        "num_comments": 42,
        "points": 300,
        "story_text": None,
    }
]


def test_fetch_returns_signals():
    mock_client = _make_mock_client(SAMPLE_HITS)
    connector = HackerNewsConnector(_http_client=mock_client)
    q = SourceQuery(query_id="q1", source_id="hn", query="AI tool", max_items=10)
    result = connector.fetch(q, _source(), _ctx())
    assert len(result.raw_signals) == 1
    sig = result.raw_signals[0]
    assert sig.title == "Show HN: AI tool"
    assert sig.source_url == "https://example.com/ai-tool"
    assert sig.author_or_org == "alice"
    assert result.errors == []


def test_no_query_returns_error():
    connector = HackerNewsConnector()
    q = SourceQuery(query_id="q1", source_id="hn", query=None, max_items=5)
    result = connector.fetch(q, _source(), _ctx())
    assert len(result.errors) > 0
    assert len(result.raw_signals) == 0


def test_http_failure_does_not_raise():
    mock_client = MagicMock()
    mock_client.get.side_effect = Exception("network error")
    connector = HackerNewsConnector(_http_client=mock_client)
    q = SourceQuery(query_id="q1", source_id="hn", query="AI", max_items=5)
    result = connector.fetch(q, _source(), _ctx())
    assert len(result.errors) > 0
    assert len(result.raw_signals) == 0


def test_max_items_respected():
    hits = [dict(SAMPLE_HITS[0], objectID=str(i), title=f"Story {i}", url=f"https://hn.com/{i}") for i in range(20)]
    mock_client = _make_mock_client(hits)
    connector = HackerNewsConnector(_http_client=mock_client)
    q = SourceQuery(query_id="q1", source_id="hn", query="AI", max_items=5)
    result = connector.fetch(q, _source(), _ctx())
    assert len(result.raw_signals) <= 5
