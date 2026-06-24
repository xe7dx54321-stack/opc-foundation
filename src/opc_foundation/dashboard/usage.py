"""使用情况分析。

功能说明（小白解读）：
    分析"哪些能力被下游项目使用了，哪些没人用，哪些引用了不存在的能力"。
    帮助发现未使用的能力和错误的引用。

    不包含任何投资判断字段。
"""
from __future__ import annotations

from .models import Capability, CapabilityUsageRegistry


def build_usage_index(
    usage_registry: CapabilityUsageRegistry,
) -> dict[str, list[dict]]:
    """构建使用索引。

    功能说明：
        遍历所有项目的所有工作流的所有阶段，
        把"能力 ID -> 使用位置列表"整理成索引。
        这样查某个能力被谁用了就很快。

    参数：
        usage_registry: 使用注册表

    返回：
        {capability_id: [{project, workflow, stage, agent, status, purpose}, ...]}
    """
    index: dict[str, list[dict]] = {}
    for project in usage_registry.projects:
        for workflow in project.workflows:
            for stage in workflow.stages:
                for cap_id in stage.capabilities:
                    if cap_id not in index:
                        index[cap_id] = []
                    index[cap_id].append(
                        {
                            "project": project.project_id,
                            "workflow": workflow.workflow_id,
                            "stage": stage.stage_id,
                            "agent": stage.agent,
                            "status": stage.status,
                            "purpose": stage.purpose,
                        }
                    )
    return index


def find_unused_capabilities(
    capabilities: list[Capability],
    usage_registry: CapabilityUsageRegistry,
) -> list[str]:
    """找出没有被任何项目使用的能力。

    功能说明：
        对比能力列表和使用索引，返回没有被引用的能力 ID 列表。

    参数：
        capabilities:   能力列表
        usage_registry: 使用注册表

    返回：
        未被使用的能力 ID 列表
    """
    index = build_usage_index(usage_registry)
    return [c.capability_id for c in capabilities if c.capability_id not in index]


def find_unknown_usage_references(
    capabilities: list[Capability],
    usage_registry: CapabilityUsageRegistry,
) -> list[tuple[str, str]]:
    """找出使用注册表中引用了不存在能力的地方。

    功能说明：
        遍历使用注册表，检查每个阶段引用的 capability_id 是否在能力列表中存在。
        返回不存在的引用列表。

    参数：
        capabilities:   能力列表
        usage_registry: 使用注册表

    返回：
        [(project_id, unknown_capability_id), ...] 列表
    """
    known = {c.capability_id for c in capabilities}
    unknown: list[tuple[str, str]] = []
    for project in usage_registry.projects:
        for workflow in project.workflows:
            for stage in workflow.stages:
                for cap_id in stage.capabilities:
                    if cap_id not in known:
                        unknown.append((project.project_id, cap_id))
    return unknown
