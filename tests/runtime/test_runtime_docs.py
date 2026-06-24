"""Runtime 文档测试。

覆盖：
1. runtime docs exist
2. runtime docs mention standard commands
3. runtime docs mention forbidden fields
4. runtime output contract docs exist
5. capability registry mentions Shared Runtime Foundation
6. readiness summary mentions Shared Runtime Foundation
"""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = PROJECT_ROOT / "docs"

RUNTIME_FOUNDATION_DOC = DOCS_DIR / "runtime_foundation.md"
RUNTIME_CONTRACT_DOC = DOCS_DIR / "runtime_output_contract.md"
CAPABILITY_REGISTRY_DOC = DOCS_DIR / "foundation_capability_registry.md"
READINESS_SUMMARY_DOC = DOCS_DIR / "foundation_readiness_summary.md"


def test_runtime_foundation_doc_exists() -> None:
    """runtime_foundation.md 必须存在。"""
    assert RUNTIME_FOUNDATION_DOC.exists(), f"文档不存在: {RUNTIME_FOUNDATION_DOC}"


def test_runtime_output_contract_doc_exists() -> None:
    """runtime_output_contract.md 必须存在。"""
    assert RUNTIME_CONTRACT_DOC.exists(), f"文档不存在: {RUNTIME_CONTRACT_DOC}"


def test_runtime_foundation_mentions_standard_commands() -> None:
    """runtime_foundation.md 必须提到标准命令。"""
    content = RUNTIME_FOUNDATION_DOC.read_text(encoding="utf-8")
    assert "validate-config" in content
    assert "dry-run" in content
    assert "source-health" in content
    assert "retry-failed" in content


def test_runtime_foundation_mentions_forbidden_fields() -> None:
    """runtime_foundation.md 必须提到禁止字段。"""
    content = RUNTIME_FOUNDATION_DOC.read_text(encoding="utf-8")
    assert "investment_rating" in content or "investment rating" in content.lower()
    assert "trade_signal" in content or "trade signal" in content.lower()


def test_runtime_contract_mentions_standard_files() -> None:
    """runtime_output_contract.md 必须提到标准文件。"""
    content = RUNTIME_CONTRACT_DOC.read_text(encoding="utf-8")
    assert "documents.jsonl" in content
    assert "filings.jsonl" in content
    assert "source_health.jsonl" in content
    assert "failed_queue.jsonl" in content
    assert "run_log.jsonl" in content


def test_runtime_contract_mentions_downstream_rule() -> None:
    """runtime_output_contract.md 必须提到下游消费规则。"""
    content = RUNTIME_CONTRACT_DOC.read_text(encoding="utf-8")
    assert "downstream" in content.lower() or "下游" in content


def test_capability_registry_mentions_shared_runtime() -> None:
    """capability_registry 必须提到 Shared Runtime Foundation。"""
    content = CAPABILITY_REGISTRY_DOC.read_text(encoding="utf-8")
    assert "Shared Runtime" in content or "Runtime Foundation" in content


def test_readiness_summary_mentions_shared_runtime() -> None:
    """readiness_summary 必须提到 Shared Runtime Foundation。"""
    content = READINESS_SUMMARY_DOC.read_text(encoding="utf-8")
    assert "Shared Runtime" in content or "Runtime Foundation" in content


def test_runtime_foundation_mentions_health_semantics() -> None:
    """runtime_foundation.md 必须提到健康状态语义。"""
    content = RUNTIME_FOUNDATION_DOC.read_text(encoding="utf-8")
    assert "healthy" in content.lower()
    assert "degraded" in content.lower()
    assert "empty_source" in content or "empty source" in content.lower()


def test_runtime_foundation_mentions_adoption_policy() -> None:
    """runtime_foundation.md 必须提到迁移策略。"""
    content = RUNTIME_FOUNDATION_DOC.read_text(encoding="utf-8")
    assert "adoption" in content.lower() or "迁移" in content or "migration" in content.lower()
