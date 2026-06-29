"""OPC Foundation Dashboard 模块。

功能说明（小白解读）：
    这个模块提供一个 Streamlit dashboard，用来查看 opc-foundation 的：
    - 能力地图（有哪些能力，属于哪条主线，成熟度如何）
    - 项目工作流（哪些下游项目用了哪些能力）
    - 健康监控（每个能力的运行健康状态）
    - 运行日志（最近的运行记录）
    - 失败队列（失败项列表）
    - 文档入口（相关文档链接）
    - 配置检查（校验配置是否正确）

    核心原则：Foundation provides infrastructure. Business systems keep judgment.
    这个模块只展示基础设施状态，不包含任何投资判断字段。
"""
from __future__ import annotations

from .models import (
    Capability,
    CapabilityRegistry,
    CapabilityRuntimeSummary,
    CapabilityTrack,
    CapabilityUsageProject,
    CapabilityUsageRegistry,
    CapabilityUsageStage,
    CapabilityUsageWorkflow,
    DashboardSummary,
    TrialRuntimeSummary,
    TrialSourceStatus,
)
from .loaders import (
    check_docs_exist,
    load_capabilities_config,
    load_jsonl_safe,
    load_usage_registry,
    validate_capabilities,
)
from .health import (
    build_dashboard_summary,
    build_runtime_summary,
)
from .usage import (
    build_usage_index,
    find_unused_capabilities,
    find_unknown_usage_references,
)
from .docs import (
    collect_core_docs,
    collect_docs_from_capabilities,
)

__all__ = [
    # models
    "Capability",
    "CapabilityRegistry",
    "CapabilityRuntimeSummary",
    "CapabilityTrack",
    "CapabilityUsageProject",
    "CapabilityUsageRegistry",
    "CapabilityUsageStage",
    "CapabilityUsageWorkflow",
    "DashboardSummary",
    "TrialRuntimeSummary",
    "TrialSourceStatus",
    # loaders
    "check_docs_exist",
    "load_capabilities_config",
    "load_jsonl_safe",
    "load_usage_registry",
    "validate_capabilities",
    # health
    "build_dashboard_summary",
    "build_runtime_summary",
    # usage
    "build_usage_index",
    "find_unused_capabilities",
    "find_unknown_usage_references",
    # docs
    "collect_core_docs",
    "collect_docs_from_capabilities",
]
