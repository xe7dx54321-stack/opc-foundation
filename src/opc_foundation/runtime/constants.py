"""Runtime 共享常量。

功能说明（小白解读）：
    定义所有 foundation 模块通用的文件名和目录名常量。
    比如 index 目录叫什么、source_health 文件叫什么。
    这样所有模块用统一的命名，下游系统也好找文件。

注意：
    Research 和 Document Extraction 都用 documents.jsonl；
    Official Filing 用 filings.jsonl；
    不要强行统一成一个名字。
"""
from __future__ import annotations

# 标准目录名
STANDARD_INDEX_DIR = "index"
STANDARD_REPORTS_DIR = "reports"

# 标准索引文件名
SOURCE_HEALTH_FILE = "source_health.jsonl"
FAILED_QUEUE_FILE = "failed_queue.jsonl"
RUN_LOG_FILE = "run_log.jsonl"

# 主索引文件名（不同模块可能不同）
DOCUMENTS_INDEX_FILE = "documents.jsonl"
DOCUMENTS_LATEST_FILE = "documents.latest.jsonl"
FILINGS_INDEX_FILE = "filings.jsonl"
FILINGS_LATEST_FILE = "filings.latest.jsonl"

# 标准 CLI 命令
STANDARD_COMMANDS = [
    "validate-config",
    "dry-run",
    "run",
    "source-health",
    "report",
    "retry-failed",
]
