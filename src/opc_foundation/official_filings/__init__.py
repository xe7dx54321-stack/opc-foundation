"""Official Filing Foundation 模块。

功能说明（小白解读）：
    本模块提供官方披露/公告归档的基础设施能力。
    支持 SEC EDGAR、CNINFO 巨潮资讯、HKEXnews 港交所披露易 等官方公开披露源。
    只做归档和元数据整理，不做投资判断。

核心能力：
    - 多源官方披露发现（discover）
    - 标准化元数据模型
    - 本地归档存储（raw/html/pdf_metadata）
    - 去重（canonical_key / content_hash）
    - Source Health 监控
    - Failed Queue 失败重试
    - 日报生成
    - CLI 命令行工具

边界：
    - 不做投资判断
    - 不做 ticker impact
    - 不做利好/利空判断
    - 不下载需要授权的文件
"""
from __future__ import annotations

from .models import (
    FilingCandidate,
    FilingDefaults,
    FilingRunResult,
    FilingSourceConfig,
    FilingSourceHealth,
    NormalizedFiling,
    FailedFiling,
)
from .config import (
    FilingArchiveConfig,
    FilingConfigError,
    load_filing_config,
    validate_filing_config,
)

__all__ = [
    "FilingCandidate",
    "FilingDefaults",
    "FilingRunResult",
    "FilingSourceConfig",
    "FilingSourceHealth",
    "NormalizedFiling",
    "FailedFiling",
    "FilingArchiveConfig",
    "FilingConfigError",
    "load_filing_config",
    "validate_filing_config",
]
