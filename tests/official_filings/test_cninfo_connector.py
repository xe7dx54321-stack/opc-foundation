"""测试 CNINFO 巨潮资讯 connector。"""
from __future__ import annotations

import pytest

from opc_foundation.official_filings.connectors.cninfo import CNINFOFilingConnector
from opc_foundation.official_filings.models import (
    FilingArchiveConfig,
    FilingDefaults,
    FilingSourceConfig,
)


def _make_source(
    endpoint_url: str = "https://www.cninfo.com.cn/new/hisAnnouncement/query",
    max_items: int | None = None,
    filing_types: list[str] | None = None,
) -> FilingSourceConfig:
    """构造一个 cninfo source 配置。"""
    return FilingSourceConfig(
        source_id="cninfo_test",
        source_name="CNINFO Test",
        source_type="cninfo_announcement",
        market="CN",
        jurisdiction="CN",
        base_url="https://www.cninfo.com.cn",
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


def test_cninfo_discover_parses_announcements(
    cninfo_announcements_sample: dict,
) -> None:
    """能从 fixture JSON 解析出候选披露。"""
    connector = CNINFOFilingConnector(
        json_by_url=lambda url: cninfo_announcements_sample
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # fixture 里有 5 条公告
    assert len(candidates) == 5
    assert candidates[0].source_type == "cninfo_announcement"
    assert candidates[0].market == "CN"
    assert candidates[0].jurisdiction == "CN"


def test_cninfo_discover_issuer_info(
    cninfo_announcements_sample: dict,
) -> None:
    """正确解析发行方信息（股票代码、名称）。"""
    connector = CNINFOFilingConnector(
        json_by_url=lambda url: cninfo_announcements_sample
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates[0].issuer_name == "平安银行"
    assert candidates[0].issuer_code == "000001"


def test_cninfo_discover_filing_title(
    cninfo_announcements_sample: dict,
) -> None:
    """正确解析公告标题。"""
    connector = CNINFOFilingConnector(
        json_by_url=lambda url: cninfo_announcements_sample
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert "2023年年度报告" in candidates[0].filing_title


def test_cninfo_discover_announcement_id(
    cninfo_announcements_sample: dict,
) -> None:
    """正确解析公告 ID。"""
    connector = CNINFOFilingConnector(
        json_by_url=lambda url: cninfo_announcements_sample
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates[0].announcement_id == "1234567890"


def test_cninfo_discover_pdf_url(
    cninfo_announcements_sample: dict,
) -> None:
    """正确生成 PDF URL。"""
    connector = CNINFOFilingConnector(
        json_by_url=lambda url: cninfo_announcements_sample
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates[0].pdf_url is not None
    assert "cninfo.com.cn" in candidates[0].pdf_url
    assert "1234567890.PDF" in candidates[0].pdf_url


def test_cninfo_discover_max_items(
    cninfo_announcements_sample: dict,
) -> None:
    """max_items 限制生效。"""
    connector = CNINFOFilingConnector(
        json_by_url=lambda url: cninfo_announcements_sample
    )
    source = _make_source(max_items=2)
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert len(candidates) == 2


def test_cninfo_discover_filing_types_filter(
    cninfo_announcements_sample: dict,
) -> None:
    """filing_types 过滤生效。"""
    connector = CNINFOFilingConnector(
        json_by_url=lambda url: cninfo_announcements_sample
    )
    source = _make_source(filing_types=["年度报告"])
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert len(candidates) == 1
    assert candidates[0].filing_type == "年度报告"


def test_cninfo_discover_filing_date(
    cninfo_announcements_sample: dict,
) -> None:
    """正确解析公告日期（从毫秒时间戳）。"""
    connector = CNINFOFilingConnector(
        json_by_url=lambda url: cninfo_announcements_sample
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    # 1703721600000 = 2023-12-28 00:00:00 UTC+8
    assert candidates[0].filing_date is not None
    assert len(candidates[0].filing_date) == 10  # YYYY-MM-DD 格式


def test_cninfo_discover_missing_endpoint_url() -> None:
    """缺少 endpoint_url 时抛出 ValueError。"""
    connector = CNINFOFilingConnector()
    source = FilingSourceConfig(
        source_id="test",
        source_name="Test",
        source_type="cninfo_announcement",
    )
    cfg = _make_config()

    with pytest.raises(ValueError, match="缺少 endpoint_url"):
        connector.discover(source, cfg)


def test_cninfo_discover_empty_announcements() -> None:
    """announcements 为空列表时返回空列表。"""
    connector = CNINFOFilingConnector(
        json_by_url=lambda url: {"announcements": []}
    )
    source = _make_source()
    cfg = _make_config()

    candidates = connector.discover(source, cfg)
    assert candidates == []
