"""Dashboard 数据模型。

功能说明（小白解读）：
    定义 dashboard 用到的所有数据结构（dataclass）。
    用 dataclasses 实现，不依赖 pydantic，保持轻量。
    所有 dataclass 用 frozen=True，创建后不可修改。

    不包含任何投资判断字段（如 ticker / rating / score）。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class RuntimeMode(str, Enum):
    """能力运行模式（M3B-3b 新增）。

    功能说明（小白解读）：
        标记一个能力属于哪种运行模式，用于校准 Dashboard 健康状态显示：
        - data_source:    数据能力，需要运行记录（research / official_filing / document_extraction）
        - utility:        工具能力，不需要运行记录（runtime.*）
        - known_limited:  已知限制能力（如 HKEX 因客户端渲染限制）
        - manual_only:    人工触发能力（如 manual_url）

    为什么要这个？
        之前所有能力都用同一种方式判断健康状态，导致：
        - 工具能力被误报成"未配置"
        - 已知限制被误报成"新故障"
        - 数据能力无记录被误报成"未知"
    """

    DATA_SOURCE = "data_source"
    UTILITY = "utility"
    KNOWN_LIMITED = "known_limited"
    MANUAL_ONLY = "manual_only"


# 中文显示标签
RUNTIME_MODE_LABELS = {
    RuntimeMode.DATA_SOURCE: "数据能力",
    RuntimeMode.UTILITY: "工具能力",
    RuntimeMode.KNOWN_LIMITED: "已知限制",
    RuntimeMode.MANUAL_ONLY: "人工触发",
}


@dataclass(frozen=True)
class CapabilityTrack:
    """能力主线（track）。

    功能说明：
        一条主线代表一个 foundation 基础设施方向，比如 research / official_filing。
        用 frozen dataclass，创建后不可修改。

    参数：
        track_id:    主线 ID（如 research）
        name:        主线名称（如 Research Source Foundation）
        status:      主线状态（如 production_trial_ready / mvp_ready）
        description: 主线描述
    """

    track_id: str
    name: str
    status: str
    description: str
    name_en: str = ""


@dataclass(frozen=True)
class Capability:
    """单条能力（capability）。

    功能说明：
        一条能力代表 foundation 提供的一个具体功能，比如 research.rss_feed。
        用 frozen dataclass，创建后不可修改。

    参数：
        capability_id:      能力 ID（如 research.rss_feed）
        name:               能力名称（如 RSS Feed）
        track:              所属主线 ID（如 research）
        category:           分类（如 source / filing / document / runtime）
        maturity_status:    成熟度（如 production_trial_ready / mvp_ready / degraded）
        description:        能力描述
        input_type:         输入类型（如 rss_feed / pdf）
        primary_output:     主输出文件路径（如 data/research_archive/index/documents.latest.jsonl）
        health_file:        健康检查文件路径（source_health.jsonl）
        run_log_file:       运行日志文件路径（run_log.jsonl）
        failed_queue_file:  失败队列文件路径（failed_queue.jsonl）
        docs:               相关文档路径列表
        sources:            已接入的数据源列表（每个源有 name/status/url 等）
        runtime_mode:       运行模式（M3B-3b 新增：data_source/utility/known_limited/manual_only）
    """

    capability_id: str
    name: str
    track: str
    category: str
    maturity_status: str
    description: str
    input_type: str
    primary_output: str
    health_file: str
    run_log_file: str
    failed_queue_file: str
    docs: list[str]
    display_name: str = ""
    what_it_does: list[str] = field(default_factory=list)
    typical_usage: str = ""
    sources: list[dict] = field(default_factory=list)
    runtime_mode: str = "data_source"  # 默认为数据能力，向后兼容

    @property
    def runtime_mode_enum(self) -> RuntimeMode:
        """获取运行模式枚举对象。

        功能说明：
            安全的获取方式，解析失败时返回 data_source 兜底。
            用于内部逻辑判断（不依赖 enum 比较，避免字符串硬编码）。

        返回：
            RuntimeMode 枚举对象
        """
        try:
            return RuntimeMode(self.runtime_mode)
        except ValueError:
            return RuntimeMode.DATA_SOURCE


@dataclass(frozen=True)
class CapabilityRegistry:
    """能力注册表。

    功能说明：
        从 foundation_capabilities.yaml 加载的完整注册表。
        包含所有主线和能力列表。

    参数：
        version:      配置版本
        updated_at:   更新时间
        tracks:       主线列表
        capabilities: 能力列表
    """

    version: str
    updated_at: str
    tracks: list[CapabilityTrack]
    capabilities: list[Capability]

    def get_capability(self, capability_id: str) -> Capability | None:
        """根据能力 ID 获取能力对象。

        功能说明：
            在注册表中查找指定能力。
            找不到返回 None。

        参数：
            capability_id: 能力 ID

        返回：
            Capability 或 None
        """
        for cap in self.capabilities:
            if cap.capability_id == capability_id:
                return cap
        return None


@dataclass(frozen=True)
class CapabilityUsageStage:
    """使用阶段（stage）。

    功能说明：
        一个工作流中的一个阶段，引用若干能力。
        比如 disclosure_monitoring 工作流的 collect_filings 阶段。

    参数：
        stage_id:     阶段 ID
        stage_name:   阶段名称
        agent:        执行 agent 名称
        status:       阶段状态（如 planned / candidate / active）
        purpose:      阶段目的说明
        capabilities: 引用的能力 ID 列表
    """

    stage_id: str
    stage_name: str
    agent: str
    status: str
    purpose: str
    capabilities: list[str]


@dataclass(frozen=True)
class CapabilityUsageWorkflow:
    """使用工作流（workflow）。

    功能说明：
        一个项目中的一个工作流，包含若干阶段。

    参数：
        workflow_id:   工作流 ID
        workflow_name: 工作流名称
        status:        工作流状态
        description:   工作流描述（可选）
        stages:        阶段列表
    """

    workflow_id: str
    workflow_name: str
    status: str
    stages: list[CapabilityUsageStage]
    description: str = ""


@dataclass(frozen=True)
class CapabilityUsageProject:
    """使用项目（project）。

    功能说明：
        一个下游项目，包含若干工作流。

    参数：
        project_id:   项目 ID
        project_name: 项目名称
        status:       项目状态（如 planned / candidate / active）
        description:  项目描述（可选）
        workflows:    工作流列表
    """

    project_id: str
    project_name: str
    status: str
    workflows: list[CapabilityUsageWorkflow]
    description: str = ""


@dataclass(frozen=True)
class CapabilityUsageRegistry:
    """使用注册表。

    功能说明：
        从 capability_usage_registry.yaml 加载的完整使用注册表。
        包含所有项目和它们的工作流。

    参数：
        version:    配置版本
        updated_at: 更新时间
        projects:   项目列表
    """

    version: str
    updated_at: str
    projects: list[CapabilityUsageProject]


@dataclass(frozen=True)
class CapabilityRuntimeSummary:
    """能力运行时摘要。

    功能说明：
        一条能力的运行时健康状态摘要。
        由 health.py 的 build_runtime_summary 函数生成。
        只包含运行状态信息，不包含投资判断字段。

    参数：
        capability_id:        能力 ID
        runtime_health:       运行健康状态（healthy/degraded/failed/unknown_never_run/not_configured/utility/known_limited）
        latest_status:        最近一次原始状态（来自 source_health 或 run_log）
        latest_run_at:        最近运行时间
        last_success_at:      上次成功时间
        last_failure_at:      上次失败时间
        recent_run_count:     最近运行次数
        recent_failure_count: 最近失败次数
        consecutive_failures: 连续失败次数
        failed_queue_count:   失败队列积压数量
        needs_attention:      是否需要人工关注
        stale:                是否过期（长时间没运行）
        latest_error:         最近错误信息
        runtime_mode:         运行模式（M3B-3b 新增：data_source/utility/known_limited/manual_only）
        status_explanation:   状态解释文本（M3B-3b 新增：中文说明当前状态的具体含义）
    """

    capability_id: str
    runtime_health: str
    latest_status: str
    latest_run_at: str
    last_success_at: str
    last_failure_at: str
    recent_run_count: int
    recent_failure_count: int
    consecutive_failures: int
    failed_queue_count: int
    needs_attention: bool
    stale: bool
    latest_error: str
    runtime_mode: str = "data_source"
    status_explanation: str = ""


@dataclass(frozen=True)
class DashboardSummary:
    """Dashboard 汇总统计。

    功能说明：
        整个 dashboard 的汇总数字，用于总览页面快速展示。
        包含成熟度统计、运行健康统计、使用情况统计。

    参数：
        total_capabilities:          能力总数
        production_trial_ready_count:成熟度=production_trial_ready 的数量
        mvp_ready_count:             成熟度=mvp_ready 的数量
        degraded_count:              成熟度=degraded 的数量
        failed_count:                运行健康=failed 的数量
        unknown_count:               运行健康=unknown 的数量
        not_configured_count:        运行健康=not_configured 的数量
        needs_attention_count:       需要关注的能力数量
        stale_count:                 过期的能力数量
        used_count:                  被使用的能力数量
        unused_count:                未被使用的能力数量
    """

    total_capabilities: int
    production_trial_ready_count: int
    mvp_ready_count: int
    degraded_count: int
    failed_count: int
    unknown_count: int
    not_configured_count: int
    needs_attention_count: int
    stale_count: int
    used_count: int
    unused_count: int


# ===========================================================================
# 运行手册相关数据模型（M3B-2 新增）
# ===========================================================================


@dataclass(frozen=True)
class CommonFailure:
    """常见失败类型。

    功能说明：
        记录某个能力常见的失败类型、含义和排查方向。
        用 frozen dataclass，创建后不可修改。

    参数：
        error_type: 错误类型标识（英文，便于搜索）
        meaning:     错误含义（中文）
        check:       排查方向（中文）
    """

    error_type: str
    meaning: str = ""
    check: str = ""


@dataclass(frozen=True)
class CapabilityRunbook:
    """能力运行手册。

    功能说明（小白解读）：
        一个能力的完整运行手册，告诉你：
        - 这个能力叫啥、能干啥
        - 怎么配置、怎么运行
        - 输出在哪、失败了怎么排查

        用 frozen dataclass，创建后不可修改。

    参数：
        capability_id:        能力 ID（必须存在于 foundation_capabilities.yaml）
        title:                中文标题
        summary:              中文摘要
        maturity_label:       成熟度中文标签（如"可试运行"、"MVP 可用"）
        owner_agent:          负责 Agent 名称
        config_templates:     配置模板文件路径列表
        local_config_path:    本地配置文件路径
        primary_output:       主要输出文件路径
        health_file:          健康状态文件路径
        run_log_file:         运行日志文件路径
        failed_queue_file:    失败队列文件路径
        report_dir:           报告目录路径
        commands:             运行命令字典（key 是命令类型，value 是命令字符串）
        can_do:               能做什么（中文列表）
        cannot_do:            不能做什么（中文列表）
        common_failures:      常见失败列表
        troubleshooting_steps:排查步骤（按顺序，中文）
        docs:                 相关文档路径列表
    """

    capability_id: str
    title: str = ""
    summary: str = ""
    maturity_label: str = ""
    owner_agent: str = ""
    config_templates: list[str] = field(default_factory=list)
    local_config_path: str = ""
    primary_output: str = ""
    health_file: str = ""
    run_log_file: str = ""
    failed_queue_file: str = ""
    report_dir: str = ""
    commands: dict[str, str] = field(default_factory=dict)
    can_do: list[str] = field(default_factory=list)
    cannot_do: list[str] = field(default_factory=list)
    common_failures: list[CommonFailure] = field(default_factory=list)
    troubleshooting_steps: list[str] = field(default_factory=list)
    docs: list[str] = field(default_factory=list)

    @property
    def is_tool_only(self) -> bool:
        """判断是否是工具类能力（不需要单独运行）。

        功能说明：
            如果 commands 为空，说明这个能力是工具类，
            被其他模块调用，不需要单独运行。

        返回：
            bool: True 表示是工具类能力
        """
        return len(self.commands) == 0


@dataclass
class RunbookRegistry:
    """运行手册注册表。

    功能说明：
        从 capability_runbooks.yaml 加载的完整运行手册注册表。
        包含所有能力的运行手册。
        注意：这个类不是 frozen，因为加载过程中可能需要修改。

    参数：
        version:      配置版本
        updated_at:   更新时间
        runbooks:     运行手册列表
        load_error:   加载错误信息（如果加载失败）
    """

    version: str = ""
    updated_at: str = ""
    runbooks: list[CapabilityRunbook] = field(default_factory=list)
    load_error: str | None = None

    def get_runbook(self, capability_id: str) -> CapabilityRunbook | None:
        """根据能力 ID 获取运行手册。

        功能说明：
            在注册表中查找指定能力的运行手册。
            找不到返回 None。

        参数：
            capability_id: 能力 ID

        返回：
            CapabilityRunbook 或 None
        """
        for rb in self.runbooks:
            if rb.capability_id == capability_id:
                return rb
        return None


# ===========================================================================
# Runtime Binding 相关数据模型（M3B-3 新增）
# ===========================================================================


@dataclass(frozen=True)
class CapabilityRuntimeBinding:
    """能力运行时绑定配置。

    功能说明（小白解读）：
        告诉 Dashboard 某个 capability_id 应该从哪些真实运行文件中读取数据。
        比如 research.rss_feed 这个能力，它的健康数据存在哪里，
        运行日志存在哪里，失败队列存在哪里。

        用 frozen dataclass，创建后不可修改。

    参数：
        capability_id:       能力 ID（必须存在于 foundation_capabilities.yaml）
        archive_root:        归档根目录（如 data/research_archive）
        source_types:        匹配的 source_type 列表（如 ["rss_feed"]）
        source_ids:          匹配的 source_id 列表（为空表示不限制）
        file_extensions:     文件扩展名（用于文档抽取类能力，如 [".pdf"]）
        health_file:         健康状态文件路径（source_health.jsonl）
        run_log_file:        运行日志文件路径（run_log.jsonl）
        failed_queue_file:   失败队列文件路径（failed_queue.jsonl）
        report_dir:          报告目录路径
    """

    capability_id: str
    archive_root: str = ""
    source_types: list[str] = field(default_factory=list)
    source_ids: list[str] = field(default_factory=list)
    file_extensions: list[str] = field(default_factory=list)
    health_file: str = ""
    run_log_file: str = ""
    failed_queue_file: str = ""
    report_dir: str = ""


@dataclass
class RuntimeBindingRegistry:
    """运行时绑定注册表。

    功能说明：
        从 capability_runtime_bindings.yaml 加载的完整绑定配置。
        包含所有能力的运行时绑定信息。
        注意：这个类不是 frozen，因为加载过程中可能需要修改。

    参数：
        version:      配置版本
        updated_at:   更新时间
        bindings:     绑定配置列表
        load_error:   加载错误信息（如果加载失败）
    """

    version: str = ""
    updated_at: str = ""
    bindings: list[CapabilityRuntimeBinding] = field(default_factory=list)
    load_error: str | None = None

    def get_binding(self, capability_id: str) -> CapabilityRuntimeBinding | None:
        """根据能力 ID 获取运行时绑定配置。

        功能说明：
            在注册表中查找指定能力的绑定配置。
            找不到返回 None。

        参数：
            capability_id: 能力 ID

        返回：
            CapabilityRuntimeBinding 或 None
        """
        for b in self.bindings:
            if b.capability_id == capability_id:
                return b
        return None


@dataclass(frozen=True)
class CapabilityRuntimeEvidence:
    """能力运行时证据（从真实数据文件中匹配到的记录）。

    功能说明（小白解读）：
        从真实的 source_health / run_log / failed_queue 文件中，
        按 binding 规则匹配到的所有记录。
        这些记录是判断健康状态的"证据"。

        用 frozen dataclass，创建后不可修改。

    参数：
        capability_id:            能力 ID
        matched_health_records:   匹配到的健康状态记录列表
        matched_run_records:      匹配到的运行日志记录列表
        matched_failed_records:   匹配到的失败队列记录列表
        latest_health_record:     最新的健康状态记录
        latest_run_record:        最新的运行日志记录
        latest_failed_record:     最新的失败队列记录
        latest_report_path:       最新的报告文件路径
    """

    capability_id: str
    matched_health_records: list[dict] = field(default_factory=list)
    matched_run_records: list[dict] = field(default_factory=list)
    matched_failed_records: list[dict] = field(default_factory=list)
    latest_health_record: dict | None = None
    latest_run_record: dict | None = None
    latest_failed_record: dict | None = None
    latest_report_path: str = ""