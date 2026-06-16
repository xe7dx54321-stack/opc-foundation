"""Test GitHub rate limit handling."""
from unittest.mock import MagicMock
import httpx
from opc_foundation.sources.connectors.github_issues import GitHubIssuesConnector
from opc_foundation.sources.source_schema import SourceQuery, SourceDefinition
from opc_foundation.run.run_context import RunContext


def _source():
    return SourceDefinition(source_id="gh", source_name="GH",
                            source_type="github_issue", connector="github_issues")


def _ctx():
    return RunContext(pipeline_name="test")


def _mock_response(status_code=200, json_data=None, headers=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.headers = headers or {}
    if json_data:
        resp.json.return_value = json_data
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"HTTP {status_code}", request=MagicMock(), response=resp
        )
    else:
        resp.raise_for_status = MagicMock()
    return resp


def test_403_produces_access_denied_warning():
    mock = MagicMock()
    mock.get.return_value = _mock_response(403)
    connector = GitHubIssuesConnector(_http_client=mock, max_retries=0)
    q = SourceQuery(query_id="q1", source_id="gh", query="AI tools", max_items=5)
    result = connector.fetch(q, _source(), _ctx())
    assert any("access_denied" in w for w in result.warnings)
    assert len(result.raw_signals) == 0


def test_429_produces_rate_limit_warning():
    mock = MagicMock()
    mock.get.return_value = _mock_response(429, headers={"x-ratelimit-remaining": "0"})
    connector = GitHubIssuesConnector(_http_client=mock, max_retries=0)
    q = SourceQuery(query_id="q1", source_id="gh", query="AI tools", max_items=5)
    result = connector.fetch(q, _source(), _ctx())
    assert any("rate_limit" in w for w in result.warnings)
    assert len(result.raw_signals) == 0


def test_rate_limit_headers_preserved_in_metadata():
    mock = MagicMock()
    rate_headers = {"x-ratelimit-remaining": "42", "x-ratelimit-reset": "1700000000"}
    items = [{
        "id": 1, "html_url": "https://github.com/o/r/issues/1",
        "title": "Test", "body": "Body text here",
        "user": {"login": "dev"}, "created_at": "2026-01-01T00:00:00Z",
        "state": "open", "comments": 0, "labels": []
    }]
    mock.get.return_value = _mock_response(
        200, json_data={"items": items, "total_count": 1}, headers=rate_headers
    )
    connector = GitHubIssuesConnector(_http_client=mock)
    q = SourceQuery(query_id="q1", source_id="gh", query="Test", max_items=5)
    result = connector.fetch(q, _source(), _ctx())
    assert "rate_limit_headers" in result.metadata
    sig = result.raw_signals[0]
    assert sig.metadata.get("rate_limit_remaining") == "42"


def test_without_token_still_fetches():
    import os
    os.environ.pop("GITHUB_TOKEN", None)
    mock = MagicMock()
    resp = MagicMock()
    resp.status_code = 200
    resp.headers = {}
    resp.json.return_value = {"items": [], "total_count": 0}
    resp.raise_for_status = MagicMock()
    mock.get.return_value = resp
    connector = GitHubIssuesConnector(_http_client=mock)
    q = SourceQuery(query_id="q1", source_id="gh", query="AI", max_items=5)
    result = connector.fetch(q, _source(), _ctx())
    assert result.errors == []
    assert "Authorization" not in mock.get.call_args.kwargs.get("headers", {})