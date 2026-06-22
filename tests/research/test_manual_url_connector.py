"""测试 ManualURL connector。"""
from __future__ import annotations

from pathlib import Path

import pytest

from opc_foundation.research.connectors.manual_url import ManualURLConnector
from opc_foundation.research.models import ResearchArchiveConfig, ResearchDefaults, ResearchSourceConfig


def _make_source(path: str | None = None) -> ResearchSourceConfig:
    return ResearchSourceConfig(
        source_id="manual_test",
        source_name="Manual Test",
        source_type="manual_url",
        manual_urls_path=path,
        legal_profile="user_provided",
        tags=["manual"],
    )


def _make_config() -> ResearchArchiveConfig:
    return ResearchArchiveConfig(
        archive_root="/tmp/test",
        defaults=ResearchDefaults(max_items_per_source=10),
    )


def test_manual_url_parses_fixture(manual_urls_path: Path) -> None:
    """能解析手工 URL 文件。"""
    connector = ManualURLConnector()
    source = _make_source(str(manual_urls_path))
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # 文件里有 3 个不重复 URL（最后一个重复）
    assert len(candidates) == 3
    assert candidates[0].url == "https://example.com/manual-article-1"


def test_manual_url_skips_comments_and_empty(manual_urls_path: Path) -> None:
    """跳过注释和空行。"""
    connector = ManualURLConnector()
    source = _make_source(str(manual_urls_path))
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    urls = [c.url for c in candidates]
    # 不应包含注释 URL
    for u in urls:
        assert not u.startswith("#")
    # 不应包含空字符串
    assert "" not in urls


def test_manual_url_deduplicates(manual_urls_path: Path) -> None:
    """重复 URL 去重。"""
    connector = ManualURLConnector()
    source = _make_source(str(manual_urls_path))
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    urls = [c.url for c in candidates]
    assert len(urls) == len(set(urls))  # 无重复


def test_manual_url_canonicalizes(manual_urls_path: Path) -> None:
    """URL 规范化。"""
    connector = ManualURLConnector()
    source = _make_source(str(manual_urls_path))
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    for c in candidates:
        assert c.canonical_url  # 非空


def test_manual_url_missing_path() -> None:
    """缺少 manual_urls_path 时抛 ValueError。"""
    connector = ManualURLConnector()
    source = _make_source(path=None)
    cfg = _make_config()
    with pytest.raises(ValueError, match="缺少 manual_urls_path"):
        connector.discover(source, cfg)


def test_manual_url_file_not_exist(tmp_path: Path) -> None:
    """文件不存在时抛 ValueError。"""
    connector = ManualURLConnector()
    source = _make_source(str(tmp_path / "nonexistent.txt"))
    cfg = _make_config()
    with pytest.raises(ValueError, match="文件不存在"):
        connector.discover(source, cfg)


def test_manual_url_respects_max_items(manual_urls_path: Path) -> None:
    """max_items 限制候选数量。"""
    connector = ManualURLConnector()
    source = _make_source(str(manual_urls_path))
    source.max_items = 2
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert len(candidates) == 2


def test_manual_url_legal_profile(manual_urls_path: Path) -> None:
    """legal_profile 默认 user_provided。"""
    connector = ManualURLConnector()
    source = _make_source(str(manual_urls_path))
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates[0].legal_profile == "user_provided"
    assert candidates[0].source_type == "manual_url"
