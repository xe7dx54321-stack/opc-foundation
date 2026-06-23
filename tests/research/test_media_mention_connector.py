"""测试 MediaMentionConnector。

功能说明（小白解读）：
    本文件覆盖 Phase 2E 的 27 个测试场景，包括：
    - 4 种 extraction_profile 的解析能力
    - media mention metadata 提取（media_outlet / author / mentioned_institutions /
      mentioned_analysts / mentioned_research / mention_type / mentioned_tickers）
    - 相对 URL 转 absolute
    - max_items 限制
    - fail-soft（空列表 / 畸形 HTML）
    - archiver 集成（dry-run / run / source failure isolation）
    - mentioned_tickers 只作为 metadata，不生成 affected_tickers
    - price target mention 只作为 metadata，不生成投资建议字段
    - 边界检查（无业务字段 / example config 全部 enabled: false）

    所有测试都基于 fixture，不访问真实网络。
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from opc_foundation.research.config import load_research_config, validate_research_config
from opc_foundation.research.connectors.media_mention import (
    MediaMentionConnector,
    _extract_mentioned_institutions,
    _extract_mentioned_tickers,
    _guess_mention_type,
)
from opc_foundation.research.models import (
    ResearchArchiveConfig,
    ResearchDefaults,
    ResearchSourceConfig,
)


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


def _make_source(
    url: str | None = "https://example.com/media/articles",
    extraction_profile: str = "media_mention_article_list",
    max_items: int | None = None,
    base_url: str | None = None,
    source_id: str = "mm_test",
) -> ResearchSourceConfig:
    """构造一个 media_mention source 配置。

    参数：
        url:                采集入口 URL
        extraction_profile: 抽取 profile 名
        max_items:          候选数上限
        base_url:           基础 URL（相对链接解析）
        source_id:          source ID

    返回：
        ResearchSourceConfig 对象
    """
    return ResearchSourceConfig(
        source_id=source_id,
        source_name="Media Mention Test",
        source_type="media_mention",
        url=url,
        base_url=base_url,
        extraction_profile=extraction_profile,
        legal_profile="licensed_media",
        tags=["media", "research_mention"],
        max_items=max_items,
    )


def _make_config() -> ResearchArchiveConfig:
    """构造一个最小配置。"""
    return ResearchArchiveConfig(
        archive_root="/tmp/test",
        defaults=ResearchDefaults(max_items_per_source=20),
    )


# ---------------------------------------------------------------------------
# 1. media_mention_article_list profile
# ---------------------------------------------------------------------------


def test_parses_media_mention_article_list(
    sample_media_mention_article_list_html: str,
) -> None:
    """media_mention_article_list 能从 HTML article list 提取 candidates。"""
    connector = MediaMentionConnector(
        html_by_url=lambda url: sample_media_mention_article_list_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # fixture 有 4 篇文章
    assert len(candidates) == 4
    assert "Goldman Sachs Raises AI Outlook" in candidates[0].title


# ---------------------------------------------------------------------------
# 2. media_mention_cards profile
# ---------------------------------------------------------------------------


def test_parses_media_mention_cards(sample_media_mention_cards_html: str) -> None:
    """media_mention_cards 能从 card list 提取 candidates。"""
    connector = MediaMentionConnector(
        html_by_url=lambda url: sample_media_mention_cards_html
    )
    source = _make_source(
        url="https://example.com/media/cards",
        extraction_profile="media_mention_cards",
    )
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # fixture 有 4 张卡片，1 张无链接应被跳过
    assert len(candidates) == 3
    assert "Goldman Sachs Raises AI Outlook" in candidates[0].title


# ---------------------------------------------------------------------------
# 3. media_mention_news_list profile
# ---------------------------------------------------------------------------


def test_parses_media_mention_news_list(
    sample_media_mention_news_list_html: str,
) -> None:
    """media_mention_news_list 能从 article list 提取 candidates。"""
    connector = MediaMentionConnector(
        html_by_url=lambda url: sample_media_mention_news_list_html
    )
    source = _make_source(
        url="https://example.com/media/news",
        extraction_profile="media_mention_news_list",
    )
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert len(candidates) == 4
    assert "Goldman Sachs Raises AI Outlook" in candidates[0].title


# ---------------------------------------------------------------------------
# 4. media_mention_detail profile
# ---------------------------------------------------------------------------


def test_parses_media_mention_detail(sample_media_mention_detail_html: str) -> None:
    """media_mention_detail 能从单篇 detail fixture 生成 1 个 candidate。"""
    connector = MediaMentionConnector(
        html_by_url=lambda url: sample_media_mention_detail_html
    )
    source = _make_source(
        url="https://example.com/media/detail",
        extraction_profile="media_mention_detail",
    )
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert len(candidates) == 1
    # 标题优先从 h1 提取
    assert candidates[0].title == "Goldman Sachs Raises AI Outlook, Cites Strong Demand"
    # document_kind 应为 media_mention_detail
    assert candidates[0].raw_entry["document_kind"] == "media_mention_detail"


# ---------------------------------------------------------------------------
# 5. relative URL 转 absolute
# ---------------------------------------------------------------------------


def test_relative_url_canonicalized(
    sample_media_mention_article_list_html: str,
) -> None:
    """相对 URL 应根据 base_url/source.url 转成 absolute。"""
    connector = MediaMentionConnector(
        html_by_url=lambda url: sample_media_mention_article_list_html
    )
    source = _make_source(url="https://example.com/media/articles")
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # 相对路径 /media/article-1 应被转成 absolute
    assert candidates[0].url == "https://example.com/media/article-1"


def test_relative_url_with_base_url(
    sample_media_mention_article_list_html: str,
) -> None:
    """base_url 也能用于相对链接解析。"""
    connector = MediaMentionConnector(
        html_by_url=lambda url: sample_media_mention_article_list_html
    )
    source = _make_source(
        url="https://example.com/media/articles/list",
        base_url="https://example.com",
    )
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates[0].url == "https://example.com/media/article-1"


# ---------------------------------------------------------------------------
# 6. published_at 提取
# ---------------------------------------------------------------------------


def test_published_at_from_time_tag(
    sample_media_mention_article_list_html: str,
) -> None:
    """能从 <time datetime="..."> 提取 published_at。"""
    connector = MediaMentionConnector(
        html_by_url=lambda url: sample_media_mention_article_list_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates[0].published_at == "2026-03-15T09:00:00+08:00"


def test_published_at_from_meta_in_detail(
    sample_media_mention_detail_html: str,
) -> None:
    """detail 页面能从 <meta name="date"> 提取 published_at。"""
    connector = MediaMentionConnector(
        html_by_url=lambda url: sample_media_mention_detail_html
    )
    source = _make_source(
        url="https://example.com/media/detail",
        extraction_profile="media_mention_detail",
    )
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # detail 页面有 <meta name="date" content="2026-03-15">
    assert candidates[0].published_at is not None


# ---------------------------------------------------------------------------
# 7. summary 提取
# ---------------------------------------------------------------------------


def test_summary_from_class(sample_media_mention_article_list_html: str) -> None:
    """能从 class='summary' 提取摘要。"""
    connector = MediaMentionConnector(
        html_by_url=lambda url: sample_media_mention_article_list_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates[0].summary is not None
    assert "Goldman Sachs" in candidates[0].summary


def test_summary_from_meta_in_detail(sample_media_mention_detail_html: str) -> None:
    """能从 <meta name='description'> 提取摘要（detail profile）。"""
    connector = MediaMentionConnector(
        html_by_url=lambda url: sample_media_mention_detail_html
    )
    source = _make_source(
        url="https://example.com/media/detail",
        extraction_profile="media_mention_detail",
    )
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # detail 页面优先从 class='summary' 提取
    assert candidates[0].summary is not None


# ---------------------------------------------------------------------------
# 8. media_outlet / author 进入 raw_entry
# ---------------------------------------------------------------------------


def test_media_outlet_in_raw_entry_detail(
    sample_media_mention_detail_html: str,
) -> None:
    """media_outlet 能进入 raw_entry（detail profile）。"""
    connector = MediaMentionConnector(
        html_by_url=lambda url: sample_media_mention_detail_html
    )
    source = _make_source(
        url="https://example.com/media/detail",
        extraction_profile="media_mention_detail",
    )
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    raw = candidates[0].raw_entry
    # detail fixture 有 <p class="media-outlet">Reuters</p>
    assert raw["media_outlet"] == "Reuters"


def test_author_in_raw_entry(sample_media_mention_article_list_html: str) -> None:
    """author 能进入 raw_entry。"""
    connector = MediaMentionConnector(
        html_by_url=lambda url: sample_media_mention_article_list_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # fixture 有 <p class="author">By Jane Doe</p>
    assert candidates[0].author is not None
    assert "Jane Doe" in candidates[0].author


# ---------------------------------------------------------------------------
# 9. mentioned_institutions 进入 raw_entry
# ---------------------------------------------------------------------------


def test_mentioned_institutions_in_raw_entry(
    sample_media_mention_article_list_html: str,
) -> None:
    """mentioned_institutions 能进入 raw_entry。"""
    connector = MediaMentionConnector(
        html_by_url=lambda url: sample_media_mention_article_list_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    raw = candidates[0].raw_entry
    # fixture 第一篇文章提到 Goldman Sachs
    assert "Goldman Sachs" in raw["mentioned_institutions"]


def test_mentioned_institutions_in_detail(
    sample_media_mention_detail_html: str,
) -> None:
    """detail 页面能提取多个 mentioned_institutions。"""
    connector = MediaMentionConnector(
        html_by_url=lambda url: sample_media_mention_detail_html
    )
    source = _make_source(
        url="https://example.com/media/detail",
        extraction_profile="media_mention_detail",
    )
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    raw = candidates[0].raw_entry
    # detail fixture 提到 Goldman Sachs / Morgan Stanley / J.P. Morgan / Bank of America
    institutions = raw["mentioned_institutions"]
    assert "Goldman Sachs" in institutions
    assert "Morgan Stanley" in institutions


# ---------------------------------------------------------------------------
# 10. mentioned_analysts 进入 raw_entry
# ---------------------------------------------------------------------------


def test_mentioned_analysts_in_raw_entry(
    sample_media_mention_article_list_html: str,
) -> None:
    """mentioned_analysts 能进入 raw_entry。"""
    connector = MediaMentionConnector(
        html_by_url=lambda url: sample_media_mention_article_list_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    raw = candidates[0].raw_entry
    # fixture 第一篇文章提到 "analyst Jane Doe"
    analysts = raw["mentioned_analysts"]
    assert len(analysts) > 0
    assert any("Jane Doe" in a for a in analysts)


# ---------------------------------------------------------------------------
# 11. mentioned_research 进入 raw_entry
# ---------------------------------------------------------------------------


def test_mentioned_research_in_raw_entry(
    sample_media_mention_article_list_html: str,
) -> None:
    """mentioned_research 能进入 raw_entry。"""
    connector = MediaMentionConnector(
        html_by_url=lambda url: sample_media_mention_article_list_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    raw = candidates[0].raw_entry
    # fixture 第一篇文章提到 "research note"
    assert raw["mentioned_research"] is not None


# ---------------------------------------------------------------------------
# 12. mention_type 进入 raw_entry
# ---------------------------------------------------------------------------


def test_mention_type_in_raw_entry(
    sample_media_mention_article_list_html: str,
) -> None:
    """mention_type 能进入 raw_entry。"""
    connector = MediaMentionConnector(
        html_by_url=lambda url: sample_media_mention_article_list_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    raw = candidates[0].raw_entry
    # fixture 第一篇文章提到 "research note"，应识别为 research_citation
    assert raw["mention_type"] == "research_citation"


def test_mention_type_guess_from_text() -> None:
    """_guess_mention_type 能从文本识别 mention_type。"""
    assert _guess_mention_type("research note from Goldman") == "research_citation"
    assert _guess_mention_type("analyst Jane Doe said") == "analyst_quote"
    assert _guess_mention_type("upgrade Sample Tech to Buy") == "rating_action"
    assert _guess_mention_type("price target raised to $200") == "price_target_mention"
    assert _guess_mention_type("at the technology conference") == "conference_commentary"
    assert _guess_mention_type("market outlook remains positive") == "market_commentary"
    assert _guess_mention_type("some random text") == "unknown"


# ---------------------------------------------------------------------------
# 13. mentioned_tickers 进入 raw_entry，且不等同于 affected_tickers
# ---------------------------------------------------------------------------


def test_mentioned_tickers_in_raw_entry(
    sample_media_mention_article_list_html: str,
) -> None:
    """mentioned_tickers 能进入 raw_entry。"""
    connector = MediaMentionConnector(
        html_by_url=lambda url: sample_media_mention_article_list_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    raw = candidates[0].raw_entry
    # fixture 第一篇文章提到 NVDA 和 AVGO
    tickers = raw["mentioned_tickers"]
    assert "NVDA" in tickers
    assert "AVGO" in tickers


def test_mentioned_tickers_not_affected_tickers(
    sample_media_mention_article_list_html: str,
) -> None:
    """mentioned_tickers 不等同于 affected_tickers，不应出现 affected_tickers 字段。"""
    connector = MediaMentionConnector(
        html_by_url=lambda url: sample_media_mention_article_list_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    raw = candidates[0].raw_entry
    # mentioned_tickers 应该存在
    assert "mentioned_tickers" in raw
    # 但不应有 affected_tickers
    assert "affected_tickers" not in raw


def test_extract_mentioned_tickers_helper() -> None:
    """_extract_mentioned_tickers 能从文本识别 ticker。"""
    tickers = _extract_mentioned_tickers("NVDA and AVGO were mentioned")
    assert "NVDA" in tickers
    assert "AVGO" in tickers


def test_extract_mentioned_institutions_helper() -> None:
    """_extract_mentioned_institutions 能从文本识别机构名。"""
    institutions = _extract_mentioned_institutions(
        "Goldman Sachs and Morgan Stanley commented"
    )
    assert "Goldman Sachs" in institutions
    assert "Morgan Stanley" in institutions


# ---------------------------------------------------------------------------
# 14. tags 和 legal_profile 继承 source
# ---------------------------------------------------------------------------


def test_inherits_source_tags_and_legal_profile(
    sample_media_mention_article_list_html: str,
) -> None:
    """候选文档继承 source 的 tags 和 legal_profile。"""
    connector = MediaMentionConnector(
        html_by_url=lambda url: sample_media_mention_article_list_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    for c in candidates:
        assert c.legal_profile == "licensed_media"
        assert c.tags == ["media", "research_mention"]
        assert c.source_id == "mm_test"
        assert c.source_type == "media_mention"


# ---------------------------------------------------------------------------
# 15. max_items 生效
# ---------------------------------------------------------------------------


def test_respects_max_items(sample_media_mention_article_list_html: str) -> None:
    """max_items 限制候选数量。"""
    connector = MediaMentionConnector(
        html_by_url=lambda url: sample_media_mention_article_list_html
    )
    source = _make_source(max_items=2)
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert len(candidates) == 2


def test_max_items_from_defaults(sample_media_mention_article_list_html: str) -> None:
    """没有 source.max_items 时，使用 defaults.max_items_per_source。"""
    connector = MediaMentionConnector(
        html_by_url=lambda url: sample_media_mention_article_list_html
    )
    source = _make_source()  # max_items=None
    cfg = ResearchArchiveConfig(
        archive_root="/tmp/test",
        defaults=ResearchDefaults(max_items_per_source=3),
    )

    candidates = connector.discover(source, cfg)
    assert len(candidates) == 3


# ---------------------------------------------------------------------------
# 16. empty list fail-soft
# ---------------------------------------------------------------------------


def test_empty_list_fail_soft(sample_media_mention_empty_html: str) -> None:
    """空列表页返回空候选列表，不崩溃。"""
    connector = MediaMentionConnector(
        html_by_url=lambda url: sample_media_mention_empty_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates == []


# ---------------------------------------------------------------------------
# 17. malformed HTML fail-soft
# ---------------------------------------------------------------------------


def test_malformed_html_fail_soft(sample_media_mention_malformed_html: str) -> None:
    """损坏的 HTML 也能解析出能用的候选，不崩溃。"""
    connector = MediaMentionConnector(
        html_by_url=lambda url: sample_media_mention_malformed_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # 至少能解析出一些候选（malformed fixture 有 4 个 article，2 个有效链接）
    assert len(candidates) >= 1
    # 所有候选都有 url 和 canonical_url
    for c in candidates:
        assert c.url
        assert c.canonical_url


# ---------------------------------------------------------------------------
# 18. archiver dry-run with media_mention fixture
# ---------------------------------------------------------------------------


def test_archiver_dry_run_with_media_mention(
    sample_media_mention_article_list_html: str,
    temp_archive_root: Path,
) -> None:
    """archiver dry-run 能发现 media mention 候选，不抓正文。"""
    from opc_foundation.research.archiver import ResearchArchiver, ResearchInjectors

    cfg = ResearchArchiveConfig(
        archive_root=str(temp_archive_root),
        defaults=ResearchDefaults(max_items_per_source=20),
        sources=[
            ResearchSourceConfig(
                source_id="mm_test",
                source_name="Media Mention Test",
                source_type="media_mention",
                url="https://example.com/media/articles",
                extraction_profile="media_mention_article_list",
                enabled=True,
                legal_profile="licensed_media",
                tags=["media"],
            ),
        ],
    )

    archiver = ResearchArchiver(
        cfg,
        injectors=ResearchInjectors(
            media_mention_html_by_url=lambda url: sample_media_mention_article_list_html,
        ),
    )
    result = archiver.dry_run()

    assert result.mode == "dry_run"
    # fixture 有 4 篇文章
    assert result.candidate_count == 4
    assert result.saved_count == 0  # dry-run 不抓正文
    assert result.new_count == 4


# ---------------------------------------------------------------------------
# 19. archiver run with media_mention fixture
# ---------------------------------------------------------------------------


def test_archiver_run_with_media_mention(
    sample_media_mention_article_list_html: str,
    sample_media_mention_detail_html: str,
    temp_archive_root: Path,
) -> None:
    """archiver run 能从 media_mention 归档文档。"""
    from opc_foundation.research.archiver import ResearchArchiver, ResearchInjectors

    cfg = ResearchArchiveConfig(
        archive_root=str(temp_archive_root),
        defaults=ResearchDefaults(max_items_per_source=20),
        sources=[
            ResearchSourceConfig(
                source_id="mm_test",
                source_name="Media Mention Test",
                source_type="media_mention",
                url="https://example.com/media/articles",
                extraction_profile="media_mention_article_list",
                enabled=True,
                legal_profile="licensed_media",
                tags=["media"],
            ),
        ],
    )

    # 注入：列表页 HTML + 详情页 HTML
    def mm_html_injector(url: str) -> str | None:
        if url == "https://example.com/media/articles":
            return sample_media_mention_article_list_html
        return None

    def detail_html_injector(url: str) -> str | None:
        if "/media/article-" in url:
            return sample_media_mention_detail_html
        return None

    archiver = ResearchArchiver(
        cfg,
        injectors=ResearchInjectors(
            media_mention_html_by_url=mm_html_injector,
            http_html=detail_html_injector,
        ),
    )
    result = archiver.run()

    assert result.mode == "run"
    assert result.candidate_count == 4
    # 至少有一些 saved 或 partial
    assert result.saved_count + result.partial_count > 0


# ---------------------------------------------------------------------------
# 20. run 后 documents.jsonl 字段完整
# ---------------------------------------------------------------------------


def test_documents_jsonl_fields_complete(
    sample_media_mention_article_list_html: str,
    sample_media_mention_detail_html: str,
    temp_archive_root: Path,
) -> None:
    """run 后 documents.jsonl 字段完整。"""
    import json

    from opc_foundation.research.archiver import ResearchArchiver, ResearchInjectors

    cfg = ResearchArchiveConfig(
        archive_root=str(temp_archive_root),
        defaults=ResearchDefaults(max_items_per_source=20),
        sources=[
            ResearchSourceConfig(
                source_id="mm_test",
                source_name="Media Mention Test",
                source_type="media_mention",
                url="https://example.com/media/articles",
                extraction_profile="media_mention_article_list",
                enabled=True,
                legal_profile="licensed_media",
                tags=["media"],
            ),
        ],
    )

    archiver = ResearchArchiver(
        cfg,
        injectors=ResearchInjectors(
            media_mention_html_by_url=lambda url: sample_media_mention_article_list_html
            if url == "https://example.com/media/articles" else None,
            http_html=lambda url: sample_media_mention_detail_html
            if "/media/article-" in url else None,
        ),
    )
    archiver.run()

    jsonl_path = temp_archive_root / "index" / "documents.jsonl"
    assert jsonl_path.exists()
    lines = jsonl_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) >= 1

    doc = json.loads(lines[0])
    # 必须字段
    required_fields = [
        "document_id",
        "source_id",
        "source_name",
        "source_type",
        "title",
        "url",
        "canonical_url",
        "captured_at",
        "content_type",
        "legal_profile",
        "tags",
        "content_hash",
        "status",
        "metadata_path",
        "extraction_quality",
    ]
    for field in required_fields:
        assert field in doc, f"documents.jsonl 缺少字段: {field}"
    assert doc["source_type"] == "media_mention"
    assert doc["legal_profile"] == "licensed_media"


# ---------------------------------------------------------------------------
# 21. detail page 能归档为 document.md
# ---------------------------------------------------------------------------


def test_detail_page_archived_as_markdown(
    sample_media_mention_article_list_html: str,
    sample_media_mention_detail_html: str,
    temp_archive_root: Path,
) -> None:
    """detail page 能归档为 document.md。"""
    from opc_foundation.research.archiver import ResearchArchiver, ResearchInjectors

    cfg = ResearchArchiveConfig(
        archive_root=str(temp_archive_root),
        defaults=ResearchDefaults(max_items_per_source=20),
        sources=[
            ResearchSourceConfig(
                source_id="mm_test",
                source_name="Media Mention Test",
                source_type="media_mention",
                url="https://example.com/media/articles",
                extraction_profile="media_mention_article_list",
                enabled=True,
                legal_profile="licensed_media",
                tags=["media"],
            ),
        ],
    )

    archiver = ResearchArchiver(
        cfg,
        injectors=ResearchInjectors(
            media_mention_html_by_url=lambda url: sample_media_mention_article_list_html
            if url == "https://example.com/media/articles" else None,
            http_html=lambda url: sample_media_mention_detail_html
            if "/media/article-" in url else None,
        ),
    )
    result = archiver.run()

    # 至少有一个文档的 markdown_path 不为空
    saved_with_md = [d for d in result.saved_documents if d.markdown_path]
    assert len(saved_with_md) > 0
    # markdown 文件实际存在
    for d in saved_with_md:
        assert Path(d.markdown_path).exists()


# ---------------------------------------------------------------------------
# 22. source failure isolation
# ---------------------------------------------------------------------------


def test_source_failure_isolation(
    sample_media_mention_article_list_html: str,
    sample_media_mention_detail_html: str,
    temp_archive_root: Path,
) -> None:
    """单个 media_mention source 失败不影响其他 source。"""
    from opc_foundation.research.archiver import ResearchArchiver, ResearchInjectors

    cfg = ResearchArchiveConfig(
        archive_root=str(temp_archive_root),
        defaults=ResearchDefaults(max_items_per_source=20),
        sources=[
            # 这个 source 会失败（HTML 内容为空）
            ResearchSourceConfig(
                source_id="broken_mm",
                source_name="Broken Media Mention",
                source_type="media_mention",
                url="https://broken.example.com/media",
                extraction_profile="media_mention_article_list",
                enabled=True,
                legal_profile="licensed_media",
                tags=["media"],
            ),
            # 这个 source 会成功
            ResearchSourceConfig(
                source_id="ok_mm",
                source_name="OK Media Mention",
                source_type="media_mention",
                url="https://example.com/media/articles",
                extraction_profile="media_mention_article_list",
                enabled=True,
                legal_profile="licensed_media",
                tags=["media"],
            ),
        ],
    )

    def mm_html_injector(url: str) -> str | None:
        if "broken.example.com" in url:
            return ""  # 空内容，触发失败
        if "example.com/media/articles" in url:
            return sample_media_mention_article_list_html
        return None

    archiver = ResearchArchiver(
        cfg,
        injectors=ResearchInjectors(
            media_mention_html_by_url=mm_html_injector,
            http_html=lambda url: sample_media_mention_detail_html
            if "/media/article-" in url else None,
        ),
    )
    result = archiver.run()

    # broken_mm 失败，ok_mm 成功
    broken_stat = next(s for s in result.source_stats if s["source_id"] == "broken_mm")
    ok_stat = next(s for s in result.source_stats if s["source_id"] == "ok_mm")
    assert broken_stat["status"] == "failed"
    assert ok_stat["status"] in ("healthy", "degraded")
    assert ok_stat["candidate_count"] == 4


# ---------------------------------------------------------------------------
# 23. 配置校验
# ---------------------------------------------------------------------------


def test_validate_config_media_mention_requires_url() -> None:
    """media_mention 缺少 url 和 base_url 时校验失败。"""
    cfg = ResearchArchiveConfig(
        archive_root="/tmp/test",
        defaults=ResearchDefaults(),
        sources=[
            ResearchSourceConfig(
                source_id="bad_mm",
                source_name="Bad Media Mention",
                source_type="media_mention",
                url=None,
                base_url=None,
                extraction_profile="media_mention_article_list",
                enabled=False,
                legal_profile="licensed_media",
            ),
        ],
    )
    errors = validate_research_config(cfg)
    assert any("media_mention" in e for e in errors)


def test_validate_config_media_mention_passes() -> None:
    """合法的 media_mention 配置应校验通过。"""
    cfg = ResearchArchiveConfig(
        archive_root="/tmp/test",
        defaults=ResearchDefaults(),
        sources=[
            ResearchSourceConfig(
                source_id="ok_mm_list",
                source_name="OK Media Mention List",
                source_type="media_mention",
                url="https://example.com/media/articles",
                extraction_profile="media_mention_article_list",
                enabled=False,
                legal_profile="licensed_media",
            ),
            ResearchSourceConfig(
                source_id="ok_mm_detail",
                source_name="OK Media Mention Detail",
                source_type="media_mention",
                url="https://example.com/media/detail",
                extraction_profile="media_mention_detail",
                enabled=False,
                legal_profile="licensed_media",
            ),
        ],
    )
    errors = validate_research_config(cfg)
    assert errors == []


# ---------------------------------------------------------------------------
# 24. no business fields in output
# ---------------------------------------------------------------------------


def test_no_business_fields_in_output(
    sample_media_mention_article_list_html: str,
) -> None:
    """候选文档不包含任何投研判断字段。"""
    connector = MediaMentionConnector(
        html_by_url=lambda url: sample_media_mention_article_list_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert len(candidates) > 0

    cand_dict = candidates[0].model_dump()
    forbidden_fields = {
        "affected_tickers",
        "expectation_delta",
        "investment_rating",
        "trade_signal",
        "watchlist",
        "sentiment",
        "bullish",
        "bearish",
        "recommendation",
        "action_decision",
        "signal",
    }
    for field in forbidden_fields:
        assert field not in cand_dict, f"候选文档不应包含业务字段: {field}"


def test_no_business_fields_in_raw_entry(
    sample_media_mention_article_list_html: str,
) -> None:
    """raw_entry 中也不包含投研判断字段。"""
    connector = MediaMentionConnector(
        html_by_url=lambda url: sample_media_mention_article_list_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert len(candidates) > 0

    raw = candidates[0].raw_entry
    forbidden_keys = {
        "affected_tickers",
        "expectation_delta",
        "investment_rating",
        "trade_signal",
        "watchlist",
        "sentiment",
        "recommendation",
        "action_decision",
        "signal",
    }
    for key in forbidden_keys:
        assert key not in raw, f"raw_entry 不应包含业务字段: {key}"


# ---------------------------------------------------------------------------
# 25. example config 全部 enabled: false
# ---------------------------------------------------------------------------


def test_example_config_all_disabled() -> None:
    """example config 中所有 source 的 enabled 都为 false。"""
    example_path = Path(__file__).parent.parent.parent / "configs" / "research_sources.example.yaml"
    assert example_path.exists(), f"example config 不存在: {example_path}"

    with open(example_path, "r", encoding="utf-8") as f:
        cfg_dict = yaml.safe_load(f)

    sources = cfg_dict.get("sources") or []
    assert len(sources) > 0, "example config 应该至少有一个 source"

    for src in sources:
        assert src.get("enabled") is False, (
            f"source [{src.get('source_id')}] enabled 应为 false，实际为 {src.get('enabled')}"
        )


def test_example_config_loads_and_validates() -> None:
    """example config 能被 load_research_config 加载并通过校验。"""
    example_path = Path(__file__).parent.parent.parent / "configs" / "research_sources.example.yaml"
    cfg = load_research_config(example_path)
    errors = validate_research_config(cfg)
    assert errors == [], f"example config 校验失败: {errors}"


def test_example_config_has_media_mention_sources() -> None:
    """example config 包含至少 3 个 media_mention source。"""
    example_path = Path(__file__).parent.parent.parent / "configs" / "research_sources.example.yaml"
    cfg = load_research_config(example_path)
    mm_sources = [s for s in cfg.sources if s.source_type == "media_mention"]
    assert len(mm_sources) >= 3, f"example config 应至少有 3 个 media_mention source，实际 {len(mm_sources)}"


# ---------------------------------------------------------------------------
# 26. price target mention 只作为 metadata，不生成投资建议字段
# ---------------------------------------------------------------------------


def test_price_target_mention_is_metadata_not_recommendation(
    sample_media_mention_news_list_html: str,
) -> None:
    """price target mention 只作为 raw_entry metadata，不生成投资建议字段。"""
    connector = MediaMentionConnector(
        html_by_url=lambda url: sample_media_mention_news_list_html
    )
    source = _make_source(
        url="https://example.com/media/news",
        extraction_profile="media_mention_news_list",
    )
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # 第三篇文章提到 "price target of $200"
    jpm_cand = next(c for c in candidates if "J.P. Morgan" in c.title or "JPMorgan" in c.title)
    raw = jpm_cand.raw_entry

    # mention_type 应该是 price_target_mention
    assert raw["mention_type"] == "price_target_mention"
    # 但不应有 recommendation / signal / action_decision 等业务字段
    assert "recommendation" not in raw
    assert "signal" not in raw
    assert "action_decision" not in raw
    assert "investment_rating" not in raw


# ---------------------------------------------------------------------------
# 27. rating words 只作为媒体原文 metadata，不生成 recommendation/signal/action_decision
# ---------------------------------------------------------------------------


def test_rating_words_are_metadata_not_recommendation(
    sample_media_mention_news_list_html: str,
) -> None:
    """rating words 只作为媒体原文 metadata，不生成 recommendation/signal/action_decision。"""
    connector = MediaMentionConnector(
        html_by_url=lambda url: sample_media_mention_news_list_html
    )
    source = _make_source(
        url="https://example.com/media/news",
        extraction_profile="media_mention_news_list",
    )
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # 第二篇文章提到 "downgraded"
    ms_cand = next(c for c in candidates if "Morgan Stanley" in c.title)
    raw = ms_cand.raw_entry

    # mention_type 应该是 rating_action
    assert raw["mention_type"] == "rating_action"
    # 但不应有 recommendation / signal / action_decision 等业务字段
    assert "recommendation" not in raw
    assert "signal" not in raw
    assert "action_decision" not in raw
    assert "investment_rating" not in raw


# ---------------------------------------------------------------------------
# 补充：connector 边界
# ---------------------------------------------------------------------------


def test_missing_url_raises() -> None:
    """缺少 url 时抛 ValueError。"""
    connector = MediaMentionConnector()
    source = _make_source(url=None, base_url=None)
    cfg = _make_config()
    with pytest.raises(ValueError, match="缺少 url"):
        connector.discover(source, cfg)


def test_empty_html_raises() -> None:
    """HTML 内容为空时抛 ValueError。"""
    connector = MediaMentionConnector(html_by_url=lambda url: "")
    source = _make_source()
    cfg = _make_config()
    with pytest.raises(ValueError, match="内容为空"):
        connector.discover(source, cfg)


def test_reads_local_file(tmp_path: Path, sample_media_mention_article_list_html: str) -> None:
    """能读取本地 HTML 文件。"""
    html_path = tmp_path / "media_mentions.html"
    html_path.write_text(sample_media_mention_article_list_html, encoding="utf-8")

    connector = MediaMentionConnector()
    source = _make_source(url=str(html_path))
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert len(candidates) == 4


def test_raw_entry_contains_document_kind(
    sample_media_mention_article_list_html: str,
) -> None:
    """raw_entry 保留 document_kind 和 profile 用于审计。"""
    connector = MediaMentionConnector(
        html_by_url=lambda url: sample_media_mention_article_list_html
    )
    source = _make_source(extraction_profile="media_mention_article_list")
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    raw = candidates[0].raw_entry
    assert raw["document_kind"] == "media_mention"
    assert raw["profile"] == "media_mention_article_list"
    assert raw["detail_url"] == "https://example.com/media/article-1"
