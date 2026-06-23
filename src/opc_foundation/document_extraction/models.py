"""Document Extraction Foundation 的数据模型。

功能说明（小白解读）：
    本文件定义 Document Extraction Foundation 用到的核心数据结构：
    - SourceType         文档来源类型（本地文件/官方披露PDF/IR演示/公开报告等）
    - LegalProfile       合规档案（用户提供的/官方公开的/公开IR/未知）
    - ExtractionStatus   抽取状态（成功/部分/失败/跳过）
    - ExtractionQuality  抽取质量（高/中/低/空/失败）
    - HealthStatus       健康状态（健康/降级/失败/禁用/未知）
    - DocumentExtractionConfig   单个文档源的配置
    - DocumentArchiveConfig      一次运行的完整配置
    - DocumentCandidate          待抽取的文档候选
    - ExtractedDocument          抽取后的标准文档（核心输出）
    - DocumentExtractionHealth   源健康状态
    - DocumentExtractionRunResult 运行结果汇总

所有模型用 pydantic BaseModel 实现，与 official_filings / research 模块风格一致。

注意：
    这些模型里绝对不包含任何投资判断字段。
    document_hash 只是文件的 SHA256，foundation 不解释其投资含义。
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 枚举常量（用字符串枚举，避免引入额外依赖）
# ---------------------------------------------------------------------------

# source_type 合法取值
SOURCE_TYPE_LOCAL_DOCUMENT = "local_document"
SOURCE_TYPE_OFFICIAL_FILING_PDF = "official_filing_pdf"
SOURCE_TYPE_IR_PRESENTATION = "ir_presentation"
SOURCE_TYPE_PUBLIC_REPORT = "public_report"
SOURCE_TYPE_POLICY_DOCUMENT = "policy_document"
SOURCE_TYPE_UNKNOWN = "unknown"

IMPLEMENTED_SOURCE_TYPES = {
    SOURCE_TYPE_LOCAL_DOCUMENT,
    SOURCE_TYPE_OFFICIAL_FILING_PDF,
    SOURCE_TYPE_IR_PRESENTATION,
    SOURCE_TYPE_PUBLIC_REPORT,
    SOURCE_TYPE_POLICY_DOCUMENT,
    SOURCE_TYPE_UNKNOWN,
}

# legal_profile 合法取值
LEGAL_PROFILE_USER_PROVIDED = "user_provided"
LEGAL_PROFILE_OFFICIAL_PUBLIC = "official_public"
LEGAL_PROFILE_PUBLIC_IR = "public_ir"
LEGAL_PROFILE_UNKNOWN = "unknown"

LEGAL_PROFILES = {
    LEGAL_PROFILE_USER_PROVIDED,
    LEGAL_PROFILE_OFFICIAL_PUBLIC,
    LEGAL_PROFILE_PUBLIC_IR,
    LEGAL_PROFILE_UNKNOWN,
}

# extraction_status 合法取值
EXTRACTION_STATUS_SUCCESS = "success"
EXTRACTION_STATUS_PARTIAL = "partial"
EXTRACTION_STATUS_FAILED = "failed"
EXTRACTION_STATUS_SKIPPED = "skipped"

EXTRACTION_STATUSES = {
    EXTRACTION_STATUS_SUCCESS,
    EXTRACTION_STATUS_PARTIAL,
    EXTRACTION_STATUS_FAILED,
    EXTRACTION_STATUS_SKIPPED,
}

# extraction_quality 合法取值
EXTRACTION_QUALITY_HIGH = "high"
EXTRACTION_QUALITY_MEDIUM = "medium"
EXTRACTION_QUALITY_LOW = "low"
EXTRACTION_QUALITY_EMPTY = "empty"
EXTRACTION_QUALITY_FAILED = "failed"

EXTRACTION_QUALITIES = {
    EXTRACTION_QUALITY_HIGH,
    EXTRACTION_QUALITY_MEDIUM,
    EXTRACTION_QUALITY_LOW,
    EXTRACTION_QUALITY_EMPTY,
    EXTRACTION_QUALITY_FAILED,
}

# health_status 合法取值
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
ERROR_TYPE_READ = "read_error"
ERROR_TYPE_PARSE = "parse_error"
ERROR_TYPE_EXTRACTOR = "extractor_error"
ERROR_TYPE_STORAGE = "storage_error"
ERROR_TYPE_EMPTY_SOURCE = "empty_source"
ERROR_TYPE_UNSUPPORTED = "unsupported_source_type"
ERROR_TYPE_UNKNOWN = "unknown_error"

ERROR_TYPES = {
    ERROR_TYPE_CONFIG,
    ERROR_TYPE_READ,
    ERROR_TYPE_PARSE,
    ERROR_TYPE_EXTRACTOR,
    ERROR_TYPE_STORAGE,
    ERROR_TYPE_EMPTY_SOURCE,
    ERROR_TYPE_UNSUPPORTED,
    ERROR_TYPE_UNKNOWN,
}

# 文件扩展名到 source_type 的默认映射
EXTENSION_TO_SOURCE_TYPE = {
    ".pdf": SOURCE_TYPE_OFFICIAL_FILING_PDF,
    ".html": SOURCE_TYPE_PUBLIC_REPORT,
    ".htm": SOURCE_TYPE_PUBLIC_REPORT,
    ".txt": SOURCE_TYPE_LOCAL_DOCUMENT,
    ".md": SOURCE_TYPE_LOCAL_DOCUMENT,
    ".markdown": SOURCE_TYPE_LOCAL_DOCUMENT,
}

# MIME type 映射
MIME_TYPE_TO_EXTENSION = {
    "application/pdf": ".pdf",
    "text/html": ".html",
    "text/plain": ".txt",
    "text/markdown": ".md",
}


# ---------------------------------------------------------------------------
# 默认参数与配置
# ---------------------------------------------------------------------------


class DocumentExtractionDefaults(BaseModel):
    """运行默认参数。

    字段说明（小白解读）：
        max_documents:       一次最多处理多少个文档
        save_raw:            是否保存原始文件
        save_markdown:       是否保存 markdown 版本
        save_metadata:       是否保存元数据
        extract_text:         是否提取文本
        extract_tables:       是否提取表格（默认 false，OCR 关闭）
        ocr_enabled:         是否启用 OCR（默认 false，本阶段不实现）
    """

    max_documents: int = 20
    save_raw: bool = True
    save_markdown: bool = True
    save_metadata: bool = True
    extract_text: bool = True
    extract_tables: bool = False
    ocr_enabled: bool = False


class DocumentExtractionConfig(BaseModel):
    """一个文档源的配置。

    字段说明（小白解读）：
        source_id:      稳定唯一 ID
        source_name:    人类可读名称
        source_type:    文档类型
        input_path:     输入目录路径
        input_glob:     文件匹配模式（如 "*.pdf"）
        enabled:        是否启用
        legal_profile:  合规档案
        document_type:  文档类型（可覆盖 source_type）
        max_documents:  覆盖 defaults.max_documents
        save_raw:       覆盖 defaults.save_raw
        save_markdown:  覆盖 defaults.save_markdown
        save_metadata:  覆盖 defaults.save_metadata
        extract_text:    覆盖 defaults.extract_text
        extract_tables:  覆盖 defaults.extract_tables
        ocr_enabled:     覆盖 defaults.ocr_enabled（默认 false）
    """

    source_id: str
    source_name: str
    source_type: str = SOURCE_TYPE_LOCAL_DOCUMENT

    input_path: str | None = None
    input_glob: str = "*"

    enabled: bool = True
    legal_profile: str = LEGAL_PROFILE_UNKNOWN
    document_type: str | None = None

    max_documents: int | None = None
    save_raw: bool | None = None
    save_markdown: bool | None = None
    save_metadata: bool | None = None
    extract_text: bool | None = None
    extract_tables: bool | None = None
    ocr_enabled: bool | None = None


class DocumentArchiveConfig(BaseModel):
    """一次运行的完整配置。

    字段说明（小白解读）：
        archive_root:  归档根目录
        defaults:     默认参数
        sources:      文档源列表
        raw:         原始配置 dict（方便下游读取额外字段）
    """

    archive_root: str
    defaults: DocumentExtractionDefaults = Field(default_factory=DocumentExtractionDefaults)
    sources: list[DocumentExtractionConfig] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# 候选文档
# ---------------------------------------------------------------------------


class DocumentCandidate(BaseModel):
    """待抽取的文档候选。

    可能来自本地文件扫描、URL 列表等。

    字段说明（小白解读）：
        source_id:        所属 source
        source_type:     文档类型
        document_path:   本地文件路径（绝对或相对路径）
        document_url:    文档 URL（如果有）
        document_title:  文档标题（可从文件名或 URL 推断）
        document_type:   文档类型（可覆盖 source_type）
        file_extension:  文件扩展名（如 .pdf）
        mime_type:       MIME 类型（如 application/pdf）
        legal_profile:   合规档案
        raw_entry:      原始条目（便于调试/二次处理）
        discovered_at:  发现时间（ISO 字符串）
    """

    source_id: str
    source_type: str

    document_path: str | None = None
    document_url: str | None = None
    document_title: str | None = None
    document_type: str | None = None

    file_extension: str | None = None
    mime_type: str | None = None
    legal_profile: str = LEGAL_PROFILE_UNKNOWN

    raw_entry: dict[str, Any] = Field(default_factory=dict)
    discovered_at: str | None = None


# ---------------------------------------------------------------------------
# 抽取后的标准文档
# ---------------------------------------------------------------------------


class ExtractedDocument(BaseModel):
    """抽取后的标准文档模型，是 Document Extraction Foundation 最核心输出。

    每条文档都会写一条到 documents.jsonl。

    extraction_status 取值（小白解读）：
        success  - 成功抽取文本/metadata
        partial  - 部分字段缺失（如只有 metadata 没有 text）
        failed   - 抽取过程中出错（进入 failed queue）
        skipped  - 被跳过（如 disabled source、重复文档）

    extraction_quality 取值（小白解读）：
        high     - 文本量大、质量高
        medium   - 文本量中等、质量一般
        low      - 文本量少或质量较低
        empty    - 几乎没有提取到文本
        failed   - 抽取失败

    canonical_key 生成规则：
        source_id + document_hash
        用于去重判断同一份文档
    """

    document_id: str

    source_id: str
    source_type: str

    document_title: str | None = None
    document_type: str | None = None

    original_path: str | None = None
    document_url: str | None = None

    file_extension: str | None = None
    mime_type: str | None = None

    page_count: int | None = None
    char_count: int | None = None
    word_count: int | None = None

    content_hash: str
    document_hash: str

    canonical_key: str

    raw_path: str | None = None
    text_path: str | None = None
    markdown_path: str | None = None
    metadata_path: str | None = None

    extraction_quality: str = EXTRACTION_QUALITY_FAILED
    extraction_status: str = EXTRACTION_STATUS_FAILED

    error_type: str | None = None
    error_message: str | None = None

    created_at: str
    updated_at: str | None = None

    raw_entry: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# 失败队列
# ---------------------------------------------------------------------------


class FailedDocument(BaseModel):
    """失败队列条目。

    记录足够多的信息，便于 retry-failed 命令重跑。

    字段说明（小白解读）：
        source_id:        所属 source
        source_type:     文档类型
        document_title:  文档标题（可能为空）
        original_path:   原始文件路径（用于重试）
        document_url:    文档 URL（用于重试）
        canonical_key:   规范化 key（用于去重）
        failed_at:       失败时间（ISO 字符串）
        error:           错误信息
        error_type:      标准化错误类型
        retryable:       是否可重试
        retry_count:     已重试次数
        run_id:          失败时所属的运行 ID
        raw_entry:       原始条目（便于调试，不记录正文/secrets）
    """

    source_id: str
    source_type: str
    document_title: str | None = None
    original_path: str | None = None
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


class DocumentExtractionHealth(BaseModel):
    """源健康状态。

    status 取值（小白解读）：
        healthy   - 最近运行成功，且 failed_count_last_run = 0
        degraded  - 能 discover 或部分保存，但存在 partial/failed/warnings
        failed    - connector 失败、read 失败、config invalid、连续失败
        disabled  - 配置中 enabled=false
        unknown   - 尚未运行过
    """

    source_id: str
    source_type: str | None = None
    checked_at: str
    status: str

    last_success_at: str | None = None
    last_failure_at: str | None = None
    last_error_type: str | None = None
    last_error: str | None = None
    consecutive_failures: int = 0

    candidate_count_last_run: int = 0
    saved_count_last_run: int = 0
    partial_count_last_run: int = 0
    failed_count_last_run: int = 0
    duplicate_count_last_run: int = 0

    last_run_id: str | None = None
    last_report_path: str | None = None


class DocumentExtractionRunResult(BaseModel):
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
    partial_count: int = 0
    failed_count: int = 0
    duplicate_count: int = 0
    skipped_count: int = 0

    source_stats: list[dict[str, Any]] = Field(default_factory=list)
    saved_documents: list[ExtractedDocument] = Field(default_factory=list)
    failed_documents: list[FailedDocument] = Field(default_factory=list)
    source_health: list[DocumentExtractionHealth] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    report_path: str | None = None
    exit_code: int = 0


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


def compute_document_hash(file_path: str | Path) -> str:
    """计算文件的 SHA256 哈希作为 document_hash。

    功能说明（小白解读）：
        读取文件的全部内容，计算 SHA256 哈希值。
        这个哈希值可以唯一标识文件内容，用于去重。

    参数：
        file_path: 文件路径

    返回：
        SHA256 哈希字符串（十六进制）
    """
    path = Path(file_path)
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_content_hash(text: str) -> str:
    """计算文本内容的 SHA256 哈希作为 content_hash。

    功能说明（小白解读）：
        对提取出来的纯文本内容计算哈希。
        用于判断文档内容是否发生变化。

    参数：
        text: 文本内容

    返回：
        SHA256 哈希字符串（十六进制）
    """
    hasher = hashlib.sha256()
    hasher.update(text.encode("utf-8"))
    return hasher.hexdigest()


def build_canonical_key(source_id: str, document_hash: str) -> str:
    """构建文档的 canonical_key，用于去重判断。

    功能说明（小白解读）：
        将 source_id 和 document_hash 组合成唯一 key。
        同一个 source 中的同一份文件（相同 hash）会被视为重复。

    参数：
        source_id:     源 ID
        document_hash: 文档哈希

    返回：
        组合后的 canonical_key
    """
    return f"{source_id}::{document_hash}"


def infer_source_type_from_path(file_path: str | Path) -> str:
    """根据文件扩展名推断 source_type。

    参数：
        file_path: 文件路径

    返回：
        推断的 source_type，默认为 SOURCE_TYPE_UNKNOWN
    """
    path = Path(file_path)
    ext = path.suffix.lower()
    return EXTENSION_TO_SOURCE_TYPE.get(ext, SOURCE_TYPE_UNKNOWN)


def infer_mime_type(file_path: str | Path) -> str | None:
    """根据文件扩展名推断 MIME type。

    参数：
        file_path: 文件路径

    返回：
        推断的 MIME type，如果未知则返回 None
    """
    path = Path(file_path)
    ext = path.suffix.lower()

    # 常见 MIME type 映射
    mime_map = {
        ".pdf": "application/pdf",
        ".html": "text/html",
        ".htm": "text/html",
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".markdown": "text/markdown",
    }
    return mime_map.get(ext)
