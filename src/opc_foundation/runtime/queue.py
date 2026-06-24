"""Failed Queue 通用 helper。

功能说明（小白解读）：
    定义通用的失败队列记录结构和读写函数。
    所有 foundation 模块都可以复用这个结构来记录失败项。

    通用字段：
    - source_id:     哪个源失败了
    - source_type:   源类型
    - item_key:      失败项的唯一标识
    - error_type:    错误类型
    - error_message: 错误信息

    不包含任何业务判断字段（如 ticker / rating / score）。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .jsonl import append_jsonl, read_jsonl


@dataclass(frozen=True)
class FailedQueueRecord:
    """失败队列记录。

    功能说明：
        记录一个失败项的通用信息。
        用 frozen dataclass，创建后不可修改。

    参数：
        source_id:     源 ID
        source_type:   源类型
        item_key:      失败项的唯一标识（如文件路径 / URL hash）
        error_type:    错误类型（如 ParseError / NetworkError）
        error_message: 错误详细信息
        retry_count:   重试次数（默认 0）
        created_at:    创建时间 ISO 字符串（可选）
        raw_entry:     原始数据（可选，用于调试）
    """

    source_id: str
    source_type: str
    item_key: str
    error_type: str
    error_message: str
    retry_count: int = 0
    created_at: str | None = None
    raw_entry: dict[str, Any] | None = None


def append_failed_record(
    path: str | Path, record: FailedQueueRecord | dict[str, Any]
) -> None:
    """向失败队列追加一条记录。

    功能说明：
        将一条失败记录追加到 failed_queue.jsonl。
        支持 FailedQueueRecord 对象或 dict。

    参数：
        path:   失败队列文件路径
        record: FailedQueueRecord 对象或 dict

    异常处理：
        如果序列化失败，抛出 TypeError。
        如果文件写入失败，抛出 OSError。
    """
    if isinstance(record, FailedQueueRecord):
        data = asdict(record)
    else:
        data = record
    append_jsonl(path, data)


def load_failed_records(path: str | Path) -> list[dict[str, Any]]:
    """读取失败队列的所有记录。

    功能说明：
        读取 failed_queue.jsonl 的所有记录。
        空文件或文件不存在返回 []。

    参数：
        path: 失败队列文件路径

    返回：
        dict 列表。空文件或文件不存在返回 []。

    异常处理：
        不会抛出 JSONDecodeError，坏行被跳过。
    """
    return read_jsonl(path)
