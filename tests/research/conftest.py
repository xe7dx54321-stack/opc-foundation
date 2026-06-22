"""tests/research/ 共享 fixture。

功能说明（小白解读）：
    pytest fixture 是测试之间共享数据/对象的方式。
    这里定义了一些常用的 fixture，比如临时归档目录、示例配置等。
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    """测试 fixtures 目录路径。"""
    return FIXTURES_DIR


@pytest.fixture
def sample_feed_xml() -> str:
    """读取 sample_feed.xml 内容。"""
    return (FIXTURES_DIR / "sample_feed.xml").read_text(encoding="utf-8")


@pytest.fixture
def sample_article_html() -> str:
    """读取 sample_article.html 内容。"""
    return (FIXTURES_DIR / "sample_article.html").read_text(encoding="utf-8")


@pytest.fixture
def sample_wechat_articles_path() -> Path:
    """sample_wechat_articles.jsonl 的路径。"""
    return FIXTURES_DIR / "sample_wechat_articles.jsonl"


@pytest.fixture
def manual_urls_path() -> Path:
    """manual_urls.txt 的路径。"""
    return FIXTURES_DIR / "manual_urls.txt"


@pytest.fixture
def temp_archive_root(tmp_path: Path) -> Path:
    """临时归档根目录（每个测试独立，测试结束自动清理）。"""
    root = tmp_path / "research_archive"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def sample_config_dict(temp_archive_root: Path, sample_feed_xml: str, tmp_path: Path) -> dict:
    """构造一个示例配置 dict（用于测试 load_research_config）。

    把 sample_feed.xml 复制到临时目录，让配置里的 feed_url 指向它。
    """
    feed_path = tmp_path / "feed.xml"
    feed_path.write_text(sample_feed_xml, encoding="utf-8")

    wechat_jsonl = FIXTURES_DIR / "sample_wechat_articles.jsonl"
    wechat_copy = tmp_path / "wechat_articles.jsonl"
    shutil.copyfile(wechat_jsonl, wechat_copy)

    manual_urls = FIXTURES_DIR / "manual_urls.txt"
    manual_copy = tmp_path / "manual_urls.txt"
    shutil.copyfile(manual_urls, manual_copy)

    return {
        "archive_root": str(temp_archive_root),
        "defaults": {
            "fetch_timeout_seconds": 10,
            "max_items_per_source": 5,
            "save_html": True,
            "save_markdown": True,
            "save_raw": True,
            "download_assets": False,
            "user_agent": "Mozilla/5.0 (test)",
        },
        "sources": [
            {
                "source_id": "rss_test",
                "source_name": "RSS Test Source",
                "source_type": "rss_feed",
                "feed_url": str(feed_path),
                "enabled": True,
                "legal_profile": "official_public",
                "tags": ["test", "rss"],
            },
            {
                "source_id": "wechat_test",
                "source_name": "WeChat Test Source",
                "source_type": "wechat_archive",
                "url": str(wechat_copy),
                "enabled": True,
                "legal_profile": "rebroadcast",
                "tags": ["test", "wechat"],
            },
            {
                "source_id": "manual_test",
                "source_name": "Manual URL Test Source",
                "source_type": "manual_url",
                "manual_urls_path": str(manual_copy),
                "enabled": True,
                "legal_profile": "user_provided",
                "tags": ["test", "manual"],
            },
            {
                "source_id": "disabled_source",
                "source_name": "Disabled Source",
                "source_type": "rss_feed",
                "feed_url": str(feed_path),
                "enabled": False,
                "legal_profile": "official_public",
            },
        ],
    }
