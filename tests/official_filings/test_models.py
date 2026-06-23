"""测试 official_filings 的数据模型。"""
from __future__ import annotations

import pytest

from opc_foundation.official_filings.models import (
    FilingCandidate,
    FilingDefaults,
    FilingSourceConfig,
    FilingSourceHealth,
    NormalizedFiling,
    FailedFiling,
    FILING_STATUS_SAVED,
    FILING_STATUS_DUPLICATE,
    HEALTH_STATUS_HEALTHY,
    IMPLEMENTED_SOURCE_TYPES,
    LEGAL_PROFILES,
)


# ---------------------------------------------------------------------------
# FilingDefaults
# ---------------------------------------------------------------------------


def test_filing_defaults_default_values() -> None:
    """FilingDefaults 的默认值正确。"""
    d = FilingDefaults()
    assert d.fetch_timeout_seconds == 30
    assert d.max_items_per_source == 20
    assert d.save_raw is True
    assert d.save_html is True
    assert d.save_pdf_metadata is True
    assert d.download_pdfs is False


def test_filing_defaults_custom_values() -> None:
    """FilingDefaults 可以自定义值。"""
    d = FilingDefaults(max_items_per_source=50, download_pdfs=True)
    assert d.max_items_per_source == 50
    assert d.download_pdfs is True


# ---------------------------------------------------------------------------
# FilingSourceConfig
# ---------------------------------------------------------------------------


def test_filing_source_config_minimal() -> None:
    """FilingSourceConfig 最小字段配置。"""
    s = FilingSourceConfig(
        source_id="test",
        source_name="Test Source",
        source_type="sec_edgar",
    )
    assert s.source_id == "test"
    assert s.source_name == "Test Source"
    assert s.source_type == "sec_edgar"
    assert s.enabled is True
    assert s.legal_profile == "unknown"
    assert s.max_items is None


def test_filing_source_config_full() -> None:
    """FilingSourceConfig 完整字段配置。"""
    s = FilingSourceConfig(
        source_id="test_sec",
        source_name="Test SEC",
        source_type="sec_edgar",
        market="US",
        jurisdiction="US",
        base_url="https://www.sec.gov",
        endpoint_url="https://data.sec.gov/submissions/CIK0000320193.json",
        enabled=False,
        legal_profile="official_public",
        fetch_profile="default",
        max_items=10,
        filing_types=["10-K", "10-Q"],
        issuer_filter=["0000320193"],
        date_from="2024-01-01",
        date_to="2024-12-31",
        save_raw=True,
        save_html=True,
        save_pdf_metadata=True,
        download_pdfs=False,
    )
    assert s.source_id == "test_sec"
    assert s.market == "US"
    assert s.filing_types == ["10-K", "10-Q"]
    assert s.enabled is False


# ---------------------------------------------------------------------------
# FilingCandidate
# ---------------------------------------------------------------------------


def test_filing_candidate_basic() -> None:
    """FilingCandidate 基本字段。"""
    c = FilingCandidate(
        source_id="test_sec",
        source_type="sec_edgar",
        issuer_name="Apple Inc.",
        issuer_code="320193",
        filing_type="10-K",
        filing_title="10-K Annual Report",
        filing_date="2023-10-26",
        accession_number="0000320193-23-000107",
        document_url="https://www.sec.gov/Archives/edgar/data/320193/000032019323000107/0000320193-23-000107-index.htm",
    )
    assert c.source_id == "test_sec"
    assert c.issuer_name == "Apple Inc."
    assert c.issuer_code == "320193"
    assert c.filing_type == "10-K"
    assert c.filing_date == "2023-10-26"
    assert c.accession_number == "0000320193-23-000107"


# ---------------------------------------------------------------------------
# NormalizedFiling
# ---------------------------------------------------------------------------


def test_normalized_filing_basic() -> None:
    """NormalizedFiling 基本字段。"""
    f = NormalizedFiling(
        filing_id="of_abc123",
        source_id="test_sec",
        source_type="sec_edgar",
        issuer_name="Apple Inc.",
        issuer_code="320193",
        filing_type="10-K",
        filing_title="10-K Annual Report",
        filing_date="2023-10-26",
        content_hash="abc123def456",
        canonical_key="sec_edgar|320193|2023-10-26|10-K|acc:0000320193-23-000107",
        metadata_path="metadata/of_abc123.json",
        created_at="2024-01-01T00:00:00Z",
        status=FILING_STATUS_SAVED,
    )
    assert f.filing_id == "of_abc123"
    assert f.content_hash == "abc123def456"
    assert f.status == FILING_STATUS_SAVED


# ---------------------------------------------------------------------------
# 禁止字段检查：确保模型中不包含投资判断字段
# ---------------------------------------------------------------------------


FORBIDDEN_FIELDS = {
    "affected_tickers",
    "expectation_delta",
    "investment_rating",
    "trade_signal",
    "watchlist",
    "action_decision",
    "recommendation",
    "opportunity_score",
    "risk_score",
    "position_size",
    "target_price",
}


def test_no_forbidden_fields_in_models() -> None:
    """确保核心模型中不包含任何投资判断字段。"""
    model_classes = [
        FilingCandidate,
        NormalizedFiling,
        FilingSourceConfig,
        FilingSourceHealth,
        FailedFiling,
    ]
    for cls in model_classes:
        model_fields = set(cls.model_fields.keys())
        forbidden_found = model_fields & FORBIDDEN_FIELDS
        assert not forbidden_found, (
            f"{cls.__name__} 中发现禁止字段: {forbidden_found}"
        )


# ---------------------------------------------------------------------------
# 枚举常量
# ---------------------------------------------------------------------------


def test_implemented_source_types_contains_all_three() -> None:
    """IMPLEMENTED_SOURCE_TYPES 包含三个 source type。"""
    assert "sec_edgar" in IMPLEMENTED_SOURCE_TYPES
    assert "cninfo_announcement" in IMPLEMENTED_SOURCE_TYPES
    assert "hkex_announcement" in IMPLEMENTED_SOURCE_TYPES


def test_legal_profiles() -> None:
    """LEGAL_PROFILES 包含合法取值。"""
    assert "official_public" in LEGAL_PROFILES
    assert "public_ir" in LEGAL_PROFILES
    assert "unknown" in LEGAL_PROFILES
