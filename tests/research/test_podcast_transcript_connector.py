"""测试 PodcastTranscriptConnector。

功能说明（小白解读）：
    本文件覆盖 Phase 2B 的 20 个测试场景，包括：
    - 4 种 extraction_profile 的解析能力
    - 字段提取（published_at / summary / author / language）
    - 相对 URL 转 absolute
    - max_items 限制
    - fail-soft（空列表 / 畸形 HTML）
    - archiver 集成（dry-run / run / source failure isolation）
    - 边界检查（无业务字段 / example config 全部 enabled: false）

    所有测试都基于 fixture，不访问真实网络。
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from opc_foundation.research.config import load_research_config, validate_research_config
from opc_foundation.research.connectors.podcast_transcript import (
    PodcastTranscriptConnector,
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
    url: str | None = "https://example.com/podcast",
    feed_url: str | None = None,
    extraction_profile: str = "podcast_episode_list",
    max_items: int | None = None,
    base_url: str | None = None,
    source_id: str = "pod_test",
) -> ResearchSourceConfig:
    """构造一个 podcast_transcript source 配置。

    参数：
        url:                采集入口 URL
        feed_url:           RSS feed URL
        extraction_profile: 抽取 profile 名
        max_items:          候选数上限
        base_url:           基础 URL（相对链接解析）
        source_id:          source ID

    返回：
        ResearchSourceConfig 对象
    """
    return ResearchSourceConfig(
        source_id=source_id,
        source_name="Podcast Test",
        source_type="podcast_transcript",
        url=url,
        feed_url=feed_url,
        base_url=base_url,
        extraction_profile=extraction_profile,
        legal_profile="official_public",
        tags=["podcast", "transcript"],
        max_items=max_items,
    )


def _make_config() -> ResearchArchiveConfig:
    """构造一个最小配置。"""
    return ResearchArchiveConfig(
        archive_root="/tmp/test",
        defaults=ResearchDefaults(max_items_per_source=10),
    )


# ---------------------------------------------------------------------------
# 1. podcast_episode_list profile
# ---------------------------------------------------------------------------


def test_parses_podcast_episode_list(sample_podcast_episode_list_html: str) -> None:
    """podcast_episode_list 能从 HTML list 提取 candidates。"""
    connector = PodcastTranscriptConnector(
        html_by_url=lambda url: sample_podcast_episode_list_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # fixture 有 5 个 article，第 5 个无链接应被跳过
    assert len(candidates) == 4
    assert candidates[0].title == "Episode 1: 2026 宏观经济展望"
    assert candidates[1].title == "Episode 2: 新能源行业深度研究"


# ---------------------------------------------------------------------------
# 2. simple_episode_cards profile
# ---------------------------------------------------------------------------


def test_parses_simple_episode_cards() -> None:
    """simple_episode_cards 能从 card list 提取 candidates。"""
    html = """
    <html lang="en"><body>
        <div class="card episode-card">
            <h3><a href="/podcast/episode-1">卡片 Episode 1</a></h3>
            <time datetime="2026-01-15T09:00:00+08:00">2026-01-15</time>
            <p class="summary">卡片摘要一</p>
            <p class="author">主持人：张三</p>
            <p class="duration">28:15</p>
        </div>
        <div class="podcast-card">
            <h3><a href="/podcast/episode-2">卡片 Episode 2</a></h3>
            <time datetime="2026-01-16T10:30:00+08:00">2026-01-16</time>
            <p class="summary">卡片摘要二</p>
        </div>
    </body></html>
    """
    connector = PodcastTranscriptConnector(html_by_url=lambda url: html)
    source = _make_source(extraction_profile="simple_episode_cards")
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert len(candidates) == 2
    assert candidates[0].title == "卡片 Episode 1"
    assert candidates[0].summary == "卡片摘要一"
    assert candidates[1].title == "卡片 Episode 2"


# ---------------------------------------------------------------------------
# 3. podcast_feed profile
# ---------------------------------------------------------------------------


def test_parses_podcast_feed(sample_podcast_feed_xml: str) -> None:
    """podcast_feed 能从 RSS fixture 提取 candidates。"""
    connector = PodcastTranscriptConnector(html_by_url=lambda url: sample_podcast_feed_xml)
    source = _make_source(
        url=None,
        feed_url="https://example.com/podcast/feed.xml",
        extraction_profile="podcast_feed",
    )
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # fixture 有 4 个 item
    assert len(candidates) == 4
    assert candidates[0].title == "Episode 1: 2026 宏观经济展望"
    assert candidates[1].title == "Episode 2: 新能源行业深度研究"
    # 第 4 个 item 没有 enclosure，但仍然应该被解析
    assert candidates[3].title == "Episode 4: 区域经济专题"


def test_podcast_feed_extracts_audio_url(sample_podcast_feed_xml: str) -> None:
    """podcast_feed 能提取 enclosure 中的 audio_url。"""
    connector = PodcastTranscriptConnector(html_by_url=lambda url: sample_podcast_feed_xml)
    source = _make_source(
        url=None,
        feed_url="https://example.com/podcast/feed.xml",
        extraction_profile="podcast_feed",
    )
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # Episode 1 有 enclosure
    assert candidates[0].raw_entry["audio_url"] == "https://example.com/podcast/audio/episode-1.mp3"
    # Episode 4 没有 enclosure，audio_url 应为 None
    assert candidates[3].raw_entry["audio_url"] is None


def test_podcast_feed_extracts_feed_guid(sample_podcast_feed_xml: str) -> None:
    """podcast_feed 能提取 guid 作为 feed_guid。"""
    connector = PodcastTranscriptConnector(html_by_url=lambda url: sample_podcast_feed_xml)
    source = _make_source(
        url=None,
        feed_url="https://example.com/podcast/feed.xml",
        extraction_profile="podcast_feed",
    )
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates[0].raw_entry["feed_guid"] == "episode-001"
    assert candidates[1].raw_entry["feed_guid"] == "episode-002"


# ---------------------------------------------------------------------------
# 4. transcript_page profile
# ---------------------------------------------------------------------------


def test_parses_transcript_page(sample_podcast_episode_detail_html: str) -> None:
    """transcript_page 能从单篇 transcript fixture 生成 1 个 candidate。"""
    connector = PodcastTranscriptConnector(
        html_by_url=lambda url: sample_podcast_episode_detail_html
    )
    source = _make_source(
        url="https://example.com/podcast/episode-1/transcript",
        extraction_profile="transcript_page",
    )
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert len(candidates) == 1
    # 标题优先从 h1 提取
    assert candidates[0].title == "Episode 1: 2026 宏观经济展望"
    # url 应等于 source.url
    assert candidates[0].url == "https://example.com/podcast/episode-1/transcript"


# ---------------------------------------------------------------------------
# 5. relative URL 转 absolute
# ---------------------------------------------------------------------------


def test_relative_url_canonicalized(sample_podcast_episode_list_html: str) -> None:
    """相对 URL 应根据 base_url/source.url 转成 absolute。"""
    connector = PodcastTranscriptConnector(
        html_by_url=lambda url: sample_podcast_episode_list_html
    )
    source = _make_source(url="https://example.com/podcast")
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # 相对路径 /podcast/episode-1 应被转成 absolute
    assert candidates[0].url == "https://example.com/podcast/episode-1"
    assert candidates[0].canonical_url == "https://example.com/podcast/episode-1"
    assert candidates[1].url == "https://example.com/podcast/episode-2"


def test_relative_url_with_base_url(sample_podcast_episode_list_html: str) -> None:
    """base_url 也能用于相对链接解析（当 source.url 是文件路径时）。"""
    connector = PodcastTranscriptConnector(
        html_by_url=lambda url: sample_podcast_episode_list_html
    )
    source = _make_source(
        url="https://example.com/podcast/list",
        base_url="https://example.com",
    )
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # 相对路径 /podcast/episode-1 应被转成 absolute
    assert candidates[0].url == "https://example.com/podcast/episode-1"


# ---------------------------------------------------------------------------
# 6. published_at 提取
# ---------------------------------------------------------------------------


def test_published_at_from_time_tag(sample_podcast_episode_list_html: str) -> None:
    """能从 <time datetime="..."> 提取发布时间。"""
    connector = PodcastTranscriptConnector(
        html_by_url=lambda url: sample_podcast_episode_list_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates[0].published_at == "2026-01-15T09:00:00+08:00"
    assert candidates[1].published_at == "2026-01-16T10:30:00+08:00"


def test_published_at_from_pubdate_in_feed(sample_podcast_feed_xml: str) -> None:
    """能从 RSS pubDate 提取发布时间。"""
    connector = PodcastTranscriptConnector(html_by_url=lambda url: sample_podcast_feed_xml)
    source = _make_source(
        url=None,
        feed_url="https://example.com/podcast/feed.xml",
        extraction_profile="podcast_feed",
    )
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates[0].published_at == "Wed, 15 Jan 2026 09:00:00 +0800"


def test_published_at_from_meta_in_transcript_page(sample_podcast_episode_detail_html: str) -> None:
    """能从 <meta name="date"> 提取发布时间（transcript_page profile）。"""
    connector = PodcastTranscriptConnector(
        html_by_url=lambda url: sample_podcast_episode_detail_html
    )
    source = _make_source(
        url="https://example.com/podcast/episode-1/transcript",
        extraction_profile="transcript_page",
    )
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # fixture 中 meta name="date" content="2026-01-15"
    assert candidates[0].published_at == "2026-01-15"


# ---------------------------------------------------------------------------
# 7. summary 提取
# ---------------------------------------------------------------------------


def test_summary_from_class(sample_podcast_episode_list_html: str) -> None:
    """能从 class="summary" 提取摘要。"""
    connector = PodcastTranscriptConnector(
        html_by_url=lambda url: sample_podcast_episode_list_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates[0].summary == "本期讨论 2026 年宏观经济走势，涵盖 GDP、CPI、就业等核心指标。"


def test_summary_from_description_in_feed(sample_podcast_feed_xml: str) -> None:
    """能从 RSS description 提取摘要。"""
    connector = PodcastTranscriptConnector(html_by_url=lambda url: sample_podcast_feed_xml)
    source = _make_source(
        url=None,
        feed_url="https://example.com/podcast/feed.xml",
        extraction_profile="podcast_feed",
    )
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates[0].summary == "本期讨论 2026 年宏观经济走势，涵盖 GDP、CPI、就业等核心指标。"


def test_summary_fallback_to_p_tag(sample_podcast_episode_list_html: str) -> None:
    """没有 class="summary" 时，能从 <p> 提取摘要（Episode 4）。"""
    connector = PodcastTranscriptConnector(
        html_by_url=lambda url: sample_podcast_episode_list_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # Episode 4 没有 class="summary"，但有 <p> 文本
    ep4 = next(c for c in candidates if "Episode 4" in c.title)
    assert ep4.summary is not None
    assert "粤港澳大湾区" in ep4.summary


# ---------------------------------------------------------------------------
# 8. author 提取
# ---------------------------------------------------------------------------


def test_author_from_class(sample_podcast_episode_list_html: str) -> None:
    """能从 class="author" 提取作者。"""
    connector = PodcastTranscriptConnector(
        html_by_url=lambda url: sample_podcast_episode_list_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates[0].author == "主持人：张三"
    assert candidates[1].author == "主持人：李四"
    # Episode 3 没有 author
    ep3 = next(c for c in candidates if "Episode 3" in c.title)
    assert ep3.author is None


def test_author_from_meta_in_transcript_page(sample_podcast_episode_detail_html: str) -> None:
    """能从 <meta name="author"> 提取作者（transcript_page profile）。"""
    connector = PodcastTranscriptConnector(
        html_by_url=lambda url: sample_podcast_episode_detail_html
    )
    source = _make_source(
        url="https://example.com/podcast/episode-1/transcript",
        extraction_profile="transcript_page",
    )
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates[0].author == "主持人：张三"


def test_author_from_feed(sample_podcast_feed_xml: str) -> None:
    """能从 RSS author 提取作者。"""
    connector = PodcastTranscriptConnector(html_by_url=lambda url: sample_podcast_feed_xml)
    source = _make_source(
        url=None,
        feed_url="https://example.com/podcast/feed.xml",
        extraction_profile="podcast_feed",
    )
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates[0].author == "主持人：张三"


# ---------------------------------------------------------------------------
# 9. tags 和 legal_profile 继承 source
# ---------------------------------------------------------------------------


def test_inherits_source_tags_and_legal_profile(
    sample_podcast_episode_list_html: str,
) -> None:
    """候选文档继承 source 的 tags 和 legal_profile。"""
    connector = PodcastTranscriptConnector(
        html_by_url=lambda url: sample_podcast_episode_list_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    for c in candidates:
        assert c.legal_profile == "official_public"
        assert c.tags == ["podcast", "transcript"]
        assert c.source_id == "pod_test"
        assert c.source_type == "podcast_transcript"


# ---------------------------------------------------------------------------
# 10. max_items 生效
# ---------------------------------------------------------------------------


def test_respects_max_items(sample_podcast_episode_list_html: str) -> None:
    """max_items 限制候选数量。"""
    connector = PodcastTranscriptConnector(
        html_by_url=lambda url: sample_podcast_episode_list_html
    )
    source = _make_source(max_items=2)
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert len(candidates) == 2


def test_max_items_from_defaults(sample_podcast_episode_list_html: str) -> None:
    """没有 source.max_items 时，使用 defaults.max_items_per_source。"""
    connector = PodcastTranscriptConnector(
        html_by_url=lambda url: sample_podcast_episode_list_html
    )
    source = _make_source()  # max_items=None
    cfg = ResearchArchiveConfig(
        archive_root="/tmp/test",
        defaults=ResearchDefaults(max_items_per_source=3),
    )

    candidates = connector.discover(source, cfg)
    assert len(candidates) == 3


# ---------------------------------------------------------------------------
# 11. empty list fail-soft
# ---------------------------------------------------------------------------


def test_empty_list_fail_soft(sample_podcast_empty_html: str) -> None:
    """空列表页返回空候选列表，不崩溃。"""
    connector = PodcastTranscriptConnector(
        html_by_url=lambda url: sample_podcast_empty_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates == []


# ---------------------------------------------------------------------------
# 12. malformed HTML fail-soft
# ---------------------------------------------------------------------------


def test_malformed_html_fail_soft(sample_podcast_malformed_html: str) -> None:
    """损坏的 HTML 也能解析出能用的候选，不崩溃。"""
    connector = PodcastTranscriptConnector(
        html_by_url=lambda url: sample_podcast_malformed_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # 至少能解析出 episode-1 和 episode-2（无 href / 空 href 的会被跳过）
    titles = [c.title for c in candidates]
    assert "损坏 Episode 1" in titles
    assert "损坏 Episode 2" in titles
    # 无链接 / 空链接的不应出现
    for c in candidates:
        assert c.url
        assert c.canonical_url


# ---------------------------------------------------------------------------
# 13. archiver dry-run with podcast fixture
# ---------------------------------------------------------------------------


def test_archiver_dry_run_with_podcast(
    sample_podcast_episode_list_html: str,
    temp_archive_root: Path,
) -> None:
    """archiver dry-run 能发现 podcast 候选，不抓正文。"""
    from opc_foundation.research.archiver import ResearchArchiver, ResearchInjectors

    cfg = ResearchArchiveConfig(
        archive_root=str(temp_archive_root),
        defaults=ResearchDefaults(max_items_per_source=5),
        sources=[
            ResearchSourceConfig(
                source_id="pod_test",
                source_name="Podcast Test",
                source_type="podcast_transcript",
                url="https://example.com/podcast",
                extraction_profile="podcast_episode_list",
                enabled=True,
                legal_profile="official_public",
                tags=["podcast"],
            ),
        ],
    )

    archiver = ResearchArchiver(
        cfg,
        injectors=ResearchInjectors(
            podcast_html_by_url=lambda url: sample_podcast_episode_list_html,
        ),
    )
    result = archiver.dry_run()

    assert result.mode == "dry_run"
    # fixture 有 5 个 article，1 个无链接被跳过 → 4 个候选
    assert result.candidate_count == 4
    assert result.saved_count == 0  # dry-run 不抓正文
    assert result.new_count == 4


# ---------------------------------------------------------------------------
# 14. archiver run with podcast fixture
# ---------------------------------------------------------------------------


def test_archiver_run_with_podcast(
    sample_podcast_episode_list_html: str,
    sample_podcast_episode_detail_html: str,
    temp_archive_root: Path,
) -> None:
    """archiver run 能从 podcast_transcript 归档文档。"""
    from opc_foundation.research.archiver import ResearchArchiver, ResearchInjectors

    cfg = ResearchArchiveConfig(
        archive_root=str(temp_archive_root),
        defaults=ResearchDefaults(max_items_per_source=5),
        sources=[
            ResearchSourceConfig(
                source_id="pod_test",
                source_name="Podcast Test",
                source_type="podcast_transcript",
                url="https://example.com/podcast",
                extraction_profile="podcast_episode_list",
                enabled=True,
                legal_profile="official_public",
                tags=["podcast"],
            ),
        ],
    )

    # 注入：列表页 HTML + 详情页 HTML
    def podcast_html_injector(url: str) -> str | None:
        if url == "https://example.com/podcast":
            return sample_podcast_episode_list_html
        return None

    def detail_html_injector(url: str) -> str | None:
        # 所有 episode 详情页都返回 transcript fixture
        if "/podcast/episode-" in url:
            return sample_podcast_episode_detail_html
        return None

    archiver = ResearchArchiver(
        cfg,
        injectors=ResearchInjectors(
            podcast_html_by_url=podcast_html_injector,
            http_html=detail_html_injector,
        ),
    )
    result = archiver.run()

    assert result.mode == "run"
    assert result.candidate_count == 4
    # 至少有一些 saved 或 partial
    assert result.saved_count + result.partial_count > 0


# ---------------------------------------------------------------------------
# 15. run 后 documents.jsonl 字段完整
# ---------------------------------------------------------------------------


def test_documents_jsonl_fields_complete(
    sample_podcast_episode_list_html: str,
    sample_podcast_episode_detail_html: str,
    temp_archive_root: Path,
) -> None:
    """run 后 documents.jsonl 字段完整。"""
    import json

    from opc_foundation.research.archiver import ResearchArchiver, ResearchInjectors

    cfg = ResearchArchiveConfig(
        archive_root=str(temp_archive_root),
        defaults=ResearchDefaults(max_items_per_source=5),
        sources=[
            ResearchSourceConfig(
                source_id="pod_test",
                source_name="Podcast Test",
                source_type="podcast_transcript",
                url="https://example.com/podcast",
                extraction_profile="podcast_episode_list",
                enabled=True,
                legal_profile="official_public",
                tags=["podcast"],
            ),
        ],
    )

    archiver = ResearchArchiver(
        cfg,
        injectors=ResearchInjectors(
            podcast_html_by_url=lambda url: sample_podcast_episode_list_html
            if url == "https://example.com/podcast" else None,
            http_html=lambda url: sample_podcast_episode_detail_html
            if "/podcast/episode-" in url else None,
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
    assert doc["source_type"] == "podcast_transcript"
    assert doc["legal_profile"] == "official_public"


# ---------------------------------------------------------------------------
# 16. transcript detail 能归档为 document.md
# ---------------------------------------------------------------------------


def test_transcript_detail_archived_as_markdown(
    sample_podcast_episode_list_html: str,
    sample_podcast_episode_detail_html: str,
    temp_archive_root: Path,
) -> None:
    """transcript 详情页能归档为 document.md。"""
    from opc_foundation.research.archiver import ResearchArchiver, ResearchInjectors

    cfg = ResearchArchiveConfig(
        archive_root=str(temp_archive_root),
        defaults=ResearchDefaults(max_items_per_source=5),
        sources=[
            ResearchSourceConfig(
                source_id="pod_test",
                source_name="Podcast Test",
                source_type="podcast_transcript",
                url="https://example.com/podcast",
                extraction_profile="podcast_episode_list",
                enabled=True,
                legal_profile="official_public",
                tags=["podcast"],
            ),
        ],
    )

    archiver = ResearchArchiver(
        cfg,
        injectors=ResearchInjectors(
            podcast_html_by_url=lambda url: sample_podcast_episode_list_html
            if url == "https://example.com/podcast" else None,
            http_html=lambda url: sample_podcast_episode_detail_html
            if "/podcast/episode-" in url else None,
        ),
    )
    result = archiver.run()

    # 至少有一个文档的 markdown_path 不为空
    saved_with_md = [
        d for d in result.saved_documents if d.markdown_path
    ]
    assert len(saved_with_md) > 0
    # markdown 文件实际存在
    for d in saved_with_md:
        assert Path(d.markdown_path).exists()


# ---------------------------------------------------------------------------
# 17. source failure isolation
# ---------------------------------------------------------------------------


def test_source_failure_isolation(
    sample_podcast_episode_list_html: str,
    sample_podcast_episode_detail_html: str,
    temp_archive_root: Path,
) -> None:
    """单个 podcast source 失败不影响其他 source。"""
    from opc_foundation.research.archiver import ResearchArchiver, ResearchInjectors

    cfg = ResearchArchiveConfig(
        archive_root=str(temp_archive_root),
        defaults=ResearchDefaults(max_items_per_source=5),
        sources=[
            # 这个 source 会失败（HTML 内容为空）
            ResearchSourceConfig(
                source_id="broken_pod",
                source_name="Broken Podcast",
                source_type="podcast_transcript",
                url="https://broken.example.com/podcast",
                extraction_profile="podcast_episode_list",
                enabled=True,
                legal_profile="official_public",
                tags=["podcast"],
            ),
            # 这个 source 会成功
            ResearchSourceConfig(
                source_id="ok_pod",
                source_name="OK Podcast",
                source_type="podcast_transcript",
                url="https://example.com/podcast",
                extraction_profile="podcast_episode_list",
                enabled=True,
                legal_profile="official_public",
                tags=["podcast"],
            ),
        ],
    )

    def podcast_html_injector(url: str) -> str | None:
        if "broken.example.com" in url:
            return ""  # 空内容，触发失败
        if "example.com/podcast" in url:
            return sample_podcast_episode_list_html
        return None

    archiver = ResearchArchiver(
        cfg,
        injectors=ResearchInjectors(
            podcast_html_by_url=podcast_html_injector,
            http_html=lambda url: sample_podcast_episode_detail_html
            if "/podcast/episode-" in url else None,
        ),
    )
    result = archiver.run()

    # broken_pod 失败，ok_pod 成功
    broken_stat = next(s for s in result.source_stats if s["source_id"] == "broken_pod")
    ok_stat = next(s for s in result.source_stats if s["source_id"] == "ok_pod")
    assert broken_stat["status"] == "failed"
    assert ok_stat["status"] in ("healthy", "degraded")
    assert ok_stat["candidate_count"] == 4


# ---------------------------------------------------------------------------
# 18. 配置校验
# ---------------------------------------------------------------------------


def test_validate_config_podcast_feed_requires_feed_url() -> None:
    """podcast_feed profile 缺少 feed_url 和 url 时校验失败。"""
    cfg = ResearchArchiveConfig(
        archive_root="/tmp/test",
        defaults=ResearchDefaults(),
        sources=[
            ResearchSourceConfig(
                source_id="bad_pod",
                source_name="Bad Podcast",
                source_type="podcast_transcript",
                url=None,
                feed_url=None,
                extraction_profile="podcast_feed",
                enabled=False,
                legal_profile="official_public",
            ),
        ],
    )
    errors = validate_research_config(cfg)
    assert any("podcast_feed" in e for e in errors)


def test_validate_config_podcast_episode_list_requires_url() -> None:
    """podcast_episode_list profile 缺少 url 和 base_url 时校验失败。"""
    cfg = ResearchArchiveConfig(
        archive_root="/tmp/test",
        defaults=ResearchDefaults(),
        sources=[
            ResearchSourceConfig(
                source_id="bad_pod",
                source_name="Bad Podcast",
                source_type="podcast_transcript",
                url=None,
                base_url=None,
                extraction_profile="podcast_episode_list",
                enabled=False,
                legal_profile="official_public",
            ),
        ],
    )
    errors = validate_research_config(cfg)
    assert any("podcast_episode_list" in e for e in errors)


def test_validate_config_podcast_transcript_passes() -> None:
    """合法的 podcast_transcript 配置应校验通过。"""
    cfg = ResearchArchiveConfig(
        archive_root="/tmp/test",
        defaults=ResearchDefaults(),
        sources=[
            ResearchSourceConfig(
                source_id="ok_pod_page",
                source_name="OK Podcast Page",
                source_type="podcast_transcript",
                url="https://example.com/podcast",
                extraction_profile="podcast_episode_list",
                enabled=False,
                legal_profile="official_public",
            ),
            ResearchSourceConfig(
                source_id="ok_pod_feed",
                source_name="OK Podcast Feed",
                source_type="podcast_transcript",
                feed_url="https://example.com/feed.xml",
                extraction_profile="podcast_feed",
                enabled=False,
                legal_profile="official_public",
            ),
        ],
    )
    errors = validate_research_config(cfg)
    assert errors == []


# ---------------------------------------------------------------------------
# 19. no business fields in output
# ---------------------------------------------------------------------------


def test_no_business_fields_in_output(sample_podcast_episode_list_html: str) -> None:
    """候选文档不包含任何投研判断字段。"""
    connector = PodcastTranscriptConnector(
        html_by_url=lambda url: sample_podcast_episode_list_html
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
    }
    for field in forbidden_fields:
        assert field not in cand_dict, f"候选文档不应包含业务字段: {field}"


def test_no_business_fields_in_raw_entry(sample_podcast_feed_xml: str) -> None:
    """raw_entry 中也不包含投研判断字段。"""
    connector = PodcastTranscriptConnector(html_by_url=lambda url: sample_podcast_feed_xml)
    source = _make_source(
        url=None,
        feed_url="https://example.com/podcast/feed.xml",
        extraction_profile="podcast_feed",
    )
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
    }
    for key in forbidden_keys:
        assert key not in raw, f"raw_entry 不应包含业务字段: {key}"


# ---------------------------------------------------------------------------
# 20. example config 全部 enabled: false
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


def test_example_config_has_podcast_sources() -> None:
    """example config 包含至少 2 个 podcast_transcript source。"""
    example_path = Path(__file__).parent.parent.parent / "configs" / "research_sources.example.yaml"
    cfg = load_research_config(example_path)
    podcast_sources = [s for s in cfg.sources if s.source_type == "podcast_transcript"]
    assert len(podcast_sources) >= 2, f"example config 应至少有 2 个 podcast_transcript source，实际 {len(podcast_sources)}"


# ---------------------------------------------------------------------------
# 补充：connector 边界
# ---------------------------------------------------------------------------


def test_missing_url_raises() -> None:
    """缺少 url 时抛 ValueError（podcast_episode_list profile）。"""
    connector = PodcastTranscriptConnector()
    source = _make_source(url=None, base_url=None)
    cfg = _make_config()
    with pytest.raises(ValueError, match="缺少 url"):
        connector.discover(source, cfg)


def test_missing_feed_url_raises() -> None:
    """缺少 feed_url 时抛 ValueError（podcast_feed profile）。"""
    connector = PodcastTranscriptConnector()
    source = _make_source(
        url=None,
        feed_url=None,
        extraction_profile="podcast_feed",
    )
    cfg = _make_config()
    with pytest.raises(ValueError, match="缺少 feed_url"):
        connector.discover(source, cfg)


def test_empty_html_raises() -> None:
    """HTML 内容为空时抛 ValueError。"""
    connector = PodcastTranscriptConnector(html_by_url=lambda url: "")
    source = _make_source()
    cfg = _make_config()
    with pytest.raises(ValueError, match="内容为空"):
        connector.discover(source, cfg)


def test_reads_local_file(tmp_path: Path, sample_podcast_episode_list_html: str) -> None:
    """能读取本地 HTML 文件。"""
    html_path = tmp_path / "podcast_list.html"
    html_path.write_text(sample_podcast_episode_list_html, encoding="utf-8")

    connector = PodcastTranscriptConnector()
    source = _make_source(url=str(html_path))
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert len(candidates) == 4


def test_raw_entry_contains_episode_url(sample_podcast_episode_list_html: str) -> None:
    """raw_entry 保留 episode_url 和 profile 用于审计。"""
    connector = PodcastTranscriptConnector(
        html_by_url=lambda url: sample_podcast_episode_list_html
    )
    source = _make_source(extraction_profile="podcast_episode_list")
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    raw = candidates[0].raw_entry
    assert raw["episode_url"] == "https://example.com/podcast/episode-1"
    assert raw["transcript_url"] == "https://example.com/podcast/episode-1"
    assert raw["profile"] == "podcast_episode_list"


def test_raw_entry_contains_duration(sample_podcast_episode_list_html: str) -> None:
    """raw_entry 保留 duration 字段。"""
    connector = PodcastTranscriptConnector(
        html_by_url=lambda url: sample_podcast_episode_list_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # Episode 1 有 duration 28:15
    ep1 = next(c for c in candidates if "Episode 1" in c.title)
    assert ep1.raw_entry["duration"] == "28:15"
