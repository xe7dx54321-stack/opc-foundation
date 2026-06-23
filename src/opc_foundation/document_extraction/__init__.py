"""Document Extraction Foundation Module.

本模块提供通用公开文档抽取能力，用于服务：
- CNINFO 公告 PDF
- HKEX 公告 PDF metadata
- SEC filing exhibits
- 公司 IR presentation
- 公开白皮书
- 公开行业报告
- 公开政策文件
- 本地用户提供文档

核心原则：
- Foundation 提供基础设施
- 业务系统保留判断力

禁止：
- 不做 OCR
- 不做投资判断
- 不访问真实外部网站
- 不下载远程 PDF
"""

from .models import (
    # 枚举常量
    SOURCE_TYPE_LOCAL_DOCUMENT,
    SOURCE_TYPE_OFFICIAL_FILING_PDF,
    SOURCE_TYPE_IR_PRESENTATION,
    SOURCE_TYPE_PUBLIC_REPORT,
    SOURCE_TYPE_POLICY_DOCUMENT,
    SOURCE_TYPE_UNKNOWN,
    IMPLEMENTED_SOURCE_TYPES,
    LEGAL_PROFILE_USER_PROVIDED,
    LEGAL_PROFILE_OFFICIAL_PUBLIC,
    LEGAL_PROFILE_PUBLIC_IR,
    LEGAL_PROFILE_UNKNOWN,
    LEGAL_PROFILES,
    EXTRACTION_STATUS_SUCCESS,
    EXTRACTION_STATUS_PARTIAL,
    EXTRACTION_STATUS_FAILED,
    EXTRACTION_STATUS_SKIPPED,
    EXTRACTION_STATUSES,
    EXTRACTION_QUALITY_HIGH,
    EXTRACTION_QUALITY_MEDIUM,
    EXTRACTION_QUALITY_LOW,
    EXTRACTION_QUALITY_EMPTY,
    EXTRACTION_QUALITY_FAILED,
    EXTRACTION_QUALITIES,
    HEALTH_STATUS_HEALTHY,
    HEALTH_STATUS_DEGRADED,
    HEALTH_STATUS_FAILED,
    HEALTH_STATUS_DISABLED,
    HEALTH_STATUS_UNKNOWN,
    HEALTH_STATUSES,
    ERROR_TYPE_CONFIG,
    ERROR_TYPE_READ,
    ERROR_TYPE_PARSE,
    ERROR_TYPE_EXTRACTOR,
    ERROR_TYPE_STORAGE,
    ERROR_TYPE_EMPTY_SOURCE,
    ERROR_TYPE_UNSUPPORTED,
    ERROR_TYPE_UNKNOWN,
    ERROR_TYPES,
    # 模型
    DocumentExtractionDefaults,
    DocumentExtractionConfig,
    DocumentArchiveConfig,
    DocumentCandidate,
    ExtractedDocument,
    FailedDocument,
    DocumentExtractionHealth,
    DocumentExtractionRunResult,
    # 辅助函数
    compute_document_hash,
    compute_content_hash,
    build_canonical_key,
    infer_source_type_from_path,
    infer_mime_type,
)

from .config import load_config, validate_config
from .archiver import DocumentArchiver

__all__ = [
    # 枚举
    "SOURCE_TYPE_LOCAL_DOCUMENT",
    "SOURCE_TYPE_OFFICIAL_FILING_PDF",
    "SOURCE_TYPE_IR_PRESENTATION",
    "SOURCE_TYPE_PUBLIC_REPORT",
    "SOURCE_TYPE_POLICY_DOCUMENT",
    "SOURCE_TYPE_UNKNOWN",
    "IMPLEMENTED_SOURCE_TYPES",
    "LEGAL_PROFILE_USER_PROVIDED",
    "LEGAL_PROFILE_OFFICIAL_PUBLIC",
    "LEGAL_PROFILE_PUBLIC_IR",
    "LEGAL_PROFILE_UNKNOWN",
    "LEGAL_PROFILES",
    "EXTRACTION_STATUS_SUCCESS",
    "EXTRACTION_STATUS_PARTIAL",
    "EXTRACTION_STATUS_FAILED",
    "EXTRACTION_STATUS_SKIPPED",
    "EXTRACTION_STATUSES",
    "EXTRACTION_QUALITY_HIGH",
    "EXTRACTION_QUALITY_MEDIUM",
    "EXTRACTION_QUALITY_LOW",
    "EXTRACTION_QUALITY_EMPTY",
    "EXTRACTION_QUALITY_FAILED",
    "EXTRACTION_QUALITIES",
    "HEALTH_STATUS_HEALTHY",
    "HEALTH_STATUS_DEGRADED",
    "HEALTH_STATUS_FAILED",
    "HEALTH_STATUS_DISABLED",
    "HEALTH_STATUS_UNKNOWN",
    "HEALTH_STATUSES",
    "ERROR_TYPE_CONFIG",
    "ERROR_TYPE_READ",
    "ERROR_TYPE_PARSE",
    "ERROR_TYPE_EXTRACTOR",
    "ERROR_TYPE_STORAGE",
    "ERROR_TYPE_EMPTY_SOURCE",
    "ERROR_TYPE_UNSUPPORTED",
    "ERROR_TYPE_UNKNOWN",
    "ERROR_TYPES",
    # 模型
    "DocumentExtractionDefaults",
    "DocumentExtractionConfig",
    "DocumentArchiveConfig",
    "DocumentCandidate",
    "ExtractedDocument",
    "FailedDocument",
    "DocumentExtractionHealth",
    "DocumentExtractionRunResult",
    # 辅助函数
    "compute_document_hash",
    "compute_content_hash",
    "build_canonical_key",
    "infer_source_type_from_path",
    "infer_mime_type",
    # 配置和归档
    "load_config",
    "validate_config",
    "DocumentArchiver",
]
