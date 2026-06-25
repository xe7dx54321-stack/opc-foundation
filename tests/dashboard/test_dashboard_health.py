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
    build_runtime_evidence,
    build_runtime_summary,
    build_runtime_summary_from_evidence,
    suggest_action,
)
from opc_foundation.dashboard.loaders import load_usage_registry
from opc_foundation.dashboard.models import (
    Capability,
    CapabilityRuntimeBinding,
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


# ===========================================================================
# Runtime Binding 健康聚合测试（M3B-3 新增）
# ===========================================================================


def _make_test_cap() -> Capability:
    """创建测试用 Capability。"""
    return Capability(
        capability_id="test.cap",
        name="Test Cap",
        track="research",
        category="research_source",
        maturity_status="production_trial_ready",
        description="test",
        input_type="rss_feed",
        primary_output="data/test/latest.jsonl",
        health_file="data/test/source_health.jsonl",
        run_log_file="data/test/run_log.jsonl",
        failed_queue_file="data/test/failed_queue.jsonl",
        docs=[],
    )


def _make_test_binding() -> CapabilityRuntimeBinding:
    """创建测试用 CapabilityRuntimeBinding。"""
    return CapabilityRuntimeBinding(
        capability_id="test.cap",
        archive_root="data/test",
        source_types=["rss_feed"],
        source_ids=[],
        health_file="data/test/source_health.jsonl",
        run_log_file="data/test/run_log.jsonl",
        failed_queue_file="data/test/failed_queue.jsonl",
        report_dir="data/test/reports",
    )


def _write_jsonl(path: Path, records: list[dict]) -> None:
    """写入 JSONL 文件。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def test_build_runtime_evidence_no_binding() -> None:
    """无 binding 时返回空证据。"""
    cap = _make_test_cap()
    evidence = build_runtime_evidence(cap, None, PROJECT_ROOT)
    assert evidence.capability_id == "test.cap"
    assert len(evidence.matched_health_records) == 0
    assert evidence.latest_health_record is None


def test_build_runtime_summary_no_binding() -> None:
    """无 binding 时显示"未配置"。"""
    from opc_foundation.dashboard.models import CapabilityRuntimeEvidence

    cap = _make_test_cap()
    binding = None
    evidence = CapabilityRuntimeEvidence(capability_id="test.cap")
    summary = build_runtime_summary_from_evidence(cap, binding, evidence)
    assert summary.runtime_health == "not_configured"


def test_build_runtime_summary_healthy(tmp_path: Path) -> None:
    """source_health healthy 能聚合为 healthy。"""
    cap = _make_test_cap()
    binding = _make_test_binding()

    health_path = tmp_path / "data" / "test" / "source_health.jsonl"
    _write_jsonl(health_path, [
        {"source_id": "s1", "source_type": "rss_feed", "status": "healthy",
         "checked_at": "2026-06-24T10:00:00+00:00"},
    ])

    evidence = build_runtime_evidence(cap, binding, tmp_path)
    summary = build_runtime_summary_from_evidence(cap, binding, evidence)
    assert summary.runtime_health == "healthy"


def test_build_runtime_summary_degraded(tmp_path: Path) -> None:
    """source_health degraded 能聚合为 degraded。"""
    cap = _make_test_cap()
    binding = _make_test_binding()

    health_path = tmp_path / "data" / "test" / "source_health.jsonl"
    _write_jsonl(health_path, [
        {"source_id": "s1", "source_type": "rss_feed", "status": "degraded",
         "checked_at": "2026-06-24T10:00:00+00:00"},
    ])

    evidence = build_runtime_evidence(cap, binding, tmp_path)
    summary = build_runtime_summary_from_evidence(cap, binding, evidence)
    assert summary.runtime_health == "degraded"


def test_build_runtime_summary_failed(tmp_path: Path) -> None:
    """source_health failed 能聚合为 failed。"""
    cap = _make_test_cap()
    binding = _make_test_binding()

    health_path = tmp_path / "data" / "test" / "source_health.jsonl"
    _write_jsonl(health_path, [
        {"source_id": "s1", "source_type": "rss_feed", "status": "failed",
         "checked_at": "2026-06-24T10:00:00+00:00"},
    ])

    evidence = build_runtime_evidence(cap, binding, tmp_path)
    summary = build_runtime_summary_from_evidence(cap, binding, evidence)
    assert summary.runtime_health == "failed"


def test_build_runtime_summary_unknown_no_records(tmp_path: Path) -> None:
    """无记录时显示 unknown_never_run（M3B-3b 校准后状态名）。"""
    cap = _make_test_cap()
    binding = _make_test_binding()

    evidence = build_runtime_evidence(cap, binding, tmp_path)
    summary = build_runtime_summary_from_evidence(cap, binding, evidence)
    assert summary.runtime_health == "unknown_never_run"


def test_build_runtime_summary_failed_queue_triggers_attention(tmp_path: Path) -> None:
    """failed_queue 非空能触发"需关注"。"""
    cap = _make_test_cap()
    binding = _make_test_binding()

    health_path = tmp_path / "data" / "test" / "source_health.jsonl"
    _write_jsonl(health_path, [
        {"source_id": "s1", "source_type": "rss_feed", "status": "degraded",
         "checked_at": "2026-06-24T10:00:00+00:00"},
    ])

    failed_path = tmp_path / "data" / "test" / "failed_queue.jsonl"
    _write_jsonl(failed_path, [
        {"source_id": "s1", "source_type": "rss_feed", "failed_at": "2026-06-24T09:00:00+00:00"},
    ])

    evidence = build_runtime_evidence(cap, binding, tmp_path)
    summary = build_runtime_summary_from_evidence(cap, binding, evidence)
    assert summary.needs_attention is True
    assert summary.failed_queue_count == 1


def test_build_runtime_summary_recent_three_failures_triggers_attention(tmp_path: Path) -> None:
    """最近三次异常能触发"需关注"。"""
    cap = _make_test_cap()
    binding = _make_test_binding()

    run_log_path = tmp_path / "data" / "test" / "run_log.jsonl"
    _write_jsonl(run_log_path, [
        {"run_id": "r1", "source_type": "rss_feed", "status": "failed",
         "started_at": "2026-06-22T10:00:00+00:00"},
        {"run_id": "r2", "source_type": "rss_feed", "status": "failed",
         "started_at": "2026-06-23T10:00:00+00:00"},
        {"run_id": "r3", "source_type": "rss_feed", "status": "failed",
         "started_at": "2026-06-24T10:00:00+00:00"},
    ])

    evidence = build_runtime_evidence(cap, binding, tmp_path)
    summary = build_runtime_summary_from_evidence(cap, binding, evidence, recent_n=3)
    assert summary.needs_attention is True
    assert summary.recent_failure_count >= 2


def test_build_runtime_summary_stale(tmp_path: Path) -> None:
    """过旧 latest_run_at 能触发"过期"。"""
    cap = _make_test_cap()
    binding = _make_test_binding()

    old_date = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    health_path = tmp_path / "data" / "test" / "source_health.jsonl"
    _write_jsonl(health_path, [
        {"source_id": "s1", "source_type": "rss_feed", "status": "healthy",
         "checked_at": old_date},
    ])

    evidence = build_runtime_evidence(cap, binding, tmp_path)
    summary = build_runtime_summary_from_evidence(cap, binding, evidence, stale_days=7)
    assert summary.stale is True


def test_suggest_action_not_configured() -> None:
    """suggest_action: not_configured 返回正确中文。"""
    assert suggest_action("not_configured", False, False) == "尚未绑定运行数据"


def test_suggest_action_unknown() -> None:
    """suggest_action: unknown_never_run 返回正确中文（M3B-3b 校准后）。"""
    assert suggest_action("unknown_never_run", False, False) == "尚未发现运行记录，运行能力后会更新"


def test_suggest_action_stale() -> None:
    """suggest_action: stale 返回正确中文。"""
    assert suggest_action("healthy", False, True) == "超过设定时间未运行，建议重新运行"


def test_suggest_action_failed() -> None:
    """suggest_action: failed 返回正确中文。"""
    assert suggest_action("failed", True, False) == "优先查看失败队列和最近报告"


def test_suggest_action_needs_attention() -> None:
    """suggest_action: needs_attention 返回正确中文。"""
    assert suggest_action("degraded", True, False) == "连续异常，建议重新 dry-run 并检查配置"


def test_suggest_action_degraded() -> None:
    """suggest_action: degraded 返回正确中文。"""
    assert suggest_action("degraded", False, False) == "查看能力详情中的排查步骤"


def test_suggest_action_healthy() -> None:
    """suggest_action: healthy 返回正确中文。"""
    assert suggest_action("healthy", False, False) == "无需处理"


def test_suggest_action_default() -> None:
    """suggest_action: 未知状态返回默认中文。"""
    assert suggest_action("disabled", False, False) == "持续观察"
