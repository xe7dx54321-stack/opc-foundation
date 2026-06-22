"""测试 research/dedupe.py —— SQLite 去重。"""
from __future__ import annotations

from pathlib import Path

from opc_foundation.research.dedupe import (
    ResearchSeenStore,
    document_id_for,
    url_key,
    title_key,
)
from opc_foundation.research.models import DocumentCandidate, NormalizedDocument


def _make_candidate(
    url: str = "https://example.com/article-1",
    title: str = "测试标题",
    source_id: str = "s1",
    published_at: str | None = "2026-01-01T00:00:00Z",
) -> DocumentCandidate:
    return DocumentCandidate(
        source_id=source_id,
        source_name="Source 1",
        source_type="rss_feed",
        title=title,
        url=url,
        canonical_url=url,
        published_at=published_at,
    )


def _make_document(
    candidate: DocumentCandidate,
    status: str = "saved",
) -> NormalizedDocument:
    return NormalizedDocument(
        document_id=document_id_for(candidate),
        source_id=candidate.source_id,
        source_name=candidate.source_name,
        source_type=candidate.source_type,
        title=candidate.title,
        url=candidate.url,
        canonical_url=candidate.canonical_url,
        published_at=candidate.published_at,
        captured_at="2026-01-01T00:00:00Z",
        updated_at=None,
        author=None,
        summary=None,
        language=None,
        content_type="article",
        legal_profile="unknown",
        tags=[],
        content_hash="abc",
        status=status,
        markdown_path=None,
        html_path=None,
        raw_path=None,
        metadata_path="/tmp/m.json",
        attachments=[],
        extraction_quality="high",
        error=None,
    )


def test_url_key_stable() -> None:
    """url_key 对同一 URL 返回相同值。"""
    k1 = url_key("https://example.com/a")
    k2 = url_key("https://example.com/a")
    assert k1 == k2
    assert k1 != url_key("https://example.com/b")


def test_title_key_includes_source_id() -> None:
    """title_key 包含 source_id。"""
    k1 = title_key("s1", "title", "2026-01-01")
    k2 = title_key("s2", "title", "2026-01-01")
    assert k1 != k2


def test_document_id_for_stable() -> None:
    """document_id 基于 canonical_url 稳定生成。"""
    c1 = _make_candidate(url="https://example.com/a")
    c2 = _make_candidate(url="https://example.com/a")
    c3 = _make_candidate(url="https://example.com/b")
    assert document_id_for(c1) == document_id_for(c2)
    assert document_id_for(c1) != document_id_for(c3)
    assert document_id_for(c1).startswith("rs_")


def test_seen_store_new_candidate_not_seen(tmp_path: Path) -> None:
    """新候选未被见过。"""
    store = ResearchSeenStore(tmp_path / "seen.sqlite")
    cand = _make_candidate()
    assert store.has_seen(cand) is False
    store.close()


def test_seen_store_mark_seen(tmp_path: Path) -> None:
    """标记 seen 后能识别为已见过。"""
    store = ResearchSeenStore(tmp_path / "seen.sqlite")
    cand = _make_candidate()
    doc = _make_document(cand)
    store.mark_seen(doc)
    assert store.has_seen(cand) is True
    store.close()


def test_seen_store_failed_not_blocking(tmp_path: Path) -> None:
    """failed 状态不阻塞重试。"""
    store = ResearchSeenStore(tmp_path / "seen.sqlite")
    cand = _make_candidate()
    doc = _make_document(cand, status="failed")
    store.mark_seen(doc)
    # failed 不算"已见过"
    assert store.has_seen(cand) is False
    store.close()


def test_seen_store_partial_blocks(tmp_path: Path) -> None:
    """partial 状态算"已见过"。"""
    store = ResearchSeenStore(tmp_path / "seen.sqlite")
    cand = _make_candidate()
    doc = _make_document(cand, status="partial")
    store.mark_seen(doc)
    assert store.has_seen(cand) is True
    store.close()


def test_seen_store_duplicate_blocks(tmp_path: Path) -> None:
    """duplicate 状态算"已见过"。"""
    store = ResearchSeenStore(tmp_path / "seen.sqlite")
    cand = _make_candidate()
    doc = _make_document(cand, status="duplicate")
    store.mark_seen(doc)
    assert store.has_seen(cand) is True
    store.close()


def test_seen_store_title_fallback(tmp_path: Path) -> None:
    """URL 不同但 source_id+title+published_at 相同时，title fallback 命中。"""
    store = ResearchSeenStore(tmp_path / "seen.sqlite")
    # 第一条：URL A
    cand1 = _make_candidate(url="https://example.com/a", title="同标题", source_id="s1")
    doc1 = _make_document(cand1)
    store.mark_seen(doc1)

    # 第二条：URL B 但标题/source_id/published_at 相同
    cand2 = _make_candidate(url="https://example.com/b", title="同标题", source_id="s1")
    assert store.has_seen(cand2) is True
    store.close()


def test_seen_store_persists_across_connections(tmp_path: Path) -> None:
    """SQLite 持久化：关闭重开后记录还在。"""
    db_path = tmp_path / "seen.sqlite"
    store1 = ResearchSeenStore(db_path)
    cand = _make_candidate()
    doc = _make_document(cand)
    store1.mark_seen(doc)
    store1.close()

    store2 = ResearchSeenStore(db_path)
    assert store2.has_seen(cand) is True
    store2.close()


def test_seen_store_count_by_status(tmp_path: Path) -> None:
    """按状态计数。"""
    store = ResearchSeenStore(tmp_path / "seen.sqlite")
    cand1 = _make_candidate(url="https://example.com/a")
    cand2 = _make_candidate(url="https://example.com/b")
    store.mark_seen(_make_document(cand1, status="saved"))
    store.mark_seen(_make_document(cand2, status="failed"))

    assert store.count_by_status(["saved"]) == 1
    assert store.count_by_status(["failed"]) == 1
    assert store.count_by_status(["saved", "failed"]) == 2
    assert store.count_by_status(["partial"]) == 0
    store.close()
