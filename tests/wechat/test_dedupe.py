"""去重 SeenStore SQLite 测试。"""
from __future__ import annotations

from pathlib import Path

from opc_foundation.wechat.dedupe import WeChatSeenStore, article_id_for
from opc_foundation.wechat.models import ArchivedArticle, ArticleCandidate


def _candidate(url: str, title: str, account: str = "示例公众号A") -> ArticleCandidate:
    return ArticleCandidate(
        source="rss",
        account_name=account,
        account_id="example_a",
        title=title,
        url=url,
        canonical_url=url,
    )


def _archived(cand: ArticleCandidate, status: str = "saved") -> ArchivedArticle:
    return ArchivedArticle(
        article_id=article_id_for(cand),
        source=cand.source,
        account_name=cand.account_name,
        account_id=cand.account_id,
        title=cand.title,
        url=cand.url,
        canonical_url=cand.canonical_url,
        published_at=cand.published_at,
        captured_at="2026-06-22T10:00:00+08:00",
        status=status,
        archive_dir="./articles/2026/06/dir",
        metadata_path="./articles/2026/06/dir/metadata.json",
    )


def test_seen_store_roundtrip(tmp_path: Path):
    db = tmp_path / "seen.sqlite"
    store = WeChatSeenStore(db)
    cand = _candidate("http://mp.weixin.qq.com/s/a", "标题A")
    assert store.has_seen(cand) is False
    store.mark_seen(_archived(cand, status="saved"))
    assert store.has_seen(cand) is True


def test_failed_articles_are_not_blocked(tmp_path: Path):
    """失败的文章不应被永久屏蔽（下次重试仍能被处理）。"""

    db = tmp_path / "seen.sqlite"
    store = WeChatSeenStore(db)
    cand = _candidate("http://mp.weixin.qq.com/s/b", "标题B")
    store.mark_seen(_archived(cand, status="failed"))
    # failed 的 should not be marked as "seen"
    assert store.has_seen(cand) is False


def test_title_fallback_match(tmp_path: Path):
    """当 URL 不一样但账号+标题+发布时间相同时，也能命中。"""

    db = tmp_path / "seen.sqlite"
    store = WeChatSeenStore(db)
    cand_a = ArticleCandidate(
        source="rss",
        account_name="公众号",
        title="同标题",
        url="http://a.example.com/x",
        canonical_url="http://a.example.com/x",
        published_at="2026-06-22",
    )
    cand_b = ArticleCandidate(
        source="rss",
        account_name="公众号",
        title="同标题",
        url="http://b.example.com/y",
        canonical_url="http://b.example.com/y",
        published_at="2026-06-22",
    )
    store.mark_seen(_archived(cand_a))
    assert store.has_seen(cand_b) is True
