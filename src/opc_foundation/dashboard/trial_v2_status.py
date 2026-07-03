"""Trial V2 Content-Ready 只读状态加载器。

M3C-5A10-sidecar: 读取 data/foundation_trial_v2_content_ready/ 运行产物，
提供 Daily Status 和 Control Center 的只读观察数据。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class TrialV2ContentReadySummary:
    """Trial V2 Content-Ready 运行时摘要（只读）。"""
    source_count: int = 8
    last_run_at: Optional[str] = None
    latest_run_id: Optional[str] = None
    success_count: int = 0
    failed_count: int = 0
    content_ready_count: int = 0
    content_watch_count: int = 0
    content_reject_count: int = 0
    technical_only_count: int = 0
    failed_queue_count: int = 0
    production_enabled: bool = False
    trial_scope: str = "trial_v2_content_ready"
    observation_status: str = "not_started"
    wind_public_watch_flag: bool = False
    wind_public_garbled_text_observed: bool = False
    data_exists: bool = False
    latest_report_path: Optional[str] = None
    latest_report_content: Optional[str] = None


def _load_jsonl_safe(path: Path) -> list[dict]:
    """安全加载 JSONL 文件。"""
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").strip().split("\n")
        records = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except (json.JSONDecodeError, TypeError):
                continue
        return records
    except Exception:
        return []


def _parse_iso_timestamp(ts: Optional[str]) -> Optional[datetime]:
    """安全解析 ISO 时间戳。"""
    if not ts:
        return None
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00").split("+")[0])
        except (ValueError, AttributeError):
            continue
    return None


def _determine_observation_status(run_records: list[dict]) -> str:
    """判定 24h 观察状态。

    规则：
    - not_started: 没有任何 run 记录
    - partial_observation: 有 run 记录，但不足 morning + afternoon + evening + daily_check
    - completed_24h: 检测到同一观察窗口内包含 morning + afternoon + evening + daily_check
    """
    if not run_records:
        return "not_started"

    # 收集所有不同的 run_id / job 字段
    run_types = set()
    for r in run_records:
        rid = r.get("run_id", "")
        job = r.get("job", "")
        if rid:
            if "morning" in rid:
                run_types.add("morning")
            elif "afternoon" in rid:
                run_types.add("afternoon")
            elif "evening" in rid:
                run_types.add("evening")
        if job:
            if "morning" in job:
                run_types.add("morning")
            elif "afternoon" in job:
                run_types.add("afternoon")
            elif "evening" in job:
                run_types.add("evening")
            elif "daily_check" in job or "check" in job:
                run_types.add("daily_check")
        # Fallback: also check status field for daily_check
        if rid and ("check" in rid):
            run_types.add("daily_check")

    required = {"morning", "afternoon", "evening", "daily_check"}
    if required.issubset(run_types):
        return "completed_24h"
    return "partial_observation"


def _detect_wind_public_garbled_text(
    preflight_path: Optional[Path],
    report_dir: Optional[Path],
) -> tuple[bool, bool]:
    """检测 wind_public watch flag 和 garbled_text。"""
    watch_flag = False
    garbled_observed = False

    # Check preflight data
    if preflight_path and preflight_path.exists():
        records = _load_jsonl_safe(preflight_path)
        for r in records:
            if r.get("source_id") == "wind_public":
                watch_flag = True
                flags = r.get("noise_flags", [])
                if "garbled_text" in flags:
                    garbled_observed = True

    # Check latest report
    if report_dir and report_dir.exists():
        latest = report_dir / "trial_v2_content_ready_validation_latest.md"
        if latest.exists():
            content = latest.read_text(encoding="utf-8").lower()
            if "wind_public" in content:
                watch_flag = True
            if "garbled" in content or "乱码" in content:
                garbled_observed = True

    return watch_flag, garbled_observed


def load_trial_v2_content_ready_summary(
    base_dir: Optional[str] = None,
) -> TrialV2ContentReadySummary:
    """加载 Trial V2 Content-Ready 运行时摘要（只读，fail-soft）。

    Args:
        base_dir: 仓库根目录。默认自动检测。

    Returns:
        TrialV2ContentReadySummary: 只读摘要数据。
    """
    if base_dir is None:
        base_dir = os.getcwd()

    base = Path(base_dir)
    idx_dir = base / "data" / "foundation_trial_v2_content_ready" / "index"
    rep_dir = base / "data" / "foundation_trial_v2_content_ready" / "reports"
    preflight_path = idx_dir / "preflight_content_ready_audit.jsonl"
    health_path = idx_dir / "source_health.jsonl"
    runlog_path = idx_dir / "run_log.jsonl"
    failed_path = idx_dir / "failed_queue.jsonl"
    latest_report = rep_dir / "trial_v2_content_ready_validation_latest.md"

    # Fail-soft: 如果 data 目录不存在
    if not idx_dir.exists():
        return TrialV2ContentReadySummary()

    data_exists = True

    # Load source_health
    health_records = _load_jsonl_safe(health_path)

    # Load run_log
    run_records = _load_jsonl_safe(runlog_path)

    # Load failed_queue
    failed_records = _load_jsonl_safe(failed_path)

    # Determine last_run_at and latest_run_id
    last_run_at = None
    latest_run_id = None
    latest_ts = None
    for r in run_records:
        ts = _parse_iso_timestamp(r.get("timestamp"))
        if ts and (latest_ts is None or ts > latest_ts):
            latest_ts = ts
            last_run_at = r.get("timestamp", "")
            latest_run_id = r.get("run_id", "")

    # Count success/failed from health records
    success_count = 0
    failed_count = 0
    for r in health_records:
        status = r.get("content_status", "pending")
        if status == "content_ready":
            success_count += 1
        elif status in ("content_watch", "content_reject", "technical_only"):
            failed_count += 1

    # Count by content_status from latest batch
    # Use the latest 8 records (one batch)
    latest_batch = health_records[-8:] if len(health_records) >= 8 else health_records
    content_ready_count = sum(1 for r in latest_batch if r.get("content_status") == "content_ready")
    content_watch_count = sum(1 for r in latest_batch if r.get("content_status") == "content_watch")
    content_reject_count = sum(1 for r in latest_batch if r.get("content_status") == "content_reject")
    technical_only_count = sum(1 for r in latest_batch if r.get("content_status") == "technical_only")

    # Source count from allowlist
    source_count = len(set(r.get("source_id", "") for r in health_records)) if health_records else 8

    # Observation status
    observation_status = _determine_observation_status(run_records)

    # Wind public garbled text detection
    wind_watch, wind_garbled = _detect_wind_public_garbled_text(preflight_path, rep_dir)

    # Latest report
    report_content = None
    if latest_report.exists():
        try:
            report_content = latest_report.read_text(encoding="utf-8")
        except Exception:
            report_content = None

    return TrialV2ContentReadySummary(
        source_count=source_count,
        last_run_at=last_run_at,
        latest_run_id=latest_run_id,
        success_count=success_count,
        failed_count=failed_count,
        content_ready_count=content_ready_count,
        content_watch_count=content_watch_count,
        content_reject_count=content_reject_count,
        technical_only_count=technical_only_count,
        failed_queue_count=len(failed_records),
        production_enabled=False,
        trial_scope="trial_v2_content_ready",
        observation_status=observation_status,
        wind_public_watch_flag=wind_watch,
        wind_public_garbled_text_observed=wind_garbled,
        data_exists=data_exists,
        latest_report_path=str(latest_report) if latest_report.exists() else None,
        latest_report_content=report_content,
    )
