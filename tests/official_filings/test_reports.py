"""测试 official_filings 的日报生成。"""
from __future__ import annotations

from opc_foundation.official_filings.models import (
    FilingRunResult,
    FilingSourceHealth,
    HEALTH_STATUS_HEALTHY,
    NormalizedFiling,
    FILING_STATUS_SAVED,
)
from opc_foundation.official_filings.reports import (
    build_filing_daily_report,
    daily_report_filename,
)


# ---------------------------------------------------------------------------
# daily_report_filename
# ---------------------------------------------------------------------------


def test_daily_report_filename_with_date() -> None:
    """给定 finished_at 时生成正确的文件名。"""
    name = daily_report_filename("2024-01-15T10:30:00Z")
    assert name == "daily_filing_2024-01-15.md"


def test_daily_report_filename_empty() -> None:
    """空字符串时用今天的日期。"""
    name = daily_report_filename("")
    assert name.startswith("daily_filing_")
    assert name.endswith(".md")
    # 应该包含今天的日期格式
    assert len(name) == len("daily_filing_YYYY-MM-DD.md")


# ---------------------------------------------------------------------------
# build_filing_daily_report
# ---------------------------------------------------------------------------


def test_report_contains_all_sections() -> None:
    """日报包含所有必需的章节。"""
    result = FilingRunResult(
        run_id="run_test_001",
        mode="run",
        archive_root="./data/official_filings",
        started_at="2024-01-15T00:00:00Z",
        finished_at="2024-01-15T01:00:00Z",
        source_count=3,
        enabled_source_count=2,
        candidate_count=10,
        saved_count=8,
        duplicate_count=1,
        failed_count=1,
    )

    report = build_filing_daily_report(result)

    # 标题
    assert "Official Filing Foundation 采集日报" in report
    # 总览
    assert "## 1. 总览" in report
    assert "Source 总数：3" in report
    assert "候选披露：10" in report
    assert "新保存：8" in report
    # Source 健康概览
    assert "## 2. Source 健康概览" in report
    # 新保存披露
    assert "## 3. 新保存披露" in report
    # Partial / Failed
    assert "## 4. Partial / Failed" in report
    # Warnings
    assert "## 5. Warnings" in report
    # 下游消费入口
    assert "## 6. 下游消费入口" in report
    assert "filings.jsonl" in report
    assert "filings.latest.jsonl" in report


def test_report_with_saved_filings() -> None:
    """有保存的披露时，报告中包含披露列表。"""
    filing = NormalizedFiling(
        filing_id="of_test001",
        source_id="test_sec",
        source_type="sec_edgar",
        issuer_name="Apple Inc.",
        issuer_code="320193",
        filing_type="10-K",
        filing_title="10-K Annual Report",
        filing_date="2023-10-26",
        content_hash="abc123",
        canonical_key="test_key",
        metadata_path="metadata/of_test001.json",
        created_at="2024-01-15T00:00:00Z",
        status=FILING_STATUS_SAVED,
    )

    result = FilingRunResult(
        run_id="run_test_002",
        mode="run",
        archive_root="./data/test",
        started_at="2024-01-15T00:00:00Z",
        finished_at="2024-01-15T01:00:00Z",
        source_count=1,
        enabled_source_count=1,
        candidate_count=1,
        saved_count=1,
        saved_filings=[filing],
    )

    report = build_filing_daily_report(result)
    assert "Apple Inc." in report
    assert "10-K" in report
    assert "10-K Annual Report" in report


def test_report_no_saved_filings() -> None:
    """没有新保存时也有明确说明。"""
    result = FilingRunResult(
        run_id="run_test_003",
        mode="run",
        archive_root="./data/test",
        started_at="2024-01-15T00:00:00Z",
        finished_at="2024-01-15T01:00:00Z",
        source_count=1,
        enabled_source_count=1,
    )

    report = build_filing_daily_report(result)
    assert "本次无新保存的披露。" in report


def test_report_no_failures() -> None:
    """没有失败时也有明确说明。"""
    result = FilingRunResult(
        run_id="run_test_004",
        mode="run",
        archive_root="./data/test",
        started_at="2024-01-15T00:00:00Z",
        finished_at="2024-01-15T01:00:00Z",
    )

    report = build_filing_daily_report(result)
    assert "本次无失败。" in report


def test_report_no_warnings() -> None:
    """没有警告时也有明确说明。"""
    result = FilingRunResult(
        run_id="run_test_005",
        mode="run",
        archive_root="./data/test",
        started_at="2024-01-15T00:00:00Z",
        finished_at="2024-01-15T01:00:00Z",
    )

    report = build_filing_daily_report(result)
    assert "本次无警告。" in report


def test_report_contains_no_investment_judgment() -> None:
    """日报中不包含投资判断字段。"""
    result = FilingRunResult(
        run_id="run_test_006",
        mode="run",
        archive_root="./data/test",
        started_at="2024-01-15T00:00:00Z",
        finished_at="2024-01-15T01:00:00Z",
    )

    report = build_filing_daily_report(result)
    # 不应包含任何投资判断相关的词
    assert "利好" not in report
    assert "利空" not in report
    assert "买入" not in report
    assert "卖出" not in report
    assert "目标价" not in report


def test_report_with_source_health() -> None:
    """有 source health 时表格正常显示。"""
    health = FilingSourceHealth(
        source_id="test_sec",
        source_type="sec_edgar",
        checked_at="2024-01-15T01:00:00Z",
        status=HEALTH_STATUS_HEALTHY,
        candidate_count_last_run=5,
        saved_count_last_run=5,
        failed_count_last_run=0,
    )

    result = FilingRunResult(
        run_id="run_test_007",
        mode="run",
        archive_root="./data/test",
        started_at="2024-01-15T00:00:00Z",
        finished_at="2024-01-15T01:00:00Z",
        source_health=[health],
    )

    report = build_filing_daily_report(result)
    assert "test_sec" in report
    assert "sec_edgar" in report
    assert "healthy" in report


def test_report_mentions_downstream_contract() -> None:
    """日报中提到下游消费入口和 foundation 边界。"""
    result = FilingRunResult(
        run_id="run_test_008",
        mode="run",
        archive_root="./data/test",
        started_at="2024-01-15T00:00:00Z",
        finished_at="2024-01-15T01:00:00Z",
    )

    report = build_filing_daily_report(result)
    # 明确说明 foundation 不做投资判断
    assert "不做投资判断" in report
    assert "Foundation" in report
