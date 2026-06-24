"""OPC Foundation Shared Runtime 模块。

功能说明（小白解读）：
    这是 opc-foundation 的共享运行时层，提供跨模块通用的：
    - 运行模式常量（validate-config / dry-run / run 等）
    - 运行状态和健康状态枚举
    - 标准 archive 路径 helper
    - JSONL 读写 helper
    - failed_queue / run_log 通用结构

    这一层不属于任何具体业务模块，所有 foundation 模块都可以复用。

核心原则：
    Foundation provides infrastructure. Business systems keep judgment.
"""
from __future__ import annotations

from .constants import (
    DOCUMENTS_INDEX_FILE,
    DOCUMENTS_LATEST_FILE,
    FAILED_QUEUE_FILE,
    FILINGS_INDEX_FILE,
    FILINGS_LATEST_FILE,
    RUN_LOG_FILE,
    SOURCE_HEALTH_FILE,
    STANDARD_COMMANDS,
    STANDARD_INDEX_DIR,
    STANDARD_REPORTS_DIR,
)
from .jsonl import (
    append_jsonl,
    read_jsonl,
    read_latest_jsonl,
    write_jsonl_snapshot,
)
from .models import (
    HealthStatus,
    RunMode,
    RuntimeCommandResult,
    RuntimeIndexFiles,
    RuntimeStatus,
)
from .paths import (
    ArchivePaths,
    build_archive_paths,
    ensure_archive_dirs,
)
from .queue import (
    FailedQueueRecord,
    append_failed_record,
    load_failed_records,
)
from .run_log import (
    RunLogRecord,
    append_run_log,
    load_run_log,
)

__all__ = [
    "STANDARD_INDEX_DIR",
    "STANDARD_REPORTS_DIR",
    "SOURCE_HEALTH_FILE",
    "FAILED_QUEUE_FILE",
    "RUN_LOG_FILE",
    "DOCUMENTS_INDEX_FILE",
    "DOCUMENTS_LATEST_FILE",
    "FILINGS_INDEX_FILE",
    "FILINGS_LATEST_FILE",
    "STANDARD_COMMANDS",
    "RunMode",
    "RuntimeStatus",
    "HealthStatus",
    "RuntimeIndexFiles",
    "RuntimeCommandResult",
    "ArchivePaths",
    "build_archive_paths",
    "ensure_archive_dirs",
    "append_jsonl",
    "read_jsonl",
    "write_jsonl_snapshot",
    "read_latest_jsonl",
    "FailedQueueRecord",
    "append_failed_record",
    "load_failed_records",
    "RunLogRecord",
    "append_run_log",
    "load_run_log",
]
