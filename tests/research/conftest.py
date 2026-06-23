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
def sample_official_research_list_html() -> str:
    """读取 sample_official_research_list.html 内容。"""
    return (FIXTURES_DIR / "sample_official_research_list.html").read_text(encoding="utf-8")


@pytest.fixture
def sample_official_research_article_html() -> str:
    """读取 sample_official_research_article.html 内容。"""
    return (FIXTURES_DIR / "sample_official_research_article.html").read_text(encoding="utf-8")


@pytest.fixture
def sample_official_research_empty_html() -> str:
    """读取 sample_official_research_empty.html 内容。"""
    return (FIXTURES_DIR / "sample_official_research_empty.html").read_text(encoding="utf-8")


@pytest.fixture
def sample_official_research_malformed_html() -> str:
    """读取 sample_official_research_malformed.html 内容。"""
    return (FIXTURES_DIR / "sample_official_research_malformed.html").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Phase 2B：podcast_transcript fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_podcast_episode_list_html() -> str:
    """读取 sample_podcast_episode_list.html 内容（podcast episode 列表页）。"""
    return (FIXTURES_DIR / "sample_podcast_episode_list.html").read_text(encoding="utf-8")


@pytest.fixture
def sample_podcast_episode_detail_html() -> str:
    """读取 sample_podcast_episode_detail.html 内容（单篇 transcript 详情页）。"""
    return (FIXTURES_DIR / "sample_podcast_episode_detail.html").read_text(encoding="utf-8")


@pytest.fixture
def sample_podcast_feed_xml() -> str:
    """读取 sample_podcast_feed.xml 内容（podcast RSS feed）。"""
    return (FIXTURES_DIR / "sample_podcast_feed.xml").read_text(encoding="utf-8")


@pytest.fixture
def sample_podcast_empty_html() -> str:
    """读取 sample_podcast_empty.html 内容（空列表页，用于 fail-soft 测试）。"""
    return (FIXTURES_DIR / "sample_podcast_empty.html").read_text(encoding="utf-8")


@pytest.fixture
def sample_podcast_malformed_html() -> str:
    """读取 sample_podcast_malformed.html 内容（畸形 HTML，用于 fail-soft 测试）。"""
    return (FIXTURES_DIR / "sample_podcast_malformed.html").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Phase 2C：conference_transcript fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_conference_event_list_html() -> str:
    """读取 sample_conference_event_list.html 内容（conference event 列表页）。"""
    return (FIXTURES_DIR / "sample_conference_event_list.html").read_text(encoding="utf-8")


@pytest.fixture
def sample_conference_event_detail_html() -> str:
    """读取 sample_conference_event_detail.html 内容（event detail 页面，含 transcript/webcast/presentation 链接）。"""
    return (FIXTURES_DIR / "sample_conference_event_detail.html").read_text(encoding="utf-8")


@pytest.fixture
def sample_conference_transcript_html() -> str:
    """读取 sample_conference_transcript.html 内容（单篇 transcript 页面）。"""
    return (FIXTURES_DIR / "sample_conference_transcript.html").read_text(encoding="utf-8")


@pytest.fixture
def sample_conference_presentation_page_html() -> str:
    """读取 sample_conference_presentation_page.html 内容（presentation 页面，含 PDF 链接）。"""
    return (FIXTURES_DIR / "sample_conference_presentation_page.html").read_text(encoding="utf-8")


@pytest.fixture
def sample_conference_empty_html() -> str:
    """读取 sample_conference_empty.html 内容（空列表页，用于 fail-soft 测试）。"""
    return (FIXTURES_DIR / "sample_conference_empty.html").read_text(encoding="utf-8")


@pytest.fixture
def sample_conference_malformed_html() -> str:
    """读取 sample_conference_malformed.html 内容（畸形 HTML，用于 fail-soft 测试）。"""
    return (FIXTURES_DIR / "sample_conference_malformed.html").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Phase 2D：analyst_action fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_analyst_action_table_html() -> str:
    """读取 sample_analyst_action_table.html 内容（评级变动表格）。"""
    return (FIXTURES_DIR / "sample_analyst_action_table.html").read_text(encoding="utf-8")


@pytest.fixture
def sample_analyst_action_cards_html() -> str:
    """读取 sample_analyst_action_cards.html 内容（卡片式评级变动页面）。"""
    return (FIXTURES_DIR / "sample_analyst_action_cards.html").read_text(encoding="utf-8")


@pytest.fixture
def sample_analyst_action_news_list_html() -> str:
    """读取 sample_analyst_action_news_list.html 内容（新闻列表式评级变动页面）。"""
    return (FIXTURES_DIR / "sample_analyst_action_news_list.html").read_text(encoding="utf-8")


@pytest.fixture
def sample_analyst_action_detail_html() -> str:
    """读取 sample_analyst_action_detail.html 内容（单篇评级变动详情页）。"""
    return (FIXTURES_DIR / "sample_analyst_action_detail.html").read_text(encoding="utf-8")


@pytest.fixture
def sample_analyst_action_empty_html() -> str:
    """读取 sample_analyst_action_empty.html 内容（空列表页，用于 fail-soft 测试）。"""
    return (FIXTURES_DIR / "sample_analyst_action_empty.html").read_text(encoding="utf-8")


@pytest.fixture
def sample_analyst_action_malformed_html() -> str:
    """读取 sample_analyst_action_malformed.html 内容（畸形 HTML，用于 fail-soft 测试）。"""
    return (FIXTURES_DIR / "sample_analyst_action_malformed.html").read_text(encoding="utf-8")


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
