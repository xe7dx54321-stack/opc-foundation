"""Contract test harness – all connectors must satisfy the same invariants."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import feedparser
import pytest

from opc_foundation.run.run_context import RunContext
from opc_foundation.sources.connector_base import SourceConnector
from opc_foundation.sources.connectors.github_issues import GitHubIssuesConnector
from opc_foundation.sources.connectors.hacker_news import HackerNewsConnector
from opc_foundation.sources.connectors.manual_url import ManualUrlConnector
from opc_foundation.sources.connectors.rss import RssConnector
from opc_foundation.sources.source_schema import FetchResult, SourceDefinition, SourceQuery

FIXTURES = Path(__file__).parent / "fixtures"


def _ctx():
    return RunContext(pipeline_name="contract_test")


# ---------------------------------------------------------------------------
# Fixture-backed connector builders
# ---------------------------------------------------------------------------

def _hn_connector():
    data = json.loads((FIXTURES / "hn_response.json").read_text())
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = data
    mock_resp.raise_for_status = MagicMock()
    mock_resp.headers = {}
    client = MagicMock()
    client.get.return_value = mock_resp
    return HackerNewsConnector(_http_client=client), SourceDefinition(
        source_id="hn", source_name="HN", source_type="community_discussion",
        connector="hacker_news"
    ), SourceQuery(query_id="q1", source_id="hn", query="AI tools", max_items=2)


def _gh_connector():
    data = json.loads((FIXTURES / "github_issues_response.json").read_text())
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = data
    mock_resp.raise_for_status = MagicMock()
    mock_resp.headers = {}
    client = MagicMock()
    client.get.return_value = mock_resp
    return GitHubIssuesConnector(_http_client=client), SourceDefinition(
        source_id="gh", source_name="GH", source_type="github_issue",
        connector="github_issues"
    ), SourceQuery(query_id="q2", source_id="gh", query="AI tools", max_items=5)


def _rss_connector():
    xml = (FIXTURES / "rss_feed.xml").read_text(encoding="utf-8")
    parsed = feedparser.parse(xml)
    return RssConnector(), SourceDefinition(
        source_id="rss1", source_name="RSS Feed", source_type="rss", connector="rss"
    ), SourceQuery(query_id="q3", source_id="rss1", url="mock://feed", max_items=10), parsed


def _manual_connector(tmp_path):
    csv = tmp_path / "urls.csv"
    csv.write_text(
        "url,source_type,source_name,title,collection_query,notes\n"
        "https://example.com/a,web,Ex,Title A,q,note A\n"
        "https://example.com/b,web,Ex,Title B,q,note B\n",
        encoding="utf-8"
    )
    return ManualUrlConnector(), SourceDefinition(
        source_id="manual", source_name="Manual", source_type="manual_url",
        connector="manual_url"
    ), SourceQuery(query_id="q4", source_id="manual", url=str(csv), max_items=10)


# ---------------------------------------------------------------------------
# Contract assertions
# ---------------------------------------------------------------------------

def _assert_contracts(result: FetchResult) -> None:
    assert isinstance(result, FetchResult), "Must return FetchResult"
    assert isinstance(result.raw_signals, list)
    assert isinstance(result.errors, list)
    assert isinstance(result.warnings, list)
    assert result.fetched_at, "fetched_at must be set"
    for sig in result.raw_signals:
        assert sig.source_url or sig.source_note, \
            f"Signal {sig.signal_id}: must have source_url or source_note"
        assert sig.raw_text, f"Signal {sig.signal_id}: raw_text must not be empty"
        assert sig.fetched_at, f"Signal {sig.signal_id}: fetched_at must be set"


# ---------------------------------------------------------------------------
# HN
# ---------------------------------------------------------------------------

def test_hn_returns_fetch_result():
    connector, source, query = _hn_connector()
    result = connector.fetch(query, source, _ctx())
    _assert_contracts(result)


def test_hn_signals_count_respects_max_items():
    connector, source, query = _hn_connector()
    query.max_items = 1
    result = connector.fetch(query, source, _ctx())
    assert len(result.raw_signals) <= 1


def test_hn_failure_never_raises():
    client = MagicMock()
    client.get.side_effect = Exception("fatal network error")
    connector = HackerNewsConnector(_http_client=client)
    source = SourceDefinition(source_id="hn", source_name="HN",
                              source_type="community_discussion", connector="hacker_news")
    query = SourceQuery(query_id="q", source_id="hn", query="AI", max_items=5)
    result = connector.fetch(query, source, _ctx())
    _assert_contracts(result)
    assert len(result.errors) > 0


# ---------------------------------------------------------------------------
# GitHub
# ---------------------------------------------------------------------------

def test_gh_returns_fetch_result():
    connector, source, query = _gh_connector()
    result = connector.fetch(query, source, _ctx())
    _assert_contracts(result)


def test_gh_signals_count_respects_max_items():
    connector, source, query = _gh_connector()
    query.max_items = 1
    result = connector.fetch(query, source, _ctx())
    assert len(result.raw_signals) <= 1


def test_gh_failure_never_raises():
    client = MagicMock()
    client.get.side_effect = Exception("boom")
    connector = GitHubIssuesConnector(_http_client=client)
    source = SourceDefinition(source_id="gh", source_name="GH",
                              source_type="github_issue", connector="github_issues")
    query = SourceQuery(query_id="q", source_id="gh", query="AI", max_items=5)
    result = connector.fetch(query, source, _ctx())
    _assert_contracts(result)
    assert len(result.errors) > 0


# ---------------------------------------------------------------------------
# RSS
# ---------------------------------------------------------------------------

def test_rss_returns_fetch_result():
    connector, source, query, parsed_feed = _rss_connector()
    with patch("opc_foundation.sources.connectors.rss.feedparser.parse", return_value=parsed_feed):
        result = connector.fetch(query, source, _ctx())
    _assert_contracts(result)


def test_rss_max_items_respected():
    connector, source, query, parsed_feed = _rss_connector()
    query.max_items = 1
    with patch("opc_foundation.sources.connectors.rss.feedparser.parse", return_value=parsed_feed):
        result = connector.fetch(query, source, _ctx())
    assert len(result.raw_signals) <= 1


def test_rss_failure_never_raises():
    with patch("opc_foundation.sources.connectors.rss.feedparser.parse",
               side_effect=Exception("crash")):
        connector = RssConnector()
        source = SourceDefinition(source_id="rss1", source_name="RSS",
                                  source_type="rss", connector="rss")
        query = SourceQuery(query_id="q", source_id="rss1", url="http://bad.feed/", max_items=5)
        result = connector.fetch(query, source, _ctx())
    _assert_contracts(result)
    assert len(result.errors) > 0


# ---------------------------------------------------------------------------
# Manual URL
# ---------------------------------------------------------------------------

def test_manual_returns_fetch_result(tmp_path):
    connector, source, query = _manual_connector(tmp_path)
    result = connector.fetch(query, source, _ctx())
    _assert_contracts(result)


def test_manual_max_items_respected(tmp_path):
    connector, source, query = _manual_connector(tmp_path)
    query.max_items = 1
    result = connector.fetch(query, source, _ctx())
    assert len(result.raw_signals) <= 1


def test_manual_failure_never_raises():
    connector = ManualUrlConnector()
    source = SourceDefinition(source_id="m", source_name="M",
                              source_type="manual_url", connector="manual_url")
    query = SourceQuery(query_id="q", source_id="m", url="/nonexistent/path.csv", max_items=5)
    result = connector.fetch(query, source, _ctx())
    _assert_contracts(result)