"""Dashboard health aggregation 测试。

覆盖：
1. not_configured（health_file 为空）
2. unknown（文件不存在）
3. healthy（source_health 为 healthy）
4. degraded（source_health 为 degraded）
5. failed（source_health 为 failed）
6. needs_attention（recent failures >= 2）
7. stale（latest_run_at 超过 stale_days）
8. build_dashboard_summary 统计正确
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from opc_foundation.dashboard.health import (
    build_dashboard_summary,
    build_runtime_summary,
)
from opc_foundation.dashboard.loaders import load_usage_registry
from opc_foundation.dashboard.models import (
    Capability,
    CapabilityRuntimeSummary,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
USAGE_PATH = PROJECT_ROOT / "configs" / "capability_usage_registry.example.yaml"


def _make_cap(health_file: str = "", run_log_file: str = "", failed_queue_file: str = "") -> Capability:
    """创建测试用 Capability。"""
    return Capability(
        capability_id="test.cap",
        name="Test",
        track="research",
        category="research_source",
        maturity_status="production_trial_ready",
        description="test",
        input_type="rss_feed",
        primary_output="data/test/latest.jsonl",
        health_file=health_file,
        run_log_file=run_log_file,
        failed_queue_file=failed_queue_file,
        docs=[],
    )


def _write_jsonl(path: Path, records: list[dict]) -> None:
    """写入 JSONL 文件。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def test_not_configured() -> None:
    """health_file 为空时应返回 not_configured。"""
    cap = _make_cap(health_file="")
    summary = build_runtime_summary(cap, PROJECT_ROOT)
    assert summary.runtime_health == "not_configured"


def test_unknown_when_files_missing(tmp_path: Path) -> None:
    """文件不存在时应返回 unknown。"""
    cap = _make_cap(
        health_file="data/nonexistent/source_health.jsonl",
        run_log_file="data/nonexistent/run_log.jsonl",
        failed_queue_file="data/nonexistent/failed_queue.jsonl",
    )
    summary = build_runtime_summary(cap, PROJECT_ROOT)
    assert summary.runtime_health == "unknown"


def test_healthy(tmp_path: Path) -> None:
    """source_health 为 healthy 时应返回 healthy。"""
    health_path = tmp_path / "source_health.jsonl"
    _write_jsonl(health_path, [{"source_id": "s1", "status": "healthy", "checked_at": "2026-06-24T10:00:00+00:00"}])

    cap = _make_cap(
        health_file=str(health_path),
        run_log_file=str(tmp_path / "run_log.jsonl"),
        failed_queue_file=str(tmp_path / "failed_queue.jsonl"),
    )
    summary = build_runtime_summary(cap, tmp_path)
    assert summary.runtime_health == "healthy"


def test_degraded(tmp_path: Path) -> None:
    """source_health 为 degraded 时应返回 degraded。"""
    health_path = tmp_path / "source_health.jsonl"
    _write_jsonl(health_path, [{"source_id": "s1", "status": "degraded", "checked_at": "2026-06-24T10:00:00+00:00"}])

    cap = _make_cap(
        health_file=str(health_path),
        run_log_file=str(tmp_path / "run_log.jsonl"),
        failed_queue_file=str(tmp_path / "failed_queue.jsonl"),
    )
    summary = build_runtime_summary(cap, tmp_path)
    assert summary.runtime_health == "degraded"


def test_failed(tmp_path: Path) -> None:
    """source_health 为 failed 时应返回 failed。"""
    health_path = tmp_path / "source_health.jsonl"
    _write_jsonl(health_path, [{"source_id": "s1", "status": "failed", "checked_at": "2026-06-24T10:00:00+00:00"}])

    cap = _make_cap(
        health_file=str(health_path),
        run_log_file=str(tmp_path / "run_log.jsonl"),
        failed_queue_file=str(tmp_path / "failed_queue.jsonl"),
    )
    summary = build_runtime_summary(cap, tmp_path)
    assert summary.runtime_health == "failed"


def test_needs_attention(tmp_path: Path) -> None:
    """最近 2 次运行都失败时应返回 needs_attention=True。"""
    run_log_path = tmp_path / "run_log.jsonl"
    _write_jsonl(run_log_path, [
        {"run_id": "r1", "status": "failed", "started_at": "2026-06-22T10:00:00+00:00"},
        {"run_id": "r2", "status": "failed", "started_at": "2026-06-23T10:00:00+00:00"},
        {"run_id": "r3", "status": "failed", "started_at": "2026-06-24T10:00:00+00:00"},
    ])

    cap = _make_cap(
        health_file=str(tmp_path / "source_health.jsonl"),
        run_log_file=str(run_log_path),
        failed_queue_file=str(tmp_path / "failed_queue.jsonl"),
    )
    summary = build_runtime_summary(cap, tmp_path)
    assert summary.needs_attention is True


def test_stale(tmp_path: Path) -> None:
    """最近运行时间超过 stale_days 时应返回 stale=True。"""
    old_date = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    health_path = tmp_path / "source_health.jsonl"
    _write_jsonl(health_path, [{"source_id": "s1", "status": "healthy", "checked_at": old_date}])

    cap = _make_cap(
        health_file=str(health_path),
        run_log_file=str(tmp_path / "run_log.jsonl"),
        failed_queue_file=str(tmp_path / "failed_queue.jsonl"),
    )
    summary = build_runtime_summary(cap, tmp_path, stale_days=7)
    assert summary.stale is True


def test_build_dashboard_summary() -> None:
    """build_dashboard_summary 应正确统计。"""
    from opc_foundation.dashboard.models import Capability

    caps = [
        Capability(
            capability_id="test.cap1", name="C1", track="research",
            category="research_source", maturity_status="production_trial_ready",
            description="", input_type="", primary_output="",
            health_file="", run_log_file="", failed_queue_file="", docs=[],
        ),
        Capability(
            capability_id="test.cap2", name="C2", track="runtime",
            category="runtime", maturity_status="mvp_ready",
            description="", input_type="", primary_output="",
            health_file="", run_log_file="", failed_queue_file="", docs=[],
        ),
    ]
    summaries = {
        "test.cap1": CapabilityRuntimeSummary(
            capability_id="test.cap1", runtime_health="not_configured",
            latest_status="", latest_run_at="", last_success_at="",
            last_failure_at="", recent_run_count=0, recent_failure_count=0,
            consecutive_failures=0, failed_queue_count=0,
            needs_attention=False, stale=False, latest_error="",
        ),
        "test.cap2": CapabilityRuntimeSummary(
            capability_id="test.cap2", runtime_health="not_configured",
            latest_status="", latest_run_at="", last_success_at="",
            last_failure_at="", recent_run_count=0, recent_failure_count=0,
            consecutive_failures=0, failed_queue_count=0,
            needs_attention=False, stale=False, latest_error="",
        ),
    }
    usage_reg = load_usage_registry(USAGE_PATH)
    summary = build_dashboard_summary(caps, summaries, usage_reg)
    assert summary.total_capabilities == 2
    assert summary.production_trial_ready_count == 1
    assert summary.mvp_ready_count == 1
    assert summary.not_configured_count == 2
