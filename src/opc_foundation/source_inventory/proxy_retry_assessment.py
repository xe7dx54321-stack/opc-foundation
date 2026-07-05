"""Proxy Retry Assessment 模型 (M3C-6F)。

功能说明（小白解读）：
    M3C-6A 覆盖度重审中，merck_ir / yahoo_finance / the_fly 三源
    被归类为 tls_or_proxy_backlog，即当前本地网络环境下存在
    TLS / DNS / 超时等网络可达性问题。

    本阶段通过 direct 与 proxy-env 两种模式对比，判断：
        1. 是否只是本地网络出口问题
        2. 代理环境下能否恢复正常 HTTP / TLS 访问
        3. 是否存在真正的 login / paywall / captcha / anti-bot 阻断
        4. 能否提取有效 title / URL / date
        5. 是否可进入下一批 scheduled_candidate

    核心约束：
        - proxy retry 只用于判断网络可达性，不得用于绕过任何防护
        - trial_v2_allowlist_allowed_now 默认 false
        - captcha_or_antibot_observed=true 时不得成为 scheduled_candidate
        - login_required=true 时不得成为 scheduled_candidate
        - paywall_observed=true 时不得成为 scheduled_candidate
        - valid_item_count < 3 时不得成为 scheduled_candidate
        - dated_item_count < 2 时不得成为 scheduled_candidate
        - 不得记录 / 提交真实 proxy URL
        - 不得记录 / 提交 cookie / token / secret
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# 常量集合
# ---------------------------------------------------------------------------

#: M3C-6F 允许的候选源白名单
M3C_6F_ALLOWED_CANDIDATES: set[str] = {
    "merck_ir",
    "yahoo_finance",
    "the_fly",
}

#: 合法的 final decision 值（M3C-6F 结论）
PROXY_FINAL_DECISIONS: set[str] = {
    "scheduled_candidate",
    "low_frequency_candidate",
    "on_demand_candidate",
    "tls_or_proxy_backlog",
    "captcha_or_antibot_blocked",
    "login_or_paywall_blocked",
    "manual_review_only",
    "not_worth_it",
}

#: 允许进入 scheduled_candidate 的 final decision 集合
SCHEDULED_CANDIDATE_ELIGIBLE_DECISIONS: set[str] = {
    "scheduled_candidate",
}

#: 成为 scheduled_candidate 的最小 valid item 数
MIN_VALID_ITEMS_FOR_SCHEDULED: int = 3

#: 成为 scheduled_candidate 的最小 dated item 数
MIN_DATED_ITEMS_FOR_SCHEDULED: int = 2

#: 单个 source 最多记录的 sample item 数
MAX_SAMPLE_ITEMS_RECORDED: int = 3

#: 网络状态枚举值
NETWORK_STATUS_VALUES: set[str] = {
    "success",
    "http_error",
    "tls_error",
    "dns_error",
    "timeout",
    "connection_error",
    "not_configured",
    "not_tested",
}

#: 错误类型枚举值
ERROR_TYPE_VALUES: set[str] = {
    "none",
    "http_4xx",
    "http_5xx",
    "tls_handshake",
    "tls_certificate",
    "dns_resolution",
    "timeout_connect",
    "timeout_read",
    "connection_refused",
    "connection_reset",
    "proxy_not_configured",
    "unknown",
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
    "http_proxy=",
    "https_proxy=",
    "all_proxy=",
)


# ---------------------------------------------------------------------------
# 数据类
# ---------------------------------------------------------------------------

@dataclass
class ProxyRetrySampleItem:
    """Proxy retry 观察到的样本 item。

    Attributes:
        title:                 标题
        url:                   URL
        date_text:             日期文本（相对时间或绝对时间字符串）
        extraction_method:     提取方法（如 html_parsing / feed_parsing）
    """

    title: str = ""
    url: str = ""
    date_text: str = ""
    extraction_method: str = "html_parsing"


@dataclass
class ProxyRetryAttempt:
    """单次网络尝试（direct 或 proxy-env）的结果。

    Attributes:
        mode:                       模式（direct / proxy-env）
        status:                     网络状态（success / http_error / tls_error 等）
        http_status:                HTTP 状态码（0 表示未收到响应）
        error_type:                 错误类型（none / http_4xx / tls_handshake 等）
        error_message:              错误消息摘要（不含敏感信息）
        content_type:               Content-Type 响应头
        content_length:             Content-Length 或实际 body 字节数
        tls_error_observed:         是否观察到 TLS 错误
        dns_error_observed:         是否观察到 DNS 错误
        timeout_observed:           是否观察到超时
        captcha_or_antibot_observed: 是否观察到验证码 / anti-bot
        cloudflare_or_botwall_observed: 是否观察到 Cloudflare / botwall
        login_required:             是否需要登录
        paywall_observed:           是否观察到付费墙
        valid_item_count:           有效 item 数量
        dated_item_count:           有日期 item 数量
        sample_items:               样本 item 列表（最多 3 条）
        risk_flags:                 风险标记列表
        notes:                      备注
    """

    mode: str = "direct"
    status: str = "not_tested"
    http_status: int = 0
    error_type: str = "none"
    error_message: str = ""
    content_type: str = ""
    content_length: int = 0
    tls_error_observed: bool = False
    dns_error_observed: bool = False
    timeout_observed: bool = False
    captcha_or_antibot_observed: bool = False
    cloudflare_or_botwall_observed: bool = False
    login_required: bool = False
    paywall_observed: bool = False
    valid_item_count: int = 0
    dated_item_count: int = 0
    sample_items: list[ProxyRetrySampleItem] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class ProxyRetryDecision:
    """单个候选源的 proxy retry 最终决策。

    Attributes:
        recommended_execution_mode:       推荐执行模式
        trial_v2_allowlist_allowed_now:   是否允许进入 trial_v2 allowlist（M3C-6F 必须 false）
        low_frequency_allowed_now:        是否允许进入低频调度
        on_demand_allowed_now:            是否允许进入按需触发
        next_action:                      建议下一步动作
        risk_flags:                       风险标记列表
    """

    recommended_execution_mode: str = "manual_review_only"
    trial_v2_allowlist_allowed_now: bool = False
    low_frequency_allowed_now: bool = False
    on_demand_allowed_now: bool = False
    next_action: str = "manual_reaudit"
    risk_flags: list[str] = field(default_factory=list)


@dataclass
class ProxyRetrySourceResult:
    """单个候选源的完整 proxy retry 评估结果。

    Attributes:
        source_id:                       源 ID
        prior_status:                    之前的状态（如 tls_or_proxy_backlog）
        prior_score:                     之前的评分
        direct_attempt:                  direct 模式尝试结果
        proxy_env_attempt:               proxy-env 模式尝试结果
        proxy_env_configured:            proxy 环境变量是否配置（不记录具体值）
        decision:                        最终决策
        notes:                           备注
    """

    source_id: str
    prior_status: str = "tls_or_proxy_backlog"
    prior_score: int = 0
    direct_attempt: ProxyRetryAttempt = field(default_factory=ProxyRetryAttempt)
    proxy_env_attempt: ProxyRetryAttempt = field(
        default_factory=lambda: ProxyRetryAttempt(mode="proxy-env")
    )
    proxy_env_configured: bool = False
    decision: ProxyRetryDecision = field(default_factory=ProxyRetryDecision)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典（用于 JSON 序列化）。"""
        return {
            "source_id": self.source_id,
            "prior_status": self.prior_status,
            "prior_score": self.prior_score,
            "direct_attempt": _attempt_to_dict(self.direct_attempt),
            "proxy_env_attempt": _attempt_to_dict(self.proxy_env_attempt),
            "proxy_env_configured": self.proxy_env_configured,
            "decision": {
                "recommended_execution_mode": self.decision.recommended_execution_mode,
                "trial_v2_allowlist_allowed_now": self.decision.trial_v2_allowlist_allowed_now,
                "low_frequency_allowed_now": self.decision.low_frequency_allowed_now,
                "on_demand_allowed_now": self.decision.on_demand_allowed_now,
                "next_action": self.decision.next_action,
                "risk_flags": list(self.decision.risk_flags),
            },
            "notes": self.notes,
        }


def _attempt_to_dict(attempt: ProxyRetryAttempt) -> dict[str, Any]:
    """将 ProxyRetryAttempt 转换为字典。"""
    return {
        "mode": attempt.mode,
        "status": attempt.status,
        "http_status": attempt.http_status,
        "error_type": attempt.error_type,
        "error_message": attempt.error_message,
        "content_type": attempt.content_type,
        "content_length": attempt.content_length,
        "tls_error_observed": attempt.tls_error_observed,
        "dns_error_observed": attempt.dns_error_observed,
        "timeout_observed": attempt.timeout_observed,
        "captcha_or_antibot_observed": attempt.captcha_or_antibot_observed,
        "cloudflare_or_botwall_observed": attempt.cloudflare_or_botwall_observed,
        "login_required": attempt.login_required,
        "paywall_observed": attempt.paywall_observed,
        "valid_item_count": attempt.valid_item_count,
        "dated_item_count": attempt.dated_item_count,
        "sample_items": [
            {
                "title": s.title,
                "url": s.url,
                "date_text": s.date_text,
                "extraction_method": s.extraction_method,
            }
            for s in attempt.sample_items
        ],
        "risk_flags": list(attempt.risk_flags),
        "notes": attempt.notes,
    }


@dataclass
class ProxyRetryBatchReport:
    """M3C-6F 整批 proxy retry 报告。

    Attributes:
        batch_name:             批次名称
        base_commit:            基准 commit
        branch:                 分支名
        m3c_6g_merge_commit:    M3C-6G merge commit
        trial_v2_source_count:  当前 trial_v2 源数量
        proxy_env_configured:   proxy 环境变量是否配置（全局）
        sources:                各源的结果列表
        generated_at:           生成时间
    """

    batch_name: str = "m3c_6f_proxy_retry_batch"
    base_commit: str = ""
    branch: str = ""
    m3c_6g_merge_commit: str = ""
    trial_v2_source_count: int = 9
    proxy_env_configured: bool = False
    sources: list[ProxyRetrySourceResult] = field(default_factory=list)
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {
            "batch_name": self.batch_name,
            "base_commit": self.base_commit,
            "branch": self.branch,
            "m3c_6g_merge_commit": self.m3c_6g_merge_commit,
            "trial_v2_source_count": self.trial_v2_source_count,
            "proxy_env_configured": self.proxy_env_configured,
            "sources": [s.to_dict() for s in self.sources],
            "generated_at": self.generated_at,
        }


# ---------------------------------------------------------------------------
# 校验函数
# ---------------------------------------------------------------------------

def validate_proxy_retry_result(result: ProxyRetrySourceResult) -> list[str]:
    """校验单个 ProxyRetrySourceResult，返回所有错误。

    校验内容：
        - source_id 非空且必须在 M3C-6F 允许的候选白名单内
        - final decision 必须在 PROXY_FINAL_DECISIONS 内
        - trial_v2_allowlist_allowed_now 必须为 False
        - login_required=true 时不得是 scheduled_candidate
        - paywall_observed=true 时不得是 scheduled_candidate
        - captcha_or_antibot_observed=true 时不得是 scheduled_candidate
        - valid_item_count < 3 时不得是 scheduled_candidate
        - dated_item_count < 2 时不得是 scheduled_candidate
        - sample_items 不得包含敏感关键字
        - notes / error_message 不得包含敏感关键字
        - attempt 数量不超过上限

    Args:
        result: 待校验的 ProxyRetrySourceResult。

    Returns:
        错误信息列表。空列表表示校验通过。
    """
    errors: list[str] = []
    prefix = f"source_id={result.source_id!r}"

    if not result.source_id:
        errors.append("source_id 不能为空")
        return errors

    if result.source_id not in M3C_6F_ALLOWED_CANDIDATES:
        errors.append(
            f"{prefix}.source_id 不在 M3C-6F 允许候选白名单 "
            f"{sorted(M3C_6F_ALLOWED_CANDIDATES)}"
        )

    decision_mode = result.decision.recommended_execution_mode
    if decision_mode not in PROXY_FINAL_DECISIONS:
        errors.append(
            f"{prefix}.recommended_execution_mode={decision_mode!r} 不在合法范围 "
            f"{sorted(PROXY_FINAL_DECISIONS)}"
        )

    if result.decision.trial_v2_allowlist_allowed_now:
        errors.append(
            f"{prefix}.trial_v2_allowlist_allowed_now 必须为 False"
            f"（M3C-6F 阶段不得直接进入 trial_v2 allowlist）"
        )

    best_attempt = _pick_best_attempt(result)

    if decision_mode == "scheduled_candidate":
        if best_attempt.login_required:
            errors.append(
                f"{prefix}.login_required=true 时不得成为 scheduled_candidate"
            )
        if best_attempt.paywall_observed:
            errors.append(
                f"{prefix}.paywall_observed=true 时不得成为 scheduled_candidate"
            )
        if best_attempt.captcha_or_antibot_observed:
            errors.append(
                f"{prefix}.captcha_or_antibot_observed=true 时不得成为 scheduled_candidate"
            )
        if best_attempt.cloudflare_or_botwall_observed:
            errors.append(
                f"{prefix}.cloudflare_or_botwall_observed=true 时不得成为 scheduled_candidate"
            )
        if best_attempt.valid_item_count < MIN_VALID_ITEMS_FOR_SCHEDULED:
            errors.append(
                f"{prefix}.valid_item_count={best_attempt.valid_item_count}"
                f" < {MIN_VALID_ITEMS_FOR_SCHEDULED} 时不得成为 scheduled_candidate"
            )
        if best_attempt.dated_item_count < MIN_DATED_ITEMS_FOR_SCHEDULED:
            errors.append(
                f"{prefix}.dated_item_count={best_attempt.dated_item_count}"
                f" < {MIN_DATED_ITEMS_FOR_SCHEDULED} 时不得成为 scheduled_candidate"
            )

    for attempt_name, attempt in [
        ("direct_attempt", result.direct_attempt),
        ("proxy_env_attempt", result.proxy_env_attempt),
    ]:
        for i, s in enumerate(attempt.sample_items):
            sensitive_hits = (
                scan_sensitive_keywords(s.title)
                + scan_sensitive_keywords(s.url)
                + scan_sensitive_keywords(s.date_text)
            )
            if sensitive_hits:
                errors.append(
                    f"{prefix}.{attempt_name}.sample_items[{i}] 包含敏感关键字: {sensitive_hits}"
                )

        sensitive_notes = scan_sensitive_keywords(attempt.notes)
        if sensitive_notes:
            errors.append(
                f"{prefix}.{attempt_name}.notes 包含敏感关键字: {sensitive_notes}"
            )

        sensitive_err = scan_sensitive_keywords(attempt.error_message)
        if sensitive_err:
            errors.append(
                f"{prefix}.{attempt_name}.error_message 包含敏感关键字: {sensitive_err}"
            )

        if len(attempt.sample_items) > MAX_SAMPLE_ITEMS_RECORDED:
            errors.append(
                f"{prefix}.{attempt_name}.sample_items 数量 {len(attempt.sample_items)} "
                f"超过上限 {MAX_SAMPLE_ITEMS_RECORDED}"
            )

        if attempt.status not in NETWORK_STATUS_VALUES:
            errors.append(
                f"{prefix}.{attempt_name}.status={attempt.status!r} 不在合法范围 "
                f"{sorted(NETWORK_STATUS_VALUES)}"
            )

        if attempt.error_type not in ERROR_TYPE_VALUES:
            errors.append(
                f"{prefix}.{attempt_name}.error_type={attempt.error_type!r} 不在合法范围 "
                f"{sorted(ERROR_TYPE_VALUES)}"
            )

    sensitive_notes_global = scan_sensitive_keywords(result.notes)
    if sensitive_notes_global:
        errors.append(f"{prefix}.notes 包含敏感关键字: {sensitive_notes_global}")

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


def _pick_best_attempt(result: ProxyRetrySourceResult) -> ProxyRetryAttempt:
    """选择状态最好的 attempt 用于决策。

    优先级：proxy-env success > direct success > proxy-env partial > direct partial
    """
    attempts = [result.proxy_env_attempt, result.direct_attempt]
    success_attempts = [a for a in attempts if a.status == "success"]
    if success_attempts:
        return max(success_attempts, key=lambda a: a.valid_item_count)

    http_attempts = [a for a in attempts if a.status == "http_error" and a.http_status > 0]
    if http_attempts:
        return http_attempts[0]

    return result.direct_attempt


# ---------------------------------------------------------------------------
# 决策计算
# ---------------------------------------------------------------------------

def compute_proxy_retry_decision(result: ProxyRetrySourceResult) -> ProxyRetryDecision:
    """根据 direct / proxy-env 两种模式的结果计算最终决策。

    决策规则：
        1. 若任一模式出现 login_required -> login_or_paywall_blocked
        2. 若任一模式出现 paywall_observed -> login_or_paywall_blocked
        3. 若任一模式出现 captcha_or_antibot_observed -> captcha_or_antibot_blocked
        4. 若任一模式出现 cloudflare_or_botwall_observed -> captcha_or_antibot_blocked
        5. 若两种模式均不可达（非 success）-> tls_or_proxy_backlog
        6. 取最佳模式（proxy-env 优先）判断：
           - valid_item_count >= 3 且 dated_item_count >= 2 -> scheduled_candidate
           - valid_item_count >= 1 但 item 少 / 更新频率低 -> low_frequency_candidate
           - 内容价值高但不适合固定调度 -> on_demand_candidate
           - 否则 -> manual_review_only

    Args:
        result: ProxyRetrySourceResult 实例。

    Returns:
        ProxyRetryDecision 实例。
    """
    decision = ProxyRetryDecision()
    decision.trial_v2_allowlist_allowed_now = False

    best = _pick_best_attempt(result)

    has_any_success = (
        result.direct_attempt.status == "success"
        or result.proxy_env_attempt.status == "success"
    )

    # 1. Blocker: login / paywall
    if best.login_required or best.paywall_observed:
        decision.recommended_execution_mode = "login_or_paywall_blocked"
        decision.low_frequency_allowed_now = False
        decision.on_demand_allowed_now = False
        decision.next_action = "exclude_from_automation"
        decision.risk_flags.append("login_or_paywall_blocker")
        return decision

    # 2. Blocker: captcha / anti-bot / cloudflare
    if best.captcha_or_antibot_observed or best.cloudflare_or_botwall_observed:
        decision.recommended_execution_mode = "captcha_or_antibot_blocked"
        decision.low_frequency_allowed_now = False
        decision.on_demand_allowed_now = False
        decision.next_action = "move_to_antibot_backlog"
        decision.risk_flags.append("captcha_or_antibot_blocker")
        return decision

    # 3. 两种模式均不可达
    if not has_any_success:
        decision.recommended_execution_mode = "tls_or_proxy_backlog"
        decision.low_frequency_allowed_now = False
        decision.on_demand_allowed_now = False
        decision.next_action = "continue_monitoring_or_dedicated_proxy_troubleshooting"
        if best.tls_error_observed:
            decision.risk_flags.append("tls_error")
        if best.dns_error_observed:
            decision.risk_flags.append("dns_error")
        if best.timeout_observed:
            decision.risk_flags.append("timeout")
        return decision

    # 4. 有成功访问，按 item 数量判断
    if best.valid_item_count >= MIN_VALID_ITEMS_FOR_SCHEDULED and best.dated_item_count >= MIN_DATED_ITEMS_FOR_SCHEDULED:
        decision.recommended_execution_mode = "scheduled_candidate"
        decision.low_frequency_allowed_now = True
        decision.on_demand_allowed_now = True
        decision.next_action = "candidate_preflight_round_2_or_allowlist_proposal"
        return decision

    if best.valid_item_count >= 1:
        if best.valid_item_count < MIN_VALID_ITEMS_FOR_SCHEDULED:
            decision.recommended_execution_mode = "low_frequency_candidate"
            decision.low_frequency_allowed_now = True
            decision.on_demand_allowed_now = True
            decision.next_action = "low_frequency_trial_or_on_demand_registry"
            decision.risk_flags.append("insufficient_items_for_scheduled")
            return decision

    # 5. 能访问但内容提取不足
    decision.recommended_execution_mode = "manual_review_only"
    decision.low_frequency_allowed_now = False
    decision.on_demand_allowed_now = False
    decision.next_action = "manual_content_extraction_review"
    decision.risk_flags.append("content_extraction_insufficient")
    return decision


def apply_proxy_retry_decision(result: ProxyRetrySourceResult) -> ProxyRetrySourceResult:
    """根据尝试结果，应用决策计算：填充 decision 字段。

    Args:
        result: ProxyRetrySourceResult 实例（会被就地修改）。

    Returns:
        修改后的 ProxyRetrySourceResult。
    """
    result.decision = compute_proxy_retry_decision(result)
    return result


def is_m3c_6f_candidate(source_id: str) -> bool:
    """判断 source_id 是否在 M3C-6F 允许的候选白名单内。

    Args:
        source_id: 待检查的源 ID。

    Returns:
        True 表示在白名单内，False 表示不在。
    """
    return source_id in M3C_6F_ALLOWED_CANDIDATES


def make_default_proxy_result(source_id: str) -> ProxyRetrySourceResult:
    """为指定 source_id 创建一个默认的 ProxyRetrySourceResult。

    所有字段默认为 false / 0 / 空列表，decision 默认为 manual_review_only。

    Args:
        source_id: 源 ID。

    Returns:
        默认的 ProxyRetrySourceResult 实例。
    """
    return ProxyRetrySourceResult(
        source_id=source_id,
        prior_status="tls_or_proxy_backlog",
        prior_score=0,
        direct_attempt=ProxyRetryAttempt(mode="direct", status="not_tested"),
        proxy_env_attempt=ProxyRetryAttempt(mode="proxy-env", status="not_tested"),
        proxy_env_configured=False,
        decision=ProxyRetryDecision(
            recommended_execution_mode="manual_review_only",
            trial_v2_allowlist_allowed_now=False,
            low_frequency_allowed_now=False,
            on_demand_allowed_now=False,
            next_action="run_proxy_retry_assessment",
        ),
        notes="",
    )


def check_proxy_env_configured() -> bool:
    """检查环境变量中是否配置了代理（不读取具体值）。

    只检查环境变量名是否存在且非空，不返回具体代理 URL。

    Returns:
        True 表示至少配置了一个代理环境变量。
    """
    import os

    proxy_env_names = (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    )
    for name in proxy_env_names:
        value = os.environ.get(name, "")
        if value:
            return True
    return False
