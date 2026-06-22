"""测试 WeChatArchive connector。"""
from __future__ import annotations

from pathlib import Path

import pytest

from opc_foundation.research.connectors.wechat_archive import WeChatArchiveConnector
from opc_foundation.research.models import ResearchArchiveConfig, ResearchDefaults, ResearchSourceConfig


def _make_source(url: str) -> ResearchSourceConfig:
    """构造一个 wechat_archive source。"""
    return ResearchSourceConfig(
        source_id="wechat_test",
        source_name="WeChat Test",
        source_type="wechat_archive",
        url=url,
        legal_profile="rebroadcast",
        tags=["wechat"],
    )


def _make_config() -> ResearchArchiveConfig:
    return ResearchArchiveConfig(
        archive_root="/tmp/test",
        defaults=ResearchDefaults(max_items_per_source=10),
    )


def test_wechat_connector_parses_fixture(sample_wechat_articles_path: Path) -> None:
    """能从 jsonl 解析候选文档。"""
    connector = WeChatArchiveConnector()
    source = _make_source(str(sample_wechat_articles_path))
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert len(candidates) == 2
    assert candidates[0].title == "微信公众号测试文章一"
    assert candidates[1].title == "微信公众号测试文章二"


def test_wechat_connector_preserves_archive_paths(sample_wechat_articles_path: Path) -> None:
    """保留原始 wechat archive 路径。"""
    connector = WeChatArchiveConnector()
    source = _make_source(str(sample_wechat_articles_path))
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    raw = candidates[0].raw_entry
    assert "wechat_markdown_path" in raw
    assert "wechat_html_path" in raw
    assert raw["wechat_markdown_path"].endswith("article.md")


def test_wechat_connector_canonicalizes_url(sample_wechat_articles_path: Path) -> None:
    """URL 规范化。"""
    connector = WeChatArchiveConnector()
    source = _make_source(str(sample_wechat_articles_path))
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates[0].canonical_url == "https://mp.weixin.qq.com/s/test-article-1"


def test_wechat_connector_missing_url() -> None:
    """缺少 url 时抛 ValueError。"""
    connector = WeChatArchiveConnector()
    source = ResearchSourceConfig(
        source_id="wechat_test",
        source_name="WeChat Test",
        source_type="wechat_archive",
    )
    cfg = _make_config()
    with pytest.raises(ValueError, match="缺少 url"):
        connector.discover(source, cfg)


def test_wechat_connector_file_not_exist(tmp_path: Path) -> None:
    """文件不存在时抛 ValueError。"""
    connector = WeChatArchiveConnector()
    source = _make_source(str(tmp_path / "nonexistent.jsonl"))
    cfg = _make_config()
    with pytest.raises(ValueError, match="索引不存在"):
        connector.discover(source, cfg)


def test_wechat_connector_respects_max_items(sample_wechat_articles_path: Path) -> None:
    """max_items 限制候选数量。"""
    connector = WeChatArchiveConnector()
    source = _make_source(str(sample_wechat_articles_path))
    source.max_items = 1
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert len(candidates) == 1


def test_wechat_connector_legal_profile(sample_wechat_articles_path: Path) -> None:
    """legal_profile 默认 rebroadcast。"""
    connector = WeChatArchiveConnector()
    source = _make_source(str(sample_wechat_articles_path))
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates[0].legal_profile == "rebroadcast"
    assert candidates[0].source_type == "wechat_archive"
