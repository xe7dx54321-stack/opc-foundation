"""Runtime 通用数据模型。

功能说明（小白解读）：
    定义跨模块通用的枚举和数据结构：
    - RunMode:           运行模式（验证配置/试运行/正式运行等）
    - RuntimeStatus:     运行状态（成功/部分/失败/跳过）
    - HealthStatus:      健康状态（健康/降级/失败/禁用/未知）
    - RuntimeIndexFiles: 标准索引文件名集合
    - RuntimeCommandResult: 命令执行结果

    这些模型用 dataclass 实现，不依赖 pydantic，保持轻量。
    不包含任何 ticker / investment / scoring 字段。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RunMode(str, Enum):
    """运行模式枚举。

    对应 CLI 命令：
    - VALIDATE_CONFIG: 验证配置文件
    - DRY_RUN:         试运行，不保存
    - RUN:             正式运行
    - SOURCE_HEALTH:   查看源健康状态
    - REPORT:          生成日报
    - RETRY_FAILED:    重试失败项
    """

    VALIDATE_CONFIG = "validate-config"
    DRY_RUN = "dry-run"
    RUN = "run"
    SOURCE_HEALTH = "source-health"
    REPORT = "report"
    RETRY_FAILED = "retry-failed"


class RuntimeStatus(str, Enum):
    """运行状态枚举。

    - SUCCESS: 全部成功
    - PARTIAL: 部分成功
    - FAILED:  全部失败
    - SKIPPED: 跳过（如重复运行）
    """

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"


class HealthStatus(str, Enum):
    """健康状态枚举。

    推荐语义：
    - HEALTHY:  enabled + candidates > 0 + no failures
    - DEGRADED: enabled + candidates > 0 + partial/failed docs
                或 enabled + candidates = 0 (empty_source)
    - FAILED:   connector/runtime exception
    - DISABLED: source disabled
    - UNKNOWN:  默认/未检查
    """

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    DISABLED = "disabled"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class RuntimeIndexFiles:
    """标准索引文件名集合。

    功能说明：
        定义一个 archive 目录下标准索引文件的命名约定。
        不同模块的主索引文件名可能不同（documents.jsonl vs filings.jsonl），
        但 source_health / failed_queue / run_log 是统一的。

    参数：
        primary_index: 主索引文件名（如 documents.jsonl 或 filings.jsonl）
        latest_index:  最新快照文件名（如 documents.latest.jsonl）
        source_health: 源健康状态文件名（默认 source_health.jsonl）
        failed_queue:  失败队列文件名（默认 failed_queue.jsonl）
        run_log:       运行日志文件名（默认 run_log.jsonl）
    """

    primary_index: str
    latest_index: str
    source_health: str = "source_health.jsonl"
    failed_queue: str = "failed_queue.jsonl"
    run_log: str = "run_log.jsonl"


@dataclass(frozen=True)
class RuntimeCommandResult:
    """命令执行结果。

    功能说明：
        记录一次 CLI 命令执行的结果，可用于 run_log 或返回给调用方。

    参数：
        command:      执行的命令名（如 run / dry-run）
        status:       执行状态
        archive_root: 归档根目录路径（可选）
        report_path:  生成的报告路径（可选）
        message:      附加消息（可选）
        metadata:     附加元数据（可选）
    """

    command: str
    status: RuntimeStatus
    archive_root: str | None = None
    report_path: str | None = None
    message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
