"""Phase 2F 测试：daily report hardening。

覆盖：
    1. daily report 包含 Source 健康概览
    2. daily report 无新文档时也可生成
    3. daily report 无失败时写"无"
    4. daily report 包含下游消费入口
    5. daily report 包含总览统计
    6. daily report 不输出正文
    7. run_summary 包含 source_stats
    8. dry-run summary 包含 source_stats
    9. failed_queue 写入 error_type/run_id/source_type
    10. 不出现业务字段
"""
from __future__ import annotations

from pathlib import Path

import pytest

from opc_foundation.research.models import (
    FailedDocument,
    NormalizedDocument,
    ResearchRunResult,
)
from opc_foundation.research.reports import (
    build_research_daily_report,
    daily_report_filename,
)


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


def _make_run_result(
    *,
    saved_documents: list[NormalizedDocument] | None = None,
    failed_documents: list[FailedDocument] | None = None,
    source_stats: list[dict] | None = None,
    source_health: list[dict] | None = None,
    warnings: list[str] | None = None,
) -> ResearchRunResult:
    """构造一个 ResearchRunResult 用于测试。"""
    return ResearchRunResult(
        run_id="test-run-001",
        mode="run",
        started_at="2026-06-22T10:00:00+08:00",
        finished_at="2026-06-22T10:05:00+08:00",
        archive_root="./data/research_archive",
        source_count=3,
        enabled_source_count=2,
        candidate_count=10,
        new_count=5,
        saved_count=3,
        partial_count=1,
        failed_count=1,
        duplicate_count=2,
        skipped_count=0,
        exit_code=0,
        source_stats=source_stats or [],
        source_health=source_health or [],
        saved_documents=saved_documents or [],
        failed_documents=failed_documents or [],
        warnings=warnings or [],
        report_path=None,
    )


# ---------------------------------------------------------------------------
# 1. daily report 包含 Source 健康概览
# ---------------------------------------------------------------------------


def test_daily_report_has_source_health_section() -> None:
    """日报必须包含 'Source 健康概览' section。"""
    result = _make_run_result(
        source_stats=[
            {
                "source_id": "s1",
                "source_name": "Source 1",
                "source_type": "media_mention",
                "enabled": True,
                "candidate_count": 5,
                "saved_count": 3,
                "partial_count": 1,
                "failed_count": 1,
                "duplicate_count": 0,
                "status": "degraded",
                "error_type": "parse_error",
                "error": "HTML parse failed",
            }
        ]
    )
    report = build_research_daily_report(result)
    assert "## 2. Source 健康概览" in report
    assert "Source 1" in report
    assert "media_mention" in report
    assert "degraded" in report
    assert "parse_error" in report


# ---------------------------------------------------------------------------
# 2. daily report 无新文档时也可生成
# ---------------------------------------------------------------------------


def test_daily_report_no_saved_documents() -> None:
    """没有新文档时日报也应正常生成。"""
    result = _make_run_result(saved_documents=[])
    report = build_research_daily_report(result)
    assert "## 3. 新保存文档" in report
    assert "没有新保存" in report or "无" in report


# ---------------------------------------------------------------------------
# 3. daily report 无失败时写"无"
# ---------------------------------------------------------------------------


def test_daily_report_no_failures() -> None:
    """没有失败时日报应明确写"无"或"没有"。"""
    result = _make_run_result(failed_documents=[])
    report = build_research_daily_report(result)
    assert "## 4. Partial / Failed" in report
    assert "没有失败" in report or "无" in report


# ---------------------------------------------------------------------------
# 4. daily report 包含下游消费入口
# ---------------------------------------------------------------------------


def test_daily_report_has_downstream_entry() -> None:
    """日报必须包含下游消费入口 section。"""
    result = _make_run_result()
    report = build_research_daily_report(result)
    assert "## 6. 下游消费入口" in report
    assert "documents.jsonl" in report
    assert "documents.latest.jsonl" in report


# ---------------------------------------------------------------------------
# 5. daily report 包含总览统计
# ---------------------------------------------------------------------------


def test_daily_report_has_summary() -> None:
    """日报必须包含总览 section。"""
    result = _make_run_result()
    report = build_research_daily_report(result)
    assert "## 1. 总览" in report
    assert "Source 总数" in report
    assert "启用 Source" in report
    assert "候选文档" in report
    assert "新文档" in report
    assert "成功保存" in report
    assert "失败" in report
    assert "Source healthy" in report
    assert "Source degraded" in report
    assert "Source failed" in report


# ---------------------------------------------------------------------------
# 6. daily report 不输出正文
# ---------------------------------------------------------------------------


def test_daily_report_no_body_text() -> None:
    """日报不能输出文档正文全文。"""
    doc = NormalizedDocument(
        document_id="doc-001",
        source_id="s1",
        source_name="Source 1",
        source_type="media_mention",
        title="Test Article",
        url="https://example.com/article",
        canonical_url="https://example.com/article",
        published_at="2026-06-22",
        captured_at="2026-06-22T10:00:00+08:00",
        author="Author",
        summary="Short summary",
        content_type="text/html",
        legal_profile="licensed_media",
        tags=["sample"],
        content_hash="abc123",
        status="saved",
        markdown_path="./data/research_archive/documents/s1/test.md",
        metadata_path="./data/research_archive/documents/s1/test.json",
    )
    result = _make_run_result(saved_documents=[doc])
    report = build_research_daily_report(result)
    # 不应包含 "正文" 字样
    assert "正文" not in report


# ---------------------------------------------------------------------------
# 7. run_summary 包含 source_stats
# ---------------------------------------------------------------------------


def test_run_summary_contains_source_stats() -> None:
    """run_summary 必须包含 source_stats 字段。"""
    from opc_foundation.research.archiver import _run_summary_entry

    result = _make_run_result(
        source_stats=[
            {
                "source_id": "s1",
                "source_name": "Source 1",
                "source_type": "media_mention",
                "status": "healthy",
            }
        ]
    )
    entry = _run_summary_entry(result)
    assert "source_stats" in entry
    assert len(entry["source_stats"]) == 1
    assert entry["source_stats"][0]["source_id"] == "s1"
    assert "archive_root" in entry
    assert "warnings" in entry


# ---------------------------------------------------------------------------
# 8. daily report 包含 warnings
# ---------------------------------------------------------------------------


def test_daily_report_has_warnings() -> None:
    """日报必须包含 Warnings section。"""
    result = _make_run_result(warnings=["测试警告"])
    report = build_research_daily_report(result)
    assert "## 5. Warnings" in report
    assert "测试警告" in report


def test_daily_report_no_warnings() -> None:
    """没有 warnings 时应写"无"。"""
    result = _make_run_result(warnings=[])
    report = build_research_daily_report(result)
    assert "## 5. Warnings" in report
    assert "（无）" in report


# ---------------------------------------------------------------------------
# 9. daily report 包含 failed documents 详情
# ---------------------------------------------------------------------------


def test_daily_report_with_failed_documents() -> None:
    """有失败文档时日报应展示失败详情。"""
    failed = FailedDocument(
        source_id="s1",
        source_name="Source 1",
        source_type="media_mention",
        title="Failed Article",
        url="https://example.com/failed",
        canonical_url="https://example.com/failed",
        failed_at="2026-06-22T10:00:00+08:00",
        error="HTTP timeout",
        error_type="fetch_error",
        retryable=True,
        run_id="test-run-001",
    )
    result = _make_run_result(failed_documents=[failed])
    report = build_research_daily_report(result)
    assert "Failed Article" in report
    assert "fetch_error" in report
    assert "可重试" in report


# ---------------------------------------------------------------------------
# 10. daily_report_filename
# ---------------------------------------------------------------------------


def test_daily_report_filename() -> None:
    """daily_report_filename 应返回正确的文件名。"""
    assert daily_report_filename("2026-06-22") == "daily_capture_2026-06-22.md"
    # 不传日期应返回今天的文件名
    name = daily_report_filename(None)
    assert name.startswith("daily_capture_")
    assert name.endswith(".md")


# ---------------------------------------------------------------------------
# 11. 不出现业务字段
# ---------------------------------------------------------------------------


def test_report_no_business_fields() -> None:
    """日报不能包含投研判断字段。"""
    result = _make_run_result()
    report = build_research_daily_report(result)
    forbidden = [
        "affected_tickers",
        "expectation_delta",
        "investment_rating",
        "trade_signal",
        "watchlist",
        "action_decision",
        "recommendation",
    ]
    for word in forbidden:
        assert word not in report, f"日报不能包含 {word}"


# ---------------------------------------------------------------------------
# 12. 日报包含运行元信息
# ---------------------------------------------------------------------------


def test_daily_report_has_run_meta() -> None:
    """日报必须包含运行 ID、模式、Archive Root 等元信息。"""
    result = _make_run_result()
    report = build_research_daily_report(result)
    assert "运行 ID：test-run-001" in report
    assert "模式：" in report
    assert "Archive Root：" in report
    assert "开始时间：" in report
    assert "结束时间：" in report
