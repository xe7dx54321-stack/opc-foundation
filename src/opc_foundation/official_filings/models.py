"""Official Filing Foundation 的数据模型。

功能说明（小白解读）：
    本文件定义 Official Filing Foundation 用到的核心数据结构：
    - FilingDefaults         全局默认参数（超时、抓取条数、保存选项等）
    - FilingSourceConfig 一个官方披露源的配置
    - FilingArchiveConfig 一次运行的完整配置
    - FilingCandidate   Connector 输出的候选披露
    - NormalizedFiling   归档后的标准披露（最核心输出）
    - FailedFiling       失败队列记录
    - FilingSourceHealth 源健康状态
    - FilingRunResult    一次运行的汇总结果

所有模型用 pydantic BaseModel 实现，与现有 research / wechat 模块风格一致。

注意：
    这些模型里绝对不包含任何投资判断字段。
    issuer_code 只是披露方代码（CIK / 股票代码等），foundation 不解释其投资含义。
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 枚举常量（用字符串枚举，避免引入额外依赖）
# ---------------------------------------------------------------------------

# source_type 合法取值
SOURCE_TYPE_SEC_EDGAR = "sec_edgar"
SOURCE_TYPE_CNINFO_ANNOUNCEMENT = "cninfo_announcement"
SOURCE_TYPE_HKEX_ANNOUNCEMENT = "hkex_announcement"

IMPLEMENTED_SOURCE_TYPES = {
    SOURCE_TYPE_SEC_EDGAR,
    SOURCE_TYPE_CNINFO_ANNOUNCEMENT,
    SOURCE_TYPE_HKEX_ANNOUNCEMENT,
}

# legal_profile 合法取值
LEGAL_PROFILE_OFFICIAL_PUBLIC = "official_public"
LEGAL_PROFILE_PUBLIC_IR = "public_ir"
LEGAL_PROFILE_UNKNOWN = "unknown"

LEGAL_PROFILES = {
    LEGAL_PROFILE_OFFICIAL_PUBLIC,
    LEGAL_PROFILE_PUBLIC_IR,
    LEGAL_PROFILE_UNKNOWN,
}

# Source Health status 合法取值
HEALTH_STATUS_HEALTHY = "healthy"
HEALTH_STATUS_DEGRADED = "degraded"
HEALTH_STATUS_FAILED = "failed"
HEALTH_STATUS_DISABLED = "disabled"
HEALTH_STATUS_UNKNOWN = "unknown"

HEALTH_STATUSES = {
    HEALTH_STATUS_HEALTHY,
    HEALTH_STATUS_DEGRADED,
    HEALTH_STATUS_FAILED,
    HEALTH_STATUS_DISABLED,
    HEALTH_STATUS_UNKNOWN,
}

# error_type 合法取值
ERROR_TYPE_CONFIG = "config_error"
ERROR_TYPE_FETCH = "fetch_error"
ERROR_TYPE_PARSE = "parse_error"
ERROR_TYPE_CONNECTOR = "connector_error"
ERROR_TYPE_STORAGE = "storage_error"
ERROR_TYPE_EMPTY_SOURCE = "empty_source"
ERROR_TYPE_UNSUPPORTED = "unsupported_source_type"
ERROR_TYPE_UNKNOWN = "unknown_error"

ERROR_TYPES = {
    ERROR_TYPE_CONFIG,
    ERROR_TYPE_FETCH,
    ERROR_TYPE_PARSE,
    ERROR_TYPE_CONNECTOR,
    ERROR_TYPE_STORAGE,
    ERROR_TYPE_EMPTY_SOURCE,
    ERROR_TYPE_UNSUPPORTED,
    ERROR_TYPE_UNKNOWN,
}

# Filing status（NormalizedFiling.status）
FILING_STATUS_SAVED = "saved"
FILING_STATUS_DUPLICATE = "duplicate"
FILING_STATUS_PARTIAL = "partial"
FILING_STATUS_FAILED = "failed"
FILING_STATUS_SKIPPED = "skipped"

FILING_STATUSES = {
    FILING_STATUS_SAVED,
    FILING_STATUS_DUPLICATE,
    FILING_STATUS_PARTIAL,
    FILING_STATUS_FAILED,
    FILING_STATUS_SKIPPED,
}

# extraction_quality 合法取值
EXTRACTION_QUALITY_HIGH = "high"
EXTRACTION_QUALITY_MEDIUM = "medium"
EXTRACTION_QUALITY_LOW = "low"
EXTRACTION_QUALITY_EMPTY = "empty"
EXTRACTION_QUALITY_UNKNOWN = "unknown"

EXTRACTION_QUALITIES = {
    EXTRACTION_QUALITY_HIGH,
    EXTRACTION_QUALITY_MEDIUM,
    EXTRACTION_QUALITY_LOW,
    EXTRACTION_QUALITY_EMPTY,
    EXTRACTION_QUALITY_UNKNOWN,
}


# ---------------------------------------------------------------------------
# 默认参数与配置
# ---------------------------------------------------------------------------


class FilingDefaults(BaseModel):
    """运行默认参数。

    字段说明（小白解读）：
        fetch_timeout_seconds:  抓取的超时秒数
        max_items_per_source:   每个 source 一次最多处理多少条候选
        save_raw:               是否保存原始响应
        save_html:              是否保存 HTML
        save_pdf_metadata:    是否保存 PDF 元数据
        download_pdfs:          是否下载 PDF 文件（默认 false，只存 URL）
        user_agent:             HTTP 请求 User-Agent
    """

    fetch_timeout_seconds: int = 30
    max_items_per_source: int = 20
    save_raw: bool = True
    save_html: bool = True
    save_pdf_metadata: bool = True
    download_pdfs: bool = False
    user_agent: str = "Mozilla/5.0 (compatible; opc-foundation-filings/0.1)"


class FilingSourceConfig(BaseModel):
    """一个官方披露源的配置。

    字段说明（小白解读）：
        source_id:      稳定唯一 ID
        source_name:    人类可读名称
        source_type:    sec_edgar / cninfo_announcement / hkex_announcement
        market:         市场（US / CN / HK 等）
        jurisdiction:   司法辖区（US / CN / HK 等）
        base_url:       基础 URL
        endpoint_url:  API 端点或列表页 URL
        enabled:        是否启用
        legal_profile:  合规档案
        fetch_profile:  抓取参数 profile 名
        max_items:      覆盖 defaults.max_items_per_source
        filing_types:   要抓取的披露类型过滤（空列表表示全部）
        issuer_filter:  披露方过滤（CIK 列表、股票代码列表等，空表示全部）
        date_from:     起始日期（YYYY-MM-DD，可选）
        date_to:       结束日期（YYYY-MM-DD，可选）
        save_raw:      覆盖 defaults.save_raw
        save_html:     覆盖 defaults.save_html
        save_pdf_metadata: 覆盖 defaults.save_pdf_metadata
        download_pdfs: 覆盖 defaults.download_pdfs
    """

    source_id: str
    source_name: str
    source_type: str
    market: str | None = None
    jurisdiction: str | None = None

    base_url: str | None = None
    endpoint_url: str | None = None

    enabled: bool = True

    legal_profile: str = LEGAL_PROFILE_UNKNOWN
    fetch_profile: str = "default"

    max_items: int | None = None
    filing_types: list[str] = Field(default_factory=list)
    issuer_filter: list[str] = Field(default_factory=list)

    date_from: str | None = None
    date_to: str | None = None

    save_raw: bool | None = None
    save_html: bool | None = None
    save_pdf_metadata: bool | None = None
    download_pdfs: bool | None = None


class FilingArchiveConfig(BaseModel):
    """一次运行的完整配置。

    字段说明（小白解读）：
        archive_root: 归档根目录
        defaults:     默认参数
        sources:      信息源列表
        raw:          原始配置 dict（方便下游读取额外字段）
    """

    archive_root: str
    defaults: FilingDefaults = Field(default_factory=FilingDefaults)
    sources: list[FilingSourceConfig] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# 候选披露
# ---------------------------------------------------------------------------


class FilingCandidate(BaseModel):
    """Connector 输出的候选披露。

    可能来自 SEC submissions JSON、CNINFO 公告列表、HKEX 公告列表等。

    字段说明（小白解读）：
        source_id:       所属 source
        source_type:    source 类型
        market:         市场
        jurisdiction:   司法辖区
        issuer_name:    披露方名称（公司名）
        issuer_code:    披露方代码（CIK / 股票代码等，foundation 不解释投资含义）
        filing_type:     披露类型（10-K / 年度报告 / 年报 等）
        filing_title:   披露标题
        filing_date:   披露日期（YYYY-MM-DD）
        announcement_id: 公告 ID（CNINFO/HKEX 用）
        accession_number:  SEC accession number（SEC 用）
        source_url:    列表页 / API URL
        document_url:  文档详情页 URL
        pdf_url:       PDF 文件 URL
        html_url:      HTML 版本 URL
        raw_entry:    原始条目（便于调试/二次处理）
        discovered_at: 发现时间（ISO 字符串）
    """

    source_id: str
    source_type: str
    market: str | None = None
    jurisdiction: str | None = None

    issuer_name: str | None = None
    issuer_code: str | None = None

    filing_type: str | None = None
    filing_title: str | None = None
    filing_date: str | None = None

    announcement_id: str | None = None
    accession_number: str | None = None

    source_url: str | None = None
    document_url: str | None = None
    pdf_url: str | None = None
    html_url: str | None = None

    raw_entry: dict[str, Any] = Field(default_factory=dict)
    discovered_at: str | None = None


# ---------------------------------------------------------------------------
# 归档后的标准披露
# ---------------------------------------------------------------------------


class NormalizedFiling(BaseModel):
    """归档后的标准披露模型，是 Official Filing Foundation 最核心输出。

    每条披露都会写一条到 filings.jsonl。

    status 取值（小白解读）：
        saved      - 成功保存元数据、原始响应等
        duplicate  - 已在之前运行中被保存
        partial    - 部分字段缺失，但仍保存了可用信息
        failed     - 抓取或写入过程中出错（进入 failed queue）
        skipped    - 被跳过（如 disabled source）

    canonical_key 生成规则：
        source_type + issuer_code + filing_date + filing_type + document_url/accession_number/announcement_id
        用于去重判断同一份披露
    """

    filing_id: str

    source_id: str
    source_type: str
    market: str | None = None
    jurisdiction: str | None = None

    issuer_name: str | None = None
    issuer_code: str | None = None

    filing_type: str | None = None
    filing_title: str | None = None
    filing_date: str | None = None

    source_url: str | None = None
    document_url: str | None = None
    pdf_url: str | None = None
    html_url: str | None = None

    content_hash: str
    canonical_key: str

    raw_path: str | None = None
    html_path: str | None = None
    pdf_metadata_path: str | None = None
    metadata_path: str

    extraction_quality: str = EXTRACTION_QUALITY_UNKNOWN
    status: str = FILING_STATUS_SAVED

    created_at: str
    updated_at: str | None = None

    raw_entry: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


# ---------------------------------------------------------------------------
# 失败队列
# ---------------------------------------------------------------------------


class FailedFiling(BaseModel):
    """失败队列条目。

    记录足够多的信息，便于 retry-failed 命令重跑。

    字段说明（小白解读）：
        source_id:       所属 source
        source_type:    source 类型
        filing_title:   披露标题（可能为空）
        document_url: 文档 URL（用于重试）
        canonical_key:  规范化 key（用于去重）
        failed_at:     失败时间（ISO 字符串）
        error:         错误信息
        error_type:   标准化错误类型
        retryable:     是否可重试
        retry_count: 已重试次数
        run_id:       失败时所属的运行 ID
        raw_entry:    原始条目（便于调试，不记录正文/secrets）
    """

    source_id: str
    source_type: str
    filing_title: str | None = None
    document_url: str | None = None
    canonical_key: str | None = None
    failed_at: str
    error: str
    error_type: str | None = None
    retryable: bool = True
    retry_count: int = 0
    run_id: str | None = None
    raw_entry: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# 源健康与运行结果
# ---------------------------------------------------------------------------


class FilingSourceHealth(BaseModel):
    """源健康状态。

    status 取值（小白解读）：
        healthy   - 最近运行成功，且 failed_count_last_run = 0
        degraded  - 能 discover 或部分保存，但存在 partial/failed/warnings
        failed    - connector 失败、fetch 失败、config invalid、连续失败
        disabled  - 配置中 enabled=false
        unknown   - 尚未运行过
    """

    source_id: str
    source_type: str | None = None
    checked_at: str
    status: str

    last_success_at: str | None = None
    last_failure_at: str | None = None
    consecutive_failures: int = 0
    last_error: str | None = None
    last_error_type: str | None = None

    candidate_count_last_run: int = 0
    saved_count_last_run: int = 0
    duplicate_count_last_run: int = 0
    partial_count_last_run: int = 0
    failed_count_last_run: int = 0

    last_run_id: str | None = None
    last_report_path: str | None = None


class FilingRunResult(BaseModel):
    """一次完整运行的汇总结果，用于 CLI 输出和日报生成。"""

    run_id: str
    mode: str
    archive_root: str
    started_at: str
    finished_at: str

    source_count: int = 0
    enabled_source_count: int = 0

    candidate_count: int = 0
    saved_count: int = 0
    duplicate_count: int = 0
    partial_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0

    source_stats: list[dict[str, Any]] = Field(default_factory=list)
    saved_filings: list[NormalizedFiling] = Field(default_factory=list)
    failed_filings: list[FailedFiling] = Field(default_factory=list)
    source_health: list[FilingSourceHealth] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    report_path: str | None = None
    exit_code: int = 0
