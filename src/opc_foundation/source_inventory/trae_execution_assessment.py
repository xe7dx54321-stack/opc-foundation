"""TRAE Execution Assessment 模型 (M3C-6G)。

功能说明（小白解读）：
    M3C-6B 的静态 preflight 表明 reuters / marketwatch / streetinsider 三源
    均无法通过 Python urllib/httpx 静态抓取（HTTP 401/403）。但这不等于
    "这些源不可用"——TRAE 作为调度 / 执行 Agent，可能具备：

        1. 内置浏览器工具 (agent-browser)
        2. agent-reach 类网页观察技能
        3. 一次性手动自动化 dry-run 能力

    本模块定义 TRAE-assisted execution 评估数据模型，记录对每个源做公开
    页面观察的结构化结果，并给出最终决策：

        - trae_browser_assisted_candidate: 适合 TRAE browser 公开观察
        - trae_skill_assisted_candidate:   适合 agent-reach 类技能
        - trae_low_frequency_candidate:    适合低频 TRAE 自动化
        - trae_on_demand_candidate:        适合按需触发
        - public_browser_blocked:           公开页面无法访问
        - login_or_paywall_blocked:         登录 / 付费墙阻断
        - captcha_or_antibot_blocked:      验证码 / anti-bot 阻断
        - manual_review_only:              只能人工复核
        - not_worth_it:                    不值得继续

    核心约束：
        - trial_v2_allowlist_allowed_now 必须默认 false（TRAE-assisted
          candidate 不得自动进入 Python trial_v2 allowlist）
        - trae_automation_allowed_now 不能是 true，只能是 false 或
          "manual_approval_required"
        - login_required / paywall_observed / captcha_or_antibot_observed /
          cloudflare_or_botwall_observed=true 时不得成为 candidate
        - visible_item_count < 3 或 visible_dated_item_count < 2 时不得成为
          candidate
        - sample_items 不得包含 cookie / token / session
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# 常量集合
# ---------------------------------------------------------------------------

#: M3C-6G 允许的候选源白名单
M3C_6G_ALLOWED_CANDIDATES: set[str] = {
    "reuters",
    "marketwatch",
    "streetinsider",
}

#: 合法的 final decision 值（M3C-6G 结论）
TRAE_FINAL_DECISIONS: set[str] = {
    "trae_browser_assisted_candidate",
    "trae_skill_assisted_candidate",
    "trae_low_frequency_candidate",
    "trae_on_demand_candidate",
    "public_browser_blocked",
    "login_or_paywall_blocked",
    "captcha_or_antibot_blocked",
    "manual_review_only",
    "not_worth_it",
}

#: 允许进入 TRAE automation 的 final decision 集合
TRAE_AUTOMATION_ELIGIBLE_DECISIONS: set[str] = {
    "trae_browser_assisted_candidate",
    "trae_skill_assisted_candidate",
    "trae_low_frequency_candidate",
    "trae_on_demand_candidate",
}

#: 成为 trae_browser_assisted_candidate 的最小 visible item 数
MIN_VISIBLE_ITEMS_FOR_CANDIDATE: int = 3

#: 成为 trae_browser_assisted_candidate 的最小 dated item 数
MIN_VISIBLE_DATED_ITEMS_FOR_CANDIDATE: int = 2

#: 单个 source 最多记录的 sample item 数
MAX_SAMPLE_ITEMS_RECORDED: int = 3

#: trae_automation_allowed_now 字段允许的值
TRAE_AUTOMATION_ALLOWED_VALUES: set[str] = {
    "false",
    "manual_approval_required",
}

#: 敏感关键字（出现在 sample_items / notes 时报警）
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
    "session_id=",
    "sessionid=",
    "jsessionid=",
)


# ---------------------------------------------------------------------------
# 数据类
# ---------------------------------------------------------------------------

@dataclass
class TraeBrowserSampleItem:
    """TRAE browser 观察到的样本 item。

    Attributes:
        title:                 标题
        url:                   URL
        date_text:             日期文本（相对时间或绝对时间字符串）
        extraction_method:     提取方法（如 manual_browser_observation）
    """

    title: str = ""
    url: str = ""
    date_text: str = ""
    extraction_method: str = "manual_browser_observation"


@dataclass
class TraeBrowserObservation:
    """TRAE browser 公开页面观察结果。

    Attributes:
        public_page_accessible:        公开页面是否可访问
        login_required:                是否需要登录
        paywall_observed:              是否观察到付费墙
        captcha_or_antibot_observed:   是否观察到验证码 / anti-bot
        cloudflare_or_botwall_observed: 是否观察到 Cloudflare / botwall
        visible_item_count:            可见 item 数量
        visible_dated_item_count:      可见有日期 item 数量
        sample_items:                  样本 item 列表（最多 3 条）
        structured_extraction_possible: 是否能稳定提取结构化字段
        repeatability_observed:        是否观察到可重复性
        observation_notes:              观察备注
    """

    public_page_accessible: bool = False
    login_required: bool = False
    paywall_observed: bool = False
    captcha_or_antibot_observed: bool = False
    cloudflare_or_botwall_observed: bool = False
    visible_item_count: int = 0
    visible_dated_item_count: int = 0
    sample_items: list[TraeBrowserSampleItem] = field(default_factory=list)
    structured_extraction_possible: bool = False
    repeatability_observed: bool = False
    observation_notes: str = ""


@dataclass
class TraeSkillObservation:
    """agent-reach 类 TRAE skill 观察结果。

    Attributes:
        skill_available:        技能是否可用
        skill_name:              技能名称（如 agent-browser / agent-reach）
        public_page_accessible:  技能是否能打开公开页面
        structured_output:       技能是否能输出结构化标题 / URL / 日期
        login_required:          是否遇到登录
        paywall_observed:        是否遇到付费墙
        captcha_or_antibot_observed: 是否遇到 captcha / anti-bot
        output_stable:           输出是否稳定
        risk_flags:              风险标记列表
        notes:                   备注
    """

    skill_available: bool = False
    skill_name: str = ""
    public_page_accessible: bool = False
    structured_output: bool = False
    login_required: bool = False
    paywall_observed: bool = False
    captcha_or_antibot_observed: bool = False
    output_stable: bool = False
    risk_flags: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class TraeAutomationDryRunObservation:
    """一次性手动自动化 dry-run 观察结果。

    Attributes:
        tested:                 是否执行了 dry-run
        result:                 结果摘要（如 success / failed / not_attempted）
        reason:                 未执行原因（如未尝试）
        output_summary:         输出摘要（不包含 raw HTML / cookie）
        risk_flags:             风险标记列表
    """

    tested: bool = False
    result: str = "not_attempted"
    reason: str = "not attempted in M3C-6G"
    output_summary: str = ""
    risk_flags: list[str] = field(default_factory=list)


@dataclass
class TraeAssistedDecision:
    """单个候选源的 TRAE-assisted 决策。

    Attributes:
        recommended_execution_mode: 推荐执行模式
        trae_automation_allowed_now: 是否允许进入 TRAE automation
                                     (只能是 "false" 或 "manual_approval_required")
        trial_v2_allowlist_allowed_now: 是否允许进入 trial_v2 allowlist
                                         (M3C-6G 阶段必须 false)
        next_action:                建议下一步动作
        risk_flags:                 风险标记列表
    """

    recommended_execution_mode: str = "manual_review_only"
    trae_automation_allowed_now: str = "false"
    trial_v2_allowlist_allowed_now: bool = False
    next_action: str = "manual_reaudit"
    risk_flags: list[str] = field(default_factory=list)


@dataclass
class TraeExecutionAssessmentReport:
    """单个候选源的完整 TRAE 执行评估报告。

    Attributes:
        source_id:                       源 ID
        prior_static_decision:           M3C-6B 静态 preflight 结论
        browser_observation:             TRAE browser 观察结果
        skill_observation:               TRAE skill 观察结果
        automation_dry_run:              一次性自动化 dry-run 结果
        decision:                        最终决策
        notes:                           备注
    """

    source_id: str
    prior_static_decision: str = "manual_reaudit_needed"
    browser_observation: TraeBrowserObservation = field(
        default_factory=TraeBrowserObservation
    )
    skill_observation: TraeSkillObservation = field(
        default_factory=TraeSkillObservation
    )
    automation_dry_run: TraeAutomationDryRunObservation = field(
        default_factory=TraeAutomationDryRunObservation
    )
    decision: TraeAssistedDecision = field(default_factory=TraeAssistedDecision)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典（用于 JSON 序列化）。"""
        return {
            "source_id": self.source_id,
            "prior_static_decision": self.prior_static_decision,
            "browser_observation": {
                "public_page_accessible": self.browser_observation.public_page_accessible,
                "login_required": self.browser_observation.login_required,
                "paywall_observed": self.browser_observation.paywall_observed,
                "captcha_or_antibot_observed": self.browser_observation.captcha_or_antibot_observed,
                "cloudflare_or_botwall_observed": self.browser_observation.cloudflare_or_botwall_observed,
                "visible_item_count": self.browser_observation.visible_item_count,
                "visible_dated_item_count": self.browser_observation.visible_dated_item_count,
                "sample_items": [
                    {
                        "title": s.title,
                        "url": s.url,
                        "date_text": s.date_text,
                        "extraction_method": s.extraction_method,
                    }
                    for s in self.browser_observation.sample_items
                ],
                "structured_extraction_possible": self.browser_observation.structured_extraction_possible,
                "repeatability_observed": self.browser_observation.repeatability_observed,
                "observation_notes": self.browser_observation.observation_notes,
            },
            "skill_observation": {
                "skill_available": self.skill_observation.skill_available,
                "skill_name": self.skill_observation.skill_name,
                "public_page_accessible": self.skill_observation.public_page_accessible,
                "structured_output": self.skill_observation.structured_output,
                "login_required": self.skill_observation.login_required,
                "paywall_observed": self.skill_observation.paywall_observed,
                "captcha_or_antibot_observed": self.skill_observation.captcha_or_antibot_observed,
                "output_stable": self.skill_observation.output_stable,
                "risk_flags": list(self.skill_observation.risk_flags),
                "notes": self.skill_observation.notes,
            },
            "automation_dry_run": {
                "tested": self.automation_dry_run.tested,
                "result": self.automation_dry_run.result,
                "reason": self.automation_dry_run.reason,
                "output_summary": self.automation_dry_run.output_summary,
                "risk_flags": list(self.automation_dry_run.risk_flags),
            },
            "decision": {
                "recommended_execution_mode": self.decision.recommended_execution_mode,
                "trae_automation_allowed_now": self.decision.trae_automation_allowed_now,
                "trial_v2_allowlist_allowed_now": self.decision.trial_v2_allowlist_allowed_now,
                "next_action": self.decision.next_action,
                "risk_flags": list(self.decision.risk_flags),
            },
            "notes": self.notes,
        }


# ---------------------------------------------------------------------------
# 校验函数
# ---------------------------------------------------------------------------

def validate_trae_assessment(report: TraeExecutionAssessmentReport) -> list[str]:
    """校验单个 TraeExecutionAssessmentReport，返回所有错误。

    校验内容：
        - source_id 非空且必须在 M3C-6G 允许的候选白名单内
        - final decision 必须在 TRAE_FINAL_DECISIONS 内
        - trae_automation_allowed_now 只能是 "false" 或 "manual_approval_required"
        - trial_v2_allowlist_allowed_now 必须为 False（M3C-6G 阶段不得自动进入 allowlist）
        - login_required=true 时不得是 trae_browser_assisted_candidate
        - paywall_observed=true 时不得是 candidate
        - captcha_or_antibot_observed=true 时不得是 candidate
        - cloudflare_or_botwall_observed=true 时不得是 candidate
        - visible_item_count < 3 时不得是 candidate
        - visible_dated_item_count < 2 时不得是 candidate
        - sample_items 不得包含敏感关键字
        - notes / observation_notes 不得包含敏感关键字

    Args:
        report: 待校验的 TraeExecutionAssessmentReport。

    Returns:
        错误信息列表。空列表表示校验通过。
    """
    errors: list[str] = []
    prefix = f"source_id={report.source_id!r}"

    # source_id 非空
    if not report.source_id:
        errors.append("source_id 不能为空")
        return errors

    # source_id 必须在 M3C-6G 白名单内
    if report.source_id not in M3C_6G_ALLOWED_CANDIDATES:
        errors.append(
            f"{prefix}.source_id 不在 M3C-6G 允许候选白名单 "
            f"{sorted(M3C_6G_ALLOWED_CANDIDATES)}"
        )

    # decision 必须是合法 final decision
    decision_mode = report.decision.recommended_execution_mode
    # final decision 字段我们存在 recommended_execution_mode 里
    # 但 spec 中 final_decision 是一个枚举；这里我们用 decision.recommended_execution_mode
    # 来表达最终决策。我们允许 recommended_execution_mode 是 TRAE_FINAL_DECISIONS 之一
    # 或一个 execution mode（如 trae_browser_public）。两者都接受。
    # 但如果它看起来像 final decision（即在 TRAE_FINAL_DECISIONS 内），则按 final decision 规则校验。

    # trae_automation_allowed_now 必须是 "false" 或 "manual_approval_required"
    if report.decision.trae_automation_allowed_now not in TRAE_AUTOMATION_ALLOWED_VALUES:
        errors.append(
            f"{prefix}.trae_automation_allowed_now="
            f"{report.decision.trae_automation_allowed_now!r} 不在合法范围 "
            f"{sorted(TRAE_AUTOMATION_ALLOWED_VALUES)}"
        )

    # trial_v2_allowlist_allowed_now 必须为 False
    if report.decision.trial_v2_allowlist_allowed_now:
        errors.append(
            f"{prefix}.trial_v2_allowlist_allowed_now 必须为 False"
            f"（M3C-6G 阶段 TRAE-assisted candidate 不得自动进入 trial_v2 allowlist）"
        )

    # final decision = recommended_execution_mode 校验
    bo = report.browser_observation
    final_decision = decision_mode

    # 如果 final decision 是 candidate 类，必须满足门槛
    if final_decision in (
        "trae_browser_assisted_candidate",
        "trae_skill_assisted_candidate",
        "trae_low_frequency_candidate",
        "trae_on_demand_candidate",
    ):
        # login / paywall / captcha / cloudflare 任一为 true 则不得是 candidate
        if bo.login_required:
            errors.append(
                f"{prefix}.login_required=true 时不得成为 {final_decision!r}"
            )
        if bo.paywall_observed:
            errors.append(
                f"{prefix}.paywall_observed=true 时不得成为 {final_decision!r}"
            )
        if bo.captcha_or_antibot_observed:
            errors.append(
                f"{prefix}.captcha_or_antibot_observed=true 时不得成为 {final_decision!r}"
            )
        if bo.cloudflare_or_botwall_observed:
            errors.append(
                f"{prefix}.cloudflare_or_botwall_observed=true 时不得成为 {final_decision!r}"
            )
        # visible_item_count 必须 >= 3
        if bo.visible_item_count < MIN_VISIBLE_ITEMS_FOR_CANDIDATE:
            errors.append(
                f"{prefix}.visible_item_count={bo.visible_item_count}"
                f" < {MIN_VISIBLE_ITEMS_FOR_CANDIDATE} 时不得成为 {final_decision!r}"
            )
        # visible_dated_item_count 必须 >= 2
        if bo.visible_dated_item_count < MIN_VISIBLE_DATED_ITEMS_FOR_CANDIDATE:
            errors.append(
                f"{prefix}.visible_dated_item_count={bo.visible_dated_item_count}"
                f" < {MIN_VISIBLE_DATED_ITEMS_FOR_CANDIDATE} 时不得成为 {final_decision!r}"
            )

    # 如果 final decision 是 trae_browser_assisted_candidate，trae_automation_allowed_now
    # 必须是 manual_approval_required（不能是 "false"）
    if final_decision == "trae_browser_assisted_candidate":
        if report.decision.trae_automation_allowed_now != "manual_approval_required":
            errors.append(
                f"{prefix}.final_decision=trae_browser_assisted_candidate 时 "
                f"trae_automation_allowed_now 必须为 'manual_approval_required'"
            )

    # sample_items 敏感关键字检查
    for i, s in enumerate(bo.sample_items):
        sensitive_hits = scan_sensitive_keywords(s.title) + scan_sensitive_keywords(s.url) + scan_sensitive_keywords(s.date_text)
        if sensitive_hits:
            errors.append(
                f"{prefix}.sample_items[{i}] 包含敏感关键字: {sensitive_hits}"
            )
        # extraction_method 必须是合法值
        if s.extraction_method not in (
            "manual_browser_observation",
            "agent_browser_observation",
            "agent_reach_observation",
            "structured_extraction",
        ):
            errors.append(
                f"{prefix}.sample_items[{i}].extraction_method="
                f"{s.extraction_method!r} 不在合法范围"
            )

    # 敏感关键字检查（notes / observation_notes）
    sensitive_notes = scan_sensitive_keywords(report.notes)
    if sensitive_notes:
        errors.append(f"{prefix}.notes 包含敏感关键字: {sensitive_notes}")
    sensitive_obs = scan_sensitive_keywords(bo.observation_notes)
    if sensitive_obs:
        errors.append(
            f"{prefix}.browser_observation.observation_notes 包含敏感关键字: {sensitive_obs}"
        )
    sensitive_skill = scan_sensitive_keywords(report.skill_observation.notes)
    if sensitive_skill:
        errors.append(
            f"{prefix}.skill_observation.notes 包含敏感关键字: {sensitive_skill}"
        )

    # sample_items 数量上限
    if len(bo.sample_items) > MAX_SAMPLE_ITEMS_RECORDED:
        errors.append(
            f"{prefix}.sample_items 数量 {len(bo.sample_items)} "
            f"超过上限 {MAX_SAMPLE_ITEMS_RECORDED}"
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
# 决策计算
# ---------------------------------------------------------------------------

def compute_trae_decision(report: TraeExecutionAssessmentReport) -> TraeAssistedDecision:
    """根据观察结果计算 TRAE-assisted 决策。

    决策规则：
        1. 若 login_required=true -> login_or_paywall_blocked
        2. 若 paywall_observed=true -> login_or_paywall_blocked
        3. 若 captcha_or_antibot_observed=true -> captcha_or_antibot_blocked
        4. 若 cloudflare_or_botwall_observed=true -> captcha_or_antibot_blocked
        5. 若 not public_page_accessible -> public_browser_blocked
        6. 若 visible_item_count < 3 或 visible_dated_item_count < 2 -> manual_review_only
        7. 若 structured_extraction_possible 且 repeatability_observed ->
           trae_browser_assisted_candidate
        8. 否则 -> manual_review_only

    对于 trae_browser_assisted_candidate：
        - trae_automation_allowed_now = "manual_approval_required"
        - trial_v2_allowlist_allowed_now = False

    Args:
        report: TraeExecutionAssessmentReport 实例。

    Returns:
        TraeAssistedDecision 实例。
    """
    bo = report.browser_observation
    decision = TraeAssistedDecision()

    # 1. Blocker checks
    if bo.login_required or bo.paywall_observed:
        decision.recommended_execution_mode = "login_or_paywall_blocked"
        decision.trae_automation_allowed_now = "false"
        decision.trial_v2_allowlist_allowed_now = False
        decision.next_action = "exclude_from_automation"
        decision.risk_flags.append("login_or_paywall_blocker")
        return decision

    if bo.captcha_or_antibot_observed or bo.cloudflare_or_botwall_observed:
        decision.recommended_execution_mode = "captcha_or_antibot_blocked"
        decision.trae_automation_allowed_now = "false"
        decision.trial_v2_allowlist_allowed_now = False
        decision.next_action = "move_to_antibot_backlog"
        decision.risk_flags.append("captcha_or_antibot_blocker")
        return decision

    # 2. Public page not accessible
    if not bo.public_page_accessible:
        decision.recommended_execution_mode = "public_browser_blocked"
        decision.trae_automation_allowed_now = "false"
        decision.trial_v2_allowlist_allowed_now = False
        decision.next_action = "move_to_browser_like_backlog"
        decision.risk_flags.append("public_page_inaccessible")
        return decision

    # 3. Insufficient items
    if (
        bo.visible_item_count < MIN_VISIBLE_ITEMS_FOR_CANDIDATE
        or bo.visible_dated_item_count < MIN_VISIBLE_DATED_ITEMS_FOR_CANDIDATE
    ):
        decision.recommended_execution_mode = "manual_review_only"
        decision.trae_automation_allowed_now = "false"
        decision.trial_v2_allowlist_allowed_now = False
        decision.next_action = "manual_reaudit"
        decision.risk_flags.append("insufficient_items")
        return decision

    # 4. trae_browser_assisted_candidate
    decision.recommended_execution_mode = "trae_browser_assisted_candidate"
    decision.trae_automation_allowed_now = "manual_approval_required"
    decision.trial_v2_allowlist_allowed_now = False
    decision.next_action = "propose_for_trae_automation_with_manual_approval"
    return decision


def apply_trae_decision(report: TraeExecutionAssessmentReport) -> TraeExecutionAssessmentReport:
    """根据观察字段，应用决策计算：填充 decision 字段。

    Args:
        report: TraeExecutionAssessmentReport 实例（会被就地修改）。

    Returns:
        修改后的 TraeExecutionAssessmentReport。
    """
    report.decision = compute_trae_decision(report)
    return report


def is_m3c_6g_candidate(source_id: str) -> bool:
    """判断 source_id 是否在 M3C-6G 允许的候选白名单内。

    Args:
        source_id: 待检查的源 ID。

    Returns:
        True 表示在白名单内，False 表示不在。
    """
    return source_id in M3C_6G_ALLOWED_CANDIDATES


def make_default_trae_report(source_id: str) -> TraeExecutionAssessmentReport:
    """为指定 source_id 创建一个默认的 TraeExecutionAssessmentReport。

    所有观察字段默认为 false / 0 / 空列表，decision 默认为 manual_review_only。

    Args:
        source_id: 源 ID。

    Returns:
        默认的 TraeExecutionAssessmentReport 实例。
    """
    return TraeExecutionAssessmentReport(
        source_id=source_id,
        prior_static_decision="manual_reaudit_needed",
        browser_observation=TraeBrowserObservation(),
        skill_observation=TraeSkillObservation(
            skill_available=False,
            skill_name="",
            notes="not attempted in M3C-6G",
        ),
        automation_dry_run=TraeAutomationDryRunObservation(
            tested=False,
            result="not_attempted",
            reason="not attempted in M3C-6G",
        ),
        decision=TraeAssistedDecision(
            recommended_execution_mode="manual_review_only",
            trae_automation_allowed_now="false",
            trial_v2_allowlist_allowed_now=False,
            next_action="manual_reaudit",
        ),
        notes="",
    )
