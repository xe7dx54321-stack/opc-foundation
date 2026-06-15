"""Test GitHub Issues connector with mocked HTTP."""
from unittest.mock import MagicMock
from opc_foundation.sources.connectors.github_issues import GitHubIssuesConnector
from opc_foundation.sources.source_schema import SourceQuery, SourceDefinition
from opc_foundation.run.run_context import RunContext


def _make_mock_client(items):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"items": items, "total_count": len(items)}
    mock_resp.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.get.return_value = mock_resp
    return mock_client


def _source():
    return SourceDefinition(
        source_id="gh", source_name="GitHub", source_type="github_issue", connector="github_issues"
    )


def _ctx():
    return RunContext(pipeline_name="test")


SAMPLE_ITEMS = [
    {
        "html_url": "https://github.com/org/repo/issues/1",
        "title": "Feature request: AI integration",
        "body": "We need an AI integration for our pipeline.",
        "user": {"login": "bob"},
        "created_at": "2026-01-01T00:00:00Z",
        "state": "open",
        "comments": 5,
        "labels": [{"name": "enhancement"}],
    }
]


def test_fetch_returns_signals():
    mock_client = _make_mock_client(SAMPLE_ITEMS)
    connector = GitHubIssuesConnector(_http_client=mock_client)
    q = SourceQuery(query_id="q1", source_id="gh", query="AI integration", max_items=10)
    result = connector.fetch(q, _source(), _ctx())
    assert len(result.raw_signals) == 1
    sig = result.raw_signals[0]
    assert "AI integration" in sig.title
    assert sig.author_or_org == "bob"
    assert result.errors == []


def test_no_query_returns_error():
    connector = GitHubIssuesConnector()
    q = SourceQuery(query_id="q1", source_id="gh", query=None, max_items=5)
    result = connector.fetch(q, _source(), _ctx())
    assert len(result.errors) > 0


def test_http_failure_does_not_raise():
    mock_client = MagicMock()
    mock_client.get.side_effect = Exception("rate limited")
    connector = GitHubIssuesConnector(_http_client=mock_client)
    q = SourceQuery(query_id="q1", source_id="gh", query="test", max_items=5)
    result = connector.fetch(q, _source(), _ctx())
    assert len(result.errors) > 0
    assert len(result.raw_signals) == 0
