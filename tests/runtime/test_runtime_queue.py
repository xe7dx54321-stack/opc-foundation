"""Runtime failed queue helper 测试。

覆盖：
1. failed_queue append/load works
2. FailedQueueRecord construction
3. dict record support
4. missing file returns []
"""
from __future__ import annotations

from pathlib import Path

from opc_foundation.runtime.queue import (
    FailedQueueRecord,
    append_failed_record,
    load_failed_records,
)


def test_append_and_load_failed_record(tmp_path: Path) -> None:
    """append_failed_record + load_failed_records 应能正确读写。"""
    path = tmp_path / "failed_queue.jsonl"
    record = FailedQueueRecord(
        source_id="test_source",
        source_type="local_document",
        item_key="/path/to/file.pdf",
        error_type="ParseError",
        error_message="Failed to parse PDF",
    )
    append_failed_record(path, record)

    records = load_failed_records(path)
    assert len(records) == 1
    assert records[0]["source_id"] == "test_source"
    assert records[0]["error_type"] == "ParseError"


def test_append_dict_record(tmp_path: Path) -> None:
    """append_failed_record 应支持 dict。"""
    path = tmp_path / "failed_queue.jsonl"
    append_failed_record(path, {
        "source_id": "src2",
        "source_type": "rss_feed",
        "item_key": "abc123",
        "error_type": "NetworkError",
        "error_message": "Connection timeout",
    })

    records = load_failed_records(path)
    assert len(records) == 1
    assert records[0]["source_id"] == "src2"


def test_load_missing_file_returns_empty(tmp_path: Path) -> None:
    """文件不存在时 load_failed_records 应返回 []。"""
    path = tmp_path / "nonexistent.jsonl"
    assert load_failed_records(path) == []


def test_multiple_records(tmp_path: Path) -> None:
    """应能追加多条记录。"""
    path = tmp_path / "failed_queue.jsonl"
    for i in range(5):
        append_failed_record(path, FailedQueueRecord(
            source_id=f"src_{i}",
            source_type="local_document",
            item_key=f"item_{i}",
            error_type="ParseError",
            error_message=f"Error {i}",
        ))

    records = load_failed_records(path)
    assert len(records) == 5
    assert records[0]["source_id"] == "src_0"
    assert records[4]["source_id"] == "src_4"


def test_failed_queue_record_defaults() -> None:
    """FailedQueueRecord 默认值必须正确。"""
    record = FailedQueueRecord(
        source_id="s1",
        source_type="t1",
        item_key="k1",
        error_type="E1",
        error_message="M1",
    )
    assert record.retry_count == 0
    assert record.created_at is None
    assert record.raw_entry is None
