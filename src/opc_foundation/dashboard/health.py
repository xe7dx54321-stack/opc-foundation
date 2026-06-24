"""健康状态监控。

功能说明（小白解读）：
    根据能力的 health_file / run_log_file / failed_queue_file，
    计算每个能力的运行时健康状态摘要（CapabilityRuntimeSummary）。
    以及整个 dashboard 的汇总统计（DashboardSummary）。

    健康判断规则：
    - not_configured: health_file 为空字符串
    - unknown:        文件不存在或没有任何记录
    - healthy:        最近一次 source_health 为 healthy，或 run_log 为 success
    - degraded:       最近一次 source_health 为 degraded，或有失败但非全失败
    - failed:         最近一次明确 failed
    - needs_attention:最近 N 次中 failed/degraded >= 2，或连续失败 >= 2，
                      或失败队列有积压且最近非 healthy
    - stale:          最近运行时间超过 stale_days 天

    时间解析 fail-soft：解析失败不抛异常，按未知处理。
    不写回 data 文件（只读不写）。

    不包含任何投资判断字段。
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .loaders import load_jsonl_safe
from .models import (
    Capability,
    CapabilityRegistry,
    CapabilityRuntimeSummary,
    DashboardSummary,
)
from .usage import build_usage_index


def _parse_iso(ts: str | None) -> datetime | None:
    """安全解析 ISO 时间字符串。

    功能说明：
        把 ISO 格式的时间字符串解析成 datetime 对象。
        解析失败返回 None，不抛异常（fail-soft）。

    参数：
        ts: ISO 时间字符串（如 "2026-06-24T10:00:00+08:00"）

    返回：
        datetime 对象，解析失败返回 None
    """
    if not ts:
        return None
    try:
        # 兼容带 Z 后缀的 UTC 时间
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _is_stale(latest_run_at: str, stale_days: int) -> bool:
    """判断是否过期（长时间没运行）。

    功能说明：
        如果最近运行时间距现在超过 stale_days 天，返回 True。
        如果时间解析失败或为空，返回 False（无法判断，不算过期）。

    参数：
        latest_run_at: 最近运行时间字符串
        stale_days:    过期阈值天数

    返回：
        True 表示过期，False 表示未过期或无法判断
    """
    dt = _parse_iso(latest_run_at)
    if dt is None:
        return False
    # 处理时区感知和 naive 两种情况
    now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
    delta = now - dt
    return delta.days > stale_days


def _pick_latest_by_field(records: list[dict], field: str) -> dict | None:
    """从记录列表中按指定字段选出最新的一条。

    功能说明：
        按 field 字段（如 checked_at / started_at）排序，返回最大的一条。
        ISO 时间字符串可以按字典序排序（同格式下字典序=时间序）。

    参数：
        records: 记录列表
        field:   排序字段名

    返回：
        最新的一条记录，空列表返回 None
    """
    if not records:
        return None
    return max(records, key=lambda r: r.get(field, "") or "")


def _filter_by_source_type(
    records: list[dict], input_type: str
) -> list[dict]:
    """按 source_type 过滤记录。

    功能说明：
        从 source_health 记录中筛选 source_type 匹配的记录。
        如果没有匹配的，返回全部记录（兜底）。

    参数：
        records:    source_health 记录列表
        input_type: 能力的 input_type（如 rss_feed）

    返回：
        过滤后的记录列表
    """
    if not input_type:
        return records
    matched = [r for r in records if r.get("source_type") == input_type]
    return matched if matched else records


def build_runtime_summary(
    capability: Capability,
    project_root: Path,
    recent_n: int = 3,
    stale_days: int = 7,
) -> CapabilityRuntimeSummary:
    """构建单条能力的运行时健康摘要。

    功能说明：
        读取能力的 health_file / run_log_file / failed_queue_file，
        根据健康判断规则计算运行时状态。

    参数：
        capability:   能力对象
        project_root: 项目根目录（用于拼接相对路径）
        recent_n:     最近运行记录条数（默认 3）
        stale_days:   过期阈值天数（默认 7）

    返回：
        CapabilityRuntimeSummary 对象

    异常处理：
        文件不存在不抛异常，按 unknown 处理。
        时间解析失败不抛异常，按未知处理。
    """
    cap_id = capability.capability_id
    root = Path(project_root)

    # 规则 1：health_file 为空 -> not_configured
    if not capability.health_file:
        return CapabilityRuntimeSummary(
            capability_id=cap_id,
            runtime_health="not_configured",
            latest_status="",
            latest_run_at="",
            last_success_at="",
            last_failure_at="",
            recent_run_count=0,
            recent_failure_count=0,
            consecutive_failures=0,
            failed_queue_count=0,
            needs_attention=False,
            stale=False,
            latest_error="",
        )

    # 读取三个文件
    health_path = root / capability.health_file
    run_log_path = root / capability.run_log_file
    failed_queue_path = root / capability.failed_queue_file

    health_records = load_jsonl_safe(health_path)
    run_log_records = load_jsonl_safe(run_log_path)
    failed_queue_records = load_jsonl_safe(failed_queue_path)

    # 规则 2：没有任何记录 -> unknown
    if not health_records and not run_log_records:
        return CapabilityRuntimeSummary(
            capability_id=cap_id,
            runtime_health="unknown",
            latest_status="",
            latest_run_at="",
            last_success_at="",
            last_failure_at="",
            recent_run_count=0,
            recent_failure_count=0,
            consecutive_failures=0,
            failed_queue_count=len(failed_queue_records),
            needs_attention=len(failed_queue_records) > 0,
            stale=False,
            latest_error="",
        )

    # 按 source_type 过滤 health 记录（更精确）
    filtered_health = _filter_by_source_type(health_records, capability.input_type)
    latest_health = _pick_latest_by_field(filtered_health, "checked_at")

    # 取最近 N 条 run_log 记录
    sorted_runs = sorted(run_log_records, key=lambda r: r.get("started_at", "") or "")
    recent_runs = sorted_runs[-recent_n:] if sorted_runs else []

    # 提取各字段
    latest_status = ""
    latest_run_at = ""
    last_success_at = ""
    last_failure_at = ""
    consecutive_failures = 0
    latest_error = ""

    if latest_health:
        latest_status = latest_health.get("status", "") or ""
        last_success_at = latest_health.get("last_success_at", "") or ""
        last_failure_at = latest_health.get("last_failure_at", "") or ""
        consecutive_failures = latest_health.get("consecutive_failures", 0) or 0
        latest_error = latest_health.get("last_error", "") or ""
        latest_run_at = latest_health.get("checked_at", "") or ""

    # 也从 run_log 补充 latest_run_at 和 latest_status
    if recent_runs:
        last_run = recent_runs[-1]
        run_at = last_run.get("finished_at", "") or last_run.get("started_at", "") or ""
        if run_at and (not latest_run_at or run_at > latest_run_at):
            latest_run_at = run_at
        if not latest_status:
            latest_status = last_run.get("status", "") or ""

    # 统计最近失败次数
    recent_failure_count = sum(
        1 for r in recent_runs if r.get("status") in ("failed", "partial")
    )
    recent_run_count = len(recent_runs)

    # 失败队列积压数
    failed_queue_count = len(failed_queue_records)

    # 判断 runtime_health
    runtime_health = "unknown"

    if latest_health:
        health_status = latest_health.get("status", "")
        if health_status == "healthy":
            runtime_health = "healthy"
        elif health_status == "degraded":
            runtime_health = "degraded"
        elif health_status == "failed":
            runtime_health = "failed"
        elif health_status == "disabled":
            runtime_health = "unknown"
        else:
            runtime_health = "unknown"

    # 如果没有 health 记录但有 run_log，用 run_log 状态判断
    if not latest_health and recent_runs:
        last_run_status = recent_runs[-1].get("status", "")
        if last_run_status == "success":
            runtime_health = "healthy"
        elif last_run_status == "failed":
            runtime_health = "failed"
        elif last_run_status == "partial":
            runtime_health = "degraded"
        else:
            runtime_health = "unknown"

    # needs_attention 判断
    recent_bad = sum(
        1 for r in recent_runs if r.get("status") in ("failed", "partial")
    )
    needs_attention = (
        recent_bad >= 2
        or consecutive_failures >= 2
        or (failed_queue_count > 0 and runtime_health != "healthy")
    )

    # stale 判断
    stale = _is_stale(latest_run_at, stale_days)

    return CapabilityRuntimeSummary(
        capability_id=cap_id,
        runtime_health=runtime_health,
        latest_status=latest_status,
        latest_run_at=latest_run_at,
        last_success_at=last_success_at,
        last_failure_at=last_failure_at,
        recent_run_count=recent_run_count,
        recent_failure_count=recent_failure_count,
        consecutive_failures=consecutive_failures,
        failed_queue_count=failed_queue_count,
        needs_attention=needs_attention,
        stale=stale,
        latest_error=latest_error,
    )


def build_dashboard_summary(
    capabilities: list[Capability],
    runtime_summaries: dict[str, CapabilityRuntimeSummary],
    usage_registry,
) -> DashboardSummary:
    """构建 dashboard 汇总统计。

    功能说明：
        统计能力总数、各成熟度数量、各运行健康数量、需要关注数量、
        过期数量、已使用/未使用数量。

    参数：
        capabilities:      能力列表
        runtime_summaries: {capability_id: CapabilityRuntimeSummary} 字典
        usage_registry:    使用注册表

    返回：
        DashboardSummary 对象
    """
    # 被使用的能力 ID 集合
    used_set = set(build_usage_index(usage_registry).keys())

    total = len(capabilities)

    # 成熟度统计
    ptr = sum(1 for c in capabilities if c.maturity_status == "production_trial_ready")
    mvp = sum(1 for c in capabilities if c.maturity_status == "mvp_ready")
    degraded = sum(1 for c in capabilities if c.maturity_status == "degraded")

    # 运行健康统计
    failed = 0
    unknown = 0
    not_configured = 0
    needs_attention = 0
    stale = 0

    for c in capabilities:
        s = runtime_summaries.get(c.capability_id)
        if s is None:
            continue
        if s.runtime_health == "failed":
            failed += 1
        elif s.runtime_health == "unknown":
            unknown += 1
        elif s.runtime_health == "not_configured":
            not_configured += 1
        if s.needs_attention:
            needs_attention += 1
        if s.stale:
            stale += 1

    # 使用情况统计
    used = sum(1 for c in capabilities if c.capability_id in used_set)
    unused = total - used

    return DashboardSummary(
        total_capabilities=total,
        production_trial_ready_count=ptr,
        mvp_ready_count=mvp,
        degraded_count=degraded,
        failed_count=failed,
        unknown_count=unknown,
        not_configured_count=not_configured,
        needs_attention_count=needs_attention,
        stale_count=stale,
        used_count=used,
        unused_count=unused,
    )
