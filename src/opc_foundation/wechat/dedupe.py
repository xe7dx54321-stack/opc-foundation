"""文章级别的去重 SeenStore，基于 SQLite。

功能说明（小白解读）：
    这个文件实现了两个能力：
    1) 判断一篇文章是否已经处理过（避免重复归档同一条 URL）
    2) 记录已处理文章的状态（saved / partial / failed / duplicate）

去重 key 的选择：
    - 主 key: sha256(canonical_url)
    - 备用 key: sha256(account_name + title + published_at) （当 URL 无法使用时）

关键行为：
    - 'failed' 状态不永久屏蔽，后续 retry-failed 会重新尝试
    - 'duplicate' 也会写一条记录，便于审计
"""
from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from typing import Iterable

from ..storage.path_utils import ensure_parent
from .models import ArchivedArticle, ArticleCandidate


# SQLite 表结构。我们把 URL hash 和 title hash 都建索引，查询更快。
_SCHEMA = """
CREATE TABLE IF NOT EXISTS seen_articles (
    article_id TEXT PRIMARY KEY,
    url_hash TEXT NOT NULL,
    title_hash TEXT,
    account_name TEXT,
    title TEXT,
    canonical_url TEXT,
    status TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    error TEXT,
    retry_count INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_seen_articles_url_hash ON seen_articles(url_hash);
CREATE INDEX IF NOT EXISTS idx_seen_articles_title_hash ON seen_articles(title_hash);
"""


def _sha256_hex(text: str, length: int = 16) -> str:
    """对字符串做 SHA256，默认截断前 16 位（够用且更易读）。"""

    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:length]


def url_key(url: str) -> str:
    """基于规范化 URL 的去重 key。"""

    return _sha256_hex(url or "")


def title_key(account_name: str, title: str, published_at: str | None) -> str:
    """备用 key：账号名 + 标题 + 发布时间。"""

    parts = [account_name or "", title or "", published_at or ""]
    return _sha256_hex("||".join(parts))


def article_id_for(candidate: ArticleCandidate) -> str:
    """基于 canonical URL 生成稳定的 article_id。"""

    return "wc_" + _sha256_hex(candidate.canonical_url or candidate.url, length=32)


class WeChatSeenStore:
    """文章级 SQLite 去重与状态记录。

    使用示例：
        seen = WeChatSeenStore("./data/wechat_archive/state/seen_articles.sqlite")
        if seen.has_seen(candidate):
            # 标记为重复
            continue
        seen.mark_seen(archived_article)
    """

    # 视为"已处理成功"、不应再重复处理的状态
    _FINAL_STATUSES = {"saved", "partial", "duplicate"}

    def __init__(self, sqlite_path: str | Path) -> None:
        self._path = Path(sqlite_path)
        ensure_parent(self._path)
        self._conn = sqlite3.connect(str(self._path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    def _find_row(
        self,
        candidate: ArticleCandidate,
    ) -> sqlite3.Row | None:
        """查找候选文章是否存在记录。

        策略：先用 URL hash 查，查不到再用 title hash 查。
        只有状态为 saved/partial/duplicate 的记录视为"已见过"。
        """

        cur = self._conn.cursor()
        u_key = url_key(candidate.canonical_url)
        cur.execute(
            "SELECT * FROM seen_articles WHERE url_hash = ? ORDER BY last_seen_at DESC LIMIT 1",
            (u_key,),
        )
        row = cur.fetchone()
        if row is not None:
            return row

        t_key = title_key(
            candidate.account_name or "",
            candidate.title,
            candidate.published_at,
        )
        cur.execute(
            "SELECT * FROM seen_articles WHERE title_hash = ? ORDER BY last_seen_at DESC LIMIT 1",
            (t_key,),
        )
        return cur.fetchone()

    def has_seen(self, candidate: ArticleCandidate) -> bool:
        """判断该候选文章是否已经成功处理过。

        'failed' 不算"已见过"，以便后续可以重试。
        """

        row = self._find_row(candidate)
        if row is None:
            return False
        status = (row["status"] or "").lower()
        return status in self._FINAL_STATUSES

    def get_status(self, candidate: ArticleCandidate) -> str | None:
        """查询该文章最近一次处理的状态（若无记录则返回 None）。"""

        row = self._find_row(candidate)
        if row is None:
            return None
        return row["status"]

    # ------------------------------------------------------------------
    # 写入
    # ------------------------------------------------------------------

    def mark_seen(
        self,
        article: ArchivedArticle,
        now_str: str | None = None,
    ) -> None:
        """把已完成归档的文章写入 seen_articles 表。

        如果同一 URL / 标题已有记录，会更新 last_seen_at 和 status。
        """

        from ..run.time_utils import utcnow_iso

        now = now_str or utcnow_iso()
        u_key = url_key(article.canonical_url)
        t_key = title_key(
            article.account_name or "", article.title, article.published_at
        )

        cur = self._conn.cursor()
        # 用 URL hash 作为唯一键。若已存在则更新状态与最后时间。
        cur.execute(
            "SELECT article_id FROM seen_articles WHERE url_hash = ? LIMIT 1",
            (u_key,),
        )
        existing = cur.fetchone()

        if existing:
            cur.execute(
                """
                UPDATE seen_articles
                SET status = ?,
                    last_seen_at = ?,
                    title = ?,
                    canonical_url = ?,
                    error = ?,
                    retry_count = retry_count + (CASE WHEN status = 'failed' THEN 1 ELSE 0 END)
                WHERE url_hash = ?
                """,
                (
                    article.status,
                    now,
                    article.title,
                    article.canonical_url,
                    article.error,
                    u_key,
                ),
            )
        else:
            cur.execute(
                """
                INSERT INTO seen_articles (
                    article_id, url_hash, title_hash, account_name, title,
                    canonical_url, status, first_seen_at, last_seen_at, error, retry_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    article.article_id,
                    u_key,
                    t_key,
                    article.account_name,
                    article.title,
                    article.canonical_url,
                    article.status,
                    now,
                    now,
                    article.error,
                ),
            )
        self._conn.commit()

    # ------------------------------------------------------------------
    # 工具方法
    # ------------------------------------------------------------------

    def count_by_status(self, statuses: Iterable[str]) -> int:
        """统计某些状态的文章总数。"""

        status_list = list(statuses)
        if not status_list:
            return 0
        placeholders = ",".join(["?"] * len(status_list))
        cur = self._conn.cursor()
        cur.execute(
            f"SELECT COUNT(*) AS c FROM seen_articles WHERE status IN ({placeholders})",
            tuple(status_list),
        )
        row = cur.fetchone()
        return int(row["c"]) if row else 0

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass

    def __enter__(self) -> "WeChatSeenStore":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
