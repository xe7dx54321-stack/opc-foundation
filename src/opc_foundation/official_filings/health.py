"""Source Health 状态管理。

功能说明（小白解读）：
    每个 source 都有健康状态：healthy / degraded / failed / disabled / unknown。
    每次运行后更新健康状态记录，写入 source_health.jsonl。

    下游可以读取 source_health 来判断哪些源需要人工介入。
"""
from __future__ import annotations

from pathlib import Path

from ..storage.jsonl_store import JsonlStore
from .models import (
    FilingSourceHealth,
    HEALTH_STATUS_HEALTHY,
    HEALTH_STATUS_DEGRADED,
    HEALTH_STATUS_FAILED,
    HEALTH_STATUS_UNKNOWN,
)
from ..run.time_utils import utcnow_iso


def _health_path(archive_root: str | Path) -> Path:
    """获取 source_health.jsonl 的路径。"""
    return Path(archive_root) / "index" / "source_health.jsonl"


def load_source_health(archive_root: str | Path) -> dict[str, FilingSourceHealth]:
    """加载所有 source 的健康状态。

    参数：
        archive_root: 归档根目录

    返回：
        {source_id: FilingSourceHealth} 字典
    """
    path = _health_path(archive_root)
    records = JsonlStore.load_records(path, model=FilingSourceHealth)
    result: dict[str, FilingSourceHealth] = {}
    for r in records:
        if isinstance(r, FilingSourceHealth):
            result[r.source_id] = r
    return result


def save_source_health(
    archive_root: str | Path,
    health: FilingSourceHealth,
) -> None:
    """追加一条 source health 记录。

    参数：
        archive_root: 归档根目录
        health:       健康状态记录
    """
    path = _health_path(archive_root)
    JsonlStore.append_record(path, health)


def compute_health_status(
    candidate_count: int,
    saved_count: int,
    failed_count: int,
    partial_count: int,
    consecutive_failures: int,
    connector_failed: bool = False,
) -> str:
    """根据运行统计计算健康状态。

    参数：
        candidate_count:      本次发现的候选数
        saved_count:          本次成功保存数
        failed_count:         本次失败数
        partial_count:        本次部分保存数
        consecutive_failures: 连续失败次数
        connector_failed:     connector 是否整体失败

    返回：
        status 字符串：healthy / degraded / failed
    """
    if connector_failed or consecutive_failures >= 3:
        return HEALTH_STATUS_FAILED

    if failed_count > 0 or partial_count > 0:
        return HEALTH_STATUS_DEGRADED

    if candidate_count == 0:
        # 没有候选可能是周末/节假日，不算失败
        return HEALTH_STATUS_HEALTHY

    return HEALTH_STATUS_HEALTHY


def update_source_health(
    archive_root: str | Path,
    source_id: str,
    source_type: str | None,
    status: str,
    last_error: str | None = None,
    last_error_type: str | None = None,
    candidate_count: int = 0,
    saved_count: int = 0,
    duplicate_count: int = 0,
    partial_count: int = 0,
    failed_count: int = 0,
    run_id: str | None = None,
    last_report_path: str | None = None,
) -> FilingSourceHealth:
    """更新单个 source 的健康状态并保存。

    参数：
        archive_root:        归档根目录
        source_id:           source ID
        source_type:         source 类型
        status:              新状态
        last_error:          最近错误信息
        last_error_type:     最近错误类型
        candidate_count:     本次候选数
        saved_count:         本次保存数
        duplicate_count:     本次重复数
        partial_count:       本次部分保存数
        failed_count:        本次失败数
        run_id:              本次运行 ID
        last_report_path:    最近日报路径

    返回：
        更新后的 FilingSourceHealth
    """
    existing = load_source_health(archive_root).get(source_id)

    now = utcnow_iso()

    if existing:
        consecutive = existing.consecutive_failures
        if status == HEALTH_STATUS_FAILED or failed_count > 0:
            consecutive += 1
        else:
            consecutive = 0

        last_success = existing.last_success_at
        last_failure = existing.last_failure_at

        if status == HEALTH_STATUS_HEALTHY and saved_count > 0:
            last_success = now
        if status in (HEALTH_STATUS_FAILED, HEALTH_STATUS_DEGRADED):
            last_failure = now
    else:
        consecutive = 1 if status == HEALTH_STATUS_FAILED else 0
        last_success = now if status == HEALTH_STATUS_HEALTHY else None
        last_failure = now if status in (HEALTH_STATUS_FAILED, HEALTH_STATUS_DEGRADED) else None

    health = FilingSourceHealth(
        source_id=source_id,
        source_type=source_type,
        checked_at=now,
        status=status,
        last_success_at=last_success,
        last_failure_at=last_failure,
        consecutive_failures=consecutive,
        last_error=last_error,
        last_error_type=last_error_type,
        candidate_count_last_run=candidate_count,
        saved_count_last_run=saved_count,
        duplicate_count_last_run=duplicate_count,
        partial_count_last_run=partial_count,
        failed_count_last_run=failed_count,
        last_run_id=run_id,
        last_report_path=last_report_path,
    )

    save_source_health(archive_root, health)
    return health
