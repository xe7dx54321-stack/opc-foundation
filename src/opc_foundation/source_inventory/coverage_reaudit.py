"""M3C-6A 源覆盖率再审计（Coverage Reaudit）模块。

功能说明（小白解读）：
    对信息源（source）做一次全面的"二次体检"，评估每个源当前的覆盖层级、
    可用状态、优先级、以及下一步建议动作。输出统计数据和优先级排序，
    帮助决策接下来该优先推进哪些源。

    核心概念：
        - Layer（层级）：每个源按覆盖深度分为不同层级（scheduled / short_term_usable 等）
        - Usable State（可用状态）：描述源当前能否被系统正常使用
        - Priority（优先级）：P0 最高，P3 最低，决定推进顺序
        - Reaudit：在初次审计之后，根据最新情况重新评估

    本模块只做数据模型 + 配置加载 + 校验 + 统计排序，不访问网络、不修改文件。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


# ---------------------------------------------------------------------------
# 常量集合：合法取值
# ---------------------------------------------------------------------------

#: 合法的覆盖层级名称
LAYER_NAMES: set[str] = {
    "scheduled",
    "short_term_usable",
    "mid_term_usable",
    "long_term_usable",
    "on_demand",
    "blocked",
    "dormant",
    "removed",
}

#: 合法的 usable_state 值
USABLE_STATES: set[str] = {
    "usable",
    "partially_usable",
    "needs_work",
    "unusable",
    "blocked",
    "deprecated",
    "unknown",
}

#: 合法的 recommended_next_action 值
NEXT_ACTIONS: set[str] = {
    "schedule_now",
    "schedule_when_allowed",
    "build_connector",
    "fix_parser",
    "fix_url",
    "request_api_key",
    "investigate_access",
    "add_proxy_routing",
    "add_browser_like_access",
    "add_wechat_archive_access",
    "downgrade_to_on_demand",
    "upgrade_to_scheduled",
    "mark_blocked",
    "mark_removed",
    "no_action_needed",
    "defer",
    "revisit_later",
}

#: 合法的 priority 值
PRIORITIES: set[str] = {
    "P0",
    "P1",
    "P2",
    "P3",
}

#: 合法的 estimated_effort 值
EFFORTS: set[str] = {
    "trivial",
    "low",
    "medium",
    "high",
    "very_high",
    "unknown",
}

#: 合法的 expected_value 值
VALUES: set[str] = {
    "high",
    "medium",
    "low",
    "negligible",
    "unknown",
}

# 内部排序权重映射（数值越小优先级越高）
_PRIORITY_WEIGHT: dict[str, int] = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
_VALUE_WEIGHT: dict[str, int] = {"high": 0, "medium": 1, "low": 2, "negligible": 3, "unknown": 4}


# ---------------------------------------------------------------------------
# 数据类
# ---------------------------------------------------------------------------

@dataclass
class CoverageSourceItem:
    """单个源的覆盖率再审计条目。

    Attributes:
        source_id: 源的唯一标识符（如 ``gov_bj_housing``）
        current_layer: 当前所处的覆盖层级，取值见 ``LAYER_NAMES``
        current_status: 当前运行状态描述（自由文本）
        usable_state: 可用性状态，取值见 ``USABLE_STATES``
        recommended_next_action: 建议下一步动作，取值见 ``NEXT_ACTIONS``
        priority: 优先级，取值见 ``PRIORITIES``
        expected_path_to_usable: 从当前状态到可用的预期路径描述
        scheduling_allowed_now: 当前是否允许排入定时采集
        low_frequency_allowed: 是否允许低频采集
        on_demand_allowed: 是否允许按需采集
        needs_proxy: 是否需要代理才能访问
        needs_browser_like: 是否需要浏览器模拟访问
        needs_wechat_archive: 是否需要微信公众号归档访问
        estimated_effort: 预估工作量，取值见 ``EFFORTS``
        expected_value: 预期价值，取值见 ``VALUES``
        failure_or_gap_reason: 失败或差距原因说明（可为空）
        evidence_basis: 判断依据（日志片段 / 截图路径 / 观察记录等）
        notes: 补充备注
    """

    source_id: str
    current_layer: str
    current_status: str
    usable_state: str
    recommended_next_action: str
    priority: str
    expected_path_to_usable: str
    scheduling_allowed_now: bool
    low_frequency_allowed: bool
    on_demand_allowed: bool
    needs_proxy: bool
    needs_browser_like: bool
    needs_wechat_archive: bool
    estimated_effort: str
    expected_value: str
    failure_or_gap_reason: str = ""
    evidence_basis: str = ""
    notes: str = ""


@dataclass
class CoverageReauditConfig:
    """覆盖率再审计的完整配置。

    Attributes:
        version: 配置版本号（如 ``"1.0"``）
        scope: 审计范围，包含 ``target_layers``、``exclude_patterns`` 等键
        coverage_layers: 各层级的定义与策略
        policy: 全局策略（如 ``max_scheduled_count``、``proxy_budget``）
        sources: 所有源的再审计条目列表
    """

    version: str
    scope: dict[str, Any] = field(default_factory=dict)
    coverage_layers: dict[str, Any] = field(default_factory=dict)
    policy: dict[str, Any] = field(default_factory=dict)
    sources: list[CoverageSourceItem] = field(default_factory=list)


@dataclass
class CoverageSummary:
    """覆盖率再审计的统计摘要。

    Attributes:
        total_sources: 源总数
        layer_counts: 每个层级的源数量，键为层级名，值为数量
        scheduled_ready_count: 已就绪可排入 scheduled 的源数量
        short_term_usable_count: 短期可用（short_term_usable）的源数量
        mid_term_usable_count: 中期可用（mid_term_usable）的源数量
    """

    total_sources: int
    layer_counts: dict[str, int] = field(default_factory=dict)
    scheduled_ready_count: int = 0
    short_term_usable_count: int = 0
    mid_term_usable_count: int = 0


# ---------------------------------------------------------------------------
# 函数
# ---------------------------------------------------------------------------

def load_coverage_reaudit_config(path: str) -> CoverageReauditConfig:
    """从 YAML 文件加载覆盖率再审计配置。

    Args:
        path: YAML 配置文件的路径。

    Returns:
        解析后的 ``CoverageReauditConfig`` 实例。

    Raises:
        FileNotFoundError: 文件不存在。
        yaml.YAMLError: YAML 解析失败。
        KeyError: 缺少必要字段。
        TypeError: 字段类型不匹配。
    """
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"配置文件不存在: {path}")

    with open(file_path, "r", encoding="utf-8") as fh:
        raw: dict[str, Any] = yaml.safe_load(fh)  # type: ignore[assignment]

    if not isinstance(raw, dict):
        raise TypeError(f"YAML 顶层必须是 dict，实际类型为 {type(raw).__name__}")

    # 解析 sources 列表
    sources_raw: list[dict[str, Any]] = raw.get("sources", [])
    if not isinstance(sources_raw, list):
        raise TypeError(f"'sources' 字段必须是 list，实际类型为 {type(sources_raw).__name__}")

    sources: list[CoverageSourceItem] = []
    for idx, item_raw in enumerate(sources_raw):
        if not isinstance(item_raw, dict):
            raise TypeError(f"sources[{idx}] 必须是 dict，实际类型为 {type(item_raw).__name__}")

        # 布尔字段默认值处理
        bool_fields = (
            "scheduling_allowed_now",
            "low_frequency_allowed",
            "on_demand_allowed",
            "needs_proxy",
            "needs_browser_like",
            "needs_wechat_archive",
        )
        bool_defaults: dict[str, bool] = {f: False for f in bool_fields}
        for bf in bool_fields:
            if bf in item_raw:
                bool_defaults[bf] = bool(item_raw[bf])

        sources.append(
            CoverageSourceItem(
                source_id=str(item_raw.get("source_id", "")),
                current_layer=str(item_raw.get("current_layer", "")),
                current_status=str(item_raw.get("current_status", "")),
                usable_state=str(item_raw.get("usable_state", "")),
                recommended_next_action=str(item_raw.get("recommended_next_action", "")),
                priority=str(item_raw.get("priority", "")),
                expected_path_to_usable=str(item_raw.get("expected_path_to_usable", "")),
                scheduling_allowed_now=bool_defaults["scheduling_allowed_now"],
                low_frequency_allowed=bool_defaults["low_frequency_allowed"],
                on_demand_allowed=bool_defaults["on_demand_allowed"],
                needs_proxy=bool_defaults["needs_proxy"],
                needs_browser_like=bool_defaults["needs_browser_like"],
                needs_wechat_archive=bool_defaults["needs_wechat_archive"],
                estimated_effort=str(item_raw.get("estimated_effort", "")),
                expected_value=str(item_raw.get("expected_value", "")),
                failure_or_gap_reason=str(item_raw.get("failure_or_gap_reason", "")),
                evidence_basis=str(item_raw.get("evidence_basis", "")),
                notes=str(item_raw.get("notes", "")),
            )
        )

    return CoverageReauditConfig(
        version=str(raw.get("version", "")),
        scope=raw.get("scope", {}) or {},
        coverage_layers=raw.get("coverage_layers", {}) or {},
        policy=raw.get("policy", {}) or {},
        sources=sources,
    )


def validate_coverage_reaudit(config: CoverageReauditConfig) -> list[str]:
    """校验覆盖率再审计配置，返回所有校验错误。

    校验内容包括：
        - version 不能为空
        - 每个 source 的枚举字段是否在合法取值范围内
        - source_id 不能重复
        - source_id 不能为空字符串

    Args:
        config: 待校验的配置对象。

    Returns:
        错误信息列表。如果列表为空，表示校验通过。
    """
    errors: list[str] = []

    if not config.version:
        errors.append("version 不能为空")

    seen_ids: set[str] = set()

    for idx, src in enumerate(config.sources):
        prefix = f"sources[{idx}]"

        # source_id 非空且不重复
        if not src.source_id:
            errors.append(f"{prefix}.source_id 不能为空")
        elif src.source_id in seen_ids:
            errors.append(f"{prefix}.source_id='{src.source_id}' 重复")
        else:
            seen_ids.add(src.source_id)

        # 枚举字段校验
        if src.current_layer not in LAYER_NAMES:
            errors.append(
                f"{prefix}.current_layer='{src.current_layer}' 不在合法范围 {LAYER_NAMES}"
            )
        if src.usable_state not in USABLE_STATES:
            errors.append(
                f"{prefix}.usable_state='{src.usable_state}' 不在合法范围 {USABLE_STATES}"
            )
        if src.recommended_next_action not in NEXT_ACTIONS:
            errors.append(
                f"{prefix}.recommended_next_action='{src.recommended_next_action}'"
                f" 不在合法范围 {NEXT_ACTIONS}"
            )
        if src.priority not in PRIORITIES:
            errors.append(
                f"{prefix}.priority='{src.priority}' 不在合法范围 {PRIORITIES}"
            )
        if src.estimated_effort not in EFFORTS:
            errors.append(
                f"{prefix}.estimated_effort='{src.estimated_effort}' 不在合法范围 {EFFORTS}"
            )
        if src.expected_value not in VALUES:
            errors.append(
                f"{prefix}.expected_value='{src.expected_value}' 不在合法范围 {VALUES}"
            )

    return errors


def summarize_coverage_layers(config: CoverageReauditConfig) -> CoverageSummary:
    """统计覆盖率再审计配置中各层级的源数量。

    Args:
        config: 覆盖率再审计配置对象。

    Returns:
        ``CoverageSummary`` 实例，包含各层级的统计数量。
    """
    layer_counts: dict[str, int] = {name: 0 for name in LAYER_NAMES}
    scheduled_ready_count = 0
    short_term_usable_count = 0
    mid_term_usable_count = 0

    for src in config.sources:
        layer = src.current_layer
        if layer in layer_counts:
            layer_counts[layer] += 1
        else:
            # 未知层级也计数，便于排查
            layer_counts[layer] = layer_counts.get(layer, 0) + 1

        # 统计已就绪可 scheduled 的源
        if (
            src.current_layer == "scheduled"
            or (
                src.scheduling_allowed_now
                and src.usable_state in ("usable", "partially_usable")
            )
        ):
            scheduled_ready_count += 1

        if src.current_layer == "short_term_usable":
            short_term_usable_count += 1

        if src.current_layer == "mid_term_usable":
            mid_term_usable_count += 1

    return CoverageSummary(
        total_sources=len(config.sources),
        layer_counts=layer_counts,
        scheduled_ready_count=scheduled_ready_count,
        short_term_usable_count=short_term_usable_count,
        mid_term_usable_count=mid_term_usable_count,
    )


def rank_next_priority_sources(
    config: CoverageReauditConfig,
    top_n: int = 10,
) -> list[CoverageSourceItem]:
    """按优先级和价值排序，返回非 scheduled 层级中应优先推进的源。

    排序规则：
        1. 主排序：priority（P0 > P1 > P2 > P3）
        2. 次排序：expected_value（high > medium > low > negligible > unknown）
        3. 仅从非 ``scheduled`` 层级的源中选取

    Args:
        config: 覆盖率再审计配置对象。
        top_n: 返回的最大条目数，默认 10。

    Returns:
        排序后的源条目列表，最多 ``top_n`` 条。
    """
    # 过滤掉已处于 scheduled 层级的源
    candidates = [src for src in config.sources if src.current_layer != "scheduled"]

    # 按优先级权重 + 价值权重排序
    sorted_candidates = sorted(
        candidates,
        key=lambda s: (
            _PRIORITY_WEIGHT.get(s.priority, 99),
            _VALUE_WEIGHT.get(s.expected_value, 99),
        ),
    )

    return sorted_candidates[:top_n]
