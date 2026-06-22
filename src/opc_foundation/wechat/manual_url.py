"""手工 URL 投喂。

功能说明（小白解读）：
    用户可以把想归档的微信文章 URL 直接写到一个 txt 里，每行一条。
    本文件读取这些 URL，生成 ArticleCandidate（没有标题就用 URL 当作标题，
    真正的标题会在后续正文抓取阶段解析到后回填）。
"""
from __future__ import annotations

from pathlib import Path

from .feed_client import canonicalize_wechat_url
from .models import ArticleCandidate


def load_manual_urls(path: str | Path) -> list[str]:
    """从文本文件读取 URL 列表（去重、去注释、去空行）。

    参数：
        path: 文本文件路径

    返回：
        一个 URL 列表（按文件顺序）
    """

    p = Path(path)
    if not p.exists():
        return []

    urls: list[str] = []
    seen: set[str] = set()
    with open(p, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line in seen:
                continue
            seen.add(line)
            urls.append(line)
    return urls


def load_manual_url_candidates(
    path: str | Path,
    account_name: str = "手工投喂",
    account_id: str | None = "manual",
) -> list[ArticleCandidate]:
    """从手工 URL 文件生成 ArticleCandidate 列表。

    参数：
        path:         文本文件路径
        account_name: 来源公众号名（用于目录命名，默认"手工投喂"）
        account_id:   来源账号 ID（默认 'manual'）

    返回：
        ArticleCandidate 列表
    """

    candidates: list[ArticleCandidate] = []
    for url in load_manual_urls(path):
        canonical = canonicalize_wechat_url(url)
        candidates.append(
            ArticleCandidate(
                source="manual",
                account_name=account_name,
                account_id=account_id,
                title=url,  # 标题先放 URL，正文抓取后会回填
                url=url,
                canonical_url=canonical,
                raw_entry={"original_url": url},
            )
        )
    return candidates


def build_manual_candidate(
    url: str,
    account_name: str = "手工投喂",
    account_id: str | None = "manual",
) -> ArticleCandidate:
    """基于单个 URL 直接构造候选（在 archiver.retry_failed 等地方用）。"""

    canonical = canonicalize_wechat_url(url)
    return ArticleCandidate(
        source="manual",
        account_name=account_name,
        account_id=account_id,
        title=url,
        url=url,
        canonical_url=canonical,
        raw_entry={"original_url": url},
    )
