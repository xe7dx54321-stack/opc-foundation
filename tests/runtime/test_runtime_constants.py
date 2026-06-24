"""Runtime constants 测试。

覆盖：
1. standard command constants include validate-config/dry-run/run/source-health/report/retry-failed
2. standard index dir name
3. standard file names
4. documents vs filings file names
"""
from __future__ import annotations

from opc_foundation.runtime.constants import (
    DOCUMENTS_INDEX_FILE,
    DOCUMENTS_LATEST_FILE,
    FAILED_QUEUE_FILE,
    FILINGS_INDEX_FILE,
    FILINGS_LATEST_FILE,
    RUN_LOG_FILE,
    SOURCE_HEALTH_FILE,
    STANDARD_COMMANDS,
    STANDARD_INDEX_DIR,
    STANDARD_REPORTS_DIR,
)


def test_standard_commands_include_all() -> None:
    """STANDARD_COMMANDS 必须包含全部 6 个标准命令。"""
    expected = {
        "validate-config",
        "dry-run",
        "run",
        "source-health",
        "report",
        "retry-failed",
    }
    assert set(STANDARD_COMMANDS) == expected


def test_standard_index_dir() -> None:
    """STANDARD_INDEX_DIR 必须是 'index'。"""
    assert STANDARD_INDEX_DIR == "index"


def test_standard_reports_dir() -> None:
    """STANDARD_REPORTS_DIR 必须是 'reports'。"""
    assert STANDARD_REPORTS_DIR == "reports"


def test_source_health_file() -> None:
    """SOURCE_HEALTH_FILE 必须是 'source_health.jsonl'。"""
    assert SOURCE_HEALTH_FILE == "source_health.jsonl"


def test_failed_queue_file() -> None:
    """FAILED_QUEUE_FILE 必须是 'failed_queue.jsonl'。"""
    assert FAILED_QUEUE_FILE == "failed_queue.jsonl"


def test_run_log_file() -> None:
    """RUN_LOG_FILE 必须是 'run_log.jsonl'。"""
    assert RUN_LOG_FILE == "run_log.jsonl"


def test_documents_index_file() -> None:
    """DOCUMENTS_INDEX_FILE 必须是 'documents.jsonl'。"""
    assert DOCUMENTS_INDEX_FILE == "documents.jsonl"


def test_documents_latest_file() -> None:
    """DOCUMENTS_LATEST_FILE 必须是 'documents.latest.jsonl'。"""
    assert DOCUMENTS_LATEST_FILE == "documents.latest.jsonl"


def test_filings_index_file() -> None:
    """FILINGS_INDEX_FILE 必须是 'filings.jsonl'。"""
    assert FILINGS_INDEX_FILE == "filings.jsonl"


def test_filings_latest_file() -> None:
    """FILINGS_LATEST_FILE 必须是 'filings.latest.jsonl'。"""
    assert FILINGS_LATEST_FILE == "filings.latest.jsonl"


def test_documents_and_filings_not_same() -> None:
    """documents.jsonl 和 filings.jsonl 不应相同。"""
    assert DOCUMENTS_INDEX_FILE != FILINGS_INDEX_FILE
    assert DOCUMENTS_LATEST_FILE != FILINGS_LATEST_FILE
