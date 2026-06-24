"""Runtime run log helper 测试。

覆盖：
1. run_log append/load works
2. RunLogRecord construction
3. dict record support
4. missing file returns []
"""
from __future__ import annotations

from pathlib import Path

from opc_foundation.runtime.run_log import (
    RunLogRecord,
    append_run_log,
    load_run_log,
)


def test_append_and_load_run_log(tmp_path: Path) -> None:
    """append_run_log + load_run_log 应能正确读写。"""
    path = tmp_path / "run_log.jsonl"
    record = RunLogRecord(
        run_id="run_001",
        command="run",
        status="success",
        archive_root="/data/research_archive",
        started_at="2026-06-24T10:00:00Z",
        finished_at="2026-06-24T10:05:00Z",
        candidate_count=10,
        saved_count=8,
        duplicate_count=1,
        failed_count=1,
    )
    append_run_log(path, record)

    records = load_run_log(path)
    assert len(records) == 1
    assert records[0]["run_id"] == "run_001"
    assert records[0]["command"] == "run"
    assert records[0]["saved_count"] == 8


def test_append_dict_run_log(tmp_path: Path) -> None:
    """append_run_log 应支持 dict。"""
    path = tmp_path / "run_log.jsonl"
    append_run_log(path, {
        "run_id": "run_002",
        "command": "dry-run",
        "status": "success",
        "archive_root": "/data/test",
        "started_at": "2026-06-24T11:00:00Z",
    })

    records = load_run_log(path)
    assert len(records) == 1
    assert records[0]["command"] == "dry-run"


def test_load_missing_file_returns_empty(tmp_path: Path) -> None:
    """文件不存在时 load_run_log 应返回 []。"""
    path = tmp_path / "nonexistent.jsonl"
    assert load_run_log(path) == []


def test_multiple_run_logs(tmp_path: Path) -> None:
    """应能追加多条运行日志。"""
    path = tmp_path / "run_log.jsonl"
    for i in range(3):
        append_run_log(path, RunLogRecord(
            run_id=f"run_{i:03d}",
            command="run",
            status="success" if i < 2 else "partial",
            archive_root="/data/test",
            started_at=f"2026-06-24T{i:02d}:00:00Z",
        ))

    records = load_run_log(path)
    assert len(records) == 3
    assert records[0]["run_id"] == "run_000"
    assert records[2]["status"] == "partial"


def test_run_log_record_defaults() -> None:
    """RunLogRecord 默认值必须正确。"""
    record = RunLogRecord(
        run_id="r1",
        command="run",
        status="success",
        archive_root="/data",
        started_at="2026-01-01T00:00:00Z",
    )
    assert record.finished_at is None
    assert record.candidate_count is None
    assert record.saved_count is None
    assert record.report_path is None
    assert record.metadata is None
