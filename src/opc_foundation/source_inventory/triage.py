"""Source Inventory 分流（Triage）模块。

功能说明（小白解读）：
    把 92 个 source 按照 live smoke 结果分到不同的"处理桶"里。
    有的能直接上线，有的需要修 URL，有的需要补 connector...
    这样我们就知道接下来该先做什么了。

    分桶的核心逻辑：
    1. 先看 live smoke 状态（能不能访问）
    2. 再看错误类型（为什么失败）
    3. 再看 source 本身属性（blocked？on_demand？manual？）
    4. 最后分到对应的桶里，给出建议动作
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from .models import (
    SourceTriageResult,
    TriageBucket,
    TriageSummary,
    TRIAGE_BUCKET_LABELS,
)


def _detect_error_type(error_message: str, error_type: str = "", http_status: int = 0) -> str:
    """从错误信息中判断具体的错误类型。

    功能说明（小白解读）：
        live smoke 失败了，但失败原因有很多种：
        DNS 解析失败？TLS 握手失败？404 找不到？403 被拒绝？
        这个函数从错误信息里提取关键字，判断到底是哪种错误。

    Args:
        error_message: 错误信息字符串
        error_type: 错误类型（来自 live smoke 结果）
        http_status: HTTP 状态码（如果有）

    Returns:
        str: 识别出的错误类型标签
            - dns_resolution_failed: DNS 解析失败
            - tls_handshake_failed: TLS/SSL 握手失败
            - connection_reset: 连接被重置
            - timeout: 超时
            - ssl_certificate_error: SSL 证书错误
            - http_404: 404 找不到
            - http_403: 403 禁止访问
            - http_401: 401 未授权
            - http_4xx: 其他 4xx 错误
            - http_5xx: 5xx 服务器错误
            - unknown: 未知错误
    """
    msg = (error_message or "").lower()

    # DNS 解析失败
    if "getaddrinfo" in msg or "nodename nor servname" in msg or "dns" in msg:
        return "dns_resolution_failed"

    # TLS/SSL 握手失败
    if "ssl: unexpected_eof" in msg or "ssl_error_syscall" in msg or "tlsv1" in msg:
        return "tls_handshake_failed"
    if "sslv3" in msg or "handshake" in msg:
        return "tls_handshake_failed"

    # 连接被重置
    if "connection reset" in msg or "远程主机强迫关闭" in msg or "winerror 10054" in msg:
        return "connection_reset"

    # 超时
    if "timed out" in msg or "timeout" in msg:
        return "timeout"

    # SSL 证书错误
    if "certificate_verify_failed" in msg or "certificate verify failed" in msg:
        return "ssl_certificate_error"
    if "hostname mismatch" in msg:
        return "ssl_certificate_error"

    # HTTP 状态码判断
    if http_status == 404 or "404" in msg:
        return "http_404"
    if http_status == 403 or "403" in msg:
        return "http_403"
    if http_status == 401 or "401" in msg:
        return "http_401"
    if 400 <= http_status < 500:
        return "http_4xx"
    if 500 <= http_status < 600:
        return "http_5xx"

    # 从错误信息里找 HTTP 状态码
    match = re.search(r"http error:\s*(\d+)", msg)
    if match:
        code = int(match.group(1))
        if code == 404:
            return "http_404"
        if code == 403:
            return "http_403"
        if code == 401:
            return "http_401"
        if 400 <= code < 500:
            return "http_4xx"
        if 500 <= code < 600:
            return "http_5xx"

    return "unknown"


def triage_source(
    source: dict[str, Any],
    live_result: dict[str, Any] | None = None,
) -> SourceTriageResult:
    """对单个 source 做分流（triage）。

    功能说明（小白解读）：
        输入一个 source 的配置信息和它的 live smoke 结果，
        输出它应该分到哪个桶、为什么、建议做什么。

    分桶规则（优先级从高到低）：
        1. blocked_by_policy: 高风险源，直接 blocked
        2. on_demand_only: search provider，只按需使用
        3. dormant: 休眠源，先放着
        4. trae_trial_ready: live_ok 系列，能正常访问
        5. wechat_archive_mapping_needed: 微信公众号，需要映射
        6. needs_connector: 其他需要 connector 的
        7. dns_resolution_failed: DNS 解析失败
        8. http_4xx_or_404: HTTP 4xx 错误
        9. tls_handshake_failed / python_client_limited: TLS 握手失败
        10. replace_or_remove_candidate: 其他失败情况

    Args:
        source: source 配置字典（从 YAML 里读出来的）
        live_result: live smoke 结果字典（可选，没有的话从 source 属性判断）

    Returns:
        SourceTriageResult: 分流结果
    """
    source_id = source.get("source_id", "")
    source_name = source.get("source_name", "")
    source_group = source.get("source_group", "")
    priority = source.get("activation_priority", "")
    access_mode = source.get("access_mode", "")
    url = source.get("url", "")

    # live smoke 状态
    live_status = ""
    error_message = ""
    error_type = ""
    http_status = 0

    if live_result:
        live_status = live_result.get("status", "")
        error_message = live_result.get("error_message", "")
        error_type = live_result.get("error_type", "")
        http_status = live_result.get("http_status", 0)

    # 检测具体错误类型
    detected_error = _detect_error_type(error_message, error_type, http_status)

    # ==========================================
    # 分桶判断（按优先级）
    # ==========================================

    # 1. blocked 高风险源
    if priority == "blocked" or source_group == "blocked_high_risk_sources":
        return SourceTriageResult(
            source_id=source_id,
            source_name=source_name,
            source_group=source_group,
            priority=priority,
            latest_live_status=live_status or "blocked_by_policy",
            triage_bucket=TriageBucket.BLOCKED_BY_POLICY,
            triage_reason="高风险源，按策略禁止接入",
            recommended_action="继续保持 blocked，不接入",
            trae_trial_eligible=False,
            access_mode=access_mode,
            url=url,
        )

    # 2. on_demand / search provider
    if access_mode == "search_provider" or source_group == "search_providers":
        return SourceTriageResult(
            source_id=source_id,
            source_name=source_name,
            source_group=source_group,
            priority=priority,
            latest_live_status=live_status or "on_demand_not_run",
            triage_bucket=TriageBucket.ON_DEMAND_ONLY,
            triage_reason="搜索 provider，仅按需使用，不进入默认调度",
            recommended_action="保持 on-demand，需要时手动调用",
            trae_trial_eligible=False,
            access_mode=access_mode,
            url=url,
        )

    # 3. dormant 休眠源
    if source_group == "community_dev_signals" or access_mode == "dormant":
        return SourceTriageResult(
            source_id=source_id,
            source_name=source_name,
            source_group=source_group,
            priority=priority,
            latest_live_status=live_status or "dormant_not_run",
            triage_bucket=TriageBucket.DORMANT,
            triage_reason="社区/开发者信号，当前处于休眠状态",
            recommended_action="保持休眠，有对应需求时再激活",
            trae_trial_eligible=False,
            access_mode=access_mode,
            url=url,
        )

    # 4. live_ok 系列 → 可进入 TRAE 试运行
    if live_status in ("live_ok", "live_ok_candidates_found", "live_ok_saved", "live_ok_empty"):
        return SourceTriageResult(
            source_id=source_id,
            source_name=source_name,
            source_group=source_group,
            priority=priority,
            latest_live_status=live_status,
            triage_bucket=TriageBucket.TRAE_TRIAL_READY,
            triage_reason="Live smoke 通过，可正常访问",
            recommended_action="纳入 TRAE 试运行候选，配置调度频率后上线",
            trae_trial_eligible=True,
            access_mode=access_mode,
            url=url,
        )

    # 5. 微信公众号 / manual 模式 → 需要 wechat_archive 映射
    if access_mode == "manual" and ("wechat" in url or "微信" in source_name or "wechat" in source_id):
        return SourceTriageResult(
            source_id=source_id,
            source_name=source_name,
            source_group=source_group,
            priority=priority,
            latest_live_status=live_status or "needs_connector",
            triage_bucket=TriageBucket.WECHAT_ARCHIVE_MAPPING_NEEDED,
            triage_reason="微信公众号源，需要映射到 wechat_archive connector",
            recommended_action="配置 wechat_archive account_id 映射，验证后接入",
            trae_trial_eligible=False,
            access_mode=access_mode,
            url=url,
        )

    # 6. 其他 needs_connector
    if live_status == "needs_connector":
        return SourceTriageResult(
            source_id=source_id,
            source_name=source_name,
            source_group=source_group,
            priority=priority,
            latest_live_status=live_status,
            triage_bucket=TriageBucket.NEEDS_CONNECTOR,
            triage_reason="当前缺少对应 connector，无法接入",
            recommended_action="开发或配置对应 connector 后再验证",
            trae_trial_eligible=False,
            access_mode=access_mode,
            url=url,
        )

    # 7. DNS 解析失败
    if detected_error == "dns_resolution_failed":
        return SourceTriageResult(
            source_id=source_id,
            source_name=source_name,
            source_group=source_group,
            priority=priority,
            latest_live_status=live_status,
            triage_bucket=TriageBucket.DNS_RESOLUTION_FAILED,
            triage_reason="DNS 解析失败，可能域名已变更或 URL 配置错误",
            recommended_action="验证域名正确性，寻找替代入口或修正 URL",
            trae_trial_eligible=False,
            access_mode=access_mode,
            url=url,
            notes=error_message[:120],
        )

    # 8. HTTP 4xx 错误（包括 404、403、401 等）
    if detected_error in ("http_404", "http_403", "http_401", "http_4xx"):
        reason_map = {
            "http_404": "HTTP 404，页面可能已下线或 URL 变更",
            "http_403": "HTTP 403，可能有反爬虫或地区限制",
            "http_401": "HTTP 401，需要登录或认证",
            "http_4xx": "HTTP 4xx 客户端错误",
        }
        action_map = {
            "http_404": "验证 URL 正确性，寻找替代入口",
            "http_403": "检查反爬策略，考虑 browser-like connector",
            "http_401": "评估是否支持匿名访问，或寻找公开替代入口",
            "http_4xx": "分析具体错误，寻找解决方案",
        }
        return SourceTriageResult(
            source_id=source_id,
            source_name=source_name,
            source_group=source_group,
            priority=priority,
            latest_live_status=live_status,
            triage_bucket=TriageBucket.HTTP_4XX_OR_404,
            triage_reason=reason_map.get(detected_error, "HTTP 4xx 错误"),
            recommended_action=action_map.get(detected_error, "分析具体错误"),
            trae_trial_eligible=False,
            access_mode=access_mode,
            url=url,
            notes=f"HTTP {http_status}" if http_status else "",
        )

    # 9. TLS 握手失败 / 连接被重置 → 可能是 python client 能力不足
    if detected_error in ("tls_handshake_failed", "connection_reset", "ssl_certificate_error"):
        reason_map = {
            "tls_handshake_failed": "TLS/SSL 握手失败，可能检测到非浏览器客户端指纹",
            "connection_reset": "连接被重置，可能有反爬虫机制",
            "ssl_certificate_error": "SSL 证书校验失败，可能域名不匹配",
        }
        return SourceTriageResult(
            source_id=source_id,
            source_name=source_name,
            source_group=source_group,
            priority=priority,
            latest_live_status=live_status,
            triage_bucket=TriageBucket.TLS_HANDSHAKE_FAILED,
            triage_reason=reason_map.get(detected_error, "TLS/SSL 相关错误"),
            recommended_action="用 curl 做轻量诊断，判断是否需要 browser-like connector",
            trae_trial_eligible=False,
            access_mode=access_mode,
            url=url,
            notes=detected_error,
        )

    # 10. 超时
    if detected_error == "timeout":
        return SourceTriageResult(
            source_id=source_id,
            source_name=source_name,
            source_group=source_group,
            priority=priority,
            latest_live_status=live_status,
            triage_bucket=TriageBucket.URL_VERIFICATION_NEEDED,
            triage_reason="请求超时，可能网络慢或服务器无响应",
            recommended_action="增大超时重试，或验证 URL 是否可访问",
            trae_trial_eligible=False,
            access_mode=access_mode,
            url=url,
        )

    # 11. 其他失败情况 → 建议替换或移除
    return SourceTriageResult(
        source_id=source_id,
        source_name=source_name,
        source_group=source_group,
        priority=priority,
        latest_live_status=live_status,
        triage_bucket=TriageBucket.REPLACE_OR_REMOVE_CANDIDATE,
        triage_reason=f"访问失败（{detected_error}），原因待确认",
        recommended_action="进一步诊断，或寻找替代源",
        trae_trial_eligible=False,
        access_mode=access_mode,
        url=url,
        notes=error_message[:120] if error_message else "",
    )


def triage_all_sources(
    sources: list[dict[str, Any]],
    live_results: list[dict[str, Any]] | None = None,
) -> TriageSummary:
    """对所有 source 做批量分流。

    功能说明（小白解读）：
        把 92 个 source 全部跑一遍 triage_source，
        返回一个大汇总，方便生成报告。

    Args:
        sources: source 配置列表（从 YAML 读出来的）
        live_results: live smoke 结果列表（可选）

    Returns:
        TriageSummary: 分流汇总
    """
    # 把 live_results 转成字典，方便按 source_id 查找
    live_map: dict[str, dict[str, Any]] = {}
    if live_results:
        for r in live_results:
            sid = r.get("source_id", "")
            if sid:
                live_map[sid] = r

    results = []
    for source in sources:
        sid = source.get("source_id", "")
        live_result = live_map.get(sid)
        result = triage_source(source, live_result)
        results.append(result)

    summary = TriageSummary(
        total_sources=len(results),
        results=results,
        triaged_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )

    return summary
