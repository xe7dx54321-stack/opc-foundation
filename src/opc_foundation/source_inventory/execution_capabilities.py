"""Source Execution Capability 模型 (M3C-6B)。

功能说明（小白解读）：
    定义每个候选源的执行能力画像。M3C-6B 不只判断 "Python 静态 HTTP 能不能抓"，
    而是把每个源映射到不同的执行路径，包括：

        A. python_static_http          —— Python urllib/httpx 静态抓取
        B. rss_or_sitemap              —— RSS / Atom / sitemap 入口
        C. public_json_ld_or_metadata  —— JSON-LD / OpenGraph / metadata 提取
        D. trae_browser_public         —— TRAE 内置浏览器公开观察
        E. trae_skill_agent_reach      —— agent-reach 类 TRAE skill
        F. trae_scheduled_automation   —— TRAE 调度自动化任务
        G. on_demand_search            —— 按需搜索 / 触发式
        H. blocked_or_not_worth_it     —— 受阻或不值得

    核心约束：
        - trial_v2_allowlist_allowed_now 与 trae_automation_allowed_now 必须分开
        - TRAE browser / skill 路径只能作为执行能力评估，不得直接进入 trial_v2 allowlist
        - 任何源若 login_required / paywall_observed / captcha_or_antibot_observed=true，
          都不得标记为 scheduled_preflight_pass_static / scheduled_preflight_pass_feed

本模块只做数据模型 + 校验 + 推荐模式计算，不访问网络、不修改文件。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# 常量集合：合法取值
# ---------------------------------------------------------------------------

class ExecutionMode(str, Enum):
    """Source execution mode 枚举。

    每个 source 必须落到以下执行模式之一：
        - python_static_http:           Python urllib/httpx 静态抓取
        - rss_or_sitemap:                RSS / Atom / sitemap 入口
        - public_json_ld_or_metadata:    JSON-LD / OpenGraph / metadata
        - trae_browser_public:           TRAE 内置浏览器公开观察
        - trae_skill_agent_reach:        agent-reach 类 TRAE skill
        - trae_scheduled_automation:     TRAE 调度自动化任务
        - on_demand_search:              按需搜索 / 触发式
        - manual_review_only:            只能人工复核
        - blocked_or_not_worth_it:       受阻或不值得
    """

    PYTHON_STATIC_HTTP = "python_static_http"
    RSS_OR_SITEMAP = "rss_or_sitemap"
    PUBLIC_JSON_LD_OR_METADATA = "public_json_ld_or_metadata"
    TRAE_BROWSER_PUBLIC = "trae_browser_public"
    TRAE_SKILL_AGENT_REACH = "trae_skill_agent_reach"
    TRAE_SCHEDULED_AUTOMATION = "trae_scheduled_automation"
    ON_DEMAND_SEARCH = "on_demand_search"
    MANUAL_REVIEW_ONLY = "manual_review_only"
    BLOCKED_OR_NOT_WORTH_IT = "blocked_or_not_worth_it"


#: 合法的 candidate_layer 值
CANDIDATE_LAYERS: set[str] = {
    "scheduled_ready",
    "scheduled_candidate",
    "low_frequency_candidate",
    "on_demand_candidate",
    "rss_or_sitemap_candidate",
    "wechat_archive_candidate",
    "browser_like_backlog",
    "tls_or_proxy_backlog",
    "cloudflare_or_anti_bot_backlog",
    "blocked_or_low_value",
    "manual_reaudit_needed",
}

#: 合法的 static_http_status / feed_discovery_status / metadata_discovery_status 值
DISCOVERY_STATUSES: set[str] = {
    "ok",
    "ok_with_noise",
    "blocked",
    "not_found",
    "error",
    "not_attempted",
}

#: 合法的 trae_browser_status / trae_skill_status 值
TRAE_STATUSES: set[str] = {
    "available",
    "not_available",
    "not_attempted",
    "observed_public",
    "observed_login_required",
    "observed_paywall",
    "observed_antibot",
    "error",
}

#: 合法的 automation_suitability 值
AUTOMATION_SUITABILITY_VALUES: set[str] = {
    "suitable_for_scheduled",
    "suitable_for_low_frequency",
    "suitable_for_on_demand",
    "not_suitable",
    "manual_review_required",
}

#: 合法的 final decision 值（preflight 结论）
FINAL_DECISIONS: set[str] = {
    "scheduled_preflight_pass_static",
    "scheduled_preflight_pass_feed",
    "trae_browser_assisted_candidate",
    "trae_skill_assisted_candidate",
    "low_frequency_candidate",
    "on_demand_candidate",
    "browser_like_backlog",
    "cloudflare_or_anti_bot_backlog",
    "blocked_or_low_value",
    "manual_reaudit_needed",
}

#: 允许进入 trial_v2 allowlist 的 final decision 集合
TRIAL_V2_ALLOWLIST_ELIGIBLE_DECISIONS: set[str] = {
    "scheduled_preflight_pass_static",
    "scheduled_preflight_pass_feed",
}

#: 允许进入 TRAE automation 的 final decision 集合
TRAE_AUTOMATION_ELIGIBLE_DECISIONS: set[str] = {
    "trae_browser_assisted_candidate",
    "trae_skill_assisted_candidate",
    "low_frequency_candidate",
    "on_demand_candidate",
}

#: M3C-6B 允许的候选源白名单
M3C_6B_ALLOWED_CANDIDATES: set[str] = {
    "reuters",
    "marketwatch",
    "streetinsider",
}

#: 进入 scheduled_preflight_pass_static / feed 的最小有效 item 数
MIN_VALID_ITEMS_FOR_PASS: int = 3

#: 进入 scheduled_preflight_pass_static / feed 的最小 dated item 数
MIN_DATED_ITEMS_FOR_PASS: int = 2

#: 不允许提交的敏感关键字（出现在 evidence / notes / samples 时报警）
SENSITIVE_KEYWORDS: tuple[str, ...] = (
    "cookie:",
    "set-cookie",
    "bearer ",
    "api_key=",
    "apikey:",
    "proxy_url=",
    "http://127.0.0.1",
    "http://localhost",
    "password=",
    "secret=",
    "token=",
)


# ---------------------------------------------------------------------------
# 数据类
# ---------------------------------------------------------------------------

@dataclass
class SampleItem:
    """preflight 阶段提取的样本 item。

    Attributes:
        title:       标题
        url:         URL
        date_text:   日期文本（可能是相对时间或绝对时间字符串）
    """

    title: str = ""
    url: str = ""
    date_text: str = ""


@dataclass
class TraeBrowserAssessment:
    """TRAE 浏览器观察评估结果。

    Attributes:
        public_page_accessible:        公开页面是否可访问
        login_required:                是否需要登录
        paywall_observed:              是否观察到付费墙
        captcha_or_antibot_observed:   是否观察到验证码 / anti-bot
        visible_item_count:            可见 item 数量
        visible_dated_item_count:      可见有日期 item 数量
        sample_items:                  样本 item 列表（最多 5 条，只保留 title/url/date_text）
        automation_suitability:        自动化适配性
        notes:                         备注
    """

    public_page_accessible: bool = False
    login_required: bool = False
    paywall_observed: bool = False
    captcha_or_antibot_observed: bool = False
    visible_item_count: int = 0
    visible_dated_item_count: int = 0
    sample_items: list[SampleItem] = field(default_factory=list)
    automation_suitability: str = "not_suitable"
    notes: str = ""


@dataclass
class SourceExecutionCapability:
    """单个候选源的执行能力画像。

    Attributes:
        source_id:                            源 ID
        candidate_layer:                      候选层级
        static_http_status:                   静态 HTTP 状态
        feed_discovery_status:                 feed / sitemap 发现状态
        metadata_discovery_status:             JSON-LD / OpenGraph metadata 发现状态
        trae_browser_status:                   TRAE browser 状态
        trae_skill_status:                     TRAE skill 状态
        automation_suitability:                自动化适配性
        recommended_execution_mode:            推荐执行模式（ExecutionMode 值）
        trial_v2_allowlist_allowed_now:        是否允许进入 trial_v2 allowlist
        trae_automation_allowed_now:           是否允许进入 TRAE automation
        recommended_next_action:               建议下一步动作
        risk_flags:                            风险标记列表
        evidence_summary:                      证据摘要（不包含 raw HTML / cookie）
        static_http_valid_items:               静态 HTTP 有效 item 数
        static_http_dated_items:               静态 HTTP 有日期 item 数
        feed_count:                            发现的 feed 数量
        sitemap_count:                         发现的 sitemap 数量
        metadata_count:                        发现的 metadata 数量
        trae_browser_assessment:               TRAE browser 评估细节
        final_decision:                        最终决策（preflight 结论）
    """

    source_id: str
    candidate_layer: str = "scheduled_candidate"
    static_http_status: str = "not_attempted"
    feed_discovery_status: str = "not_attempted"
    metadata_discovery_status: str = "not_attempted"
    trae_browser_status: str = "not_attempted"
    trae_skill_status: str = "not_available"
    automation_suitability: str = "not_suitable"
    recommended_execution_mode: str = "manual_review_only"
    trial_v2_allowlist_allowed_now: bool = False
    trae_automation_allowed_now: bool = False
    recommended_next_action: str = "manual_reaudit"
    risk_flags: list[str] = field(default_factory=list)
    evidence_summary: str = ""
    static_http_valid_items: int = 0
    static_http_dated_items: int = 0
    feed_count: int = 0
    sitemap_count: int = 0
    metadata_count: int = 0
    trae_browser_assessment: TraeBrowserAssessment = field(
        default_factory=TraeBrowserAssessment
    )
    final_decision: str = "manual_reaudit_needed"

    def to_dict(self) -> dict[str, Any]:
        """转换为字典（用于 JSON 序列化）。"""
        return {
            "source_id": self.source_id,
            "candidate_layer": self.candidate_layer,
            "static_http_status": self.static_http_status,
            "feed_discovery_status": self.feed_discovery_status,
            "metadata_discovery_status": self.metadata_discovery_status,
            "trae_browser_status": self.trae_browser_status,
            "trae_skill_status": self.trae_skill_status,
            "automation_suitability": self.automation_suitability,
            "recommended_execution_mode": self.recommended_execution_mode,
            "trial_v2_allowlist_allowed_now": self.trial_v2_allowlist_allowed_now,
            "trae_automation_allowed_now": self.trae_automation_allowed_now,
            "recommended_next_action": self.recommended_next_action,
            "risk_flags": list(self.risk_flags),
            "evidence_summary": self.evidence_summary,
            "static_http_valid_items": self.static_http_valid_items,
            "static_http_dated_items": self.static_http_dated_items,
            "feed_count": self.feed_count,
            "sitemap_count": self.sitemap_count,
            "metadata_count": self.metadata_count,
            "trae_browser_assessment": {
                "public_page_accessible": self.trae_browser_assessment.public_page_accessible,
                "login_required": self.trae_browser_assessment.login_required,
                "paywall_observed": self.trae_browser_assessment.paywall_observed,
                "captcha_or_antibot_observed": self.trae_browser_assessment.captcha_or_antibot_observed,
                "visible_item_count": self.trae_browser_assessment.visible_item_count,
                "visible_dated_item_count": self.trae_browser_assessment.visible_dated_item_count,
                "sample_items": [
                    {
                        "title": s.title,
                        "url": s.url,
                        "date_text": s.date_text,
                    }
                    for s in self.trae_browser_assessment.sample_items
                ],
                "automation_suitability": self.trae_browser_assessment.automation_suitability,
                "notes": self.trae_browser_assessment.notes,
            },
            "final_decision": self.final_decision,
        }


# ---------------------------------------------------------------------------
# 校验函数
# ---------------------------------------------------------------------------

def validate_execution_capability(cap: SourceExecutionCapability) -> list[str]:
    """校验单个 SourceExecutionCapability，返回所有错误。

    校验内容：
        - source_id 非空且必须在 M3C-6B 允许的候选白名单内
        - candidate_layer / static_http_status / feed_discovery_status /
          metadata_discovery_status / trae_browser_status / trae_skill_status /
          automation_suitability / final_decision 取值合法
        - recommended_execution_mode 必须是合法 ExecutionMode 值
        - trial_v2_allowlist_allowed_now 默认必须为 False（preflight 阶段不自动开放）
        - 若 final_decision 不在 TRIAL_V2_ALLOWLIST_ELIGIBLE_DECISIONS 内，
          trial_v2_allowlist_allowed_now 必须为 False
        - 若 login_required / paywall_observed / captcha_or_antibot_observed=true，
          final_decision 不得是 scheduled_preflight_pass_static / _feed
        - scheduled_preflight_pass_static 必须有 >= MIN_VALID_ITEMS_FOR_PASS 个有效 item
        - scheduled_preflight_pass_feed 必须有 feed_count >= 1 或 sitemap_count >= 1
        - scheduled_preflight_pass_feed 必须有 >= MIN_DATED_ITEMS_FOR_PASS 个 dated item
        - evidence_summary 不得包含敏感关键字

    Args:
        cap: 待校验的 SourceExecutionCapability。

    Returns:
        错误信息列表。空列表表示校验通过。
    """
    errors: list[str] = []
    prefix = f"source_id={cap.source_id!r}"

    # source_id 非空
    if not cap.source_id:
        errors.append("source_id 不能为空")
        return errors

    # source_id 必须在 M3C-6B 白名单内
    if cap.source_id not in M3C_6B_ALLOWED_CANDIDATES:
        errors.append(
            f"{prefix}.source_id 不在 M3C-6B 允许候选白名单 {sorted(M3C_6B_ALLOWED_CANDIDATES)}"
        )

    # 枚举字段校验
    if cap.candidate_layer not in CANDIDATE_LAYERS:
        errors.append(
            f"{prefix}.candidate_layer={cap.candidate_layer!r} 不在合法范围"
        )
    if cap.static_http_status not in DISCOVERY_STATUSES:
        errors.append(
            f"{prefix}.static_http_status={cap.static_http_status!r} 不在合法范围"
        )
    if cap.feed_discovery_status not in DISCOVERY_STATUSES:
        errors.append(
            f"{prefix}.feed_discovery_status={cap.feed_discovery_status!r} 不在合法范围"
        )
    if cap.metadata_discovery_status not in DISCOVERY_STATUSES:
        errors.append(
            f"{prefix}.metadata_discovery_status={cap.metadata_discovery_status!r} 不在合法范围"
        )
    if cap.trae_browser_status not in TRAE_STATUSES:
        errors.append(
            f"{prefix}.trae_browser_status={cap.trae_browser_status!r} 不在合法范围"
        )
    if cap.trae_skill_status not in TRAE_STATUSES:
        errors.append(
            f"{prefix}.trae_skill_status={cap.trae_skill_status!r} 不在合法范围"
        )
    if cap.automation_suitability not in AUTOMATION_SUITABILITY_VALUES:
        errors.append(
            f"{prefix}.automation_suitability={cap.automation_suitability!r} 不在合法范围"
        )
    if cap.final_decision not in FINAL_DECISIONS:
        errors.append(
            f"{prefix}.final_decision={cap.final_decision!r} 不在合法范围"
        )

    # recommended_execution_mode 必须是合法 ExecutionMode 值
    valid_mode_values = {m.value for m in ExecutionMode}
    if cap.recommended_execution_mode not in valid_mode_values:
        errors.append(
            f"{prefix}.recommended_execution_mode={cap.recommended_execution_mode!r}"
            f" 不在合法 ExecutionMode 范围"
        )

    # trial_v2_allowlist_allowed_now 与 final_decision 一致性
    if cap.trial_v2_allowlist_allowed_now:
        if cap.final_decision not in TRIAL_V2_ALLOWLIST_ELIGIBLE_DECISIONS:
            errors.append(
                f"{prefix}.trial_v2_allowlist_allowed_now=true 但 final_decision="
                f"{cap.final_decision!r} 不在允许进入 trial_v2 的集合 "
                f"{sorted(TRIAL_V2_ALLOWLIST_ELIGIBLE_DECISIONS)}"
            )

    # TRAE browser / skill candidate 不得自动进入 trial_v2 allowlist
    if cap.final_decision in (
        "trae_browser_assisted_candidate",
        "trae_skill_assisted_candidate",
    ):
        if cap.trial_v2_allowlist_allowed_now:
            errors.append(
                f"{prefix}.final_decision={cap.final_decision!r} 不得自动进入 trial_v2 allowlist"
            )

    # login / paywall / captcha 校验
    blocked_flags_present = (
        cap.trae_browser_assessment.login_required
        or cap.trae_browser_assessment.paywall_observed
        or cap.trae_browser_assessment.captcha_or_antibot_observed
    )
    if blocked_flags_present and cap.final_decision in (
        "scheduled_preflight_pass_static",
        "scheduled_preflight_pass_feed",
    ):
        errors.append(
            f"{prefix}.login_required/paywall_observed/captcha_or_antibot_observed=true"
            f" 时不得标记为 {cap.final_decision!r}"
        )

    # scheduled_preflight_pass_static 必须有 >= MIN_VALID_ITEMS_FOR_PASS 个有效 item
    if cap.final_decision == "scheduled_preflight_pass_static":
        if cap.static_http_valid_items < MIN_VALID_ITEMS_FOR_PASS:
            errors.append(
                f"{prefix}.final_decision=scheduled_preflight_pass_static "
                f"但 static_http_valid_items={cap.static_http_valid_items}"
                f" < {MIN_VALID_ITEMS_FOR_PASS}"
            )
        if cap.static_http_dated_items < MIN_DATED_ITEMS_FOR_PASS:
            errors.append(
                f"{prefix}.final_decision=scheduled_preflight_pass_static "
                f"但 static_http_dated_items={cap.static_http_dated_items}"
                f" < {MIN_DATED_ITEMS_FOR_PASS}"
            )

    # scheduled_preflight_pass_feed 必须有 feed evidence
    if cap.final_decision == "scheduled_preflight_pass_feed":
        if cap.feed_count < 1 and cap.sitemap_count < 1:
            errors.append(
                f"{prefix}.final_decision=scheduled_preflight_pass_feed "
                f"但 feed_count={cap.feed_count} 且 sitemap_count={cap.sitemap_count}"
                f"（必须有 feed 或 sitemap evidence）"
            )
        if cap.static_http_dated_items < MIN_DATED_ITEMS_FOR_PASS:
            errors.append(
                f"{prefix}.final_decision=scheduled_preflight_pass_feed "
                f"但 dated items={cap.static_http_dated_items}"
                f" < {MIN_DATED_ITEMS_FOR_PASS}"
            )

    # 敏感关键字检查（evidence_summary / notes）
    sensitive_hits = scan_sensitive_keywords(cap.evidence_summary)
    if sensitive_hits:
        errors.append(
            f"{prefix}.evidence_summary 包含敏感关键字: {sensitive_hits}"
        )
    sensitive_hits_notes = scan_sensitive_keywords(
        cap.trae_browser_assessment.notes
    )
    if sensitive_hits_notes:
        errors.append(
            f"{prefix}.trae_browser_assessment.notes 包含敏感关键字: {sensitive_hits_notes}"
        )

    return errors


def scan_sensitive_keywords(text: str) -> list[str]:
    """扫描文本中是否包含敏感关键字。

    Args:
        text: 待扫描文本。

    Returns:
        命中的敏感关键字列表（小写）。
    """
    if not text:
        return []
    lower = text.lower()
    hits: list[str] = []
    for kw in SENSITIVE_KEYWORDS:
        if kw in lower:
            hits.append(kw)
    return hits


# ---------------------------------------------------------------------------
# 推荐模式计算
# ---------------------------------------------------------------------------

def compute_recommended_execution_mode(
    cap: SourceExecutionCapability,
) -> str:
    """根据 source 执行能力画像，计算推荐执行模式。

    决策优先级：
        1. 若 final_decision 为 blocked/low_value -> blocked_or_not_worth_it
        2. 若 final_decision 为 cloudflare_or_anti_bot_backlog -> blocked_or_not_worth_it
        3. 若 final_decision 为 browser_like_backlog -> trae_browser_public
        4. 若 final_decision 为 trae_skill_assisted_candidate -> trae_skill_agent_reach
        5. 若 final_decision 为 trae_browser_assisted_candidate -> trae_browser_public
        6. 若 final_decision 为 on_demand_candidate -> on_demand_search
        7. 若 final_decision 为 low_frequency_candidate -> rss_or_sitemap 或 python_static_http
        8. 若 final_decision 为 scheduled_preflight_pass_feed -> rss_or_sitemap
        9. 若 final_decision 为 scheduled_preflight_pass_static -> python_static_http
        10. 默认 manual_review_only

    Args:
        cap: SourceExecutionCapability 实例。

    Returns:
        推荐的 ExecutionMode 值。
    """
    decision = cap.final_decision

    if decision in ("blocked_or_low_value", "cloudflare_or_anti_bot_backlog"):
        return ExecutionMode.BLOCKED_OR_NOT_WORTH_IT.value
    if decision == "browser_like_backlog":
        return ExecutionMode.TRAE_BROWSER_PUBLIC.value
    if decision == "trae_skill_assisted_candidate":
        return ExecutionMode.TRAE_SKILL_AGENT_REACH.value
    if decision == "trae_browser_assisted_candidate":
        return ExecutionMode.TRAE_BROWSER_PUBLIC.value
    if decision == "on_demand_candidate":
        return ExecutionMode.ON_DEMAND_SEARCH.value
    if decision == "low_frequency_candidate":
        # 优先 RSS / sitemap，否则静态 HTTP
        if cap.feed_count > 0 or cap.sitemap_count > 0:
            return ExecutionMode.RSS_OR_SITEMAP.value
        return ExecutionMode.PYTHON_STATIC_HTTP.value
    if decision == "scheduled_preflight_pass_feed":
        return ExecutionMode.RSS_OR_SITEMAP.value
    if decision == "scheduled_preflight_pass_static":
        return ExecutionMode.PYTHON_STATIC_HTTP.value
    return ExecutionMode.MANUAL_REVIEW_ONLY.value


def compute_allowlist_flags(
    cap: SourceExecutionCapability,
) -> tuple[bool, bool]:
    """根据 final_decision 计算 trial_v2_allowlist_allowed_now 和
    trae_automation_allowed_now 两个布尔值。

    规则：
        - trial_v2_allowlist_allowed_now=true 当且仅当 final_decision 在
          TRIAL_V2_ALLOWLIST_ELIGIBLE_DECISIONS 内
        - trae_automation_allowed_now=true 当且仅当 final_decision 在
          TRAE_AUTOMATION_ELIGIBLE_DECISIONS 内
        - TRAE browser / skill candidate 不得 trial_v2_allowlist_allowed_now=true

    Args:
        cap: SourceExecutionCapability 实例。

    Returns:
        (trial_v2_allowlist_allowed_now, trae_automation_allowed_now) 元组
    """
    trial_v2 = cap.final_decision in TRIAL_V2_ALLOWLIST_ELIGIBLE_DECISIONS
    trae_auto = cap.final_decision in TRAE_AUTOMATION_ELIGIBLE_DECISIONS
    return (trial_v2, trae_auto)


def apply_recommendations(cap: SourceExecutionCapability) -> SourceExecutionCapability:
    """根据当前画像字段，应用推荐计算：填充 recommended_execution_mode 和 allowlist 标志。

    Args:
        cap: SourceExecutionCapability 实例（会被就地修改）。

    Returns:
        修改后的 SourceExecutionCapability。
    """
    cap.recommended_execution_mode = compute_recommended_execution_mode(cap)
    trial_v2, trae_auto = compute_allowlist_flags(cap)
    cap.trial_v2_allowlist_allowed_now = trial_v2
    cap.trae_automation_allowed_now = trae_auto
    return cap


def is_candidate_source(source_id: str) -> bool:
    """判断 source_id 是否在 M3C-6B 允许的候选白名单内。

    Args:
        source_id: 待检查的源 ID。

    Returns:
        True 表示在白名单内，False 表示不在。
    """
    return source_id in M3C_6B_ALLOWED_CANDIDATES


def make_default_capability(source_id: str) -> SourceExecutionCapability:
    """为指定 source_id 创建一个默认的 SourceExecutionCapability。

    所有状态默认为 not_attempted / not_available，final_decision 默认为
    manual_reaudit_needed，trial_v2_allowlist_allowed_now 默认为 False。

    Args:
        source_id: 源 ID。

    Returns:
        默认的 SourceExecutionCapability 实例。
    """
    return SourceExecutionCapability(
        source_id=source_id,
        candidate_layer="scheduled_candidate",
        static_http_status="not_attempted",
        feed_discovery_status="not_attempted",
        metadata_discovery_status="not_attempted",
        trae_browser_status="not_attempted",
        trae_skill_status="not_available",
        automation_suitability="manual_review_required",
        recommended_execution_mode=ExecutionMode.MANUAL_REVIEW_ONLY.value,
        trial_v2_allowlist_allowed_now=False,
        trae_automation_allowed_now=False,
        recommended_next_action="manual_reaudit",
        risk_flags=[],
        evidence_summary="",
        static_http_valid_items=0,
        static_http_dated_items=0,
        feed_count=0,
        sitemap_count=0,
        metadata_count=0,
        trae_browser_assessment=TraeBrowserAssessment(),
        final_decision="manual_reaudit_needed",
    )
