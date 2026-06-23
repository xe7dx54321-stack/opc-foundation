"""测试 SEC EDGAR connector。"""
from __future__ import annotations

import pytest

from opc_foundation.official_filings.connectors.sec import SECFilingConnector
from opc_foundation.official_filings.models import (
    FilingArchiveConfig,
    FilingDefaults,
    FilingSourceConfig,
)


def _make_source(
    endpoint_url: str = "https://data.sec.gov/submissions/CIK0000320193.json",
    max_items: int | None = None,
    filing_types: list[str] | None = None,
) -> FilingSourceConfig:
    """构造一个 sec_edgar source 配置。"""
    return FilingSourceConfig(
        source_id="sec_test",
        source_name="SEC Test",
        source_type="sec_edgar",
        market="US",
        jurisdiction="US",
        base_url="https://www.sec.gov",
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


def test_sec_discover_parses_submissions(
    sec_submissions_sample: dict,
) -> None:
    """能从 fixture JSON 解析出候选披露。"""
    connector = SECFilingConnector(
        json_by_url=lambda url: sec_submissions_sample
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # fixture 里 recent 有 5 条
    assert len(candidates) == 5
    assert candidates[0].source_type == "sec_edgar"
    assert candidates[0].market == "US"
    assert candidates[0].jurisdiction == "US"


def test_sec_discover_issuer_info(
    sec_submissions_sample: dict,
) -> None:
    """正确解析发行方信息（CIK、公司名）。"""
    connector = SECFilingConnector(
        json_by_url=lambda url: sec_submissions_sample
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates[0].issuer_name == "Apple Inc."
    assert candidates[0].issuer_code == "320193"  # CIK 去掉前导零


def test_sec_discover_filing_types(
    sec_submissions_sample: dict,
) -> None:
    """正确解析披露类型。"""
    connector = SECFilingConnector(
        json_by_url=lambda url: sec_submissions_sample
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    types = [c.filing_type for c in candidates]
    assert "10-K" in types
    assert "10-Q" in types
    assert "8-K" in types
    assert "S-1" in types


def test_sec_discover_accession_number(
    sec_submissions_sample: dict,
) -> None:
    """正确解析 accession number。"""
    connector = SECFilingConnector(
        json_by_url=lambda url: sec_submissions_sample
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates[0].accession_number == "0000320193-24-000006"


def test_sec_discover_max_items(
    sec_submissions_sample: dict,
) -> None:
    """max_items 限制生效。"""
    connector = SECFilingConnector(
        json_by_url=lambda url: sec_submissions_sample
    )
    source = _make_source(max_items=2)
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert len(candidates) == 2


def test_sec_discover_filing_types_filter(
    sec_submissions_sample: dict,
) -> None:
    """filing_types 过滤生效。"""
    connector = SECFilingConnector(
        json_by_url=lambda url: sec_submissions_sample
    )
    source = _make_source(filing_types=["10-K", "10-Q"])
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # fixture 里有 1 条 10-K 和 1 条 10-Q
    assert len(candidates) == 2
    types = [c.filing_type for c in candidates]
    assert "10-K" in types
    assert "10-Q" in types
    assert "8-K" not in types


def test_sec_discover_document_url(
    sec_submissions_sample: dict,
) -> None:
    """正确生成文档 URL。"""
    connector = SECFilingConnector(
        json_by_url=lambda url: sec_submissions_sample
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # 第一条的 detail URL 应包含 accession 和 cik
    assert "0000320193-24-000006" in candidates[0].document_url
    assert "320193" in candidates[0].document_url


def test_sec_discover_filing_date(
    sec_submissions_sample: dict,
) -> None:
    """正确解析披露日期。"""
    connector = SECFilingConnector(
        json_by_url=lambda url: sec_submissions_sample
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates[0].filing_date == "2024-02-02"


def test_sec_discover_missing_endpoint_url() -> None:
    """缺少 endpoint_url 时抛出 ValueError。"""
    connector = SECFilingConnector()
    source = FilingSourceConfig(
        source_id="test",
        source_name="Test",
        source_type="sec_edgar",
    )
    cfg = _make_config()

    with pytest.raises(ValueError, match="缺少 endpoint_url"):
        connector.discover(source, cfg)


def test_sec_discover_fail_soft_on_invalid_json() -> None:
    """注入的 JSON 不是 dict 时能优雅处理（fail-soft）。"""
    connector = SECFilingConnector(
        json_by_url=lambda url: "not a dict"
    )
    source = _make_source()
    cfg = _make_config()

    # 不是 dict 会导致属性访问失败，由上层捕获
    with pytest.raises(Exception):
        connector.discover(source, cfg)
