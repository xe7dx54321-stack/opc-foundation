"""tests/official_filings/ 共享 fixture。

功能说明（小白解读）：
    pytest fixture 是测试之间共享数据/对象的方式。
    这里定义了 official_filings 测试用到的共享 fixture，
    比如临时归档目录、示例配置、各 connector 的 fixture 数据等。
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    """测试 fixtures 目录路径。"""
    return FIXTURES_DIR


# ---------------------------------------------------------------------------
# SEC fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sec_submissions_sample() -> dict:
    """读取 sec_submissions_sample.json 内容（dict）。"""
    return json.loads(
        (FIXTURES_DIR / "sec_submissions_sample.json").read_text(encoding="utf-8")
    )


@pytest.fixture
def sec_filing_detail_sample_html() -> str:
    """读取 sec_filing_detail_sample.html 内容。"""
    return (FIXTURES_DIR / "sec_filing_detail_sample.html").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# CNINFO fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def cninfo_announcements_sample() -> dict:
    """读取 cninfo_announcements_sample.json 内容（dict）。"""
    return json.loads(
        (FIXTURES_DIR / "cninfo_announcements_sample.json").read_text(encoding="utf-8")
    )


@pytest.fixture
def cninfo_announcement_detail_sample_html() -> str:
    """读取 cninfo_announcement_detail_sample.html 内容。"""
    return (FIXTURES_DIR / "cninfo_announcement_detail_sample.html").read_text(
        encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# HKEX fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def hkex_announcements_sample_html() -> str:
    """读取 hkex_announcements_sample.html 内容。"""
    return (FIXTURES_DIR / "hkex_announcements_sample.html").read_text(encoding="utf-8")


@pytest.fixture
def hkex_announcement_detail_sample_html() -> str:
    """读取 hkex_announcement_detail_sample.html 内容。"""
    return (FIXTURES_DIR / "hkex_announcement_detail_sample.html").read_text(
        encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# 通用测试工具
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_archive_root(tmp_path: Path) -> Path:
    """临时归档根目录（每个测试独立，测试结束自动清理）。"""
    root = tmp_path / "official_filings"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def sample_config_dict(temp_archive_root: Path) -> dict:
    """构造一个示例配置 dict（用于测试 load_filing_config）。"""
    return {
        "archive_root": str(temp_archive_root),
        "defaults": {
            "fetch_timeout_seconds": 10,
            "max_items_per_source": 5,
            "save_raw": True,
            "save_html": True,
            "save_pdf_metadata": True,
            "download_pdfs": False,
            "user_agent": "Mozilla/5.0 (test)",
        },
        "sources": [
            {
                "source_id": "test_sec",
                "source_name": "Test SEC EDGAR",
                "source_type": "sec_edgar",
                "market": "US",
                "jurisdiction": "US",
                "base_url": "https://www.sec.gov",
                "endpoint_url": "https://data.sec.gov/submissions/CIK0000320193.json",
                "enabled": True,
                "legal_profile": "official_public",
                "max_items": 3,
            },
            {
                "source_id": "test_cninfo",
                "source_name": "Test CNINFO",
                "source_type": "cninfo_announcement",
                "market": "CN",
                "jurisdiction": "CN",
                "base_url": "https://www.cninfo.com.cn",
                "endpoint_url": "https://www.cninfo.com.cn/new/hisAnnouncement/query",
                "enabled": True,
                "legal_profile": "official_public",
                "max_items": 3,
            },
            {
                "source_id": "test_hkex",
                "source_name": "Test HKEX",
                "source_type": "hkex_announcement",
                "market": "HK",
                "jurisdiction": "HK",
                "base_url": "https://www.hkexnews.hk",
                "endpoint_url": "https://www.hkexnews.hk/listedco/listconews/advancedsearch/search_active_main_c.aspx",
                "enabled": False,
                "legal_profile": "official_public",
                "max_items": 3,
            },
        ],
    }
