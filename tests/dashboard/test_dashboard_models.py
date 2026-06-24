"""Dashboard models 测试。

覆盖：
1. CapabilityTrack 可以构造
2. Capability 可以构造
3. CapabilityRegistry 可以构造
4. CapabilityRuntimeSummary 默认值正确
5. DashboardSummary 默认值正确
6. models 不包含禁止字段
"""
from __future__ import annotations

import dataclasses

from opc_foundation.dashboard.models import (
    Capability,
    CapabilityRegistry,
    CapabilityRuntimeSummary,
    CapabilityTrack,
    CapabilityUsageProject,
    CapabilityUsageRegistry,
    CapabilityUsageStage,
    CapabilityUsageWorkflow,
    DashboardSummary,
)

PROHIBITED_FIELDS = {
    "affected_tickers",
    "expectation_delta",
    "investment_rating",
    "trade_signal",
    "watchlist",
    "action_decision",
    "recommendation",
    "opportunity_score",
    "risk_score",
    "position_size",
    "target_price",
}


def test_capability_track_construction() -> None:
    """CapabilityTrack 应能正确构造。"""
    track = CapabilityTrack(
        track_id="research",
        name="Research Source Foundation",
        status="production_trial_ready",
        description="Public research archiving.",
    )
    assert track.track_id == "research"
    assert track.status == "production_trial_ready"


def test_capability_construction() -> None:
    """Capability 应能正确构造。"""
    cap = Capability(
        capability_id="research.rss_feed",
        name="RSS Feed",
        track="research",
        category="research_source",
        maturity_status="production_trial_ready",
        description="Archive RSS feeds.",
        input_type="rss_feed",
        primary_output="data/research_archive/index/documents.latest.jsonl",
        health_file="data/research_archive/index/source_health.jsonl",
        run_log_file="data/research_archive/index/run_log.jsonl",
        failed_queue_file="data/research_archive/index/failed_queue.jsonl",
        docs=["docs/research_source_foundation.md"],
    )
    assert cap.capability_id == "research.rss_feed"
    assert cap.track == "research"
    assert len(cap.docs) == 1


def test_capability_registry_construction() -> None:
    """CapabilityRegistry 应能正确构造。"""
    reg = CapabilityRegistry(
        version="1",
        updated_at="2026-06-24",
        tracks=[],
        capabilities=[],
    )
    assert reg.version == "1"
    assert len(reg.tracks) == 0
    assert len(reg.capabilities) == 0


def test_capability_runtime_summary_defaults() -> None:
    """CapabilityRuntimeSummary 各字段应有合理默认值。"""
    s = CapabilityRuntimeSummary(
        capability_id="test.cap",
        runtime_health="unknown",
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
    assert s.runtime_health == "unknown"
    assert s.needs_attention is False
    assert s.stale is False


def test_dashboard_summary_defaults() -> None:
    """DashboardSummary 各字段应有合理默认值。"""
    s = DashboardSummary(
        total_capabilities=0,
        production_trial_ready_count=0,
        mvp_ready_count=0,
        degraded_count=0,
        failed_count=0,
        unknown_count=0,
        not_configured_count=0,
        needs_attention_count=0,
        stale_count=0,
        used_count=0,
        unused_count=0,
    )
    assert s.total_capabilities == 0
    assert s.unused_count == 0


def test_models_no_prohibited_fields() -> None:
    """所有 dashboard model 不得包含禁止的业务判断字段。"""
    all_models = [
        CapabilityTrack,
        Capability,
        CapabilityRegistry,
        CapabilityUsageStage,
        CapabilityUsageWorkflow,
        CapabilityUsageProject,
        CapabilityUsageRegistry,
        CapabilityRuntimeSummary,
        DashboardSummary,
    ]
    for model in all_models:
        fields = {f.name for f in dataclasses.fields(model)}
        intersection = fields & PROHIBITED_FIELDS
        assert not intersection, f"{model.__name__} 包含禁止字段: {intersection}"


def test_usage_models_construction() -> None:
    """使用关系模型应能正确构造。"""
    stage = CapabilityUsageStage(
        stage_id="collect",
        stage_name="采集",
        agent="Agent",
        status="planned",
        purpose="测试",
        capabilities=["research.rss_feed"],
    )
    wf = CapabilityUsageWorkflow(
        workflow_id="wf1",
        workflow_name="工作流",
        status="planned",
        stages=[stage],
    )
    proj = CapabilityUsageProject(
        project_id="proj1",
        project_name="项目",
        status="planned",
        workflows=[wf],
    )
    reg = CapabilityUsageRegistry(
        version="1",
        updated_at="2026-06-24",
        projects=[proj],
    )
    assert reg.projects[0].workflows[0].stages[0].capabilities[0] == "research.rss_feed"
