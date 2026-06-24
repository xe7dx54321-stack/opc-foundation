"""Dashboard usage mapping 测试。

覆盖：
1. build_usage_index 返回正确的映射
2. find_unused_capabilities 找到未使用的能力
3. find_unknown_usage_references 找到未知引用
"""
from __future__ import annotations

from pathlib import Path

from opc_foundation.dashboard.loaders import (
    load_capabilities_config,
    load_usage_registry,
)
from opc_foundation.dashboard.models import (
    Capability,
    CapabilityUsageProject,
    CapabilityUsageRegistry,
    CapabilityUsageStage,
    CapabilityUsageWorkflow,
)
from opc_foundation.dashboard.usage import (
    build_usage_index,
    find_unknown_usage_references,
    find_unused_capabilities,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "configs" / "foundation_capabilities.yaml"
USAGE_PATH = PROJECT_ROOT / "configs" / "capability_usage_registry.example.yaml"


def test_build_usage_index() -> None:
    """build_usage_index 应返回正确的映射。"""
    reg = load_usage_registry(USAGE_PATH)
    index = build_usage_index(reg)
    # 应该至少有一些映射
    assert len(index) > 0
    # 检查映射结构
    for cap_id, usages in index.items():
        assert isinstance(cap_id, str)
        for u in usages:
            assert "project" in u
            assert "workflow" in u
            assert "stage" in u
            assert "agent" in u


def test_find_unused_capabilities() -> None:
    """find_unused_capabilities 应找到未使用的能力。"""
    cap_reg = load_capabilities_config(CONFIG_PATH)
    usage_reg = load_usage_registry(USAGE_PATH)
    unused = find_unused_capabilities(cap_reg.capabilities, usage_reg)
    # 20 个能力中有些没被使用
    assert len(unused) > 0
    assert len(unused) < 20


def test_find_unknown_usage_references() -> None:
    """find_unknown_usage_references 应找到未知引用。"""
    cap_reg = load_capabilities_config(CONFIG_PATH)
    usage_reg = load_usage_registry(USAGE_PATH)
    unknown = find_unknown_usage_references(cap_reg.capabilities, usage_reg)
    # example 配置应该没有未知引用
    assert unknown == []


def test_find_unknown_with_bad_reference() -> None:
    """引用不存在的能力时应返回未知引用。"""
    caps = [
        Capability(
            capability_id="real.cap", name="R", track="research",
            category="research_source", maturity_status="production_trial_ready",
            description="", input_type="", primary_output="",
            health_file="", run_log_file="", failed_queue_file="", docs=[],
        ),
    ]
    usage_reg = CapabilityUsageRegistry(
        version="1",
        updated_at="2026-06-24",
        projects=[
            CapabilityUsageProject(
                project_id="proj1",
                project_name="P1",
                status="planned",
                workflows=[
                    CapabilityUsageWorkflow(
                        workflow_id="wf1",
                        workflow_name="W1",
                        status="planned",
                        stages=[
                            CapabilityUsageStage(
                                stage_id="s1",
                                stage_name="S1",
                                agent="A1",
                                status="planned",
                                purpose="test",
                                capabilities=["real.cap", "fake.cap"],
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )
    unknown = find_unknown_usage_references(caps, usage_reg)
    assert ("proj1", "fake.cap") in unknown
