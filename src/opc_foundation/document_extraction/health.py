"""Document Extraction Foundation 的健康检查模块。

功能说明（小白解读）：
    本文件负责管理和更新源健康状态：
    - 根据运行结果计算健康状态
    - 更新 source_health.jsonl
    - 支持 CLI 的 source-health 命令

    Health Status 计算规则：
    - enabled=True 但 candidate_count=0 → degraded（empty_source）
    - enabled=True 且 candidate_count>0 → 按规则计算
    - enabled=False → disabled
    - 有错误 → failed
    - 正常 → healthy
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import (
    DocumentExtractionHealth,
    ERROR_TYPE_EMPTY_SOURCE,
    HEALTH_STATUS_DEGRADED,
    HEALTH_STATUS_DISABLED,
    HEALTH_STATUS_FAILED,
    HEALTH_STATUS_HEALTHY,
    HEALTH_STATUS_UNKNOWN,
)
from .storage import append_source_health, load_source_health_index
from ..run.time_utils import utcnow_iso


def compute_health_status(
    candidate_count: int,
    saved_count: int,
    failed_count: int,
    partial_count: int,
    consecutive_failures: int,
    connector_failed: bool = False,
) -> str:
    """根据运行结果计算健康状态。

    参数：
        candidate_count:    候选文档数量
        saved_count:       成功保存数量
        failed_count:       失败数量
        partial_count:      部分成功数量
        consecutive_failures: 连续失败次数
        connector_failed:   connector 是否失败

    返回：
        health_status 字符串
    """
    # connector 失败
    if connector_failed:
        return HEALTH_STATUS_FAILED

    # 连续失败超过阈值
    if consecutive_failures >= 3:
        return HEALTH_STATUS_FAILED

    # 有失败
    if failed_count > 0:
        return HEALTH_STATUS_DEGRADED

    # 有 partial
    if partial_count > 0:
        return HEALTH_STATUS_DEGRADED

    # 没有候选（empty source）
    if candidate_count == 0:
        return HEALTH_STATUS_DEGRADED

    # 有成功保存
    if saved_count > 0:
        return HEALTH_STATUS_HEALTHY

    # 默认 unknown
    return HEALTH_STATUS_UNKNOWN


def update_source_health(
    archive_root: Path,
    source_id: str,
    source_type: str,
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
    consecutive_failures: int = 0,
) -> DocumentExtractionHealth:
    """更新源健康状态并写入文件。

    参数：
        archive_root:   归档根目录
        source_id:      源 ID
        source_type:    源类型
        status:         健康状态
        其他统计参数...

    返回：
        更新后的 DocumentExtractionHealth 对象
    """
    checked_at = utcnow_iso()

    # 获取之前的健康状态（用于计算连续失败）
    existing_health = load_source_health_index(archive_root).get(source_id)

    # 计算新增连续失败数
    new_consecutive = consecutive_failures
    if status == HEALTH_STATUS_FAILED and existing_health:
        new_consecutive = existing_health.consecutive_failures + 1
    elif status != HEALTH_STATUS_FAILED:
        new_consecutive = 0

    # 构建健康对象
    health = DocumentExtractionHealth(
        source_id=source_id,
        source_type=source_type,
        checked_at=checked_at,
        status=status,
        last_error=last_error,
        last_error_type=last_error_type,
        consecutive_failures=new_consecutive,
        candidate_count_last_run=candidate_count,
        saved_count_last_run=saved_count,
        duplicate_count_last_run=duplicate_count,
        partial_count_last_run=partial_count,
        failed_count_last_run=failed_count,
        last_run_id=run_id,
        last_report_path=last_report_path,
        last_success_at=checked_at if status == HEALTH_STATUS_HEALTHY else None,
        last_failure_at=checked_at if status == HEALTH_STATUS_FAILED else None,
    )

    # 追加到文件
    append_source_health(archive_root, health)

    return health


def save_source_health(
    archive_root: Path,
    health: DocumentExtractionHealth,
) -> None:
    """保存源健康状态（由 archiver 的 disabled 分支调用）。"""
    append_source_health(archive_root, health)


def get_source_health(
    archive_root: Path,
    source_id: str | None = None,
) -> dict[str, DocumentExtractionHealth] | DocumentExtractionHealth | None:
    """获取源健康状态。

    参数：
        archive_root: 归档根目录
        source_id:    源 ID（如果为 None，返回所有源）

    返回：
        如果指定 source_id，返回对应的健康状态或 None
        如果 source_id 为 None，返回所有健康状态的 dict
    """
    all_health = load_source_health_index(archive_root)

    if source_id is None:
        return all_health

    return all_health.get(source_id)
