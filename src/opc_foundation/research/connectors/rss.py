"""RSS / Atom feed 连接器。

功能说明（小白解读）：
    读取一个 RSS/Atom feed，解析出每条 entry 的标题、链接、发布时间、摘要、作者，
    转换成 DocumentCandidate 列表返回。

    复用仓库已有依赖：
    - feedparser（业界通用的 feed 解析库）
    - opc_foundation.research.canonicalize.canonicalize_research_url

    feed 内容可以通过 feed_content 参数注入（测试用），不访问真实网络。
"""
from __future__ import annotations

from typing import Any, Callable

import feedparser

from ..canonicalize import canonicalize_research_url
from ..models import DocumentCandidate, ResearchArchiveConfig, ResearchSourceConfig
from .base import BaseResearchConnector


class RSSConnector(BaseResearchConnector):
    """RSS/Atom feed 连接器。

    处理 source_type = rss_feed 的信息源。

    测试注入：
        构造时传 feed_content_by_url（按 feed_url 返回字符串），
        或子类覆盖 _fetch_feed_content 方法。
    """

    connector_id = "rss"

    def __init__(
        self,
        feed_content_by_url: Callable[[str], str | bytes | None] | None = None,
    ) -> None:
        """初始化 RSSConnector。

        参数：
            feed_content_by_url: 测试用注入函数，按 feed_url 返回 feed 内容
        """
        self._feed_content_by_url = feed_content_by_url

    def discover(
        self,
        source: ResearchSourceConfig,
        config: ResearchArchiveConfig,
    ) -> list[DocumentCandidate]:
        """从 RSS feed 发现候选文档。

        参数：
            source: 信息源配置（使用 source.feed_url 或 source.url）
            config: 整体配置（使用 config.defaults.max_items_per_source）

        返回：
            DocumentCandidate 列表

        异常：
            解析失败时抛出 ValueError，由上层 archiver 捕获并记录到 failed_queue
        """

        feed_url = source.feed_url or source.url
        if not feed_url:
            raise ValueError(f"source [{source.source_id}] 缺少 feed_url / url")

        # 下载 feed 内容（由上层注入或真实 HTTP）
        feed_content = self._fetch_feed_content(feed_url, source, config)
        if not feed_content:
            raise ValueError(f"source [{source.source_id}] feed 内容为空: {feed_url}")

        # 解析 feed
        parsed = feedparser.parse(feed_content)
        if parsed.get("bozo") and not parsed.get("entries"):
            bozo_exc = parsed.get("bozo_exception")
            raise ValueError(
                f"source [{source.source_id}] feed 解析失败: {bozo_exc}"
            )

        max_items = source.max_items or config.defaults.max_items_per_source
        entries = list(parsed.get("entries", []))[:max_items]

        candidates: list[DocumentCandidate] = []
        for entry in entries:
            title = entry.get("title") or ""
            link = entry.get("link") or ""
            summary = entry.get("summary") or entry.get("description") or ""
            published = entry.get("published") or entry.get("updated") or ""
            author = entry.get("author") or ""

            if not link:
                # 没有 link 的 entry 跳过（无法归档）
                continue

            canonical = canonicalize_research_url(link)
            candidates.append(
                DocumentCandidate(
                    source_id=source.source_id,
                    source_name=source.source_name,
                    source_type=source.source_type,
                    title=title or link,
                    url=link,
                    canonical_url=canonical,
                    published_at=published or None,
                    author=author or None,
                    summary=summary or None,
                    legal_profile=source.legal_profile,
                    tags=list(source.tags),
                    raw_entry=_entry_to_dict(entry),
                )
            )

        return candidates

    def _fetch_feed_content(
        self,
        feed_url: str,
        source: ResearchSourceConfig,
        config: ResearchArchiveConfig,
    ) -> str | bytes | None:
        """下载 feed 内容。

        参数：
            feed_url: feed 地址
            source:   信息源配置
            config:   整体配置

        返回：
            feed 内容（字符串或 bytes）；失败返回 None

        说明：
            优先使用构造时注入的 feed_content_by_url（测试用）。
            生产环境用 httpx 下载。
        """
        # 测试注入优先
        if self._feed_content_by_url is not None:
            return self._feed_content_by_url(feed_url)

        # 本地文件路径（以 ./ 或 ../ 开头）直接读取
        if feed_url.startswith(("./", "../", "/")) or not feed_url.startswith(("http://", "https://")):
            from pathlib import Path
            p = Path(feed_url)
            if p.exists():
                return p.read_bytes()
            return None

        # 真实 HTTP 下载
        import httpx
        try:
            with httpx.Client(
                timeout=config.defaults.fetch_timeout_seconds,
                follow_redirects=True,
            ) as client:
                resp = client.get(feed_url, headers={"User-Agent": config.defaults.user_agent})
                resp.raise_for_status()
                return resp.content
        except Exception:
            return None


def _entry_to_dict(entry: Any) -> dict[str, Any]:
    """把 feedparser entry 转成可序列化的 dict（用于 raw_entry 字段）。"""

    try:
        # feedparser entry 有 .get() 方法，但不是标准 dict
        return dict(entry)
    except Exception:
        return {"title": getattr(entry, "title", ""), "link": getattr(entry, "link", "")}
