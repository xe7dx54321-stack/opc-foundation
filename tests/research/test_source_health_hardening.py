"""Phase 2F 测试：source health hardening。

覆盖：
    1. SourceHealth 模型新字段存在
    2. FailedDocument 模型新字段存在
    3. status 规则标准化
    4. error_type 标准化
    5. classify_error 函数行为
    6. source-health CLI 在无文件时不崩溃
    7. source-health CLI 可读输出
    8. 不出现业务字段
"""
from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from opc_foundation.research.archiver import ERROR_TYPES, classify_error
from opc_foundation.research.cli import app
from opc_foundation.research.models import FailedDocument, SourceHealth


# ---------------------------------------------------------------------------
# 1. SourceHealth 模型新字段存在
# ---------------------------------------------------------------------------


def test_source_health_has_new_fields() -> None:
    """SourceHealth 必须包含 Phase 2F 新增字段。"""
    health = SourceHealth(
        source_id="test_source",
        source_name="Test Source",
        source_type="media_mention",
        checked_at="2026-06-22T10:00:00+08:00",
        status="healthy",
    )
    # Phase 2F 新增字段
    assert hasattr(health, "source_type")
    assert hasattr(health, "last_error_type")
    assert hasattr(health, "new_count_last_run")
    assert hasattr(health, "partial_count_last_run")
    assert hasattr(health, "failed_count_last_run")
    assert hasattr(health, "duplicate_count_last_run")
    assert hasattr(health, "skipped_count_last_run")
    assert hasattr(health, "last_run_id")
    assert hasattr(health, "last_report_path")
    # 默认值
    assert health.source_type == "media_mention"
    assert health.last_error_type is None
    assert health.new_count_last_run == 0
    assert health.last_run_id is None


# ---------------------------------------------------------------------------
# 2. FailedDocument 模型新字段存在
# ---------------------------------------------------------------------------


def test_failed_document_has_new_fields() -> None:
    """FailedDocument 必须包含 Phase 2F 新增字段。"""
    failed = FailedDocument(
        source_id="test_source",
        source_name="Test Source",
        source_type="media_mention",
        url="https://example.com/article",
        canonical_url="https://example.com/article",
        failed_at="2026-06-22T10:00:00+08:00",
        error="fetch failed",
        error_type="fetch_error",
        run_id="run-123",
    )
    assert hasattr(failed, "source_type")
    assert hasattr(failed, "error_type")
    assert hasattr(failed, "run_id")
    assert failed.source_type == "media_mention"
    assert failed.error_type == "fetch_error"
    assert failed.run_id == "run-123"


# ---------------------------------------------------------------------------
# 3. status 规则标准化
# ---------------------------------------------------------------------------


def test_status_values_standardized() -> None:
    """status 取值必须是标准化的 5 种之一。"""
    valid_statuses = {"healthy", "degraded", "failed", "disabled", "unknown"}
    for s in valid_statuses:
        health = SourceHealth(
            source_id="test",
            source_name="Test",
            checked_at="2026-06-22T10:00:00+08:00",
            status=s,
        )
        assert health.status == s


# ---------------------------------------------------------------------------
# 4. error_type 标准化
# ---------------------------------------------------------------------------


def test_error_types_set() -> None:
    """ERROR_TYPES 必须包含所有标准 error_type。"""
    expected = {
        "config_error",
        "connector_error",
        "fetch_error",
        "parse_error",
        "extract_error",
        "storage_error",
        "empty_source",
        "unsupported_source_type",
        "unknown_error",
    }
    assert ERROR_TYPES == expected


# ---------------------------------------------------------------------------
# 5. classify_error 函数行为
# ---------------------------------------------------------------------------


def test_classify_error_none() -> None:
    """classify_error(None) 应返回 None。"""
    assert classify_error(None) is None
    assert classify_error("") is None


def test_classify_error_fetch() -> None:
    """包含 fetch 关键词应返回 fetch_error。"""
    assert classify_error("抓取失败") == "fetch_error"
    assert classify_error("HTTP timeout") == "fetch_error"


def test_classify_error_parse() -> None:
    """包含 parse 关键词应返回 parse_error。"""
    assert classify_error("HTML 解析失败") == "parse_error"
    assert classify_error("BeautifulSoup error") == "parse_error"


def test_classify_error_extract() -> None:
    """包含 extract 关键词应返回 extract_error。"""
    assert classify_error("正文抽取失败") == "extract_error"


def test_classify_error_storage() -> None:
    """包含 storage 关键词应返回 storage_error。"""
    assert classify_error("写入文件失败") == "storage_error"
    assert classify_error("storage error") == "storage_error"


def test_classify_error_config() -> None:
    """包含 config error 关键词应返回 config_error。"""
    assert classify_error("config error: missing url") == "config_error"


def test_classify_error_unsupported() -> None:
    """包含 unsupported source_type 应返回 unsupported_source_type。"""
    assert classify_error("unsupported source_type: foo") == "unsupported_source_type"


def test_classify_error_empty() -> None:
    """包含 empty 关键词应返回 empty_source。"""
    assert classify_error("内容为空") == "empty_source"
    assert classify_error("empty source") == "empty_source"


def test_classify_error_unknown() -> None:
    """无法识别的错误应返回 unknown_error。"""
    assert classify_error("一些奇怪的错误") == "unknown_error"


# ---------------------------------------------------------------------------
# 6. source-health CLI 在无文件时不崩溃
# ---------------------------------------------------------------------------


def test_source_health_cli_no_file(tmp_path: Path) -> None:
    """source-health CLI 在没有 source_health.jsonl 时不应崩溃。"""
    runner = CliRunner()
    archive_root = tmp_path / "empty_archive"
    archive_root.mkdir()
    result = runner.invoke(app, ["source-health", "--archive-root", str(archive_root)])
    assert result.exit_code == 0
    assert "暂无" in result.output or "no" in result.output.lower()


# ---------------------------------------------------------------------------
# 7. source-health CLI 可读输出
# ---------------------------------------------------------------------------


def test_source_health_cli_with_records(tmp_path: Path) -> None:
    """source-health CLI 在有记录时应输出可读摘要。"""
    # 构造 source_health.jsonl
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    health_file = state_dir / "source_health.jsonl"
    health_file.write_text(
        '{"source_id":"s1","source_name":"Source 1","source_type":"media_mention",'
        '"checked_at":"2026-06-22T10:00:00+08:00","status":"healthy",'
        '"candidate_count_last_run":5,"saved_count_last_run":3}\n'
        '{"source_id":"s2","source_name":"Source 2","source_type":"analyst_action",'
        '"checked_at":"2026-06-22T10:00:00+08:00","status":"failed",'
        '"consecutive_failures":2,"last_error_type":"fetch_error",'
        '"last_error":"HTTP timeout","candidate_count_last_run":0,"saved_count_last_run":0}\n',
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(app, ["source-health", "--archive-root", str(tmp_path)])
    assert result.exit_code == 0
    assert "healthy" in result.output
    assert "failed" in result.output
    assert "Source 1" in result.output
    assert "Source 2" in result.output


def test_source_health_cli_status_filter(tmp_path: Path) -> None:
    """source-health CLI --status 过滤应只返回指定状态的 source。"""
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    health_file = state_dir / "source_health.jsonl"
    health_file.write_text(
        '{"source_id":"s1","source_name":"Healthy Source","source_type":"media_mention",'
        '"checked_at":"2026-06-22T10:00:00+08:00","status":"healthy"}\n'
        '{"source_id":"s2","source_name":"Failed Source","source_type":"analyst_action",'
        '"checked_at":"2026-06-22T10:00:00+08:00","status":"failed",'
        '"last_error":"timeout"}\n',
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        app, ["source-health", "--archive-root", str(tmp_path), "--status", "failed"]
    )
    assert result.exit_code == 0
    assert "Failed Source" in result.output
    assert "Healthy Source" not in result.output


def test_source_health_cli_json_format(tmp_path: Path) -> None:
    """source-health CLI --format json 应输出 JSON。"""
    import json

    state_dir = tmp_path / "state"
    state_dir.mkdir()
    health_file = state_dir / "source_health.jsonl"
    health_file.write_text(
        '{"source_id":"s1","source_name":"Source 1","source_type":"media_mention",'
        '"checked_at":"2026-06-22T10:00:00+08:00","status":"healthy"}\n',
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        app, ["source-health", "--archive-root", str(tmp_path), "--format", "json"]
    )
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["source_id"] == "s1"


# ---------------------------------------------------------------------------
# 8. 不出现业务字段
# ---------------------------------------------------------------------------


def test_models_no_business_fields() -> None:
    """SourceHealth 和 FailedDocument 不能包含投研判断字段。"""
    forbidden = {
        "affected_tickers",
        "expectation_delta",
        "investment_rating",
        "trade_signal",
        "watchlist",
        "action_decision",
        "recommendation",
    }
    health_fields = set(SourceHealth.model_fields.keys())
    failed_fields = set(FailedDocument.model_fields.keys())
    for field in forbidden:
        assert field not in health_fields, f"SourceHealth 不能包含 {field}"
        assert field not in failed_fields, f"FailedDocument 不能包含 {field}"
