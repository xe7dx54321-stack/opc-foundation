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
    CapabilityRuntimeBinding,
    CapabilityRunbook,
    CapabilityTrack,
    CapabilityUsageProject,
    CapabilityUsageRegistry,
    CapabilityUsageStage,
    CapabilityUsageWorkflow,
    CommonFailure,
    RuntimeBindingRegistry,
    RunbookRegistry,
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
                display_name=c.get("display_name", c.get("name", "")),
                what_it_does=list(c.get("what_it_does", []) or []),
                typical_usage=c.get("typical_usage", ""),
                sources=list(c.get("sources", []) or []),
                runtime_mode=c.get("runtime_mode", "data_source"),
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
                    description=wf.get("description", ""),
                    stages=stages,
                )
            )
        projects.append(
            CapabilityUsageProject(
                project_id=proj.get("project_id", ""),
                project_name=proj.get("project_name", ""),
                status=proj.get("status", ""),
                description=proj.get("description", ""),
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


def load_runbooks_config(path: str | Path) -> RunbookRegistry:
    """从 YAML 文件加载运行手册注册表。

    功能说明（小白解读）：
        读取 capability_runbooks.yaml，解析成 RunbookRegistry 对象。
        这个文件就像是每个能力的"使用说明书"合集。
        如果文件不存在，返回空 registry（version 为空，列表为空），不抛异常。

    参数：
        path: YAML 文件路径

    返回：
        RunbookRegistry 对象

    异常处理：
        文件不存在不抛异常，返回空 registry。
        YAML 解析失败抛出 yaml.YAMLError（由调用方处理）。
    """
    p = Path(path)
    if not p.exists():
        return RunbookRegistry(
            version="",
            updated_at="",
            runbooks=[],
            load_error=None,
        )

    try:
        with open(p, encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except yaml.YAMLError:
        return RunbookRegistry(
            version="",
            updated_at="",
            runbooks=[],
            load_error=f"YAML 解析失败: {path}",
        )

    runbooks: list[CapabilityRunbook] = []
    for rb_data in data.get("runbooks", []) or []:
        common_failures: list[CommonFailure] = []
        for cf in rb_data.get("common_failures", []) or []:
            common_failures.append(
                CommonFailure(
                    error_type=cf.get("error_type", ""),
                    meaning=cf.get("meaning", ""),
                    check=cf.get("check", ""),
                )
            )

        runbooks.append(
            CapabilityRunbook(
                capability_id=rb_data.get("capability_id", ""),
                title=rb_data.get("title", ""),
                summary=rb_data.get("summary", ""),
                maturity_label=rb_data.get("maturity_label", ""),
                owner_agent=rb_data.get("owner_agent", ""),
                config_templates=list(rb_data.get("config_templates", []) or []),
                local_config_path=rb_data.get("local_config_path", ""),
                primary_output=rb_data.get("primary_output", ""),
                health_file=rb_data.get("health_file", ""),
                run_log_file=rb_data.get("run_log_file", ""),
                failed_queue_file=rb_data.get("failed_queue_file", ""),
                report_dir=rb_data.get("report_dir", ""),
                commands=dict(rb_data.get("commands", {}) or {}),
                can_do=list(rb_data.get("can_do", []) or []),
                cannot_do=list(rb_data.get("cannot_do", []) or []),
                common_failures=common_failures,
                troubleshooting_steps=list(
                    rb_data.get("troubleshooting_steps", []) or []
                ),
                docs=list(rb_data.get("docs", []) or []),
            )
        )

    return RunbookRegistry(
        version=str(data.get("version", "")),
        updated_at=str(data.get("updated_at", "")),
        runbooks=runbooks,
        load_error=None,
    )


def validate_runbooks(
    runbook_registry: RunbookRegistry,
    capability_registry: CapabilityRegistry,
) -> list[str]:
    """校验运行手册注册表的完整性。

    功能说明（小白解读）：
        检查运行手册配置是否正确，主要验证两个规则：
        1. 每个 runbook 的 capability_id 必须真实存在于 foundation_capabilities.yaml 中
        2. capability_id 不能重复

    参数：
        runbook_registry:    运行手册注册表
        capability_registry: 能力注册表（用于校验 capability_id 是否存在）

    返回：
        错误信息列表。空列表表示校验通过。
    """
    errors: list[str] = []

    valid_cap_ids = {c.capability_id for c in capability_registry.capabilities}

    seen: dict[str, int] = {}
    for rb in runbook_registry.runbooks:
        seen[rb.capability_id] = seen.get(rb.capability_id, 0) + 1

        if rb.capability_id not in valid_cap_ids:
            errors.append(
                f"runbook 引用了未知的 capability_id: {rb.capability_id}"
            )

    for cap_id, count in seen.items():
        if count > 1:
            errors.append(f"runbook capability_id 重复: {cap_id} 出现了 {count} 次")

    return errors


# ===========================================================================
# Runtime Binding 相关加载函数（M3B-3 新增）
# ===========================================================================


def load_runtime_bindings_config(path: str | Path) -> RuntimeBindingRegistry:
    """从 YAML 文件加载运行时绑定注册表。

    功能说明（小白解读）：
        读取 capability_runtime_bindings.yaml，解析成 RuntimeBindingRegistry 对象。
        这个文件告诉 Dashboard 每个能力应该从哪些真实运行文件中读取数据。
        如果文件不存在，返回空 registry，不抛异常（fail-soft）。

    参数：
        path: YAML 文件路径

    返回：
        RuntimeBindingRegistry 对象

    异常处理：
        文件不存在不抛异常，返回空 registry。
        YAML 解析失败返回空 registry，并记录 load_error。
    """
    p = Path(path)
    if not p.exists():
        return RuntimeBindingRegistry(
            version="",
            updated_at="",
            bindings=[],
            load_error=None,
        )

    try:
        with open(p, encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except yaml.YAMLError:
        return RuntimeBindingRegistry(
            version="",
            updated_at="",
            bindings=[],
            load_error=f"YAML 解析失败: {path}",
        )

    bindings: list[CapabilityRuntimeBinding] = []
    for b_data in data.get("bindings", []) or []:
        bindings.append(
            CapabilityRuntimeBinding(
                capability_id=b_data.get("capability_id", ""),
                archive_root=b_data.get("archive_root", ""),
                source_types=list(b_data.get("source_types", []) or []),
                source_ids=list(b_data.get("source_ids", []) or []),
                file_extensions=list(b_data.get("file_extensions", []) or []),
                health_file=b_data.get("health_file", ""),
                run_log_file=b_data.get("run_log_file", ""),
                failed_queue_file=b_data.get("failed_queue_file", ""),
                report_dir=b_data.get("report_dir", ""),
            )
        )

    return RuntimeBindingRegistry(
        version=str(data.get("version", "")),
        updated_at=str(data.get("updated_at", "")),
        bindings=bindings,
        load_error=None,
    )


def validate_runtime_bindings(
    binding_registry: RuntimeBindingRegistry,
    capability_registry: CapabilityRegistry,
) -> list[str]:
    """校验运行时绑定注册表的完整性。

    功能说明（小白解读）：
        检查 runtime binding 配置是否正确，主要验证：
        1. 每个 binding 的 capability_id 必须真实存在于 foundation_capabilities.yaml 中
        2. capability_id 不能重复
        3. health_file / run_log_file / failed_queue_file 路径是否存在
           （注意：不存在是 warning 不是 error，因为 data/ 不提交）

    参数：
        binding_registry:    运行时绑定注册表
        capability_registry: 能力注册表（用于校验 capability_id 是否存在）

    返回：
        警告信息列表。空列表表示校验通过。
        注意：这里返回的是 warnings，不是 errors，因为运行文件不存在很正常。
    """
    warnings: list[str] = []

    valid_cap_ids = {c.capability_id for c in capability_registry.capabilities}

    # 检查重复和未知 capability_id
    seen: dict[str, int] = {}
    for b in binding_registry.bindings:
        seen[b.capability_id] = seen.get(b.capability_id, 0) + 1

        if b.capability_id not in valid_cap_ids:
            warnings.append(
                f"runtime binding 引用了未知的 capability_id: {b.capability_id}"
            )

    for cap_id, count in seen.items():
        if count > 1:
            warnings.append(
                f"runtime binding capability_id 重复: {cap_id} 出现了 {count} 次"
            )

    return warnings


def check_binding_files_exist(
    binding_registry: RuntimeBindingRegistry,
    project_root: Path,
) -> dict[str, list[str]]:
    """检查每个 binding 指向的运行文件是否存在。

    功能说明（小白解读）：
        遍历所有 binding，检查它们的 health_file / run_log_file / failed_queue_file
        在项目根目录下是否存在。
        返回缺失文件的字典，用于配置检查页面展示 warning。

    参数：
        binding_registry: 运行时绑定注册表
        project_root:     项目根目录

    返回：
        {capability_id: [缺失的文件路径列表]}
        如果某 binding 的所有文件都存在，不会出现在结果中。
    """
    root = Path(project_root)
    result: dict[str, list[str]] = {}

    for b in binding_registry.bindings:
        missing: list[str] = []

        files_to_check = [
            b.health_file,
            b.run_log_file,
            b.failed_queue_file,
        ]

        for f in files_to_check:
            if f:  # 只检查非空路径
                full = root / f
                if not full.exists():
                    missing.append(f)

        if missing:
            result[b.capability_id] = missing

    return result
