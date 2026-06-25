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
    CapabilityRuntimeBinding,
    CapabilityRuntimeEvidence,
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


# ===========================================================================
# Runtime Binding 真实数据聚合（M3B-3 新增）
# ===========================================================================


def _match_records_by_binding(
    records: list[dict],
    binding: CapabilityRuntimeBinding,
) -> list[dict]:
    """根据 binding 规则过滤记录。

    功能说明（小白解读）：
        从一堆记录中，按 binding 的规则筛选出属于这个能力的记录。
        匹配优先级：
        1. 先按 source_types 匹配（如果配置了的话）
        2. 再按 source_ids 精确匹配（如果配置了的话）
        3. 如果都没配置，返回全部记录（兜底）

    参数：
        records: 原始记录列表
        binding: 运行时绑定配置

    返回：
        匹配后的记录列表
    """
    if not records:
        return []

    matched = records

    # 1. 按 source_types 过滤
    if binding.source_types:
        matched = [
            r for r in matched
            if r.get("source_type") in binding.source_types
        ]
        # 如果 source_types 过滤后没有匹配的，用回全部记录（兜底）
        if not matched:
            matched = records

    # 2. 按 source_ids 过滤（如果配置了的话）
    if binding.source_ids:
        id_matched = [
            r for r in matched
            if r.get("source_id") in binding.source_ids
        ]
        if id_matched:
            matched = id_matched

    return matched


def _find_latest_report(report_dir: str, project_root: Path) -> str:
    """查找最新的报告文件。

    功能说明（小白解读）：
        在报告目录中找最新修改的文件，返回它的相对路径。
        目录不存在或为空就返回空字符串。

    参数：
        report_dir:   报告目录（相对路径）
        project_root: 项目根目录

    返回：
        最新报告文件的相对路径，找不到返回空字符串
    """
    if not report_dir:
        return ""

    full_dir = Path(project_root) / report_dir
    if not full_dir.is_dir():
        return ""

    try:
        files = [f for f in full_dir.iterdir() if f.is_file()]
        if not files:
            return ""
        latest = max(files, key=lambda f: f.stat().st_mtime)
        return str(latest.relative_to(project_root))
    except (OSError, PermissionError):
        return ""


def build_runtime_evidence(
    capability: Capability,
    binding: CapabilityRuntimeBinding | None,
    project_root: Path,
) -> CapabilityRuntimeEvidence:
    """构建单条能力的运行时证据。

    功能说明（小白解读）：
        从真实的 source_health / run_log / failed_queue 文件中，
        按 binding 规则匹配出属于这个能力的所有记录。
        这些记录是判断健康状态的"证据"。

        如果没有 binding，返回空的 evidence。

    参数：
        capability:   能力对象
        binding:      运行时绑定配置（可能为 None）
        project_root: 项目根目录

    返回：
        CapabilityRuntimeEvidence 对象
    """
    cap_id = capability.capability_id

    # 没有 binding -> 空证据
    if binding is None:
        return CapabilityRuntimeEvidence(
            capability_id=cap_id,
            matched_health_records=[],
            matched_run_records=[],
            matched_failed_records=[],
            latest_health_record=None,
            latest_run_record=None,
            latest_failed_record=None,
            latest_report_path="",
        )

    root = Path(project_root)

    # 读取三个文件（不存在返回空列表，fail-soft）
    health_path = root / binding.health_file if binding.health_file else None
    run_log_path = root / binding.run_log_file if binding.run_log_file else None
    failed_queue_path = root / binding.failed_queue_file if binding.failed_queue_file else None

    health_records = load_jsonl_safe(health_path) if health_path and health_path.exists() else []
    run_log_records = load_jsonl_safe(run_log_path) if run_log_path and run_log_path.exists() else []
    failed_queue_records = load_jsonl_safe(failed_queue_path) if failed_queue_path and failed_queue_path.exists() else []

    # 按 binding 规则匹配
    matched_health = _match_records_by_binding(health_records, binding)
    matched_run = _match_records_by_binding(run_log_records, binding)
    matched_failed = _match_records_by_binding(failed_queue_records, binding)

    # 找最新的记录
    latest_health = _pick_latest_by_field(matched_health, "checked_at")
    latest_run = _pick_latest_by_field(matched_run, "started_at")
    latest_failed = _pick_latest_by_field(matched_failed, "failed_at")

    # 找最新报告
    latest_report = _find_latest_report(binding.report_dir, root)

    return CapabilityRuntimeEvidence(
        capability_id=cap_id,
        matched_health_records=matched_health,
        matched_run_records=matched_run,
        matched_failed_records=matched_failed,
        latest_health_record=latest_health,
        latest_run_record=latest_run,
        latest_failed_record=latest_failed,
        latest_report_path=latest_report,
    )


def build_runtime_summary_from_evidence(
    capability: Capability,
    binding: CapabilityRuntimeBinding | None,
    evidence: CapabilityRuntimeEvidence,
    recent_n: int = 3,
    stale_days: int = 7,
) -> CapabilityRuntimeSummary:
    """根据运行时证据构建健康摘要。

    功能说明（小白解读）：
        拿到 build_runtime_evidence 收集到的证据后，
        根据健康判断规则算出这个能力的运行状态。

        健康判断规则：
        - 未配置：没有 runtime binding
        - 未知：有 binding 但没有任何记录
        - 运行正常：最近一次 health=healthy 或 run status=success，且失败队列为空
        - 降级：最近一次 health=degraded，或有失败但非全失败
        - 失败：最近一次 health=failed 或 run status=failed
        - 需关注：最近 3 次中失败/降级 >= 2，或连续失败 >= 2，或失败队列有积压且最近非健康
        - 过期：最近运行时间超过 stale_days 天

    参数：
        capability: 能力对象
        binding:    运行时绑定配置（可能为 None）
        evidence:   运行时证据
        recent_n:   最近运行记录条数（默认 3）
        stale_days: 过期阈值天数（默认 7）

    返回：
        CapabilityRuntimeSummary 对象
    """
    cap_id = capability.capability_id

    # 规则 1：没有 binding -> not_configured
    if binding is None:
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

    matched_health = evidence.matched_health_records
    matched_run = evidence.matched_run_records
    matched_failed = evidence.matched_failed_records
    latest_health = evidence.latest_health_record
    latest_run = evidence.latest_run_record

    # 规则 2：没有任何记录 -> unknown
    if not matched_health and not matched_run:
        failed_count = len(matched_failed)
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
            failed_queue_count=failed_count,
            needs_attention=failed_count > 0,
            stale=False,
            latest_error="",
        )

    # 取最近 N 条 run_log 记录
    sorted_runs = sorted(matched_run, key=lambda r: r.get("started_at", "") or "")
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
    if latest_run:
        run_at = latest_run.get("finished_at", "") or latest_run.get("started_at", "") or ""
        if run_at and (not latest_run_at or run_at > latest_run_at):
            latest_run_at = run_at
        if not latest_status:
            latest_status = latest_run.get("status", "") or ""

    # 统计最近失败次数
    recent_failure_count = sum(
        1 for r in recent_runs if r.get("status") in ("failed", "partial")
    )
    recent_run_count = len(recent_runs)

    # 失败队列积压数
    failed_queue_count = len(matched_failed)

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


def suggest_action(health: str, needs_attention: bool, stale: bool) -> str:
    """根据健康状态给出建议动作。

    功能说明（小白解读）：
        根据能力的运行健康状态，给出中文的建议动作。
        用于健康监控页面的"建议动作"列。

    参数：
        health:          运行健康状态（healthy/degraded/failed/unknown/not_configured）
        needs_attention: 是否需要关注
        stale:           是否过期

    返回：
        中文建议动作文本
    """
    if health == "not_configured":
        return "尚未绑定运行数据"
    if health == "unknown":
        return "尚未发现运行记录"
    if stale:
        return "超过设定时间未运行，建议重新运行"
    if health == "failed":
        return "优先查看失败队列和最近报告"
    if needs_attention:
        return "连续异常，建议重新 dry-run 并检查配置"
    if health == "degraded":
        return "查看能力详情中的排查步骤"
    if health == "healthy":
        return "无需处理"
    return "持续观察"
