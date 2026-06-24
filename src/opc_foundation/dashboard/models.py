"""Dashboard 数据模型。

功能说明（小白解读）：
    定义 dashboard 用到的所有数据结构（dataclass）。
    用 dataclasses 实现，不依赖 pydantic，保持轻量。
    所有 dataclass 用 frozen=True，创建后不可修改。

    不包含任何投资判断字段（如 ticker / rating / score）。
"""
from __future__ import annotations

from dataclasses import dataclass, field


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
        stages:        阶段列表
    """

    workflow_id: str
    workflow_name: str
    status: str
    stages: list[CapabilityUsageStage]


@dataclass(frozen=True)
class CapabilityUsageProject:
    """使用项目（project）。

    功能说明：
        一个下游项目，包含若干工作流。

    参数：
        project_id:   项目 ID
        project_name: 项目名称
        status:       项目状态（如 planned / candidate / active）
        workflows:    工作流列表
    """

    project_id: str
    project_name: str
    status: str
    workflows: list[CapabilityUsageWorkflow]


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
        runtime_health:       运行健康状态（healthy/degraded/failed/unknown/not_configured）
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
