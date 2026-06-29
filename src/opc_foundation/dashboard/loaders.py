"""配置加载器。

功能说明（小白解读）：
    负责从 YAML 文件和 JSONL 文件加载数据，转换成 dashboard 的数据模型。
    文件不存在时返回空 registry，不抛异常（fail-soft）。

    不包含任何投资判断字段。
"""
from __future__ import annotations

import datetime
import json
import os
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
    FoundationSource,
    RuntimeBindingRegistry,
    RunbookRegistry,
    SourceGroup,
    SourceInventory,
    SourceInventoryCheckItem,
    SourceInventoryValidationResult,
    TrialRuntimeSummary,
    TrialSourceStatus,
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


# ===========================================================================
# Source Inventory 加载和校验（M3C-0B 新增）
# ===========================================================================


# 合法枚举值
VALID_ACTIVATION_PRIORITIES = {"S", "A", "B", "C", "supplement", "blocked"}
VALID_AUTOMATION_MODES = {"scheduled", "on_demand", "manual_only", "dormant", "do_not_ingest"}
VALID_SCHEDULE_PROFILES = {
    "high_daily", "medium_daily", "low_daily", "weekly",
    "on_demand", "manual_only", "dormant", "blocked",
}
VALID_LEGAL_CONFIDENCES = {
    "official", "licensed_media", "public_ir",
    "mainstream_media", "rebroadcast", "unknown", "high_risk",
}
VALID_ACCESS_MODES = {
    "public_web", "rss", "podcast_rss", "company_ir",
    "media_page", "search_provider", "manual", "dormant",
}

# supplement/blocked/on_demand 类型的 capability_id 白名单
SPECIAL_CAPABILITY_IDS = {"supplement", "blocked"}


def load_source_inventory_config(path: str | Path) -> SourceInventory:
    """从 YAML 文件加载信息源清单。

    功能说明（小白解读）：
        读取 foundation_source_inventory.example.yaml 文件，
        把 YAML 数据转换成 SourceInventory 数据模型。
        文件不存在或格式错误时，返回空的 inventory（fail-soft）。

    参数：
        path: YAML 文件路径

    返回：
        SourceInventory 对象
        如果文件不存在或格式错误，返回空 inventory，load_error 字段有错误信息
    """
    inventory = SourceInventory()

    try:
        file_path = Path(path)
        if not file_path.exists():
            inventory.load_error = f"文件不存在: {path}"
            return inventory

        with open(file_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        inventory.version = str(data.get("version", ""))
        inventory.updated_at = str(data.get("updated_at", ""))

        # 加载 groups
        for g_data in data.get("source_groups", []) or []:
            group = SourceGroup(
                group_id=str(g_data.get("group_id", "")),
                group_name=str(g_data.get("group_name", "")),
                description=str(g_data.get("description", "")),
                default_activation_priority=str(g_data.get("default_activation_priority", "A")),
                default_automation_mode=str(g_data.get("default_automation_mode", "scheduled")),
                default_schedule_profile=str(g_data.get("default_schedule_profile", "medium_daily")),
            )
            inventory.groups.append(group)

        # 加载 sources
        for s_data in data.get("sources", []) or []:
            source = FoundationSource(
                source_id=str(s_data.get("source_id", "")),
                source_name=str(s_data.get("source_name", "")),
                source_group=str(s_data.get("source_group", "")),
                source_category=str(s_data.get("source_category", "")),
                capability_id=str(s_data.get("capability_id", "")),
                source_type=str(s_data.get("source_type", "")),
                website=str(s_data.get("website", "")),
                url=str(s_data.get("url", "")),
                institution=str(s_data.get("institution", "")),
                region=str(s_data.get("region", "global")),
                content_type=list(s_data.get("content_type", []) or []),
                access_mode=str(s_data.get("access_mode", "")),
                legal_confidence=str(s_data.get("legal_confidence", "unknown")),
                automation_mode=str(s_data.get("automation_mode", "scheduled")),
                activation_priority=str(s_data.get("activation_priority", "A")),
                schedule_profile=str(s_data.get("schedule_profile", "medium_daily")),
                recommended_frequency=str(s_data.get("recommended_frequency", "")),
                recommended_time_windows=list(s_data.get("recommended_time_windows", []) or []),
                enabled_by_default=bool(s_data.get("enabled_by_default", True)),
                notes=str(s_data.get("notes", "")),
            )
            inventory.sources.append(source)

    except yaml.YAMLError as e:
        inventory.load_error = f"YAML 格式错误: {e}"
    except Exception as e:
        inventory.load_error = f"加载失败: {e}"

    return inventory


def validate_source_inventory(
    inventory: SourceInventory,
    capabilities: CapabilityRegistry | None = None,
) -> SourceInventoryValidationResult:
    """校验信息源清单配置。

    功能说明（小白解读）：
        检查 source inventory 的配置是否正确，比如：
        - source_id 是否重复
        - source_group 是否存在
        - capability_id 是否有效
        - 枚举字段是否合法
        - 高风险源是否默认禁用
        - 搜索源是否配置成了 scheduled
        等等。
        返回校验结果，包含错误、警告、说明三种级别的检查项。

    参数：
        inventory:    信息源清单
        capabilities: 能力注册表（可选，用于校验 capability_id）

    返回：
        SourceInventoryValidationResult 校验结果
    """
    checks: list[SourceInventoryCheckItem] = []

    # 如果加载失败，直接返回错误
    if inventory.load_error:
        checks.append(SourceInventoryCheckItem(
            level="error",
            check_name="信息源清单文件加载",
            result="失败",
            detail=inventory.load_error,
        ))
        return SourceInventoryValidationResult(
            checks=checks,
            error_count=1,
        )

    group_ids = {g.group_id for g in inventory.groups}
    source_ids_seen: set[str] = set()
    capability_ids = {c.capability_id for c in capabilities.capabilities} if capabilities else set()

    # ============================================
    # 1. source_id 重复检查
    # ============================================
    duplicate_ids: list[str] = []
    for s in inventory.sources:
        if s.source_id in source_ids_seen:
            duplicate_ids.append(s.source_id)
        else:
            source_ids_seen.add(s.source_id)

    if duplicate_ids:
        checks.append(SourceInventoryCheckItem(
            level="error",
            check_name="source_id 唯一性",
            result="不通过",
            detail=f"发现 {len(duplicate_ids)} 个重复的 source_id: {', '.join(sorted(duplicate_ids)[:5])}",
        ))
    else:
        checks.append(SourceInventoryCheckItem(
            level="info",
            check_name="source_id 唯一性",
            result="通过",
            detail=f"共 {len(inventory.sources)} 个 source，全部唯一",
        ))

    # ============================================
    # 2. source_group 引用检查
    # ============================================
    invalid_groups: list[tuple[str, str]] = []
    for s in inventory.sources:
        if s.source_group not in group_ids:
            invalid_groups.append((s.source_id, s.source_group))

    if invalid_groups:
        checks.append(SourceInventoryCheckItem(
            level="error",
            check_name="source_group 引用有效性",
            result="不通过",
            detail=f"发现 {len(invalid_groups)} 个 source 的 source_group 不存在，例如: {invalid_groups[0][0]} -> {invalid_groups[0][1]}",
        ))
    else:
        checks.append(SourceInventoryCheckItem(
            level="info",
            check_name="source_group 引用有效性",
            result="通过",
            detail="所有 source 的 source_group 都存在",
        ))

    # ============================================
    # 3. capability_id 检查（如果提供了 capabilities）
    # ============================================
    if capabilities:
        invalid_caps: list[tuple[str, str]] = []
        for s in inventory.sources:
            # supplement/blocked/on_demand/dormant 的源可以用特殊 capability_id
            if (
                s.activation_priority in {"supplement", "blocked"}
                or s.automation_mode in {"on_demand", "do_not_ingest", "dormant"}
            ):
                continue
            if s.capability_id in SPECIAL_CAPABILITY_IDS:
                continue
            if s.capability_id and s.capability_id not in capability_ids:
                invalid_caps.append((s.source_id, s.capability_id))

        if invalid_caps:
            checks.append(SourceInventoryCheckItem(
                level="error",
                check_name="capability_id 引用有效性",
                result="不通过",
                detail=f"发现 {len(invalid_caps)} 个 source 的 capability_id 不存在，例如: {invalid_caps[0][0]} -> {invalid_caps[0][1]}",
            ))
        else:
            checks.append(SourceInventoryCheckItem(
                level="info",
                check_name="capability_id 引用有效性",
                result="通过",
                detail="所有 scheduled/blocked 源的 capability_id 都有效",
            ))

    # ============================================
    # 4. 枚举字段合法性检查
    # ============================================
    enum_errors = _check_enum_fields(inventory)
    checks.extend(enum_errors)

    # ============================================
    # 5. URL 为空检查（warning）
    # ============================================
    empty_url_sources = [s for s in inventory.sources if not s.url]
    if empty_url_sources:
        checks.append(SourceInventoryCheckItem(
            level="warning",
            check_name="URL 配置完整性",
            result="需注意",
            detail=f"发现 {len(empty_url_sources)} 个 source 的 URL 为空，例如: {empty_url_sources[0].source_id}",
        ))
    else:
        checks.append(SourceInventoryCheckItem(
            level="info",
            check_name="URL 配置完整性",
            result="通过",
            detail="所有 source 都配置了 URL",
        ))

    # ============================================
    # 6. legal_confidence=unknown 检查（warning）
    # ============================================
    unknown_confidence = [s for s in inventory.sources if s.legal_confidence == "unknown"]
    if unknown_confidence:
        checks.append(SourceInventoryCheckItem(
            level="warning",
            check_name="法律可信度评估",
            result="需注意",
            detail=f"发现 {len(unknown_confidence)} 个 source 的 legal_confidence 为 unknown，建议明确评估",
        ))
    else:
        checks.append(SourceInventoryCheckItem(
            level="info",
            check_name="法律可信度评估",
            result="通过",
            detail="所有 source 都有明确的法律可信度评估",
        ))

    # ============================================
    # 7. high_risk / blocked 源 enabled_by_default=true 检查（error）
    # ============================================
    enabled_high_risk = [
        s for s in inventory.sources
        if (s.legal_confidence == "high_risk" or s.activation_priority == "blocked")
        and s.enabled_by_default
    ]
    if enabled_high_risk:
        checks.append(SourceInventoryCheckItem(
            level="error",
            check_name="高风险源默认禁用",
            result="不通过",
            detail=f"发现 {len(enabled_high_risk)} 个 high_risk/blocked 源 enabled_by_default=true，例如: {enabled_high_risk[0].source_id}",
        ))
    else:
        checks.append(SourceInventoryCheckItem(
            level="info",
            check_name="高风险源默认禁用",
            result="通过",
            detail="所有 high_risk/blocked 源都默认禁用",
        ))

    # ============================================
    # 8. search provider automation_mode=scheduled 检查（error）
    # ============================================
    scheduled_search = [
        s for s in inventory.sources
        if s.source_group == "search_providers" and s.automation_mode == "scheduled"
    ]
    if scheduled_search:
        checks.append(SourceInventoryCheckItem(
            level="error",
            check_name="搜索源调度模式",
            result="不通过",
            detail=f"发现 {len(scheduled_search)} 个搜索源配置为 scheduled，应为 on_demand，例如: {scheduled_search[0].source_id}",
        ))
    else:
        checks.append(SourceInventoryCheckItem(
            level="info",
            check_name="搜索源调度模式",
            result="通过",
            detail="所有搜索源都配置为 on_demand，不进入默认高频调度",
        ))

    # ============================================
    # 9. community/dev 源 high_daily 检查（warning）
    # ============================================
    high_daily_community = [
        s for s in inventory.sources
        if s.source_group == "community_dev_signals" and s.schedule_profile == "high_daily"
    ]
    if high_daily_community:
        checks.append(SourceInventoryCheckItem(
            level="warning",
            check_name="社区源调度频率",
            result="需注意",
            detail=f"发现 {len(high_daily_community)} 个社区源配置为 high_daily，建议降低频率，例如: {high_daily_community[0].source_id}",
        ))
    else:
        checks.append(SourceInventoryCheckItem(
            level="info",
            check_name="社区源调度频率",
            result="通过",
            detail="所有社区源都未配置为 high_daily",
        ))

    # ============================================
    # 10. blocked 源必须是 do_not_ingest 或 dormant 检查（error）
    # ============================================
    blocked_wrong_mode = [
        s for s in inventory.sources
        if s.activation_priority == "blocked" and s.automation_mode not in {"do_not_ingest", "dormant"}
    ]
    if blocked_wrong_mode:
        checks.append(SourceInventoryCheckItem(
            level="error",
            check_name="禁止源自动化模式",
            result="不通过",
            detail=f"发现 {len(blocked_wrong_mode)} 个 blocked 源的 automation_mode 不是 do_not_ingest/dormant，例如: {blocked_wrong_mode[0].source_id}",
        ))
    else:
        checks.append(SourceInventoryCheckItem(
            level="info",
            check_name="禁止源自动化模式",
            result="通过",
            detail="所有 blocked 源都配置为 do_not_ingest 或 dormant",
        ))

    # ============================================
    # 汇总统计
    # ============================================
    result = summarize_source_inventory(inventory)
    # 把 checks 合并到 result 中
    # 因为 SourceInventoryValidationResult 是 frozen，我们需要重新构建
    error_count = sum(1 for c in checks if c.level == "error")
    warning_count = sum(1 for c in checks if c.level == "warning")
    info_count = sum(1 for c in checks if c.level == "info")

    return SourceInventoryValidationResult(
        checks=checks,
        error_count=error_count,
        warning_count=warning_count,
        info_count=info_count,
        group_count=result.group_count,
        source_count=result.source_count,
        priority_counts=result.priority_counts,
        automation_counts=result.automation_counts,
        enabled_count=result.enabled_count,
        high_risk_count=result.high_risk_count,
        search_provider_count=result.search_provider_count,
        community_count=result.community_count,
    )


def _check_enum_fields(inventory: SourceInventory) -> list[SourceInventoryCheckItem]:
    """检查枚举字段合法性。

    功能说明：
        辅助函数，检查所有枚举字段是否在合法范围内。
        返回 error 级别的检查项列表。

    参数：
        inventory: 信息源清单

    返回：
        检查项列表
    """
    checks: list[SourceInventoryCheckItem] = []

    # activation_priority
    invalid_priority = [
        s.source_id for s in inventory.sources
        if s.activation_priority not in VALID_ACTIVATION_PRIORITIES
    ]
    if invalid_priority:
        checks.append(SourceInventoryCheckItem(
            level="error",
            check_name="activation_priority 枚举合法性",
            result="不通过",
            detail=f"发现 {len(invalid_priority)} 个非法值，例如: {invalid_priority[0]}",
        ))
    else:
        checks.append(SourceInventoryCheckItem(
            level="info",
            check_name="activation_priority 枚举合法性",
            result="通过",
            detail=f"所有 source 的 activation_priority 都合法（共 {len(inventory.sources)} 个）",
        ))

    # automation_mode
    invalid_automation = [
        s.source_id for s in inventory.sources
        if s.automation_mode not in VALID_AUTOMATION_MODES
    ]
    if invalid_automation:
        checks.append(SourceInventoryCheckItem(
            level="error",
            check_name="automation_mode 枚举合法性",
            result="不通过",
            detail=f"发现 {len(invalid_automation)} 个非法值，例如: {invalid_automation[0]}",
        ))
    else:
        checks.append(SourceInventoryCheckItem(
            level="info",
            check_name="automation_mode 枚举合法性",
            result="通过",
            detail="所有 source 的 automation_mode 都合法",
        ))

    # schedule_profile
    invalid_schedule = [
        s.source_id for s in inventory.sources
        if s.schedule_profile not in VALID_SCHEDULE_PROFILES
    ]
    if invalid_schedule:
        checks.append(SourceInventoryCheckItem(
            level="error",
            check_name="schedule_profile 枚举合法性",
            result="不通过",
            detail=f"发现 {len(invalid_schedule)} 个非法值，例如: {invalid_schedule[0]}",
        ))
    else:
        checks.append(SourceInventoryCheckItem(
            level="info",
            check_name="schedule_profile 枚举合法性",
            result="通过",
            detail="所有 source 的 schedule_profile 都合法",
        ))

    # legal_confidence
    invalid_confidence = [
        s.source_id for s in inventory.sources
        if s.legal_confidence not in VALID_LEGAL_CONFIDENCES
    ]
    if invalid_confidence:
        checks.append(SourceInventoryCheckItem(
            level="error",
            check_name="legal_confidence 枚举合法性",
            result="不通过",
            detail=f"发现 {len(invalid_confidence)} 个非法值，例如: {invalid_confidence[0]}",
        ))
    else:
        checks.append(SourceInventoryCheckItem(
            level="info",
            check_name="legal_confidence 枚举合法性",
            result="通过",
            detail="所有 source 的 legal_confidence 都合法",
        ))

    return checks


def summarize_source_inventory(inventory: SourceInventory) -> SourceInventoryValidationResult:
    """统计信息源清单摘要。

    功能说明（小白解读）：
        统计 source inventory 的各种指标，比如：
        - group 数量、source 数量
        - 优先级分布（S/A/B/C/supplement/blocked 各多少个）
        - 自动化模式分布（scheduled/on_demand/dormant 各多少个）
        - 默认启用的源数量
        - 高风险源数量
        - 搜索源数量
        - 社区源数量
        用于 Dashboard 配置检查页面展示摘要。

    参数：
        inventory: 信息源清单

    返回：
        SourceInventoryValidationResult 对象（只有统计字段，没有 checks）
    """
    priority_counts: dict[str, int] = {}
    automation_counts: dict[str, int] = {}
    enabled_count = 0
    high_risk_count = 0
    search_provider_count = 0
    community_count = 0

    for s in inventory.sources:
        # 优先级统计
        p = s.activation_priority
        priority_counts[p] = priority_counts.get(p, 0) + 1

        # 自动化模式统计
        m = s.automation_mode
        automation_counts[m] = automation_counts.get(m, 0) + 1

        # 默认启用
        if s.enabled_by_default:
            enabled_count += 1

        # 高风险
        if s.legal_confidence == "high_risk" or s.activation_priority == "blocked":
            high_risk_count += 1

        # 搜索源
        if s.source_group == "search_providers":
            search_provider_count += 1

        # 社区源
        if s.source_group == "community_dev_signals":
            community_count += 1

    return SourceInventoryValidationResult(
        group_count=len(inventory.groups),
        source_count=len(inventory.sources),
        priority_counts=priority_counts,
        automation_counts=automation_counts,
        enabled_count=enabled_count,
        high_risk_count=high_risk_count,
        search_provider_count=search_provider_count,
        community_count=community_count,
    )


# ===========================================================================
# Trial Runtime Loader（M3C-4 新增）
# ===========================================================================


# Trial 数据目录常量，fail-soft 用
TRIAL_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "foundation_trial", "index")

# 已知的 transient watch 源（如 cls_cn HTTP 418）
TRANSIENT_WATCH_SOURCES = {"cls_cn"}


def _parse_iso_timestamp(ts: str) -> datetime.datetime:
    """解析 ISO 时间戳字符串。

    功能说明（小白解读）：
        把像 "2026-06-26T10:33:11" 这样的字符串转成 Python 能理解的 datetime 对象，
        这样我们就能比较哪个时间更晚。

    参数：
        ts: ISO 格式的时间字符串

    返回：
        datetime.datetime: 解析后的时间对象，解析失败返回 epoch time
    """
    try:
        # 兼容带时区和不带时区的情况
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        if "+" in ts or ts.count("-") > 2:
            return datetime.datetime.fromisoformat(ts)
        return datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S")
    except (ValueError, TypeError):
        return datetime.datetime.min


def load_trial_runtime_data(
    data_dir: str = TRIAL_DATA_DIR,
) -> tuple[list[dict], list[dict], list[dict]]:
    """加载 trial 运行时数据。

    功能说明（小白解读）：
        读取 data/foundation_trial/index/ 目录下的三个 JSONL 文件：
        - source_health.jsonl：每个源的健康状态
        - run_log.jsonl：运行日志
        - failed_queue.jsonl：失败队列

        如果文件不存在，就返回三个空列表（fail-soft），不会崩溃。

    参数：
        data_dir: trial 数据目录，默认从项目根目录找

    返回：
        tuple[list[dict], list[dict], list[dict]]: (source_health_rows, run_log_rows, failed_queue_rows)
    """
    source_health_path = os.path.join(data_dir, "source_health.jsonl")
    run_log_path = os.path.join(data_dir, "run_log.jsonl")
    failed_queue_path = os.path.join(data_dir, "failed_queue.jsonl")

    def _read_jsonl(path: str) -> list[dict]:
        """读取 JSONL 文件，每行一个 JSON 对象。"""
        if not os.path.exists(path):
            return []
        rows = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            rows.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        except OSError:
            return []
        return rows

    return (
        _read_jsonl(source_health_path),
        _read_jsonl(run_log_path),
        _read_jsonl(failed_queue_path),
    )


def build_trial_runtime_summary(
    data_dir: str = TRIAL_DATA_DIR,
) -> TrialRuntimeSummary:
    """构建 trial 运行时摘要。

    功能说明（小白解读）：
        把 source_health.jsonl 里的数据汇总成一份摘要，
        告诉用户：今天 trial 跑没跑、成功几个、失败几个、有没有 transient watch。

        健康状态规则：
        - healthy：成功率 >= 90%，且无 P0 错误
        - degraded：存在 transient watch 或成功率 70%-90%
        - failed：最近一次 run 未执行、严重错误、或 success < 70%
        - unknown：data 文件不存在

    参数：
        data_dir: trial 数据目录

    返回：
        TrialRuntimeSummary: trial 运行时摘要对象
    """
    source_health_rows, run_log_rows, failed_queue_rows = load_trial_runtime_data(data_dir)

    # data 文件不存在时的 fail-soft 返回
    if not source_health_rows:
        return TrialRuntimeSummary(
            data_exists=False,
            overall_health="unknown",
        )

    # 按 source_id 分组，取每个源最新的一条记录
    latest_by_source: dict[str, dict] = {}
    for row in source_health_rows:
        sid = row.get("source_id", "")
        if not sid:
            continue
        current = latest_by_source.get(sid)
        if current is None:
            latest_by_source[sid] = row
        else:
            current_ts = _parse_iso_timestamp(current.get("run_at", ""))
            row_ts = _parse_iso_timestamp(row.get("run_at", ""))
            if row_ts > current_ts:
                latest_by_source[sid] = row

    source_statuses: list[TrialSourceStatus] = []
    success_count = 0
    failed_count = 0
    transient_count = 0
    skipped_count = 0
    empty_count = 0
    latest_run_at = ""
    transient_sources: list[str] = []

    for sid, row in latest_by_source.items():
        status = row.get("status", "")
        error = row.get("error", "")

        # 判断是否为 transient watch（如 cls_cn HTTP 418）
        is_transient = sid in TRANSIENT_WATCH_SOURCES and status in ("http_error", "failed")

        if status == "success":
            success_count += 1
            if row.get("candidate_count", 0) == 0:
                empty_count += 1
        elif status in ("http_error", "url_error"):
            if is_transient:
                transient_count += 1
                transient_sources.append(sid)
            else:
                failed_count += 1
        elif status == "dry_run":
            skipped_count += 1
        elif status in ("failed", "timeout"):
            failed_count += 1

        # 更新最新 run 时间
        run_at = row.get("run_at", "")
        if run_at and (not latest_run_at or _parse_iso_timestamp(run_at) > _parse_iso_timestamp(latest_run_at)):
            latest_run_at = run_at

        source_statuses.append(TrialSourceStatus(
            source_id=sid,
            source_name=row.get("source_name", sid),
            status=status,
            run_at=run_at,
            candidate_count=row.get("candidate_count", 0),
            error=error,
        ))

    # 按 source_id 排序，让展示更稳定
    source_statuses.sort(key=lambda s: s.source_id)

    # 计算整体健康状态
    total = len(source_statuses)
    success_rate = success_count / total if total > 0 else 0.0

    if total == 0:
        overall_health = "unknown"
    elif failed_count > 0 and success_rate < 0.7:
        overall_health = "failed"
    elif transient_count > 0 or (success_rate >= 0.7 and success_rate < 0.9):
        overall_health = "degraded"
    elif success_rate >= 0.9:
        overall_health = "healthy"
    else:
        overall_health = "failed"

    return TrialRuntimeSummary(
        total_sources=total,
        success_count=success_count,
        failed_count=failed_count,
        transient_count=transient_count,
        skipped_count=skipped_count,
        empty_count=empty_count,
        latest_run_at=latest_run_at,
        overall_health=overall_health,
        source_statuses=source_statuses,
        data_exists=True,
        transient_sources=transient_sources,
        has_blocked_included=False,
    )
