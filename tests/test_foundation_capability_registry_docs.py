"""Foundation Capability Registry 文档测试。

覆盖：
1. docs/foundation_capability_registry.md exists
2. docs/foundation_readiness_summary.md exists
3. registry contains Research Source Foundation
4. registry contains Official Filing Foundation
5. registry contains Document Extraction Foundation
6. registry contains Production Trial Ready
7. registry contains documents.jsonl
8. registry contains filings.jsonl
9. registry contains forbidden business fields
10. registry mentions HKEX degraded / client-side rendering
11. readiness summary contains all three tracks
12. readiness summary says market_data / market_flow not ready yet
13. readiness summary says foundation is not investment decision system
14. source_migration doc links capability registry
15. research_source_foundation doc links capability registry
16. official_filing readiness doc links capability registry
17. document_extraction readiness doc links capability registry
"""
from __future__ import annotations

from pathlib import Path


# 路径常量
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = PROJECT_ROOT / "docs"

REGISTRY_DOC = DOCS_DIR / "foundation_capability_registry.md"
READINESS_DOC = DOCS_DIR / "foundation_readiness_summary.md"
MIGRATION_DOC = DOCS_DIR / "source_migration_from_th_capital_stock.md"
RESEARCH_FOUNDATION_DOC = DOCS_DIR / "research_source_foundation.md"
OFFICIAL_FILING_READINESS_DOC = DOCS_DIR / "official_filing_production_readiness.md"
DOC_EXT_READINESS_DOC = DOCS_DIR / "document_extraction_production_readiness.md"


# ---------------------------------------------------------------------------
# 1. 文档存在性
# ---------------------------------------------------------------------------


def test_capability_registry_doc_exists() -> None:
    """foundation_capability_registry.md 必须存在。"""
    assert REGISTRY_DOC.exists(), f"文档不存在: {REGISTRY_DOC}"


def test_readiness_summary_doc_exists() -> None:
    """foundation_readiness_summary.md 必须存在。"""
    assert READINESS_DOC.exists(), f"文档不存在: {READINESS_DOC}"


# ---------------------------------------------------------------------------
# 2. Registry 文档内容
# ---------------------------------------------------------------------------


def test_registry_contains_research_source_foundation() -> None:
    """registry 必须包含 Research Source Foundation。"""
    content = REGISTRY_DOC.read_text(encoding="utf-8")
    assert "Research Source Foundation" in content, (
        "registry 缺少 Research Source Foundation"
    )


def test_registry_contains_official_filing_foundation() -> None:
    """registry 必须包含 Official Filing Foundation。"""
    content = REGISTRY_DOC.read_text(encoding="utf-8")
    assert "Official Filing Foundation" in content, (
        "registry 缺少 Official Filing Foundation"
    )


def test_registry_contains_document_extraction_foundation() -> None:
    """registry 必须包含 Document Extraction Foundation。"""
    content = REGISTRY_DOC.read_text(encoding="utf-8")
    assert "Document Extraction Foundation" in content, (
        "registry 缺少 Document Extraction Foundation"
    )


def test_registry_contains_production_trial_ready() -> None:
    """registry 必须包含 Production Trial Ready。"""
    content = REGISTRY_DOC.read_text(encoding="utf-8")
    assert "Production Trial Ready" in content, (
        "registry 缺少 Production Trial Ready"
    )


def test_registry_contains_documents_jsonl() -> None:
    """registry 必须包含 documents.jsonl。"""
    content = REGISTRY_DOC.read_text(encoding="utf-8")
    assert "documents.jsonl" in content, "registry 缺少 documents.jsonl"


def test_registry_contains_filings_jsonl() -> None:
    """registry 必须包含 filings.jsonl。"""
    content = REGISTRY_DOC.read_text(encoding="utf-8")
    assert "filings.jsonl" in content, "registry 缺少 filings.jsonl"


def test_registry_contains_forbidden_business_fields() -> None:
    """registry 必须包含禁止业务字段列表。"""
    content = REGISTRY_DOC.read_text(encoding="utf-8")
    forbidden_fields = [
        "investment_rating",
        "trade_signal",
        "target_price",
        "risk_score",
        "opportunity_score",
    ]
    for field in forbidden_fields:
        assert field in content, f"registry 缺少禁止字段: {field}"


def test_registry_mentions_hkex_degraded() -> None:
    """registry 必须提到 HKEX degraded / client-side rendering。"""
    content = REGISTRY_DOC.read_text(encoding="utf-8")
    assert "HKEX" in content, "registry 缺少 HKEX 说明"
    assert (
        "degraded" in content.lower()
        or "client-side" in content.lower()
        or "client side" in content.lower()
    ), "registry 应提到 HKEX degraded 或 client-side rendering"


# ---------------------------------------------------------------------------
# 3. Readiness Summary 文档内容
# ---------------------------------------------------------------------------


def test_readiness_contains_all_three_tracks() -> None:
    """readiness summary 必须包含全部三条主线。"""
    content = READINESS_DOC.read_text(encoding="utf-8")
    assert "Research Source Foundation" in content, (
        "readiness 缺少 Research Source Foundation"
    )
    assert "Official Filing Foundation" in content, (
        "readiness 缺少 Official Filing Foundation"
    )
    assert "Document Extraction Foundation" in content, (
        "readiness 缺少 Document Extraction Foundation"
    )


def test_readiness_says_market_data_not_ready() -> None:
    """readiness summary 必须说明 market_data / market_flow 尚未就绪。"""
    content = READINESS_DOC.read_text(encoding="utf-8")
    assert "market_data" in content or "market data" in content.lower(), (
        "readiness 应提到 market_data"
    )
    assert "market_flow" in content or "market flow" in content.lower(), (
        "readiness 应提到 market_flow"
    )
    assert (
        "not ready" in content.lower()
        or "not implemented" in content.lower()
        or "out of scope" in content.lower()
        or "尚未实现" in content
        or "不在范围内" in content
    ), "readiness 应说明 market_data/market_flow 尚未就绪或不在范围内"


def test_readiness_says_not_investment_system() -> None:
    """readiness summary 必须明确 foundation 不是投资决策系统。"""
    content = READINESS_DOC.read_text(encoding="utf-8")
    assert (
        "not a business judgment" in content.lower()
        or "not an investment decision system" in content.lower()
        or "investment decision system" in content.lower()
        or "投资决策" in content
    ), "readiness 应明确 foundation 不是投资决策系统"


# ---------------------------------------------------------------------------
# 4. 现有文档的链接更新
# ---------------------------------------------------------------------------


def test_migration_doc_links_capability_registry() -> None:
    """source_migration 文档应链接到 capability registry。"""
    content = MIGRATION_DOC.read_text(encoding="utf-8")
    assert "foundation_capability_registry.md" in content, (
        "source_migration 文档应链接到 foundation_capability_registry.md"
    )
    assert "foundation_readiness_summary.md" in content, (
        "source_migration 文档应链接到 foundation_readiness_summary.md"
    )


def test_research_foundation_doc_links_registry() -> None:
    """research_source_foundation 文档应链接到 capability registry。"""
    content = RESEARCH_FOUNDATION_DOC.read_text(encoding="utf-8")
    assert "foundation_capability_registry.md" in content, (
        "research_source_foundation 文档应链接到 capability registry"
    )


def test_official_filing_readiness_links_registry() -> None:
    """official_filing readiness 文档应链接到 capability registry。"""
    content = OFFICIAL_FILING_READINESS_DOC.read_text(encoding="utf-8")
    assert "foundation_capability_registry.md" in content, (
        "official_filing readiness 文档应链接到 capability registry"
    )


def test_doc_ext_readiness_links_registry() -> None:
    """document_extraction readiness 文档应链接到 capability registry。"""
    content = DOC_EXT_READINESS_DOC.read_text(encoding="utf-8")
    assert "foundation_capability_registry.md" in content, (
        "document_extraction readiness 文档应链接到 capability registry"
    )


# ---------------------------------------------------------------------------
# 5. Registry 包含下游消费契约说明
# ---------------------------------------------------------------------------


def test_registry_contains_downstream_contract() -> None:
    """registry 必须包含下游消费契约说明。"""
    content = REGISTRY_DOC.read_text(encoding="utf-8")
    assert (
        "downstream" in content.lower()
        or "下游" in content
        or "consumption" in content.lower()
    ), "registry 应包含下游消费契约说明"
    assert "latest.jsonl" in content, (
        "registry 应提到 latest.jsonl 作为下游入口"
    )


# ---------------------------------------------------------------------------
# 6. Registry 包含 shared operating capabilities
# ---------------------------------------------------------------------------


def test_registry_contains_shared_operations() -> None:
    """registry 必须包含共享操作能力说明。"""
    content = REGISTRY_DOC.read_text(encoding="utf-8")
    assert "validate-config" in content, "registry 应提到 validate-config"
    assert "dry-run" in content, "registry 应提到 dry-run"
    assert "source-health" in content, "registry 应提到 source-health"
    assert "failed_queue" in content, "registry 应提到 failed_queue"
