"""Runtime models 测试。

覆盖：
1. RunMode values correct
2. RuntimeStatus values correct
3. HealthStatus values correct
4. RuntimeIndexFiles defaults
5. RuntimeCommandResult construction
6. runtime models do not contain prohibited business fields
"""
from __future__ import annotations

from opc_foundation.runtime.models import (
    HealthStatus,
    RunMode,
    RuntimeCommandResult,
    RuntimeIndexFiles,
    RuntimeStatus,
)

# 禁止的业务判断字段
PROHIBITED_FIELDS = {
    "affected_tickers",
    "expectation_delta",
    "investment_rating",
    "trade_signal",
    "watchlist",
    "action_decision",
    "recommendation",
    "opportunity_score",
    "risk_score",
    "position_size",
    "target_price",
}


# ---------------------------------------------------------------------------
# RunMode
# ---------------------------------------------------------------------------


def test_run_mode_values() -> None:
    """RunMode 枚举值必须正确。"""
    assert RunMode.VALIDATE_CONFIG.value == "validate-config"
    assert RunMode.DRY_RUN.value == "dry-run"
    assert RunMode.RUN.value == "run"
    assert RunMode.SOURCE_HEALTH.value == "source-health"
    assert RunMode.REPORT.value == "report"
    assert RunMode.RETRY_FAILED.value == "retry-failed"


def test_run_mode_is_str_enum() -> None:
    """RunMode 应该是 str Enum，可以直接当字符串用。"""
    assert RunMode.RUN == "run"
    assert RunMode.DRY_RUN == "dry-run"


# ---------------------------------------------------------------------------
# RuntimeStatus
# ---------------------------------------------------------------------------


def test_runtime_status_values() -> None:
    """RuntimeStatus 枚举值必须正确。"""
    assert RuntimeStatus.SUCCESS.value == "success"
    assert RuntimeStatus.PARTIAL.value == "partial"
    assert RuntimeStatus.FAILED.value == "failed"
    assert RuntimeStatus.SKIPPED.value == "skipped"


# ---------------------------------------------------------------------------
# HealthStatus
# ---------------------------------------------------------------------------


def test_health_status_values() -> None:
    """HealthStatus 枚举值必须正确。"""
    assert HealthStatus.HEALTHY.value == "healthy"
    assert HealthStatus.DEGRADED.value == "degraded"
    assert HealthStatus.FAILED.value == "failed"
    assert HealthStatus.DISABLED.value == "disabled"
    assert HealthStatus.UNKNOWN.value == "unknown"


# ---------------------------------------------------------------------------
# RuntimeIndexFiles
# ---------------------------------------------------------------------------


def test_runtime_index_files_defaults() -> None:
    """RuntimeIndexFiles 默认值必须正确。"""
    idx = RuntimeIndexFiles(
        primary_index="documents.jsonl",
        latest_index="documents.latest.jsonl",
    )
    assert idx.primary_index == "documents.jsonl"
    assert idx.latest_index == "documents.latest.jsonl"
    assert idx.source_health == "source_health.jsonl"
    assert idx.failed_queue == "failed_queue.jsonl"
    assert idx.run_log == "run_log.jsonl"


def test_runtime_index_files_custom() -> None:
    """RuntimeIndexFiles 应支持自定义文件名。"""
    idx = RuntimeIndexFiles(
        primary_index="filings.jsonl",
        latest_index="filings.latest.jsonl",
        source_health="custom_health.jsonl",
    )
    assert idx.primary_index == "filings.jsonl"
    assert idx.source_health == "custom_health.jsonl"


# ---------------------------------------------------------------------------
# RuntimeCommandResult
# ---------------------------------------------------------------------------


def test_runtime_command_result_construction() -> None:
    """RuntimeCommandResult 应能正确构造。"""
    result = RuntimeCommandResult(
        command="run",
        status=RuntimeStatus.SUCCESS,
        archive_root="/data/research_archive",
        report_path="/data/research_archive/reports/2026-06-24.md",
        message="3 saved, 0 failed",
    )
    assert result.command == "run"
    assert result.status == RuntimeStatus.SUCCESS
    assert result.archive_root == "/data/research_archive"
    assert result.report_path is not None
    assert result.message == "3 saved, 0 failed"
    assert result.metadata == {}


def test_runtime_command_result_minimal() -> None:
    """RuntimeCommandResult 只需 command 和 status 即可构造。"""
    result = RuntimeCommandResult(
        command="dry-run",
        status=RuntimeStatus.SUCCESS,
    )
    assert result.command == "dry-run"
    assert result.archive_root is None
    assert result.report_path is None
    assert result.message is None


# ---------------------------------------------------------------------------
# 禁止字段检查
# ---------------------------------------------------------------------------


def test_models_no_prohibited_fields() -> None:
    """Runtime models 不得包含禁止的业务判断字段。"""
    # 检查 RuntimeIndexFiles 的字段名
    idx_fields = {f.name for f in __import__("dataclasses").fields(RuntimeIndexFiles)}
    assert not (idx_fields & PROHIBITED_FIELDS), (
        f"RuntimeIndexFiles 包含禁止字段: {idx_fields & PROHIBITED_FIELDS}"
    )

    # 检查 RuntimeCommandResult 的字段名
    cmd_fields = {f.name for f in __import__("dataclasses").fields(RuntimeCommandResult)}
    assert not (cmd_fields & PROHIBITED_FIELDS), (
        f"RuntimeCommandResult 包含禁止字段: {cmd_fields & PROHIBITED_FIELDS}"
    )
