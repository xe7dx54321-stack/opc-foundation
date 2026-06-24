"""Run Log 通用 helper。

功能说明（小白解读）：
    定义通用的运行日志记录结构和读写函数。
    所有 foundation 模块都可以复用这个结构来记录每次运行的结果。

    通用字段：
    - run_id:          运行 ID
    - command:         执行的命令
    - status:          运行状态
    - archive_root:    归档根目录
    - started_at:      开始时间
    - finished_at:     结束时间
    - candidate_count: 候选数量
    - saved_count:     保存数量
    - duplicate_count: 重复数量
    - failed_count:    失败数量

    不包含任何业务判断字段。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .jsonl import append_jsonl, read_jsonl


@dataclass(frozen=True)
class RunLogRecord:
    """运行日志记录。

    功能说明：
        记录一次 CLI 命令执行的完整信息。
        用 frozen dataclass，创建后不可修改。

    参数：
        run_id:          运行 ID
        command:         执行的命令（如 run / dry-run）
        status:          运行状态（success / partial / failed / skipped）
        archive_root:    归档根目录路径
        started_at:      开始时间 ISO 字符串
        finished_at:     结束时间 ISO 字符串（可选）
        candidate_count: 候选数量（可选）
        saved_count:     保存数量（可选）
        duplicate_count: 重复数量（可选）
        failed_count:    失败数量（可选）
        report_path:     报告路径（可选）
        metadata:        附加元数据（可选）
    """

    run_id: str
    command: str
    status: str
    archive_root: str
    started_at: str
    finished_at: str | None = None
    candidate_count: int | None = None
    saved_count: int | None = None
    duplicate_count: int | None = None
    failed_count: int | None = None
    report_path: str | None = None
    metadata: dict[str, Any] | None = None


def append_run_log(
    path: str | Path, record: RunLogRecord | dict[str, Any]
) -> None:
    """向运行日志追加一条记录。

    功能说明：
        将一条运行日志记录追加到 run_log.jsonl。
        支持 RunLogRecord 对象或 dict。

    参数：
        path:   运行日志文件路径
        record: RunLogRecord 对象或 dict

    异常处理：
        如果序列化失败，抛出 TypeError。
        如果文件写入失败，抛出 OSError。
    """
    if isinstance(record, RunLogRecord):
        data = asdict(record)
    else:
        data = record
    append_jsonl(path, data)


def load_run_log(path: str | Path) -> list[dict[str, Any]]:
    """读取运行日志的所有记录。

    功能说明：
        读取 run_log.jsonl 的所有记录。
        空文件或文件不存在返回 []。

    参数：
        path: 运行日志文件路径

    返回：
        dict 列表。空文件或文件不存在返回 []。

    异常处理：
        不会抛出 JSONDecodeError，坏行被跳过。
    """
    return read_jsonl(path)
