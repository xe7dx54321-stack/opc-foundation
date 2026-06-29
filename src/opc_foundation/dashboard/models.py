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


# ===========================================================================
# Source Inventory 相关数据模型（M3C-0B 新增）
# ===========================================================================


@dataclass(frozen=True)
class SourceGroup:
    """信息源分组（source group）。

    功能说明（小白解读）：
        把信息源按类别分组，比如"投行官方公开研究"、"媒体研报二次引用"等。
        每个组有默认的优先级、自动化模式、调度档位。
        用 frozen dataclass，创建后不可修改。

    参数：
        group_id:                     分组 ID（如 official_public_research）
        group_name:                   分组名称（如 投行官方公开研究）
        description:                  分组描述
        default_activation_priority:  默认激活优先级（S/A/B/C/supplement/blocked）
        default_automation_mode:      默认自动化模式（scheduled/on_demand/...）
        default_schedule_profile:     默认调度档位（high_daily/medium_daily/...）
    """

    group_id: str
    group_name: str
    description: str = ""
    default_activation_priority: str = "A"
    default_automation_mode: str = "scheduled"
    default_schedule_profile: str = "medium_daily"


@dataclass(frozen=True)
class FoundationSource:
    """单个信息源（source）。

    功能说明（小白解读）：
        一个具体的信息源，比如"Goldman Sachs Research"网站。
        包含这个源的所有属性：ID、名称、分类、网站、接入方式、优先级等。
        用 frozen dataclass，创建后不可修改。

    参数：
        source_id:                源 ID（如 goldman_sachs_research）
        source_name:              源名称（如 Goldman Sachs Research）
        source_group:             所属分组 ID
        source_category:          源分类（如 投行官方公开研究）
        capability_id:            对应能力 ID（如 research.official_public_research）
        source_type:              源类型（如 official_public_research）
        website:                  网站名称
        url:                      网站 URL
        institution:              机构名称（如 Goldman Sachs）
        region:                   区域（global/china/...）
        content_type:             内容类型列表
        access_mode:              接入方式（public_web/rss/...）
        legal_confidence:         法律可信度（official/mainstream_media/...）
        automation_mode:          自动化模式（scheduled/on_demand/...）
        activation_priority:      激活优先级（S/A/B/C/supplement/blocked）
        schedule_profile:         调度档位（high_daily/medium_daily/...）
        recommended_frequency:    推荐采集频率
        recommended_time_windows: 推荐采集时间窗口
        enabled_by_default:       默认是否启用
        notes:                    备注
    """

    source_id: str
    source_name: str
    source_group: str
    source_category: str = ""
    capability_id: str = ""
    source_type: str = ""
    website: str = ""
    url: str = ""
    institution: str = ""
    region: str = "global"
    content_type: list[str] = field(default_factory=list)
    access_mode: str = ""
    legal_confidence: str = "unknown"
    automation_mode: str = "scheduled"
    activation_priority: str = "A"
    schedule_profile: str = "medium_daily"
    recommended_frequency: str = ""
    recommended_time_windows: list[str] = field(default_factory=list)
    enabled_by_default: bool = True
    notes: str = ""


@dataclass
class SourceInventory:
    """信息源清单（source inventory）。

    功能说明：
        从 foundation_source_inventory.example.yaml 加载的完整清单。
        包含所有 source groups 和 sources。
        注意：这个类不是 frozen，因为加载过程中可能需要修改。

    参数：
        version:      配置版本
        updated_at:   更新时间
        groups:       分组列表
        sources:      信息源列表
        load_error:   加载错误信息（如果加载失败）
    """

    version: str = ""
    updated_at: str = ""
    groups: list[SourceGroup] = field(default_factory=list)
    sources: list[FoundationSource] = field(default_factory=list)
    load_error: str | None = None

    def get_source(self, source_id: str) -> FoundationSource | None:
        """根据源 ID 获取信息源对象。

        功能说明：
            在清单中查找指定信息源。
            找不到返回 None。

        参数：
            source_id: 信息源 ID

        返回：
            FoundationSource 或 None
        """
        for s in self.sources:
            if s.source_id == source_id:
                return s
        return None

    def get_group(self, group_id: str) -> SourceGroup | None:
        """根据分组 ID 获取分组对象。

        功能说明：
            在清单中查找指定分组。
            找不到返回 None。

        参数：
            group_id: 分组 ID

        返回：
            SourceGroup 或 None
        """
        for g in self.groups:
            if g.group_id == group_id:
                return g
        return None


@dataclass(frozen=True)
class SourceInventoryCheckItem:
    """信息源清单检查项。

    功能说明（小白解读）：
        一条检查结果，比如"source_id 重复"、"URL 为空"等。
        包含级别（错误/警告/说明）、检查项名称、结果、说明。
        用 frozen dataclass，创建后不可修改。

    参数：
        level:       级别（error/warning/info）
        check_name:  检查项名称（中文）
        result:      检查结果（中文，如 通过/不通过/需注意）
        detail:      详细说明
        source_id:   关联的 source_id（如果有）
    """

    level: str
    check_name: str
    result: str
    detail: str = ""
    source_id: str = ""


@dataclass(frozen=True)
class SourceInventoryValidationResult:
    """信息源清单校验结果。

    功能说明（小白解读）：
        对 source inventory 进行校验后的完整结果。
        包含所有检查项、错误数、警告数、说明数。
        还包含统计摘要（group 数量、source 数量、优先级分布等）。
        用 frozen dataclass，创建后不可修改。

    参数：
        checks:               所有检查项列表
        error_count:          错误数量
        warning_count:        警告数量
        info_count:           说明数量
        group_count:          source group 数量
        source_count:         source 数量
        priority_counts:      优先级分布字典（S/A/B/C/supplement/blocked）
        automation_counts:    自动化模式分布字典
        enabled_count:        默认启用的源数量
        high_risk_count:      高风险禁止源数量
        search_provider_count: Search Provider 数量
        community_count:      Community/Dev 源数量
    """

    checks: list[SourceInventoryCheckItem] = field(default_factory=list)
    error_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    group_count: int = 0
    source_count: int = 0
    priority_counts: dict[str, int] = field(default_factory=dict)
    automation_counts: dict[str, int] = field(default_factory=dict)
    enabled_count: int = 0
    high_risk_count: int = 0
    search_provider_count: int = 0
    community_count: int = 0

    @property
    def is_valid(self) -> bool:
        """校验是否通过（没有错误）。

        功能说明：
            如果 error_count 为 0，说明没有必须修复的问题，返回 True。
            有警告和说明不影响通过。

        返回：
            bool: True 表示没有错误
        """
        return self.error_count == 0


# ===========================================================================
# Trial Runtime 相关数据模型（M3C-4 新增）
# ===========================================================================


@dataclass(frozen=True)
class TrialSourceStatus:
    """单个 trial source 的运行状态。

    功能说明（小白解读）：
        记录一个 trial source 最近一次运行的结果，比如：
        - 这个源叫啥（source_id, source_name）
        - 最近一次啥状态（success / http_error / url_error / dry_run）
        - 啥时候跑的（run_at）
        - 抓到了几条（candidate_count）
        - 出啥错了（error）

    参数：
        source_id:       源 ID
        source_name:     源名称
        status:          运行状态（success / http_error / url_error / dry_run / started）
        run_at:          运行时间（ISO 字符串）
        candidate_count: 抓到的候选数量
        error:           错误信息
    """

    source_id: str
    source_name: str
    status: str
    run_at: str
    candidate_count: int = 0
    error: str = ""


@dataclass(frozen=True)
class TrialRuntimeSummary:
    """Trial 运行时摘要。

    功能说明（小白解读）：
        把 15 个 trial source 的运行结果汇总成一份摘要，
        告诉用户今天 trial 跑没跑、跑了多少、成功多少、失败多少。

        健康状态规则：
        - healthy：成功率 >= 90%，且无 P0 错误
        - degraded：存在 transient watch 或成功率 70%-90%
        - failed：最近一次 run 未执行、严重错误、或 success < 70%
        - unknown：尚未生成 trial data（data 文件不存在）

    参数：
        total_sources:        trial source 总数（应该是 15）
        success_count:        最近一次 run 成功的数量
        failed_count:         最近一次 run 失败的数量
        transient_count:      transient watch 的数量（如 cls_cn HTTP 418）
        skipped_count:        dry_run 跳过的数量
        empty_count:          成功但 candidate_count=0 的数量
        latest_run_at:        最近一次 run 时间
        latest_check_at:      最近一次 check 时间
        latest_daily_status_at: 最近一次 daily status 时间
        overall_health:       整体健康状态（healthy/degraded/failed/unknown）
        source_statuses:      每个 source 的详细状态列表
        data_exists:          data 文件是否存在
        transient_sources:    被标记为 transient watch 的源 ID 列表
        has_blocked_included: 是否有 blocked 源被误纳入
    """

    total_sources: int = 0
    success_count: int = 0
    failed_count: int = 0
    transient_count: int = 0
    skipped_count: int = 0
    empty_count: int = 0
    latest_run_at: str = ""
    latest_check_at: str = ""
    latest_daily_status_at: str = ""
    overall_health: str = "unknown"
    source_statuses: list[TrialSourceStatus] = field(default_factory=list)
    data_exists: bool = False
    transient_sources: list[str] = field(default_factory=list)
    has_blocked_included: bool = False