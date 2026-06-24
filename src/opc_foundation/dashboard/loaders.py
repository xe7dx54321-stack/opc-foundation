"""配置加载器。

功能说明（小白解读）：
    负责从 YAML 文件和 JSONL 文件加载数据，转换成 dashboard 的数据模型。
    文件不存在时返回空 registry，不抛异常（fail-soft）。

    不包含任何投资判断字段。
"""
from __future__ import annotations

from pathlib import Path

import yaml

from ..runtime.jsonl import read_jsonl
from .models import (
    Capability,
    CapabilityRegistry,
    CapabilityTrack,
    CapabilityUsageProject,
    CapabilityUsageRegistry,
    CapabilityUsageStage,
    CapabilityUsageWorkflow,
)


def load_capabilities_config(path: str | Path) -> CapabilityRegistry:
    """从 YAML 文件加载能力注册表。

    功能说明：
        读取 foundation_capabilities.yaml，解析成 CapabilityRegistry 对象。
        如果文件不存在，返回空 registry（version 为空，列表为空）。

    参数：
        path: YAML 文件路径

    返回：
        CapabilityRegistry 对象

    异常处理：
        文件不存在不抛异常，返回空 registry。
        YAML 解析失败抛出 yaml.YAMLError（由调用方处理）。
    """
    p = Path(path)
    if not p.exists():
        return CapabilityRegistry(
            version="",
            updated_at="",
            tracks=[],
            capabilities=[],
        )

    with open(p, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    # 解析主线列表
    tracks: list[CapabilityTrack] = []
    for t in data.get("tracks", []) or []:
        tracks.append(
            CapabilityTrack(
                track_id=t.get("track_id", ""),
                name=t.get("name", ""),
                status=t.get("status", ""),
                description=t.get("description", ""),
            )
        )

    # 解析能力列表
    capabilities: list[Capability] = []
    for c in data.get("capabilities", []) or []:
        capabilities.append(
            Capability(
                capability_id=c.get("capability_id", ""),
                name=c.get("name", ""),
                track=c.get("track", ""),
                category=c.get("category", ""),
                maturity_status=c.get("maturity_status", ""),
                description=c.get("description", ""),
                input_type=c.get("input_type", ""),
                primary_output=c.get("primary_output", ""),
                health_file=c.get("health_file", ""),
                run_log_file=c.get("run_log_file", ""),
                failed_queue_file=c.get("failed_queue_file", ""),
                docs=list(c.get("docs", []) or []),
            )
        )

    return CapabilityRegistry(
        version=str(data.get("version", "")),
        updated_at=str(data.get("updated_at", "")),
        tracks=tracks,
        capabilities=capabilities,
    )


def load_usage_registry(path: str | Path) -> CapabilityUsageRegistry:
    """从 YAML 文件加载使用注册表。

    功能说明：
        读取 capability_usage_registry.yaml，解析成 CapabilityUsageRegistry 对象。
        如果文件不存在，返回空 registry。

    参数：
        path: YAML 文件路径

    返回：
        CapabilityUsageRegistry 对象

    异常处理：
        文件不存在不抛异常，返回空 registry。
        YAML 解析失败抛出 yaml.YAMLError（由调用方处理）。
    """
    p = Path(path)
    if not p.exists():
        return CapabilityUsageRegistry(
            version="",
            updated_at="",
            projects=[],
        )

    with open(p, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    projects: list[CapabilityUsageProject] = []
    for proj in data.get("projects", []) or []:
        workflows: list[CapabilityUsageWorkflow] = []
        for wf in proj.get("workflows", []) or []:
            stages: list[CapabilityUsageStage] = []
            for st in wf.get("stages", []) or []:
                stages.append(
                    CapabilityUsageStage(
                        stage_id=st.get("stage_id", ""),
                        stage_name=st.get("stage_name", ""),
                        agent=st.get("agent", ""),
                        status=st.get("status", ""),
                        purpose=st.get("purpose", ""),
                        capabilities=list(st.get("capabilities", []) or []),
                    )
                )
            workflows.append(
                CapabilityUsageWorkflow(
                    workflow_id=wf.get("workflow_id", ""),
                    workflow_name=wf.get("workflow_name", ""),
                    status=wf.get("status", ""),
                    stages=stages,
                )
            )
        projects.append(
            CapabilityUsageProject(
                project_id=proj.get("project_id", ""),
                project_name=proj.get("project_name", ""),
                status=proj.get("status", ""),
                workflows=workflows,
            )
        )

    return CapabilityUsageRegistry(
        version=str(data.get("version", "")),
        updated_at=str(data.get("updated_at", "")),
        projects=projects,
    )


def load_jsonl_safe(path: str | Path) -> list[dict]:
    """安全读取 JSONL 文件。

    功能说明：
        复用 runtime.jsonl.read_jsonl，读取 JSONL 文件的所有记录。
        文件不存在或空文件返回空列表，不会抛异常。

    参数：
        path: JSONL 文件路径

    返回：
        dict 列表，空文件或文件不存在返回 []

    异常处理：
        不会抛出 JSONDecodeError，坏行被跳过。
    """
    return read_jsonl(path)


def check_docs_exist(
    capabilities: list[Capability], project_root: Path
) -> dict[str, list[str]]:
    """检查每个能力的文档路径是否存在。

    功能说明：
        遍历所有能力的 docs 列表，检查每个文档路径在 project_root 下是否存在。
        返回缺失路径的字典。

    参数：
        capabilities: 能力列表
        project_root: 项目根目录

    返回：
        {capability_id: [缺失的文档路径列表]}
        如果某能力的所有文档都存在，不会出现在结果中。
    """
    root = Path(project_root)
    result: dict[str, list[str]] = {}
    for cap in capabilities:
        missing: list[str] = []
        for doc_path in cap.docs:
            full = root / doc_path
            if not full.exists():
                missing.append(doc_path)
        if missing:
            result[cap.capability_id] = missing
    return result


def validate_capabilities(registry: CapabilityRegistry) -> list[str]:
    """校验能力注册表的完整性。

    功能说明：
        检查两个规则：
        1. capability_id 必须唯一（不能重复）
        2. 每个能力的 track 必须在 tracks 列表中存在

    参数：
        registry: 能力注册表

    返回：
        错误信息列表。空列表表示校验通过。
    """
    errors: list[str] = []

    # 收集所有合法的 track_id
    valid_tracks = {t.track_id for t in registry.tracks}

    # 检查 capability_id 唯一性
    seen: dict[str, int] = {}
    for cap in registry.capabilities:
        seen[cap.capability_id] = seen.get(cap.capability_id, 0) + 1
    for cap_id, count in seen.items():
        if count > 1:
            errors.append(f"capability_id 重复: {cap_id} 出现了 {count} 次")

    # 检查 track 引用有效性
    for cap in registry.capabilities:
        if cap.track not in valid_tracks:
            errors.append(
                f"capability {cap.capability_id} 引用了未知的 track: {cap.track}"
            )

    return errors
