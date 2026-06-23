"""测试 HKEX 港交所披露易 connector。"""
from __future__ import annotations

import pytest

from opc_foundation.official_filings.connectors.hkex import HKEXFilingConnector
from opc_foundation.official_filings.models import (
    FilingArchiveConfig,
    FilingDefaults,
    FilingSourceConfig,
)


def _make_source(
    endpoint_url: str = "https://www.hkexnews.hk/listedco/listconews/advancedsearch/search_active_main_c.aspx",
    max_items: int | None = None,
    filing_types: list[str] | None = None,
) -> FilingSourceConfig:
    """构造一个 hkex source 配置。"""
    return FilingSourceConfig(
        source_id="hkex_test",
        source_name="HKEX Test",
        source_type="hkex_announcement",
        market="HK",
        jurisdiction="HK",
        base_url="https://www.hkexnews.hk",
        endpoint_url=endpoint_url,
        legal_profile="official_public",
        max_items=max_items,
        filing_types=filing_types or [],
    )


def _make_config() -> FilingArchiveConfig:
    """构造一个最小配置。"""
    return FilingArchiveConfig(
        archive_root="/tmp/test",
        defaults=FilingDefaults(max_items_per_source=10),
    )


# ---------------------------------------------------------------------------
# discover 测试
# ---------------------------------------------------------------------------


def test_hkex_discover_parses_html(
    hkex_announcements_sample_html: str,
) -> None:
    """能从 fixture HTML 解析出候选披露。"""
    connector = HKEXFilingConnector(
        html_by_url=lambda url: hkex_announcements_sample_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # fixture 里表格有 5 行数据
    assert len(candidates) == 5
    assert candidates[0].source_type == "hkex_announcement"
    assert candidates[0].market == "HK"
    assert candidates[0].jurisdiction == "HK"


def test_hkex_discover_stock_code(
    hkex_announcements_sample_html: str,
) -> None:
    """正确解析股份代号。"""
    connector = HKEXFilingConnector(
        html_by_url=lambda url: hkex_announcements_sample_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates[0].issuer_code == "00700"


def test_hkex_discover_company_name(
    hkex_announcements_sample_html: str,
) -> None:
    """正确解析公司名称。"""
    connector = HKEXFilingConnector(
        html_by_url=lambda url: hkex_announcements_sample_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert "腾讯" in candidates[0].issuer_name


def test_hkex_discover_title(
    hkex_announcements_sample_html: str,
) -> None:
    """正确解析公告标题。"""
    connector = HKEXFilingConnector(
        html_by_url=lambda url: hkex_announcements_sample_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert "业绩公告" in candidates[0].filing_title


def test_hkex_discover_document_url(
    hkex_announcements_sample_html: str,
) -> None:
    """正确解析公告 URL。"""
    connector = HKEXFilingConnector(
        html_by_url=lambda url: hkex_announcements_sample_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates[0].document_url is not None
    assert "hkexnews.hk" in candidates[0].document_url


def test_hkex_discover_pdf_url(
    hkex_announcements_sample_html: str,
) -> None:
    """PDF 链接被正确识别为 pdf_url。"""
    connector = HKEXFilingConnector(
        html_by_url=lambda url: hkex_announcements_sample_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # 第 4 条（美团）是 .pdf 链接
    pdf_candidate = candidates[3]
    assert pdf_candidate.pdf_url is not None
    assert pdf_candidate.pdf_url.endswith(".pdf")


def test_hkex_discover_max_items(
    hkex_announcements_sample_html: str,
) -> None:
    """max_items 限制生效。"""
    connector = HKEXFilingConnector(
        html_by_url=lambda url: hkex_announcements_sample_html
    )
    source = _make_source(max_items=2)
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert len(candidates) == 2


def test_hkex_discover_filing_date(
    hkex_announcements_sample_html: str,
) -> None:
    """正确解析公告日期（DD/MM/YYYY 格式）。"""
    connector = HKEXFilingConnector(
        html_by_url=lambda url: hkex_announcements_sample_html
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates[0].filing_date == "2024-01-17"


def test_hkex_discover_missing_endpoint_url() -> None:
    """缺少 endpoint_url 时抛出 ValueError。"""
    connector = HKEXFilingConnector()
    source = FilingSourceConfig(
        source_id="test",
        source_name="Test",
        source_type="hkex_announcement",
    )
    cfg = _make_config()

    with pytest.raises(ValueError, match="缺少 endpoint_url"):
        connector.discover(source, cfg)


def test_hkex_discover_empty_html() -> None:
    """空 HTML 返回空列表。"""
    connector = HKEXFilingConnector(
        html_by_url=lambda url: "<html><body></body></html>"
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert isinstance(candidates, list)
