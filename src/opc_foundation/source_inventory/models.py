"""Source Inventory Live Smoke 数据模型。

功能说明（小白解读）：
    定义 live smoke 用到的所有数据结构。
    用 dataclasses 实现，不依赖 pydantic，保持轻量。

    什么是 live smoke？
        就是对每个信息源做一次真实的连通性测试：
        - 看看网站能不能访问
        - 看看能不能提取到内容
        - 看看需不需要补 connector
        - 看看是不是 blocked 源

    状态枚举很多，记住核心几类就行：
        - live_ok 系列：能访问
        - needs_connector / parser_mismatch：能访问但解析不了
        - blocked_by_policy：按策略禁止访问
        - on_demand_not_run / dormant_not_run：按需/休眠源没跑
        - http_error / timeout / failed：访问失败
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class LiveSmokeStatus(str, Enum):
    """Live Smoke 状态枚举。

    功能说明（小白解读）：
        每个源跑完 live smoke 后会有一个状态。
        用枚举（固定选项）而不是自由文本，方便统计和 Dashboard 展示。

    状态分类：
        - 成功类：live_ok, live_ok_empty, live_ok_candidates_found, live_ok_saved
        - 可访问但解析不了：reachable_no_parser, needs_connector, parser_mismatch
        - 策略性不跑：blocked_by_policy, on_demand_not_run, dormant_not_run
        - 配置问题：missing_config, missing_api_key
        - 访问失败：http_error, timeout, failed
    """

    LIVE_OK = "live_ok"
    LIVE_OK_EMPTY = "live_ok_empty"
    LIVE_OK_CANDIDATES_FOUND = "live_ok_candidates_found"
    LIVE_OK_SAVED = "live_ok_saved"
    REACHABLE_NO_PARSER = "reachable_no_parser"
    NEEDS_CONNECTOR = "needs_connector"
    PARSER_MISMATCH = "parser_mismatch"
    BLOCKED_BY_POLICY = "blocked_by_policy"
    ON_DEMAND_NOT_RUN = "on_demand_not_run"
    DORMANT_NOT_RUN = "dormant_not_run"
    MISSING_CONFIG = "missing_config"
    MISSING_API_KEY = "missing_api_key"
    HTTP_ERROR = "http_error"
    TIMEOUT = "timeout"
    FAILED = "failed"


# 中文显示标签
LIVE_SMOKE_STATUS_LABELS = {
    LiveSmokeStatus.LIVE_OK: "可访问",
    LiveSmokeStatus.LIVE_OK_EMPTY: "可访问但暂无候选",
    LiveSmokeStatus.LIVE_OK_CANDIDATES_FOUND: "已发现候选",
    LiveSmokeStatus.LIVE_OK_SAVED: "已保存候选",
    LiveSmokeStatus.REACHABLE_NO_PARSER: "可访问但暂无解析器",
    LiveSmokeStatus.NEEDS_CONNECTOR: "需要补 connector",
    LiveSmokeStatus.PARSER_MISMATCH: "解析规则不匹配",
    LiveSmokeStatus.BLOCKED_BY_POLICY: "按策略禁止访问",
    LiveSmokeStatus.ON_DEMAND_NOT_RUN: "按需源未运行",
    LiveSmokeStatus.DORMANT_NOT_RUN: "休眠源未运行",
    LiveSmokeStatus.MISSING_CONFIG: "缺少配置",
    LiveSmokeStatus.MISSING_API_KEY: "缺少 API Key",
    LiveSmokeStatus.HTTP_ERROR: "HTTP 错误",
    LiveSmokeStatus.TIMEOUT: "请求超时",
    LiveSmokeStatus.FAILED: "失败",
}

# 状态严重级别（用于 Dashboard 颜色）
LIVE_SMOKE_STATUS_SEVERITY = {
    LiveSmokeStatus.LIVE_OK: "success",
    LiveSmokeStatus.LIVE_OK_EMPTY: "success",
    LiveSmokeStatus.LIVE_OK_CANDIDATES_FOUND: "success",
    LiveSmokeStatus.LIVE_OK_SAVED: "success",
    LiveSmokeStatus.REACHABLE_NO_PARSER: "warning",
    LiveSmokeStatus.NEEDS_CONNECTOR: "warning",
    LiveSmokeStatus.PARSER_MISMATCH: "warning",
    LiveSmokeStatus.BLOCKED_BY_POLICY: "info",
    LiveSmokeStatus.ON_DEMAND_NOT_RUN: "info",
    LiveSmokeStatus.DORMANT_NOT_RUN: "info",
    LiveSmokeStatus.MISSING_CONFIG: "warning",
    LiveSmokeStatus.MISSING_API_KEY: "warning",
    LiveSmokeStatus.HTTP_ERROR: "error",
    LiveSmokeStatus.TIMEOUT: "error",
    LiveSmokeStatus.FAILED: "error",
}


@dataclass
class CandidateItem:
    """候选内容条目。

    功能说明（小白解读）：
        从一个源页面上提取到的候选内容，比如一篇文章、一条 RSS 记录。
        只存元数据，不存全文，避免数据太大。

    参数：
        title:       标题
        url:         链接
        published:   发布时间（字符串，可能为空）
        summary:     摘要（可能为空）
        source:      来源名称
    """

    title: str = ""
    url: str = ""
    published: str = ""
    summary: str = ""
    source: str = ""


@dataclass
class SourceLiveResult:
    """单个源的 live smoke 结果。

    功能说明（小白解读）：
        记录一个 source_id 跑完 live smoke 后的所有信息：
        状态是什么、访问了没、抓到候选没、错误信息是什么。

    参数：
        source_id:          源 ID
        source_name:        源名称
        source_group:       所属分组
        access_mode:        接入方式
        status:             live smoke 状态
        visited:            是否真的访问了（blocked 源为 false）
        fetched:            是否真的抓取了内容
        candidates_found:   发现的候选数量
        candidates_saved:   保存的候选数量
        candidates:         候选列表（最多 max_candidates_per_source 条）
        response_time_ms:   响应时间（毫秒）
        http_status:        HTTP 状态码（如果有）
        error_message:      错误信息（如果失败）
        error_type:         错误类型
        notes:              备注
        checked_at:         检查时间
    """

    source_id: str
    source_name: str = ""
    source_group: str = ""
    access_mode: str = ""
    status: LiveSmokeStatus = LiveSmokeStatus.FAILED
    visited: bool = False
    fetched: bool = False
    candidates_found: int = 0
    candidates_saved: int = 0
    candidates: list[CandidateItem] = field(default_factory=list)
    response_time_ms: int = 0
    http_status: int = 0
    error_message: str = ""
    error_type: str = ""
    notes: str = ""
    checked_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典（用于 JSON 序列化）。

        Returns:
            dict: 字典形式的结果
        """
        return {
            "source_id": self.source_id,
            "source_name": self.source_name,
            "source_group": self.source_group,
            "access_mode": self.access_mode,
            "status": self.status.value,
            "visited": self.visited,
            "fetched": self.fetched,
            "candidates_found": self.candidates_found,
            "candidates_saved": self.candidates_saved,
            "candidates": [
                {
                    "title": c.title,
                    "url": c.url,
                    "published": c.published,
                    "summary": c.summary,
                    "source": c.source,
                }
                for c in self.candidates
            ],
            "response_time_ms": self.response_time_ms,
            "http_status": self.http_status,
            "error_message": self.error_message,
            "error_type": self.error_type,
            "notes": self.notes,
            "checked_at": self.checked_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SourceLiveResult":
        """从字典创建 SourceLiveResult。

        Args:
            data: 字典数据

        Returns:
            SourceLiveResult: 结果对象
        """
        candidates = [
            CandidateItem(
                title=c.get("title", ""),
                url=c.get("url", ""),
                published=c.get("published", ""),
                summary=c.get("summary", ""),
                source=c.get("source", ""),
            )
            for c in data.get("candidates", [])
        ]
        status_value = data.get("status", "failed")
        try:
            status = LiveSmokeStatus(status_value)
        except ValueError:
            status = LiveSmokeStatus.FAILED

        return cls(
            source_id=data.get("source_id", ""),
            source_name=data.get("source_name", ""),
            source_group=data.get("source_group", ""),
            access_mode=data.get("access_mode", ""),
            status=status,
            visited=data.get("visited", False),
            fetched=data.get("fetched", False),
            candidates_found=data.get("candidates_found", 0),
            candidates_saved=data.get("candidates_saved", 0),
            candidates=candidates,
            response_time_ms=data.get("response_time_ms", 0),
            http_status=data.get("http_status", 0),
            error_message=data.get("error_message", ""),
            error_type=data.get("error_type", ""),
            notes=data.get("notes", ""),
            checked_at=data.get("checked_at", ""),
        )


@dataclass
class SourceGroupLiveResult:
    """source group 级别的 live smoke 结果。

    功能说明（小白解读）：
        一个 source group 下所有源的汇总统计。
        比如"投行官方公开研究"这个组下有多少源、多少成功、多少失败。

    参数：
        group_id:       分组 ID
        group_name:     分组名称
        total_sources:  源总数
        results:        每个源的结果列表
    """

    group_id: str
    group_name: str = ""
    total_sources: int = 0
    results: list[SourceLiveResult] = field(default_factory=list)

    @property
    def status_counts(self) -> dict[str, int]:
        """按状态统计数量。

        Returns:
            dict: {状态名: 数量}
        """
        counts: dict[str, int] = {}
        for r in self.results:
            key = r.status.value
            counts[key] = counts.get(key, 0) + 1
        return counts

    @property
    def success_count(self) -> int:
        """成功类状态的数量。

        Returns:
            int: 成功数量
        """
        success_statuses = {
            LiveSmokeStatus.LIVE_OK,
            LiveSmokeStatus.LIVE_OK_EMPTY,
            LiveSmokeStatus.LIVE_OK_CANDIDATES_FOUND,
            LiveSmokeStatus.LIVE_OK_SAVED,
        }
        return sum(1 for r in self.results if r.status in success_statuses)

    @property
    def failure_count(self) -> int:
        """失败类状态的数量。

        Returns:
            int: 失败数量
        """
        failure_statuses = {
            LiveSmokeStatus.HTTP_ERROR,
            LiveSmokeStatus.TIMEOUT,
            LiveSmokeStatus.FAILED,
        }
        return sum(1 for r in self.results if r.status in failure_statuses)


@dataclass
class LiveSmokeSummary:
    """Live Smoke 总览汇总。

    功能说明（小白解读）：
        整个 92 个源跑完后的大汇总。
        包括总成功数、总失败数、各分组情况等。
        也记录了这次运行是否走了代理、代理来源是什么。

    参数：
        total_sources:      源总数
        groups:             分组结果列表
        run_started_at:     开始时间
        run_finished_at:    结束时间
        total_duration_ms:  总耗时（毫秒）
        proxy_enabled:      是否启用了代理
        proxy_mode:         代理来源（cli / env / none）
    """

    total_sources: int = 0
    groups: list[SourceGroupLiveResult] = field(default_factory=list)
    run_started_at: str = ""
    run_finished_at: str = ""
    total_duration_ms: int = 0
    proxy_enabled: bool = False
    proxy_mode: str = "none"

    @property
    def status_counts(self) -> dict[str, int]:
        """全局按状态统计数量。

        Returns:
            dict: {状态名: 数量}
        """
        counts: dict[str, int] = {}
        for g in self.groups:
            for status, count in g.status_counts.items():
                counts[status] = counts.get(status, 0) + count
        return counts

    @property
    def success_count(self) -> int:
        """全局成功数量。

        Returns:
            int: 成功数量
        """
        return sum(g.success_count for g in self.groups)

    @property
    def failure_count(self) -> int:
        """全局失败数量。

        Returns:
            int: 失败数量
        """
        return sum(g.failure_count for g in self.groups)

    @property
    def blocked_count(self) -> int:
        """blocked_by_policy 的数量。

        Returns:
            int: blocked 数量
        """
        count = 0
        for g in self.groups:
            for r in g.results:
                if r.status == LiveSmokeStatus.BLOCKED_BY_POLICY:
                    count += 1
        return count

    @property
    def needs_connector_count(self) -> int:
        """需要补 connector 的数量。

        Returns:
            int: needs_connector 数量
        """
        count = 0
        for g in self.groups:
            for r in g.results:
                if r.status == LiveSmokeStatus.NEEDS_CONNECTOR:
                    count += 1
        return count


@dataclass
class LiveSmokeRunConfig:
    """Live Smoke 运行配置。

    功能说明（小白解读）：
        跑一次 live smoke 时的参数配置：
        每个源最多抓几个候选、超时多少秒、重试几次、是否用代理。

    参数：
        max_candidates_per_source: 每个源最多候选数
        timeout_seconds:           请求超时秒数
        max_retries:               最大重试次数
        user_agent:                User-Agent 字符串
        dry_run:                   是否 dry-run（不真实访问网络）
        proxy_url:                 代理地址（如 http://127.0.0.1:7890），为空则不用代理
        proxy_mode:                代理来源（cli / env / none）
    """

    max_candidates_per_source: int = 5
    timeout_seconds: int = 20
    max_retries: int = 1
    user_agent: str = "OPC-Foundation-LiveSmoke/1.0 (+https://github.com/xe7dx54321-stack/opc-foundation)"
    dry_run: bool = False
    proxy_url: str = ""
    proxy_mode: str = "none"


# ============================================
# Triage（分流）相关模型
# ============================================

class TriageBucket(str, Enum):
    """Source 分桶枚举。

    功能说明（小白解读）：
        每个 source 跑完 live smoke 后，要把它分到一个"处理桶"里，
        表示接下来该怎么处理它。
        比如有的可以直接上线，有的需要修 URL，有的需要补 connector。

    各桶含义：
        trae_trial_ready:            可进入 TRAE 试运行候选
        url_verification_needed:     需要 URL 校验
        url_fixed:                   URL 已修正
        dns_resolution_failed:       DNS 解析失败
        http_4xx_or_404:             HTTP 4xx 或 404
        tls_handshake_failed:        TLS/SSL 握手失败
        python_client_limited:       Python urllib 客户端能力不足
        browser_like_needed:         后续需要 browser-like connector
        needs_connector:             需要补 connector
        wechat_archive_mapping_needed: 需要映射到 wechat_archive
        on_demand_only:              只按需使用
        dormant:                     休眠
        blocked_by_policy:           策略禁止访问
        replace_or_remove_candidate: 建议替换或移除
    """

    TRAE_TRIAL_READY = "trae_trial_ready"
    URL_VERIFICATION_NEEDED = "url_verification_needed"
    URL_FIXED = "url_fixed"
    DNS_RESOLUTION_FAILED = "dns_resolution_failed"
    HTTP_4XX_OR_404 = "http_4xx_or_404"
    TLS_HANDSHAKE_FAILED = "tls_handshake_failed"
    PYTHON_CLIENT_LIMITED = "python_client_limited"
    BROWSER_LIKE_NEEDED = "browser_like_needed"
    NEEDS_CONNECTOR = "needs_connector"
    WECHAT_ARCHIVE_MAPPING_NEEDED = "wechat_archive_mapping_needed"
    ON_DEMAND_ONLY = "on_demand_only"
    DORMANT = "dormant"
    BLOCKED_BY_POLICY = "blocked_by_policy"
    REPLACE_OR_REMOVE_CANDIDATE = "replace_or_remove_candidate"


# 分桶中文标签
TRIAGE_BUCKET_LABELS = {
    TriageBucket.TRAE_TRIAL_READY: "可进入 TRAE 试运行",
    TriageBucket.URL_VERIFICATION_NEEDED: "需要 URL 校验",
    TriageBucket.URL_FIXED: "URL 已修正",
    TriageBucket.DNS_RESOLUTION_FAILED: "DNS 解析失败",
    TriageBucket.HTTP_4XX_OR_404: "HTTP 4xx/404",
    TriageBucket.TLS_HANDSHAKE_FAILED: "TLS 握手失败",
    TriageBucket.PYTHON_CLIENT_LIMITED: "Python 客户端能力不足",
    TriageBucket.BROWSER_LIKE_NEEDED: "需要 browser-like connector",
    TriageBucket.NEEDS_CONNECTOR: "需要补 connector",
    TriageBucket.WECHAT_ARCHIVE_MAPPING_NEEDED: "需要微信归档映射",
    TriageBucket.ON_DEMAND_ONLY: "仅按需使用",
    TriageBucket.DORMANT: "休眠",
    TriageBucket.BLOCKED_BY_POLICY: "策略禁止访问",
    TriageBucket.REPLACE_OR_REMOVE_CANDIDATE: "建议替换或移除",
}


@dataclass
class SourceTriageResult:
    """单个 Source 的分流结果。

    功能说明（小白解读）：
        记录一个 source 经过 triage（分流）后的所有信息：
        分到哪个桶、为什么、建议做什么动作、能不能进 TRAE 试运行。

    参数：
        source_id:            源 ID
        source_name:          源名称
        source_group:         所属分组
        priority:             激活优先级（S/A/B/supplement/blocked）
        latest_live_status:   最近一次 live smoke 状态
        triage_bucket:        分桶结果
        triage_reason:        分桶原因（为什么分到这个桶）
        recommended_action:   建议动作（下一步该做什么）
        trae_trial_eligible:  是否符合 TRAE 试运行条件
        access_mode:          接入方式
        url:                  源 URL
        notes:                额外备注
    """

    source_id: str
    source_name: str = ""
    source_group: str = ""
    priority: str = ""
    latest_live_status: str = ""
    triage_bucket: TriageBucket = TriageBucket.REPLACE_OR_REMOVE_CANDIDATE
    triage_reason: str = ""
    recommended_action: str = ""
    trae_trial_eligible: bool = False
    access_mode: str = ""
    url: str = ""
    notes: str = ""

    def to_dict(self) -> dict[str, any]:
        """转换为字典（用于 JSON 序列化）。

        Returns:
            dict: 字典形式的分流结果
        """
        return {
            "source_id": self.source_id,
            "source_name": self.source_name,
            "source_group": self.source_group,
            "priority": self.priority,
            "latest_live_status": self.latest_live_status,
            "triage_bucket": self.triage_bucket.value,
            "triage_reason": self.triage_reason,
            "recommended_action": self.recommended_action,
            "trae_trial_eligible": self.trae_trial_eligible,
            "access_mode": self.access_mode,
            "url": self.url,
            "notes": self.notes,
        }


@dataclass
class TriageSummary:
    """Triage 总览汇总。

    功能说明（小白解读）：
        所有 92 个源分完桶后的大汇总。
        每个桶有多少个源、TRAE 试运行候选有哪些等。

    参数：
        total_sources:       源总数
        results:             每个源的分流结果
        triaged_at:          分流时间
    """

    total_sources: int = 0
    results: list[SourceTriageResult] = field(default_factory=list)
    triaged_at: str = ""

    @property
    def bucket_counts(self) -> dict[str, int]:
        """按分桶统计数量。

        Returns:
            dict: {分桶名: 数量}
        """
        counts: dict[str, int] = {}
        for r in self.results:
            key = r.triage_bucket.value
            counts[key] = counts.get(key, 0) + 1
        return counts

    @property
    def trae_trial_ready_count(self) -> int:
        """可进入 TRAE 试运行的源数量。

        Returns:
            int: 数量
        """
        return sum(1 for r in self.results if r.triage_bucket == TriageBucket.TRAE_TRIAL_READY)

    @property
    def trae_trial_ready_sources(self) -> list[SourceTriageResult]:
        """可进入 TRAE 试运行的源列表。

        Returns:
            list[SourceTriageResult]: 源列表
        """
        return [r for r in self.results if r.triage_bucket == TriageBucket.TRAE_TRIAL_READY]
