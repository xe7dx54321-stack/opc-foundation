"""测试 research/reports.py —— 中文日报。"""
from __future__ import annotations

from opc_foundation.research.models import (
    FailedDocument,
    NormalizedDocument,
    ResearchRunResult,
)
from opc_foundation.research.reports import (
    build_research_daily_report,
    daily_report_filename,
)


def _make_result(
    saved_count: int = 1,
    failed_count: int = 0,
    saved_documents: list[NormalizedDocument] | None = None,
    failed_documents: list[FailedDocument] | None = None,
) -> ResearchRunResult:
    return ResearchRunResult(
        run_id="run_test123",
        mode="run",
        archive_root="/tmp/test",
        started_at="2026-01-15T09:00:00Z",
        finished_at="2026-01-15T09:05:00Z",
        source_count=3,
        enabled_source_count=2,
        candidate_count=5,
        new_count=3,
        saved_count=saved_count,
        partial_count=0,
        failed_count=failed_count,
        duplicate_count=2,
        skipped_count=0,
        source_stats=[
            {
                "source_id": "s1",
                "source_name": "Source 1",
                "source_type": "rss_feed",
                "candidate_count": 3,
                "saved_count": 1,
                "failed_count": 0,
                "status": "healthy",
                "error": None,
            },
        ],
        saved_documents=saved_documents or [],
        failed_documents=failed_documents or [],
        source_health=[
            {
                "source_id": "s1",
                "source_name": "Source 1",
                "checked_at": "2026-01-15T09:00:00Z",
                "status": "healthy",
                "last_success_at": "2026-01-15T09:00:00Z",
                "last_failure_at": None,
                "consecutive_failures": 0,
                "candidate_count_last_run": 3,
                "saved_count_last_run": 1,
            },
        ],
        warnings=[],
        report_path=None,
        exit_code=0,
    )


def test_daily_report_filename() -> None:
    """文件名格式正确。"""
    assert daily_report_filename("2026-01-15") == "daily_capture_2026-01-15.md"
    assert daily_report_filename() == daily_report_filename(None)  # 默认今天


def test_report_contains_chinese_header() -> None:
    """日报包含中文标题。"""
    result = _make_result()
    report = build_research_daily_report(result)
    assert "Research Source Foundation 采集日报" in report
    assert "总览" in report
    assert "Source 健康概览" in report
    assert "新保存文档" in report


def test_report_contains_overview_numbers() -> None:
    """总览数字正确。"""
    result = _make_result(saved_count=2, failed_count=1)
    report = build_research_daily_report(result)
    assert "Source 总数：3" in report
    assert "启用 Source：2" in report
    assert "候选文档：5" in report
    assert "成功保存：2" in report
    assert "失败：1" in report
    assert "重复：2" in report


def test_report_contains_saved_documents() -> None:
    """日报列出保存的文档。"""
    doc = NormalizedDocument(
        document_id="rs_1",
        source_id="s1",
        source_name="Source 1",
        source_type="rss_feed",
        title="测试文章标题",
        url="https://example.com/article-1",
        canonical_url="https://example.com/article-1",
        published_at="2026-01-15T09:00:00Z",
        captured_at="2026-01-15T09:00:00Z",
        updated_at=None,
        author=None,
        summary=None,
        language=None,
        content_type="article",
        legal_profile="official_public",
        tags=[],
        content_hash="abc",
        status="saved",
        markdown_path="/tmp/article.md",
        html_path=None,
        raw_path=None,
        metadata_path="/tmp/m.json",
        attachments=[],
        extraction_quality="high",
        error=None,
    )
    result = _make_result(saved_documents=[doc])
    report = build_research_daily_report(result)
    assert "测试文章标题" in report
    assert "/tmp/article.md" in report


def test_report_contains_failed_documents() -> None:
    """日报列出失败文档。"""
    failed = FailedDocument(
        source_id="s1",
        source_name="Source 1",
        source_type="rss_feed",
        title="失败的文章",
        url="https://example.com/failed",
        canonical_url="https://example.com/failed",
        failed_at="2026-01-15T09:00:00Z",
        error="连接超时",
        retryable=True,
    )
    result = _make_result(failed_count=1, failed_documents=[failed])
    report = build_research_daily_report(result)
    assert "失败的文章" in report
    assert "连接超时" in report
    assert "可重试" in report


def test_report_contains_source_health() -> None:
    """日报包含 source health 表格。"""
    result = _make_result()
    report = build_research_daily_report(result)
    assert "Source 健康概览" in report
    assert "healthy" in report


def test_report_contains_warnings() -> None:
    """日报包含警告。"""
    result = _make_result()
    result.warnings = ["测试警告信息"]
    report = build_research_daily_report(result)
    assert "警告" in report
    assert "测试警告信息" in report


def test_report_empty_result() -> None:
    """空结果也能生成报告。"""
    result = ResearchRunResult(
        run_id="empty",
        mode="dry_run",
        archive_root="/tmp",
        started_at="2026-01-15T09:00:00Z",
        finished_at="2026-01-15T09:00:00Z",
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
    report = build_research_daily_report(result)
    assert "本次没有新保存的文档" in report
    assert "本次没有失败文档" in report
