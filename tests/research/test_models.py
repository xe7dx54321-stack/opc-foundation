"""测试 research/models.py —— 数据模型基础行为。"""
from __future__ import annotations

from opc_foundation.research.models import (
    DocumentCandidate,
    ExtractedResearchContent,
    FailedDocument,
    NormalizedDocument,
    ResearchArchiveConfig,
    ResearchDefaults,
    ResearchRunResult,
    ResearchSourceConfig,
    SourceHealth,
)


def test_defaults_default_values() -> None:
    """ResearchDefaults 默认值正确。"""
    d = ResearchDefaults()
    assert d.fetch_timeout_seconds == 20
    assert d.max_items_per_source == 20
    assert d.save_html is True
    assert d.save_markdown is True
    assert d.save_raw is True
    assert d.download_assets is False


def test_source_config_required_fields() -> None:
    """ResearchSourceConfig 必填字段。"""
    s = ResearchSourceConfig(
        source_id="test",
        source_name="Test",
        source_type="rss_feed",
    )
    assert s.enabled is True
    assert s.legal_profile == "unknown"
    assert s.tags == []
    assert s.priority == "normal"


def test_archive_config_defaults() -> None:
    """ResearchArchiveConfig 默认值。"""
    cfg = ResearchArchiveConfig(archive_root="/tmp/test")
    assert cfg.archive_root == "/tmp/test"
    assert cfg.sources == []
    assert isinstance(cfg.defaults, ResearchDefaults)


def test_document_candidate_to_dict_roundtrip() -> None:
    """DocumentCandidate 能转 dict 并还原。"""
    cand = DocumentCandidate(
        source_id="s1",
        source_name="Source 1",
        source_type="rss_feed",
        title="测试标题",
        url="https://example.com/test",
        canonical_url="https://example.com/test",
        tags=["a", "b"],
    )
    d = cand.model_dump()
    cand2 = DocumentCandidate(**d)
    assert cand2.title == cand.title
    assert cand2.tags == ["a", "b"]


def test_normalized_document_status_values() -> None:
    """NormalizedDocument 支持所有 status 值。"""
    for status in ("saved", "duplicate", "partial", "failed", "skipped"):
        doc = NormalizedDocument(
            document_id="rs_xxx",
            source_id="s1",
            source_name="S1",
            source_type="rss_feed",
            title="t",
            url="https://example.com",
            canonical_url="https://example.com",
            published_at=None,
            captured_at="2026-01-01T00:00:00Z",
            updated_at=None,
            author=None,
            summary=None,
            language=None,
            content_type="article",
            legal_profile="unknown",
            tags=[],
            content_hash="abc",
            status=status,
            markdown_path=None,
            html_path=None,
            raw_path=None,
            metadata_path="/tmp/m.json",
            attachments=[],
            extraction_quality="unknown",
            error=None,
        )
        assert doc.status == status


def test_source_health_status_values() -> None:
    """SourceHealth 支持所有 status 值。"""
    for status in ("healthy", "degraded", "failed", "disabled", "unknown"):
        h = SourceHealth(
            source_id="s1",
            source_name="S1",
            checked_at="2026-01-01T00:00:00Z",
            status=status,
        )
        assert h.status == status


def test_failed_document_retryable_default() -> None:
    """FailedDocument 默认 retryable=True。"""
    f = FailedDocument(
        source_id="s1",
        source_name="S1",
        source_type="rss_feed",
        title="t",
        url="https://example.com",
        canonical_url="https://example.com",
        failed_at="2026-01-01T00:00:00Z",
        error="test error",
    )
    assert f.retryable is True
    assert f.retry_count == 0


def test_research_run_result_defaults() -> None:
    """ResearchRunResult 默认计数值为 0。"""
    r = ResearchRunResult(
        run_id="run_test",
        mode="run",
        archive_root="/tmp",
        started_at="2026-01-01T00:00:00Z",
        finished_at="2026-01-01T00:01:00Z",
        source_count=0,
        enabled_source_count=0,
        candidate_count=0,
        new_count=0,
        saved_count=0,
        partial_count=0,
        failed_count=0,
        duplicate_count=0,
        skipped_count=0,
        source_stats=[],
        saved_documents=[],
        failed_documents=[],
        source_health=[],
        warnings=[],
        report_path=None,
        exit_code=0,
    )
    assert r.run_id == "run_test"
    assert r.exit_code == 0


def test_extracted_content_quality_values() -> None:
    """ExtractedResearchContent 支持所有 quality 值。"""
    for q in ("high", "medium", "low", "empty", "unknown"):
        e = ExtractedResearchContent(extraction_quality=q)
        assert e.extraction_quality == q
