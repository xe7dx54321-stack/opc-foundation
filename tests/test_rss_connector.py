"""Test RSS connector with a sample feed string."""
from unittest.mock import patch
from opc_foundation.sources.connectors.rss import RssConnector
from opc_foundation.sources.source_schema import SourceQuery, SourceDefinition
from opc_foundation.run.run_context import RunContext

SAMPLE_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <link>https://example.com</link>
    <description>A test RSS feed</description>
    <item>
      <title>Entry One</title>
      <link>https://example.com/1</link>
      <description>Summary of entry one</description>
      <pubDate>Mon, 01 Jan 2026 00:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Entry Two</title>
      <link>https://example.com/2</link>
      <description>Summary of entry two</description>
    </item>
  </channel>
</rss>"""


def _source():
    return SourceDefinition(
        source_id="rss1", source_name="RSS Feed", source_type="rss", connector="rss"
    )


def _ctx():
    return RunContext(pipeline_name="test")


def test_fetch_from_feed_string():
    import feedparser
    parsed = feedparser.parse(SAMPLE_FEED)
    with patch("opc_foundation.sources.connectors.rss.feedparser.parse", return_value=parsed):
        connector = RssConnector()
        q = SourceQuery(query_id="q1", source_id="rss1", url="https://example.com/feed.xml", max_items=10)
        result = connector.fetch(q, _source(), _ctx())
    assert len(result.raw_signals) == 2
    assert result.raw_signals[0].title == "Entry One"
    assert result.raw_signals[1].title == "Entry Two"


def test_no_url_returns_warning():
    connector = RssConnector()
    q = SourceQuery(query_id="q1", source_id="rss1", max_items=5)
    result = connector.fetch(q, _source(), _ctx())
    assert len(result.warnings) > 0
    assert len(result.raw_signals) == 0


def test_max_items_respected():
    import feedparser
    parsed = feedparser.parse(SAMPLE_FEED)
    with patch("opc_foundation.sources.connectors.rss.feedparser.parse", return_value=parsed):
        connector = RssConnector()
        q = SourceQuery(query_id="q1", source_id="rss1", url="https://example.com/feed.xml", max_items=1)
        result = connector.fetch(q, _source(), _ctx())
    assert len(result.raw_signals) == 1


def test_parse_failure_does_not_raise():
    with patch("opc_foundation.sources.connectors.rss.feedparser.parse", side_effect=Exception("boom")):
        connector = RssConnector()
        q = SourceQuery(query_id="q1", source_id="rss1", url="https://bad.url/feed", max_items=5)
        result = connector.fetch(q, _source(), _ctx())
    assert len(result.errors) > 0
    assert len(result.raw_signals) == 0
