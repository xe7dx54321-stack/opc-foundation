"""Test connector reliability: timeout, failure, empty results, warnings."""
from unittest.mock import MagicMock, patch
import httpx
from opc_foundation.sources.connectors.hacker_news import HackerNewsConnector
from opc_foundation.sources.connectors.github_issues import GitHubIssuesConnector
from opc_foundation.sources.connectors.rss import RssConnector
from opc_foundation.sources.connectors.manual_url import ManualUrlConnector
from opc_foundation.sources.source_schema import SourceQuery, SourceDefinition
from opc_foundation.run.run_context import RunContext


def _ctx():
    return RunContext(pipeline_name="reliability_test")


def _hn_source():
    return SourceDefinition(source_id="hn", source_name="HN",
                            source_type="community_discussion", connector="hacker_news")


def _gh_source():
    return SourceDefinition(source_id="gh", source_name="GH",
                            source_type="github_issue", connector="github_issues")


def _rss_source():
    return SourceDefinition(source_id="rss1", source_name="RSS",
                            source_type="rss", connector="rss")


def _manual_source():
    return SourceDefinition(source_id="manual", source_name="Manual",
                            source_type="manual_url", connector="manual_url")


# --- HN ---
def test_hn_network_failure_does_not_raise():
    mock = MagicMock()
    mock.get.side_effect = httpx.NetworkError("network down")
    connector = HackerNewsConnector(_http_client=mock)
    q = SourceQuery(query_id="q1", source_id="hn", query="AI", max_items=5)
    result = connector.fetch(q, _hn_source(), _ctx())
    assert isinstance(result.errors, list)
    assert len(result.errors) > 0
    assert len(result.raw_signals) == 0


def test_hn_empty_query_returns_warning():
    connector = HackerNewsConnector()
    q = SourceQuery(query_id="q1", source_id="hn", query="", max_items=5)
    result = connector.fetch(q, _hn_source(), _ctx())
    assert len(result.warnings) > 0
    assert len(result.raw_signals) == 0


def test_hn_empty_hits_is_not_failure():
    mock = MagicMock()
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"hits": []}
    resp.raise_for_status = MagicMock()
    mock.get.return_value = resp
    connector = HackerNewsConnector(_http_client=mock)
    q = SourceQuery(query_id="q1", source_id="hn", query="very_obscure", max_items=5)
    result = connector.fetch(q, _hn_source(), _ctx())
    assert result.errors == []
    assert len(result.raw_signals) == 0


def test_hn_429_produces_warning():
    mock = MagicMock()
    resp = MagicMock()
    resp.status_code = 429
    resp.headers = {}
    mock.get.return_value = resp
    connector = HackerNewsConnector(_http_client=mock, max_retries=0)
    q = SourceQuery(query_id="q1", source_id="hn", query="AI", max_items=5)
    result = connector.fetch(q, _hn_source(), _ctx())
    assert any("rate_limit" in w for w in result.warnings)


# --- GitHub ---
def test_gh_network_failure_does_not_raise():
    mock = MagicMock()
    mock.get.side_effect = httpx.NetworkError("down")
    connector = GitHubIssuesConnector(_http_client=mock)
    q = SourceQuery(query_id="q1", source_id="gh", query="AI", max_items=5)
    result = connector.fetch(q, _gh_source(), _ctx())
    assert len(result.errors) > 0
    assert len(result.raw_signals) == 0


def test_gh_403_produces_warning():
    mock = MagicMock()
    resp = MagicMock()
    resp.status_code = 403
    resp.headers = {}
    mock.get.return_value = resp
    connector = GitHubIssuesConnector(_http_client=mock, max_retries=0)
    q = SourceQuery(query_id="q1", source_id="gh", query="AI", max_items=5)
    result = connector.fetch(q, _gh_source(), _ctx())
    assert any("access_denied" in w for w in result.warnings)


def test_gh_empty_query_returns_warning():
    connector = GitHubIssuesConnector()
    q = SourceQuery(query_id="q1", source_id="gh", query=None, max_items=5)
    result = connector.fetch(q, _gh_source(), _ctx())
    assert len(result.warnings) > 0


# --- RSS ---
def test_rss_no_feed_url_returns_warning():
    connector = RssConnector()
    q = SourceQuery(query_id="q1", source_id="rss1", max_items=5)
    result = connector.fetch(q, _rss_source(), _ctx())
    assert len(result.warnings) > 0
    assert len(result.raw_signals) == 0


def test_rss_parse_exception_does_not_raise():
    with patch("opc_foundation.sources.connectors.rss.feedparser.parse",
               side_effect=Exception("fatal parse error")):
        connector = RssConnector()
        q = SourceQuery(query_id="q1", source_id="rss1", url="https://bad.feed/rss", max_items=5)
        result = connector.fetch(q, _rss_source(), _ctx())
    assert len(result.errors) > 0
    assert len(result.raw_signals) == 0


# --- Manual URL ---
def test_manual_url_missing_csv_returns_error():
    connector = ManualUrlConnector()
    q = SourceQuery(query_id="q1", source_id="manual", url="/does/not/exist.csv", max_items=5)
    result = connector.fetch(q, _manual_source(), _ctx())
    assert len(result.errors) > 0
    assert len(result.raw_signals) == 0


def test_manual_url_no_csv_path_returns_warning():
    connector = ManualUrlConnector()
    q = SourceQuery(query_id="q1", source_id="manual", max_items=5)
    result = connector.fetch(q, _manual_source(), _ctx())
    assert len(result.warnings) > 0


def test_manual_url_empty_url_row_skipped(tmp_path):
    csv = tmp_path / "urls.csv"
    csv.write_text("url,source_type,source_name,title,collection_query,notes\n,web,Ex,,q,note\nhttps://example.com,web,Ex,T,q,note\n",
                   encoding="utf-8")
    connector = ManualUrlConnector()
    q = SourceQuery(query_id="q1", source_id="manual", url=str(csv), max_items=10)
    result = connector.fetch(q, _manual_source(), _ctx())
    assert len(result.raw_signals) == 1
    assert any("missing url" in w for w in result.warnings)