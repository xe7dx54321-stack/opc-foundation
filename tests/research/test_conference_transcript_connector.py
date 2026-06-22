"""测试 ConferenceTranscriptConnector。

功能说明（小白解读）：
    本文件覆盖 Phase 2C 的 22 个测试场景，包括：
    - 5 种 extraction_profile 的解析能力
    - 字段提取（published_at / event_date / summary / company / speaker）
    - 相对 URL 转 absolute
    - max_items 限制
    - fail-soft（空列表 / 畸形 HTML）
    - archiver 集成（dry-run / run / source failure isolation）
    - presentation PDF metadata 保存（不下载 PDF）
    - 边界检查（无业务字段 / example config 全部 enabled: false）

    所有测试都基于 fixture，不访问真实网络。
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from opc_foundation.research.config import load_research_config, validate_research_config
from opc_foundation.research.connectors.conference_transcript import (
    ConferenceTranscriptConnector,
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
    url: str | None = "https://example.com/events",
    extraction_profile: str = "conference_event_list",
    max_items: int | None = None,
    base_url: str | None = None,
    source_id: str = "conf_test",
) -> ResearchSourceConfig:
    """构造一个 conference_transcript source 配置。

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
        source_name="Conference Test",
        source_type="conference_transcript",
        url=url,
        base_url=base_url,
        extraction_profile=extraction_profile,
        legal_profile="public_ir",
        tags=["conference", "transcript"],
        max_items=max_items,
    )


def _make_config() -> ResearchArchiveConfig:
    """构造一个最小配置。"""
    return ResearchArchiveConfig(
        archive_root="/tmp/test",
        defaults=ResearchDefaults(max_items_per_source=10),
    )


# ---------------------------------------------------------------------------
# 1. conference_event_list profile
# ---------------------------------------------------------------------------


def test_parses_conference_event_list(sample_conference_event_list_html: str) -> None:
    """conference_event_list 能从 HTML list 提取 candidates。"""
    connector = ConferenceTranscriptConnector(
        html_by_url=lambda url: sample_conference_event_list_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # fixture 有 5 个 article，第 5 个无链接应被跳过
    assert len(candidates) == 4
    assert candidates[0].title == "Event 1: 2026 TMT Conference"
    assert candidates[1].title == "Event 2: Healthcare Summit"


# ---------------------------------------------------------------------------
# 2. event_cards profile
# ---------------------------------------------------------------------------


def test_parses_event_cards() -> None:
    """event_cards 能从 card list 提取 candidates。"""
    html = """
    <html lang="en"><body>
        <div class="card event-card">
            <h3><a href="/events/card-1">卡片 Event 1</a></h3>
            <time datetime="2026-03-15T09:00:00+08:00">2026-03-15</time>
            <p class="summary">卡片摘要一</p>
            <p class="company">卡片公司一</p>
            <p class="speaker">卡片讲者一</p>
        </div>
        <div class="conference-card">
            <h3><a href="/events/card-2">卡片 Event 2</a></h3>
            <time datetime="2026-04-20T10:00:00+08:00">2026-04-20</time>
            <p class="summary">卡片摘要二</p>
        </div>
    </body></html>
    """
    connector = ConferenceTranscriptConnector(html_by_url=lambda url: html)
    source = _make_source(extraction_profile="event_cards")
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert len(candidates) == 2
    assert candidates[0].title == "卡片 Event 1"
    assert candidates[0].summary == "卡片摘要一"
    assert candidates[1].title == "卡片 Event 2"


# ---------------------------------------------------------------------------
# 3. transcript_page profile
# ---------------------------------------------------------------------------


def test_parses_transcript_page(sample_conference_transcript_html: str) -> None:
    """transcript_page 能从单篇 transcript fixture 生成 1 个 candidate。"""
    connector = ConferenceTranscriptConnector(
        html_by_url=lambda url: sample_conference_transcript_html
    )
    source = _make_source(
        url="https://example.com/conference/transcript",
        extraction_profile="transcript_page",
    )
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert len(candidates) == 1
    # 标题优先从 h1 提取
    assert candidates[0].title == "2026 TMT Conference Transcript"
    # url 应等于 source.url
    assert candidates[0].url == "https://example.com/conference/transcript"
    # document_kind 应为 transcript
    assert candidates[0].raw_entry["document_kind"] == "transcript"


# ---------------------------------------------------------------------------
# 4. presentation_page profile
# ---------------------------------------------------------------------------


def test_parses_presentation_page(sample_conference_presentation_page_html: str) -> None:
    """presentation_page 能生成 candidate 并记录 presentation_url/pdf metadata。"""
    connector = ConferenceTranscriptConnector(
        html_by_url=lambda url: sample_conference_presentation_page_html
    )
    source = _make_source(
        url="https://example.com/conference/presentation",
        extraction_profile="presentation_page",
    )
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert len(candidates) == 1
    assert candidates[0].raw_entry["document_kind"] == "presentation"
    # PDF 链接应被记录在 presentation_url
    presentation_url = candidates[0].raw_entry["presentation_url"]
    assert presentation_url is not None
    assert "presentation.pdf" in presentation_url


def test_presentation_page_does_not_download_pdf(
    sample_conference_presentation_page_html: str,
    temp_archive_root: Path,
) -> None:
    """presentation page 不下载 PDF，只保存 metadata。"""
    from opc_foundation.research.archiver import ResearchArchiver, ResearchInjectors

    cfg = ResearchArchiveConfig(
        archive_root=str(temp_archive_root),
        defaults=ResearchDefaults(max_items_per_source=5),
        sources=[
            ResearchSourceConfig(
                source_id="conf_pres",
                source_name="Conference Presentation",
                source_type="conference_transcript",
                url="https://example.com/conference/presentation",
                extraction_profile="presentation_page",
                enabled=True,
                legal_profile="public_ir",
                tags=["conference", "presentation"],
            ),
        ],
    )

    archiver = ResearchArchiver(
        cfg,
        injectors=ResearchInjectors(
            conference_html_by_url=lambda url: sample_conference_presentation_page_html,
            http_html=lambda url: sample_conference_presentation_page_html,
        ),
    )
    result = archiver.run()

    # 应该成功归档（不下载 PDF）
    assert result.saved_count + result.partial_count > 0
    # archive 目录下不应该有 PDF 文件
    pdf_files = list(temp_archive_root.rglob("*.pdf"))
    assert pdf_files == [], f"Phase 2C 不应下载 PDF，但发现: {pdf_files}"


# ---------------------------------------------------------------------------
# 5. webcast_event_page profile
# ---------------------------------------------------------------------------


def test_parses_webcast_event_page(sample_conference_event_detail_html: str) -> None:
    """webcast_event_page 能优先选择 transcript link。"""
    connector = ConferenceTranscriptConnector(
        html_by_url=lambda url: sample_conference_event_detail_html
    )
    source = _make_source(
        url="https://example.com/events/conference-1",
        extraction_profile="webcast_event_page",
    )
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert len(candidates) == 1
    # 应优先选择 transcript link 作为 candidate URL
    assert "transcript" in candidates[0].url
    # document_kind 应为 webcast_event
    assert candidates[0].raw_entry["document_kind"] == "webcast_event"
    # presentation_url 应记录 PDF 链接
    assert candidates[0].raw_entry["presentation_url"] is not None
    assert "presentation.pdf" in candidates[0].raw_entry["presentation_url"]


# ---------------------------------------------------------------------------
# 6. relative URL 转 absolute
# ---------------------------------------------------------------------------


def test_relative_url_canonicalized(sample_conference_event_list_html: str) -> None:
    """相对 URL 应根据 base_url/source.url 转成 absolute。"""
    connector = ConferenceTranscriptConnector(
        html_by_url=lambda url: sample_conference_event_list_html
    )
    source = _make_source(url="https://example.com/events")
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # 相对路径 /events/conference-1 应被转成 absolute
    assert candidates[0].url == "https://example.com/events/conference-1"
    assert candidates[0].canonical_url == "https://example.com/events/conference-1"


def test_relative_url_with_base_url(sample_conference_event_list_html: str) -> None:
    """base_url 也能用于相对链接解析。"""
    connector = ConferenceTranscriptConnector(
        html_by_url=lambda url: sample_conference_event_list_html
    )
    source = _make_source(
        url="https://example.com/events/list",
        base_url="https://example.com",
    )
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates[0].url == "https://example.com/events/conference-1"


# ---------------------------------------------------------------------------
# 7. published_at / event_date 提取
# ---------------------------------------------------------------------------


def test_published_at_from_time_tag(sample_conference_event_list_html: str) -> None:
    """能从 <time datetime="..."> 提取发布时间。"""
    connector = ConferenceTranscriptConnector(
        html_by_url=lambda url: sample_conference_event_list_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates[0].published_at == "2026-03-15T09:00:00+08:00"
    assert candidates[1].published_at == "2026-04-20T10:00:00+08:00"


def test_event_date_extracted(sample_conference_event_list_html: str) -> None:
    """能从 class='event-date' 提取 event_date 进入 raw_entry。"""
    connector = ConferenceTranscriptConnector(
        html_by_url=lambda url: sample_conference_event_list_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates[0].raw_entry["event_date"] == "2026-03-15"
    assert candidates[1].raw_entry["event_date"] == "2026-04-20"


def test_published_at_from_meta_in_transcript_page(
    sample_conference_transcript_html: str,
) -> None:
    """能从 time/meta 提取发布时间（transcript_page profile）。

    小白解读：
        fixture 中同时有 <time datetime="..."> 和 <meta name="date">，
        _extract_published_at 优先查找 <time> 标签（更精确），
        所以提取到的是 time 标签的值。
    """
    connector = ConferenceTranscriptConnector(
        html_by_url=lambda url: sample_conference_transcript_html
    )
    source = _make_source(
        url="https://example.com/conference/transcript",
        extraction_profile="transcript_page",
    )
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # fixture 中 time datetime="2026-03-15T09:00:00+08:00" 优先于 meta name="date"
    assert candidates[0].published_at == "2026-03-15T09:00:00+08:00"


# ---------------------------------------------------------------------------
# 8. summary 提取
# ---------------------------------------------------------------------------


def test_summary_from_class(sample_conference_event_list_html: str) -> None:
    """能从 class='summary' 提取摘要。"""
    connector = ConferenceTranscriptConnector(
        html_by_url=lambda url: sample_conference_event_list_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates[0].summary == "Technology, Media & Telecom conference with keynote and panels."


def test_summary_from_meta_in_transcript_page(
    sample_conference_transcript_html: str,
) -> None:
    """能从 <meta name='description'> 提取摘要（transcript_page profile）。"""
    connector = ConferenceTranscriptConnector(
        html_by_url=lambda url: sample_conference_transcript_html
    )
    source = _make_source(
        url="https://example.com/conference/transcript",
        extraction_profile="transcript_page",
    )
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates[0].summary is not None
    assert "transcript" in candidates[0].summary.lower()


# ---------------------------------------------------------------------------
# 9. author / company / speaker 提取
# ---------------------------------------------------------------------------


def test_author_from_speaker(sample_conference_event_list_html: str) -> None:
    """author 优先从 speaker 提取，其次 company。"""
    connector = ConferenceTranscriptConnector(
        html_by_url=lambda url: sample_conference_event_list_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # Event 1 有 speaker
    assert candidates[0].author == "Keynote by Jane Doe"
    # Event 3 只有 company，没有 speaker
    ep3 = next(c for c in candidates if "Event 3" in c.title)
    assert ep3.author == "Global Tech Research"


def test_company_in_raw_entry(sample_conference_event_list_html: str) -> None:
    """company 进入 raw_entry。"""
    connector = ConferenceTranscriptConnector(
        html_by_url=lambda url: sample_conference_event_list_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates[0].raw_entry["company"] == "Sample Bank Research"
    assert candidates[1].raw_entry["company"] == "Another Bank"


def test_speaker_in_raw_entry(sample_conference_event_list_html: str) -> None:
    """speaker 进入 raw_entry。"""
    connector = ConferenceTranscriptConnector(
        html_by_url=lambda url: sample_conference_event_list_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates[0].raw_entry["speaker"] == "Keynote by Jane Doe"
    # Event 3 没有 speaker
    ep3 = next(c for c in candidates if "Event 3" in c.title)
    assert ep3.raw_entry["speaker"] is None


# ---------------------------------------------------------------------------
# 10. tags 和 legal_profile 继承 source
# ---------------------------------------------------------------------------


def test_inherits_source_tags_and_legal_profile(
    sample_conference_event_list_html: str,
) -> None:
    """候选文档继承 source 的 tags 和 legal_profile。"""
    connector = ConferenceTranscriptConnector(
        html_by_url=lambda url: sample_conference_event_list_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    for c in candidates:
        assert c.legal_profile == "public_ir"
        assert c.tags == ["conference", "transcript"]
        assert c.source_id == "conf_test"
        assert c.source_type == "conference_transcript"


# ---------------------------------------------------------------------------
# 11. max_items 生效
# ---------------------------------------------------------------------------


def test_respects_max_items(sample_conference_event_list_html: str) -> None:
    """max_items 限制候选数量。"""
    connector = ConferenceTranscriptConnector(
        html_by_url=lambda url: sample_conference_event_list_html
    )
    source = _make_source(max_items=2)
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert len(candidates) == 2


def test_max_items_from_defaults(sample_conference_event_list_html: str) -> None:
    """没有 source.max_items 时，使用 defaults.max_items_per_source。"""
    connector = ConferenceTranscriptConnector(
        html_by_url=lambda url: sample_conference_event_list_html
    )
    source = _make_source()  # max_items=None
    cfg = ResearchArchiveConfig(
        archive_root="/tmp/test",
        defaults=ResearchDefaults(max_items_per_source=3),
    )

    candidates = connector.discover(source, cfg)
    assert len(candidates) == 3


# ---------------------------------------------------------------------------
# 12. empty list fail-soft
# ---------------------------------------------------------------------------


def test_empty_list_fail_soft(sample_conference_empty_html: str) -> None:
    """空列表页返回空候选列表，不崩溃。"""
    connector = ConferenceTranscriptConnector(
        html_by_url=lambda url: sample_conference_empty_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates == []


# ---------------------------------------------------------------------------
# 13. malformed HTML fail-soft
# ---------------------------------------------------------------------------


def test_malformed_html_fail_soft(sample_conference_malformed_html: str) -> None:
    """损坏的 HTML 也能解析出能用的候选，不崩溃。"""
    connector = ConferenceTranscriptConnector(
        html_by_url=lambda url: sample_conference_malformed_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # 至少能解析出 malformed-1 和 malformed-4（无 href / 空 href 的会被跳过）
    titles = [c.title for c in candidates]
    assert "损坏 Event 1: Unclosed Time Tag" in titles
    assert "损坏 Event 4: Normal Entry" in titles
    # 无链接 / 空链接的不应出现
    for c in candidates:
        assert c.url
        assert c.canonical_url


# ---------------------------------------------------------------------------
# 14. archiver dry-run with conference fixture
# ---------------------------------------------------------------------------


def test_archiver_dry_run_with_conference(
    sample_conference_event_list_html: str,
    temp_archive_root: Path,
) -> None:
    """archiver dry-run 能发现 conference 候选，不抓正文。"""
    from opc_foundation.research.archiver import ResearchArchiver, ResearchInjectors

    cfg = ResearchArchiveConfig(
        archive_root=str(temp_archive_root),
        defaults=ResearchDefaults(max_items_per_source=5),
        sources=[
            ResearchSourceConfig(
                source_id="conf_test",
                source_name="Conference Test",
                source_type="conference_transcript",
                url="https://example.com/events",
                extraction_profile="conference_event_list",
                enabled=True,
                legal_profile="public_ir",
                tags=["conference"],
            ),
        ],
    )

    archiver = ResearchArchiver(
        cfg,
        injectors=ResearchInjectors(
            conference_html_by_url=lambda url: sample_conference_event_list_html,
        ),
    )
    result = archiver.dry_run()

    assert result.mode == "dry_run"
    # fixture 有 5 个 article，1 个无链接被跳过 → 4 个候选
    assert result.candidate_count == 4
    assert result.saved_count == 0  # dry-run 不抓正文
    assert result.new_count == 4


# ---------------------------------------------------------------------------
# 15. archiver run with conference fixture
# ---------------------------------------------------------------------------


def test_archiver_run_with_conference(
    sample_conference_event_list_html: str,
    sample_conference_transcript_html: str,
    temp_archive_root: Path,
) -> None:
    """archiver run 能从 conference_transcript 归档文档。"""
    from opc_foundation.research.archiver import ResearchArchiver, ResearchInjectors

    cfg = ResearchArchiveConfig(
        archive_root=str(temp_archive_root),
        defaults=ResearchDefaults(max_items_per_source=5),
        sources=[
            ResearchSourceConfig(
                source_id="conf_test",
                source_name="Conference Test",
                source_type="conference_transcript",
                url="https://example.com/events",
                extraction_profile="conference_event_list",
                enabled=True,
                legal_profile="public_ir",
                tags=["conference"],
            ),
        ],
    )

    # 注入：列表页 HTML + 详情页 HTML
    def conference_html_injector(url: str) -> str | None:
        if url == "https://example.com/events":
            return sample_conference_event_list_html
        return None

    def detail_html_injector(url: str) -> str | None:
        # 所有 event 详情页都返回 transcript fixture
        if "/events/conference-" in url:
            return sample_conference_transcript_html
        return None

    archiver = ResearchArchiver(
        cfg,
        injectors=ResearchInjectors(
            conference_html_by_url=conference_html_injector,
            http_html=detail_html_injector,
        ),
    )
    result = archiver.run()

    assert result.mode == "run"
    assert result.candidate_count == 4
    # 至少有一些 saved 或 partial
    assert result.saved_count + result.partial_count > 0


# ---------------------------------------------------------------------------
# 16. run 后 documents.jsonl 字段完整
# ---------------------------------------------------------------------------


def test_documents_jsonl_fields_complete(
    sample_conference_event_list_html: str,
    sample_conference_transcript_html: str,
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
                source_id="conf_test",
                source_name="Conference Test",
                source_type="conference_transcript",
                url="https://example.com/events",
                extraction_profile="conference_event_list",
                enabled=True,
                legal_profile="public_ir",
                tags=["conference"],
            ),
        ],
    )

    archiver = ResearchArchiver(
        cfg,
        injectors=ResearchInjectors(
            conference_html_by_url=lambda url: sample_conference_event_list_html
            if url == "https://example.com/events" else None,
            http_html=lambda url: sample_conference_transcript_html
            if "/events/conference-" in url else None,
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
    assert doc["source_type"] == "conference_transcript"
    assert doc["legal_profile"] == "public_ir"


# ---------------------------------------------------------------------------
# 17. transcript detail 能归档为 document.md
# ---------------------------------------------------------------------------


def test_transcript_detail_archived_as_markdown(
    sample_conference_event_list_html: str,
    sample_conference_transcript_html: str,
    temp_archive_root: Path,
) -> None:
    """transcript 详情页能归档为 document.md。"""
    from opc_foundation.research.archiver import ResearchArchiver, ResearchInjectors

    cfg = ResearchArchiveConfig(
        archive_root=str(temp_archive_root),
        defaults=ResearchDefaults(max_items_per_source=5),
        sources=[
            ResearchSourceConfig(
                source_id="conf_test",
                source_name="Conference Test",
                source_type="conference_transcript",
                url="https://example.com/events",
                extraction_profile="conference_event_list",
                enabled=True,
                legal_profile="public_ir",
                tags=["conference"],
            ),
        ],
    )

    archiver = ResearchArchiver(
        cfg,
        injectors=ResearchInjectors(
            conference_html_by_url=lambda url: sample_conference_event_list_html
            if url == "https://example.com/events" else None,
            http_html=lambda url: sample_conference_transcript_html
            if "/events/conference-" in url else None,
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
# 18. presentation page 不下载 PDF（已在 test_presentation_page_does_not_download_pdf 中覆盖）
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# 19. source failure isolation
# ---------------------------------------------------------------------------


def test_source_failure_isolation(
    sample_conference_event_list_html: str,
    sample_conference_transcript_html: str,
    temp_archive_root: Path,
) -> None:
    """单个 conference source 失败不影响其他 source。"""
    from opc_foundation.research.archiver import ResearchArchiver, ResearchInjectors

    cfg = ResearchArchiveConfig(
        archive_root=str(temp_archive_root),
        defaults=ResearchDefaults(max_items_per_source=5),
        sources=[
            # 这个 source 会失败（HTML 内容为空）
            ResearchSourceConfig(
                source_id="broken_conf",
                source_name="Broken Conference",
                source_type="conference_transcript",
                url="https://broken.example.com/events",
                extraction_profile="conference_event_list",
                enabled=True,
                legal_profile="public_ir",
                tags=["conference"],
            ),
            # 这个 source 会成功
            ResearchSourceConfig(
                source_id="ok_conf",
                source_name="OK Conference",
                source_type="conference_transcript",
                url="https://example.com/events",
                extraction_profile="conference_event_list",
                enabled=True,
                legal_profile="public_ir",
                tags=["conference"],
            ),
        ],
    )

    def conference_html_injector(url: str) -> str | None:
        if "broken.example.com" in url:
            return ""  # 空内容，触发失败
        if "example.com/events" in url:
            return sample_conference_event_list_html
        return None

    archiver = ResearchArchiver(
        cfg,
        injectors=ResearchInjectors(
            conference_html_by_url=conference_html_injector,
            http_html=lambda url: sample_conference_transcript_html
            if "/events/conference-" in url else None,
        ),
    )
    result = archiver.run()

    # broken_conf 失败，ok_conf 成功
    broken_stat = next(s for s in result.source_stats if s["source_id"] == "broken_conf")
    ok_stat = next(s for s in result.source_stats if s["source_id"] == "ok_conf")
    assert broken_stat["status"] == "failed"
    assert ok_stat["status"] in ("healthy", "degraded")
    assert ok_stat["candidate_count"] == 4


# ---------------------------------------------------------------------------
# 20. 配置校验
# ---------------------------------------------------------------------------


def test_validate_config_conference_requires_url() -> None:
    """conference_transcript 缺少 url 和 base_url 时校验失败。"""
    cfg = ResearchArchiveConfig(
        archive_root="/tmp/test",
        defaults=ResearchDefaults(),
        sources=[
            ResearchSourceConfig(
                source_id="bad_conf",
                source_name="Bad Conference",
                source_type="conference_transcript",
                url=None,
                base_url=None,
                extraction_profile="conference_event_list",
                enabled=False,
                legal_profile="public_ir",
            ),
        ],
    )
    errors = validate_research_config(cfg)
    assert any("conference_transcript" in e for e in errors)


def test_validate_config_conference_passes() -> None:
    """合法的 conference_transcript 配置应校验通过。"""
    cfg = ResearchArchiveConfig(
        archive_root="/tmp/test",
        defaults=ResearchDefaults(),
        sources=[
            ResearchSourceConfig(
                source_id="ok_conf_list",
                source_name="OK Conference List",
                source_type="conference_transcript",
                url="https://example.com/events",
                extraction_profile="conference_event_list",
                enabled=False,
                legal_profile="public_ir",
            ),
            ResearchSourceConfig(
                source_id="ok_conf_transcript",
                source_name="OK Conference Transcript",
                source_type="conference_transcript",
                url="https://example.com/conference/transcript",
                extraction_profile="transcript_page",
                enabled=False,
                legal_profile="public_ir",
            ),
        ],
    )
    errors = validate_research_config(cfg)
    assert errors == []


# ---------------------------------------------------------------------------
# 21. no business fields in output
# ---------------------------------------------------------------------------


def test_no_business_fields_in_output(sample_conference_event_list_html: str) -> None:
    """候选文档不包含任何投研判断字段。"""
    connector = ConferenceTranscriptConnector(
        html_by_url=lambda url: sample_conference_event_list_html
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


def test_no_business_fields_in_raw_entry(sample_conference_event_list_html: str) -> None:
    """raw_entry 中也不包含投研判断字段。"""
    connector = ConferenceTranscriptConnector(
        html_by_url=lambda url: sample_conference_event_list_html
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
    }
    for key in forbidden_keys:
        assert key not in raw, f"raw_entry 不应包含业务字段: {key}"


# ---------------------------------------------------------------------------
# 22. example config 全部 enabled: false
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


def test_example_config_has_conference_sources() -> None:
    """example config 包含至少 2 个 conference_transcript source。"""
    example_path = Path(__file__).parent.parent.parent / "configs" / "research_sources.example.yaml"
    cfg = load_research_config(example_path)
    conf_sources = [s for s in cfg.sources if s.source_type == "conference_transcript"]
    assert len(conf_sources) >= 2, f"example config 应至少有 2 个 conference_transcript source，实际 {len(conf_sources)}"


# ---------------------------------------------------------------------------
# 补充：connector 边界
# ---------------------------------------------------------------------------


def test_missing_url_raises() -> None:
    """缺少 url 时抛 ValueError。"""
    connector = ConferenceTranscriptConnector()
    source = _make_source(url=None, base_url=None)
    cfg = _make_config()
    with pytest.raises(ValueError, match="缺少 url"):
        connector.discover(source, cfg)


def test_empty_html_raises() -> None:
    """HTML 内容为空时抛 ValueError。"""
    connector = ConferenceTranscriptConnector(html_by_url=lambda url: "")
    source = _make_source()
    cfg = _make_config()
    with pytest.raises(ValueError, match="内容为空"):
        connector.discover(source, cfg)


def test_reads_local_file(tmp_path: Path, sample_conference_event_list_html: str) -> None:
    """能读取本地 HTML 文件。"""
    html_path = tmp_path / "conference_list.html"
    html_path.write_text(sample_conference_event_list_html, encoding="utf-8")

    connector = ConferenceTranscriptConnector()
    source = _make_source(url=str(html_path))
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert len(candidates) == 4


def test_raw_entry_contains_event_url(sample_conference_event_list_html: str) -> None:
    """raw_entry 保留 event_url 和 profile 用于审计。"""
    connector = ConferenceTranscriptConnector(
        html_by_url=lambda url: sample_conference_event_list_html
    )
    source = _make_source(extraction_profile="conference_event_list")
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    raw = candidates[0].raw_entry
    assert raw["event_url"] == "https://example.com/events/conference-1"
    assert raw["transcript_url"] == "https://example.com/events/conference-1"
    assert raw["profile"] == "conference_event_list"


def test_raw_entry_contains_event_name(sample_conference_event_list_html: str) -> None:
    """raw_entry 保留 event_name 字段。"""
    connector = ConferenceTranscriptConnector(
        html_by_url=lambda url: sample_conference_event_list_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates[0].raw_entry["event_name"] == "2026 TMT Conference"
    assert candidates[1].raw_entry["event_name"] == "Healthcare Summit 2026"
