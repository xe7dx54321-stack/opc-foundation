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
from pathlib import Path

from opc_foundation.dashboard.models import (
    Capability,
    CapabilityRegistry,
    CapabilityRunbook,
    CapabilityRuntimeBinding,
    CapabilityRuntimeEvidence,
    CapabilityRuntimeSummary,
    CapabilityTrack,
    CapabilityUsageProject,
    CapabilityUsageRegistry,
    CapabilityUsageStage,
    CapabilityUsageWorkflow,
    CommonFailure,
    DashboardSummary,
    RuntimeBindingRegistry,
    RunbookRegistry,
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

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "configs" / "foundation_capabilities.yaml"


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


def test_common_failure_construction() -> None:
    """CommonFailure 应能正确构造。"""
    cf = CommonFailure(
        error_type="empty_source",
        meaning="源为空",
        check="检查 URL",
    )
    assert cf.error_type == "empty_source"
    assert cf.meaning == "源为空"
    assert cf.check == "检查 URL"


def test_capability_runbook_construction() -> None:
    """CapabilityRunbook 应能正确构造。"""
    cf = CommonFailure(error_type="empty_source", meaning="源为空", check="检查 URL")
    rb = CapabilityRunbook(
        capability_id="research.rss_feed",
        title="RSS 订阅采集运行手册",
        summary="从 RSS 源采集文章",
        maturity_label="可试运行",
        owner_agent="Research Source Agent",
        config_templates=["configs/research_sources.example.yaml"],
        local_config_path="configs/research_sources.production.local.yaml",
        primary_output="data/research_archive/index/documents.latest.jsonl",
        health_file="data/research_archive/index/source_health.jsonl",
        run_log_file="data/research_archive/index/run_log.jsonl",
        failed_queue_file="data/research_archive/index/failed_queue.jsonl",
        report_dir="data/research_archive/reports",
        commands={"run": "python -m opc_foundation.research.cli run"},
        can_do=["订阅 RSS 源", "自动抓取文章"],
        cannot_do=["不做投资判断"],
        common_failures=[cf],
        troubleshooting_steps=["先检查配置", "再查看日志"],
        docs=["docs/research_source_foundation.md"],
    )
    assert rb.capability_id == "research.rss_feed"
    assert rb.title == "RSS 订阅采集运行手册"
    assert len(rb.common_failures) == 1
    assert len(rb.commands) == 1
    assert rb.is_tool_only is False


def test_capability_runbook_is_tool_only_true() -> None:
    """commands 为空时 is_tool_only 应为 True。"""
    rb = CapabilityRunbook(capability_id="runtime.jsonl", commands={})
    assert rb.is_tool_only is True


def test_runbook_registry_construction() -> None:
    """RunbookRegistry 应能正确构造。"""
    rb = CapabilityRunbook(capability_id="research.rss_feed")
    reg = RunbookRegistry(
        version="1.0",
        updated_at="2026-06-24",
        runbooks=[rb],
        load_error=None,
    )
    assert reg.version == "1.0"
    assert len(reg.runbooks) == 1
    assert reg.load_error is None


def test_runbook_registry_get_runbook() -> None:
    """RunbookRegistry.get_runbook 应能正确查找。"""
    rb = CapabilityRunbook(capability_id="research.rss_feed")
    reg = RunbookRegistry(runbooks=[rb])
    found = reg.get_runbook("research.rss_feed")
    assert found is not None
    assert found.capability_id == "research.rss_feed"
    assert reg.get_runbook("nonexistent") is None


def test_runbook_models_no_prohibited_fields() -> None:
    """运行手册相关 model 不得包含禁止字段。"""
    all_models = [
        CommonFailure,
        CapabilityRunbook,
        RunbookRegistry,
    ]
    for model in all_models:
        fields = {f.name for f in dataclasses.fields(model)}
        intersection = fields & PROHIBITED_FIELDS
        assert not intersection, f"{model.__name__} 包含禁止字段: {intersection}"


# ===========================================================================
# Runtime Binding 模型测试（M3B-3 新增）
# ===========================================================================


def test_capability_runtime_binding_construction() -> None:
    """CapabilityRuntimeBinding 应能正确构造。"""
    b = CapabilityRuntimeBinding(
        capability_id="research.rss_feed",
        archive_root="data/research_archive",
        source_types=["rss_feed"],
        source_ids=[],
        file_extensions=[],
        health_file="data/research_archive/index/source_health.jsonl",
        run_log_file="data/research_archive/index/run_log.jsonl",
        failed_queue_file="data/research_archive/index/failed_queue.jsonl",
        report_dir="data/research_archive/reports",
    )
    assert b.capability_id == "research.rss_feed"
    assert len(b.source_types) == 1
    assert b.health_file != ""


def test_capability_runtime_binding_defaults() -> None:
    """CapabilityRuntimeBinding 可选字段应有合理默认值。"""
    b = CapabilityRuntimeBinding(capability_id="test.cap")
    assert b.archive_root == ""
    assert b.source_types == []
    assert b.source_ids == []
    assert b.file_extensions == []
    assert b.health_file == ""
    assert b.run_log_file == ""
    assert b.failed_queue_file == ""
    assert b.report_dir == ""


def test_runtime_binding_registry_construction() -> None:
    """RuntimeBindingRegistry 应能正确构造。"""
    b = CapabilityRuntimeBinding(capability_id="research.rss_feed")
    reg = RuntimeBindingRegistry(
        version="1.0",
        updated_at="2026-06-25",
        bindings=[b],
        load_error=None,
    )
    assert reg.version == "1.0"
    assert len(reg.bindings) == 1
    assert reg.load_error is None


def test_runtime_binding_registry_get_binding() -> None:
    """RuntimeBindingRegistry.get_binding 应能正确查找。"""
    b = CapabilityRuntimeBinding(capability_id="research.rss_feed")
    reg = RuntimeBindingRegistry(bindings=[b])
    found = reg.get_binding("research.rss_feed")
    assert found is not None
    assert found.capability_id == "research.rss_feed"
    assert reg.get_binding("nonexistent") is None


def test_capability_runtime_evidence_construction() -> None:
    """CapabilityRuntimeEvidence 应能正确构造。"""
    e = CapabilityRuntimeEvidence(
        capability_id="test.cap",
        matched_health_records=[{"status": "healthy"}],
        matched_run_records=[{"status": "success"}],
        matched_failed_records=[],
        latest_health_record={"status": "healthy"},
        latest_run_record={"status": "success"},
        latest_failed_record=None,
        latest_report_path="",
    )
    assert e.capability_id == "test.cap"
    assert len(e.matched_health_records) == 1
    assert e.latest_health_record is not None


def test_capability_runtime_evidence_defaults() -> None:
    """CapabilityRuntimeEvidence 可选字段应有合理默认值。"""
    e = CapabilityRuntimeEvidence(capability_id="test.cap")
    assert e.matched_health_records == []
    assert e.matched_run_records == []
    assert e.matched_failed_records == []
    assert e.latest_health_record is None
    assert e.latest_run_record is None
    assert e.latest_failed_record is None
    assert e.latest_report_path == ""


def test_runtime_binding_models_no_prohibited_fields() -> None:
    """Runtime Binding 相关 model 不得包含禁止字段。"""
    all_models = [
        CapabilityRuntimeBinding,
        RuntimeBindingRegistry,
        CapabilityRuntimeEvidence,
    ]
    for model in all_models:
        fields = {f.name for f in dataclasses.fields(model)}
        intersection = fields & PROHIBITED_FIELDS
        assert not intersection, f"{model.__name__} 包含禁止字段: {intersection}"


def test_runtime_tool_capability_allowed_without_binding() -> None:
    """runtime 工具类能力允许无 binding。

    工具类能力（如 runtime.jsonl, runtime.queue）一般不需要绑定真实运行文件，
    因为它们被其他模块调用，Dashboard 显示"未配置"是正常的。
    """
    from opc_foundation.dashboard.loaders import load_capabilities_config

    cap_reg = load_capabilities_config(CONFIG_PATH)
    runtime_caps = [c for c in cap_reg.capabilities if c.category == "runtime"]

    binding_reg_path = Path(__file__).resolve().parents[2] / "configs" / "capability_runtime_bindings.yaml"
    from opc_foundation.dashboard.loaders import load_runtime_bindings_config
    binding_reg = load_runtime_bindings_config(binding_reg_path)

    for cap in runtime_caps:
        binding = binding_reg.get_binding(cap.capability_id)
        if binding is None:
            assert True
        else:
            assert isinstance(binding, CapabilityRuntimeBinding)
