"""JSONL 读写 helper。

功能说明（小白解读）：
    提供通用的 JSONL 文件读写功能：
    - append_jsonl:       追加一条记录
    - read_jsonl:         读取所有记录
    - write_jsonl_snapshot: 覆盖写入快照
    - read_latest_jsonl:  读取快照（可限制条数）

    特点：
    - UTF-8 编码
    - ensure_ascii=False（中文不转义）
    - 自动创建父目录
    - 空文件/文件不存在返回 []
    - 单行坏 JSON fail-soft：跳过坏行
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def append_jsonl(path: str | Path, record: dict[str, Any]) -> None:
    """向 JSONL 文件追加一条记录。

    功能说明：
        将一条 dict 记录以 JSON 格式追加到文件末尾。
        如果父目录不存在，自动创建。

    参数：
        path:   文件路径
        record: 要写入的 dict 记录

    异常处理：
        如果 JSON 序列化失败，抛出 TypeError。
        如果文件写入失败，抛出 OSError。
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    """读取 JSONL 文件的所有记录。

    功能说明：
        逐行读取 JSONL 文件，返回 dict 列表。
        空文件或文件不存在返回 []。
        单行坏 JSON 会跳过（fail-soft），不中断读取。

    参数：
        path: 文件路径

    返回：
        dict 列表。空文件或文件不存在返回 []。

    异常处理：
        不会抛出 JSONDecodeError，坏行被跳过。
    """
    p = Path(path)
    if not p.exists():
        return []

    records: list[dict[str, Any]] = []
    with open(p, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                # fail-soft：跳过坏行
                continue
    return records


def write_jsonl_snapshot(path: str | Path, records: list[dict[str, Any]]) -> None:
    """覆盖写入 JSONL 快照文件。

    功能说明：
        将一批记录覆盖写入文件（先清空再写）。
        用于生成 latest.jsonl 快照。
        如果父目录不存在，自动创建。

    参数：
        path:    文件路径
        records: 要写入的 dict 列表

    异常处理：
        如果 JSON 序列化失败，抛出 TypeError。
        如果文件写入失败，抛出 OSError。
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def read_latest_jsonl(
    path: str | Path, limit: int | None = None
) -> list[dict[str, Any]]:
    """读取快照文件（可限制条数）。

    功能说明：
        读取 latest.jsonl 快照文件。
        与 read_jsonl 类似，但支持 limit 参数限制返回条数。
        空文件或文件不存在返回 []。

    参数：
        path:  文件路径
        limit: 最多返回的记录数（None 表示全部）

    返回：
        dict 列表。空文件或文件不存在返回 []。

    异常处理：
        不会抛出 JSONDecodeError，坏行被跳过。
    """
    records = read_jsonl(path)
    if limit is not None and limit > 0:
        return records[:limit]
    return records
