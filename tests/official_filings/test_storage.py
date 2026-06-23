"""测试 official_filings 的存储层。"""
from __future__ import annotations

from pathlib import Path

import pytest

from opc_foundation.official_filings.dedupe import (
    build_canonical_key,
    content_hash_for,
    filing_id_for,
)
from opc_foundation.official_filings.models import (
    FilingArchiveConfig,
    FilingCandidate,
    FilingDefaults,
    FILING_STATUS_DUPLICATE,
    FILING_STATUS_SAVED,
    NormalizedFiling,
)
from opc_foundation.official_filings.storage import (
    append_filing_index,
    archive_filing,
    load_filings_index,
    process_candidate,
    write_filings_latest,
    _filings_path,
    _filings_latest_path,
)


# ---------------------------------------------------------------------------
# 去重与 canonical_key
# ---------------------------------------------------------------------------


def test_canonical_key_stable() -> None:
    """相同的 candidate 生成相同的 canonical_key（稳定性）。"""
    c1 = FilingCandidate(
        source_id="test",
        source_type="sec_edgar",
        issuer_code="320193",
        filing_date="2023-10-26",
        filing_type="10-K",
        accession_number="0000320193-23-000107",
    )
    c2 = FilingCandidate(
        source_id="test",
        source_type="sec_edgar",
        issuer_code="320193",
        filing_date="2023-10-26",
        filing_type="10-K",
        accession_number="0000320193-23-000107",
    )
    assert build_canonical_key(c1) == build_canonical_key(c2)


def test_canonical_key_differs_for_diff_filings() -> None:
    """不同的披露生成不同的 canonical_key。"""
    c1 = FilingCandidate(
        source_id="test",
        source_type="sec_edgar",
        issuer_code="320193",
        filing_date="2023-10-26",
        filing_type="10-K",
        accession_number="0000320193-23-000107",
    )
    c2 = FilingCandidate(
        source_id="test",
        source_type="sec_edgar",
        issuer_code="320193",
        filing_date="2024-02-02",
        filing_type="10-Q",
        accession_number="0000320193-24-000006",
    )
    assert build_canonical_key(c1) != build_canonical_key(c2)


def test_canonical_key_uses_accession_first() -> None:
    """优先使用 accession_number 作为唯一标识。"""
    c = FilingCandidate(
        source_id="test",
        source_type="sec_edgar",
        issuer_code="320193",
        filing_date="2023-10-26",
        filing_type="10-K",
        accession_number="0000320193-23-000107",
    )
    key = build_canonical_key(c)
    assert "acc:0000320193-23-000107" in key


def test_canonical_key_uses_announcement_id() -> None:
    """CNINFO 用 announcement_id 作为唯一标识。"""
    c = FilingCandidate(
        source_id="test",
        source_type="cninfo_announcement",
        issuer_code="000001",
        filing_date="2023-12-28",
        filing_type="年度报告",
        announcement_id="1234567890",
    )
    key = build_canonical_key(c)
    assert "ann:1234567890" in key


def test_canonical_key_falls_back_to_url() -> None:
    """没有 accession/announcement_id 时用 document_url 兜底。"""
    c = FilingCandidate(
        source_id="test",
        source_type="hkex_announcement",
        issuer_code="00700",
        filing_date="2024-01-17",
        filing_type="业绩公告",
        document_url="https://www.hkexnews.hk/example.htm",
    )
    key = build_canonical_key(c)
    assert "url:https://www.hkexnews.hk/example.htm" in key


def test_filing_id_stable() -> None:
    """filing_id 是稳定的。"""
    c1 = FilingCandidate(
        source_id="test",
        source_type="sec_edgar",
        issuer_code="320193",
        filing_date="2023-10-26",
        filing_type="10-K",
        accession_number="0000320193-23-000107",
    )
    c2 = FilingCandidate(
        source_id="test",
        source_type="sec_edgar",
        issuer_code="320193",
        filing_date="2023-10-26",
        filing_type="10-K",
        accession_number="0000320193-23-000107",
    )
    assert filing_id_for(c1) == filing_id_for(c2)
    assert filing_id_for(c1).startswith("of_")


def test_content_hash_stable() -> None:
    """content_hash 是稳定的。"""
    c1 = FilingCandidate(
        source_id="test",
        source_type="sec_edgar",
        filing_title="10-K Annual Report",
        filing_date="2023-10-26",
        document_url="https://example.com/10k",
    )
    c2 = FilingCandidate(
        source_id="test",
        source_type="sec_edgar",
        filing_title="10-K Annual Report",
        filing_date="2023-10-26",
        document_url="https://example.com/10k",
    )
    assert content_hash_for(c1) == content_hash_for(c2)


# ---------------------------------------------------------------------------
# process_candidate
# ---------------------------------------------------------------------------


def test_process_candidate_new_filing() -> None:
    """新披露：is_new=True，status=saved。"""
    candidate = FilingCandidate(
        source_id="test_sec",
        source_type="sec_edgar",
        market="US",
        issuer_name="Apple Inc.",
        issuer_code="320193",
        filing_type="10-K",
        filing_title="10-K Annual Report",
        filing_date="2023-10-26",
        accession_number="0000320193-23-000107",
        document_url="https://www.sec.gov/Archives/edgar/data/320193/000032019323000107/0000320193-23-000107-index.htm",
    )
    config = FilingArchiveConfig(
        archive_root="/tmp/test",
        defaults=FilingDefaults(),
    )
    existing = {}

    filing, is_new = process_candidate(candidate, config, existing)
    assert is_new is True
    assert filing.status == FILING_STATUS_SAVED
    assert filing.filing_id.startswith("of_")
    assert filing.canonical_key
    assert filing.content_hash
    assert filing.created_at


def test_process_candidate_duplicate_same_hash() -> None:
    """重复披露（content_hash 相同）：is_new=False，status=duplicate。"""
    candidate = FilingCandidate(
        source_id="test_sec",
        source_type="sec_edgar",
        issuer_code="320193",
        filing_date="2023-10-26",
        filing_type="10-K",
        filing_title="10-K Annual Report",
        accession_number="0000320193-23-000107",
    )
    config = FilingArchiveConfig(
        archive_root="/tmp/test",
        defaults=FilingDefaults(),
    )

    # 第一次处理
    filing1, is_new1 = process_candidate(candidate, config, {})
    assert is_new1 is True

    # 第二次处理（相同的内容）
    existing = {filing1.canonical_key: filing1}
    filing2, is_new2 = process_candidate(candidate, config, existing)
    assert is_new2 is False
    assert filing2.status == FILING_STATUS_DUPLICATE


# ---------------------------------------------------------------------------
# 索引读写
# ---------------------------------------------------------------------------


def test_append_filing_index(temp_archive_root: Path) -> None:
    """能追加写 filings.jsonl。"""
    filing = NormalizedFiling(
        filing_id="of_test001",
        source_id="test",
        source_type="sec_edgar",
        issuer_code="320193",
        filing_type="10-K",
        filing_date="2023-10-26",
        content_hash="abc123",
        canonical_key="test|320193|2023-10-26|10-K|acc:123",
        metadata_path="metadata/of_test001.json",
        created_at="2024-01-01T00:00:00Z",
        status=FILING_STATUS_SAVED,
    )

    append_filing_index(temp_archive_root, filing)

    filings_path = _filings_path(temp_archive_root)
    assert filings_path.exists()

    # 读取验证
    lines = filings_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 1
    assert "of_test001" in lines[0]


def test_write_filings_latest(temp_archive_root: Path) -> None:
    """能覆盖写 filings.latest.jsonl。"""
    f1 = NormalizedFiling(
        filing_id="of_001",
        source_id="test",
        source_type="sec_edgar",
        issuer_code="320193",
        filing_type="10-K",
        filing_date="2023-10-26",
        content_hash="abc123",
        canonical_key="key1",
        metadata_path="metadata/of_001.json",
        created_at="2024-01-01T00:00:00Z",
        status=FILING_STATUS_SAVED,
    )
    f2 = NormalizedFiling(
        filing_id="of_002",
        source_id="test",
        source_type="sec_edgar",
        issuer_code="320193",
        filing_type="10-Q",
        filing_date="2024-02-02",
        content_hash="def456",
        canonical_key="key2",
        metadata_path="metadata/of_002.json",
        created_at="2024-01-01T00:00:00Z",
        status=FILING_STATUS_SAVED,
    )

    write_filings_latest(temp_archive_root, {"key1": f1, "key2": f2})

    latest_path = _filings_latest_path(temp_archive_root)
    assert latest_path.exists()

    lines = latest_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2


def test_load_filings_index(temp_archive_root: Path) -> None:
    """能加载 filings.latest.jsonl。"""
    f1 = NormalizedFiling(
        filing_id="of_001",
        source_id="test",
        source_type="sec_edgar",
        issuer_code="320193",
        filing_type="10-K",
        filing_date="2023-10-26",
        content_hash="abc123",
        canonical_key="key1",
        metadata_path="metadata/of_001.json",
        created_at="2024-01-01T00:00:00Z",
        status=FILING_STATUS_SAVED,
    )

    write_filings_latest(temp_archive_root, [f1])
    loaded = load_filings_index(temp_archive_root)

    assert "key1" in loaded
    assert loaded["key1"].filing_id == "of_001"


def test_load_filings_index_empty(temp_archive_root: Path) -> None:
    """不存在索引文件时返回空字典。"""
    loaded = load_filings_index(temp_archive_root)
    assert loaded == {}


# ---------------------------------------------------------------------------
# archive_filing
# ---------------------------------------------------------------------------


def test_archive_filing_writes_files(temp_archive_root: Path) -> None:
    """archive_filing 会写索引和元数据 sidecar。"""
    filing = NormalizedFiling(
        filing_id="of_archive_test",
        source_id="test_sec",
        source_type="sec_edgar",
        issuer_code="320193",
        filing_type="10-K",
        filing_date="2023-10-26",
        content_hash="abc123",
        canonical_key="test_key",
        metadata_path="metadata/of_archive_test.json",
        created_at="2024-01-01T00:00:00Z",
        status=FILING_STATUS_SAVED,
    )

    saved = archive_filing(temp_archive_root, filing)

    # 索引文件存在
    assert _filings_path(temp_archive_root).exists()
    # 元数据 sidecar 存在
    assert (temp_archive_root / "metadata" / "of_archive_test.json").exists()
    # 返回的 filing 里 metadata_path 被更新
    assert saved.metadata_path


def test_archive_filing_with_raw_content(temp_archive_root: Path) -> None:
    """提供 raw_content 时会保存原始文件。"""
    filing = NormalizedFiling(
        filing_id="of_raw_test",
        source_id="test_sec",
        source_type="sec_edgar",
        issuer_code="320193",
        filing_type="10-K",
        filing_date="2023-10-26",
        content_hash="abc123",
        canonical_key="raw_test_key",
        metadata_path="metadata/of_raw_test.json",
        created_at="2024-01-01T00:00:00Z",
        status=FILING_STATUS_SAVED,
    )

    raw_content = '{"test": "data"}'
    saved = archive_filing(temp_archive_root, filing, raw_content=raw_content, raw_ext="json")

    # raw 文件存在
    assert saved.raw_path is not None
    raw_path = temp_archive_root / saved.raw_path
    assert raw_path.exists()
    assert raw_path.read_text(encoding="utf-8") == raw_content
