"""测试 RSS connector。"""
from __future__ import annotations

from pathlib import Path

from opc_foundation.research.connectors.rss import RSSConnector
from opc_foundation.research.models import ResearchArchiveConfig, ResearchDefaults, ResearchSourceConfig


def _make_source(feed_url: str | None = None, max_items: int | None = None) -> ResearchSourceConfig:
    """构造一个 RSS source 配置。"""
    return ResearchSourceConfig(
        source_id="rss_test",
        source_name="RSS Test",
        source_type="rss_feed",
        feed_url=feed_url,
        max_items=max_items,
    )


def _make_config() -> ResearchArchiveConfig:
    """构造一个最小配置。"""
    return ResearchArchiveConfig(
        archive_root="/tmp/test",
        defaults=ResearchDefaults(max_items_per_source=10),
    )


def test_rss_connector_parses_fixture(sample_feed_xml: str) -> None:
    """能从 fixture XML 解析出候选文档。"""
    connector = RSSConnector(feed_content_by_url=lambda url: sample_feed_xml)
    source = _make_source(feed_url="https://example.com/feed.xml")
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # 第三个 entry 没有 link，应被跳过；剩下 3 个
    assert len(candidates) == 3
    assert candidates[0].title == "第一篇测试文章"
    assert candidates[1].title == "第二篇测试文章"
    assert candidates[2].title == "第四篇测试文章"


def test_rss_connector_canonicalizes_url(sample_feed_xml: str) -> None:
    """utm_* 参数应被剥离。"""
    connector = RSSConnector(feed_content_by_url=lambda url: sample_feed_xml)
    source = _make_source(feed_url="https://example.com/feed.xml")
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # 第一篇 link 含 utm_source，canonical_url 应去掉
    assert "utm_source" not in candidates[0].canonical_url
    assert candidates[0].canonical_url == "https://example.com/article-1"


def test_rss_connector_respects_max_items(sample_feed_xml: str) -> None:
    """max_items 限制候选数量。"""
    connector = RSSConnector(feed_content_by_url=lambda url: sample_feed_xml)
    source = _make_source(feed_url="https://example.com/feed.xml", max_items=2)
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert len(candidates) == 2


def test_rss_connector_reads_local_file(sample_feed_xml: str, tmp_path: Path) -> None:
    """能读取本地 feed 文件。"""
    feed_path = tmp_path / "feed.xml"
    feed_path.write_text(sample_feed_xml, encoding="utf-8")

    connector = RSSConnector()
    source = _make_source(feed_url=str(feed_path))
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert len(candidates) == 3


def test_rss_connector_missing_feed_url() -> None:
    """缺少 feed_url 时抛 ValueError。"""
    connector = RSSConnector()
    source = _make_source(feed_url=None)
    cfg = _make_config()

    import pytest
    with pytest.raises(ValueError, match="缺少 feed_url"):
        connector.discover(source, cfg)


def test_rss_connector_empty_feed_content() -> None:
    """feed 内容为空时抛 ValueError。"""
    connector = RSSConnector(feed_content_by_url=lambda url: "")
    source = _make_source(feed_url="https://example.com/feed.xml")
    cfg = _make_config()

    import pytest
    with pytest.raises(ValueError, match="feed 内容为空"):
        connector.discover(source, cfg)


def test_rss_connector_preserves_source_metadata(sample_feed_xml: str) -> None:
    """候选文档保留 source 信息。"""
    connector = RSSConnector(feed_content_by_url=lambda url: sample_feed_xml)
    source = _make_source(feed_url="https://example.com/feed.xml")
    source.legal_profile = "official_public"
    source.tags = ["news", "tech"]
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates[0].source_id == "rss_test"
    assert candidates[0].source_name == "RSS Test"
    assert candidates[0].source_type == "rss_feed"
    assert candidates[0].legal_profile == "official_public"
    assert candidates[0].tags == ["news", "tech"]
