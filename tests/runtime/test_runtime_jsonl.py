"""Runtime JSONL helper 测试。

覆盖：
1. JSONL append/read works
2. JSONL missing file returns []
3. JSONL empty file returns []
4. JSONL snapshot write works
5. JSONL bad line fail-soft
6. read_latest_jsonl with limit
7. UTF-8 / ensure_ascii=False
"""
from __future__ import annotations

import json
from pathlib import Path

from opc_foundation.runtime.jsonl import (
    append_jsonl,
    read_jsonl,
    read_latest_jsonl,
    write_jsonl_snapshot,
)


def test_append_and_read(tmp_path: Path) -> None:
    """append_jsonl + read_jsonl 应能正确读写。"""
    path = tmp_path / "test.jsonl"
    append_jsonl(path, {"name": "doc1", "value": 1})
    append_jsonl(path, {"name": "doc2", "value": 2})

    records = read_jsonl(path)
    assert len(records) == 2
    assert records[0]["name"] == "doc1"
    assert records[1]["name"] == "doc2"


def test_read_missing_file_returns_empty(tmp_path: Path) -> None:
    """文件不存在时 read_jsonl 应返回 []。"""
    path = tmp_path / "nonexistent.jsonl"
    assert read_jsonl(path) == []


def test_read_empty_file_returns_empty(tmp_path: Path) -> None:
    """空文件 read_jsonl 应返回 []。"""
    path = tmp_path / "empty.jsonl"
    path.write_text("", encoding="utf-8")
    assert read_jsonl(path) == []


def test_write_snapshot(tmp_path: Path) -> None:
    """write_jsonl_snapshot 应覆盖写入。"""
    path = tmp_path / "snapshot.jsonl"
    # 先写一些数据
    append_jsonl(path, {"old": True})
    # 覆盖写入快照
    write_jsonl_snapshot(path, [{"new": 1}, {"new": 2}])
    records = read_jsonl(path)
    assert len(records) == 2
    assert records[0] == {"new": 1}
    assert records[1] == {"new": 2}


def test_bad_line_fail_soft(tmp_path: Path) -> None:
    """坏 JSON 行应被跳过，不中断读取。"""
    path = tmp_path / "bad.jsonl"
    path.write_text(
        '{"good": 1}\n'
        'BAD JSON LINE\n'
        '{"good": 2}\n'
        '\n'
        '{"good": 3}\n',
        encoding="utf-8",
    )
    records = read_jsonl(path)
    assert len(records) == 3
    assert records[0]["good"] == 1
    assert records[1]["good"] == 2
    assert records[2]["good"] == 3


def test_read_latest_with_limit(tmp_path: Path) -> None:
    """read_latest_jsonl 应支持 limit 参数。"""
    path = tmp_path / "latest.jsonl"
    write_jsonl_snapshot(path, [{"i": i} for i in range(10)])
    limited = read_latest_jsonl(path, limit=3)
    assert len(limited) == 3
    assert limited[0]["i"] == 0
    assert limited[2]["i"] == 2


def test_read_latest_no_limit(tmp_path: Path) -> None:
    """read_latest_jsonl 不传 limit 应返回全部。"""
    path = tmp_path / "latest.jsonl"
    write_jsonl_snapshot(path, [{"i": i} for i in range(5)])
    all_records = read_latest_jsonl(path)
    assert len(all_records) == 5


def test_utf8_chinese(tmp_path: Path) -> None:
    """JSONL 应正确处理中文（ensure_ascii=False）。"""
    path = tmp_path / "chinese.jsonl"
    append_jsonl(path, {"title": "中文标题", "content": "测试内容"})
    records = read_jsonl(path)
    assert len(records) == 1
    assert records[0]["title"] == "中文标题"


def test_append_creates_parent_dir(tmp_path: Path) -> None:
    """append_jsonl 应自动创建父目录。"""
    path = tmp_path / "subdir" / "nested" / "test.jsonl"
    append_jsonl(path, {"ok": True})
    assert path.exists()
    records = read_jsonl(path)
    assert len(records) == 1
