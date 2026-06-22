"""Podcast Transcript 连接器 —— 采集播客 transcript 页面。

功能说明（小白解读）：
    很多金融机构（Morgan Stanley、UBS、BofA、Goldman、JPM 等）都会发布播客，
    讨论市场展望、行业研究、宏观观点。这些播客通常有配套的 transcript 文字稿。

    本 connector 支持 4 种 extraction_profile：
        - podcast_episode_list:  通用播客 episode 列表页（HTML）
        - simple_episode_cards:  卡片式 episode 列表（HTML）
        - podcast_feed:          RSS/Atom feed（XML）
        - transcript_page:       单篇 transcript 页面（HTML）

    本阶段只负责"发现"候选文档，生成 DocumentCandidate。
    后续的正文抓取/抽取/归档由 archiver + fetcher + extractor + storage 完成。

合规边界：
    - 不访问真实网站（测试用 fixture）
    - 不写针对真实网站的硬编码规则
    - 不做 LLM 分析
    - 不做 affected_tickers / expectation_delta / trade_signal
    - 不保存 cookie/token/API key
    - 不绕过 paywall
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable
from urllib.parse import urljoin

import feedparser
from bs4 import BeautifulSoup

from ..canonicalize import canonicalize_research_url
from ..models import DocumentCandidate, ResearchArchiveConfig, ResearchSourceConfig
from .base import BaseResearchConnector


# ---------------------------------------------------------------------------
# 类型别名
# ---------------------------------------------------------------------------


HtmlInjector = Callable[[str], str | None]
# 签名：接受 URL，返回预先准备好的 HTML/XML 字符串。返回 None 表示走真实 HTTP。


# ---------------------------------------------------------------------------
# 主类
# ---------------------------------------------------------------------------


class PodcastTranscriptConnector(BaseResearchConnector):
    """播客 transcript 连接器。

    处理 source_type = podcast_transcript 的信息源。

    支持两种入口：
        - 入口 A：podcast list page（source.url + extraction_profile=podcast_episode_list/simple_episode_cards/transcript_page）
        - 入口 B：podcast RSS/Atom feed（source.feed_url + extraction_profile=podcast_feed）

    测试注入：
        构造时传 html_by_url（按 URL 返回 HTML/XML 字符串），跳过真实 HTTP。
    """

    connector_id = "podcast_transcript"

    def __init__(
        self,
        html_by_url: HtmlInjector | None = None,
    ) -> None:
        """初始化 PodcastTranscriptConnector。

        参数：
            html_by_url: 测试用注入函数，按 URL 返回 HTML/XML 内容
        """
        self._html_by_url = html_by_url

    def discover(
        self,
        source: ResearchSourceConfig,
        config: ResearchArchiveConfig,
    ) -> list[DocumentCandidate]:
        """从播客信息源发现候选文档。

        参数：
            source: 信息源配置
            config: 整体配置

        返回：
            DocumentCandidate 列表

        异常：
            缺少 url/feed_url 时抛出 ValueError
            内容为空时抛出 ValueError
        """

        profile = source.extraction_profile or "podcast_episode_list"

        # 入口 B：RSS/Atom feed
        if profile == "podcast_feed":
            return self._discover_from_feed(source, config)

        # 入口 A：HTML 页面
        return self._discover_from_html(source, config, profile)

    # ------------------------------------------------------------------
    # 入口 A：HTML 页面
    # ------------------------------------------------------------------

    def _discover_from_html(
        self,
        source: ResearchSourceConfig,
        config: ResearchArchiveConfig,
        profile: str,
    ) -> list[DocumentCandidate]:
        """从 HTML 页面发现候选文档。

        参数：
            source: 信息源配置
            config: 整体配置
            profile: extraction_profile 名称

        返回：
            DocumentCandidate 列表
        """

        list_url = source.url or source.base_url
        if not list_url:
            raise ValueError(
                f"source [{source.source_id}] podcast_transcript 缺少 url"
            )

        html = self._fetch_html(list_url, source, config)
        if not html or not html.strip():
            raise ValueError(
                f"source [{source.source_id}] podcast 页面内容为空: {list_url}"
            )

        # transcript_page：单篇 transcript 直接生成 1 个 candidate
        if profile == "transcript_page":
            return self._parse_transcript_page(html, list_url, source)

        # 列表页解析
        if profile == "simple_episode_cards":
            raw_items = self._parse_episode_cards(html, list_url)
        else:
            # 默认 podcast_episode_list
            raw_items = self._parse_episode_list(html, list_url)

        return self._items_to_candidates(raw_items, source, config, list_url, profile)

    def _parse_episode_list(
        self,
        html: str,
        list_url: str,
    ) -> list[dict]:
        """通用播客 episode 列表解析。

        解析策略：
            1. 优先找 <article>
            2. 再找 <li>
            3. 再找 class/id 含 episode/podcast/transcript 的块
            4. 在块内找第一个有效 <a href>
            5. 提取 title / time / summary / author

        参数：
            html: HTML 字符串
            list_url: 列表页 URL

        返回：
            dict 列表
        """

        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception:
            return []

        # 1. 优先找 <article>
        containers = soup.find_all("article")
        if not containers:
            # 2. 再找 <li>
            containers = soup.find_all("li")
        if not containers:
            # 3. 再找 class/id 含 episode/podcast/transcript 的块
            containers = []
            for tag in soup.find_all(class_=True):
                classes = tag.get("class", [])
                if isinstance(classes, list):
                    classes_str = " ".join(classes).lower()
                else:
                    classes_str = str(classes).lower()
                if any(k in classes_str for k in ("episode", "podcast", "transcript")):
                    containers.append(tag)

        items: list[dict] = []
        for container in containers:
            link = container.find("a")
            if not link or not link.get("href"):
                continue
            url = link["href"].strip()
            title = self._extract_text(link) or self._extract_title_from_container(container)
            if not title:
                continue

            item = {
                "url": url,
                "title": title,
                "published_at": self._extract_published_at(container),
                "summary": self._extract_summary(container, link),
                "author": self._extract_author(container),
                "language": self._extract_language(soup),
                "duration": self._extract_duration(container),
                "episode_id": self._extract_episode_id(container),
            }
            items.append(item)

        return items

    def _parse_episode_cards(
        self,
        html: str,
        list_url: str,
    ) -> list[dict]:
        """卡片式 episode 列表解析。

        解析策略：
            找 class 含 card/episode-card/podcast-card 的元素

        参数：
            html: HTML 字符串
            list_url: 列表页 URL

        返回：
            dict 列表
        """

        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception:
            return []

        containers = []
        for tag in soup.find_all(class_=True):
            classes = tag.get("class", [])
            if isinstance(classes, list):
                classes_str = " ".join(classes).lower()
            else:
                classes_str = str(classes).lower()
            if any(k in classes_str for k in ("card", "episode-card", "podcast-card")):
                containers.append(tag)

        items: list[dict] = []
        for container in containers:
            link = container.find("a")
            if not link or not link.get("href"):
                continue
            url = link["href"].strip()
            title = self._extract_text(link) or self._extract_title_from_container(container)
            if not title:
                continue

            item = {
                "url": url,
                "title": title,
                "published_at": self._extract_published_at(container),
                "summary": self._extract_summary(container, link),
                "author": self._extract_author(container),
                "language": self._extract_language(soup),
                "duration": self._extract_duration(container),
                "episode_id": self._extract_episode_id(container),
            }
            items.append(item)

        return items

    def _parse_transcript_page(
        self,
        html: str,
        page_url: str,
        source: ResearchSourceConfig,
    ) -> list[DocumentCandidate]:
        """单篇 transcript 页面：直接生成 1 个 candidate。

        参数：
            html: HTML 字符串
            page_url: 页面 URL
            source: 信息源配置

        返回：
            含 1 个 DocumentCandidate 的列表
        """

        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception:
            return []

        # 标题：h1 → <title> → og:title
        title = ""
        h1 = soup.find("h1")
        if h1:
            title = self._extract_text(h1)
        if not title and soup.title and soup.title.string:
            title = soup.title.string.strip()
        if not title:
            og_title = soup.find("meta", property="og:title")
            if og_title and og_title.get("content"):
                title = og_title["content"].strip()
        if not title:
            title = page_url  # 兜底用 URL

        canonical = canonicalize_research_url(page_url)

        candidate = DocumentCandidate(
            source_id=source.source_id,
            source_name=source.source_name,
            source_type="podcast_transcript",
            title=title,
            url=page_url,
            canonical_url=canonical,
            published_at=self._extract_published_at(soup),
            author=self._extract_author(soup),
            summary=self._extract_summary(soup, None),
            language=self._extract_language(soup),
            legal_profile=source.legal_profile,
            tags=list(source.tags),
            raw_entry={
                "episode_url": page_url,
                "transcript_url": page_url,
                "profile": "transcript_page",
            },
        )
        return [candidate]

    # ------------------------------------------------------------------
    # 入口 B：RSS/Atom feed
    # ------------------------------------------------------------------

    def _discover_from_feed(
        self,
        source: ResearchSourceConfig,
        config: ResearchArchiveConfig,
    ) -> list[DocumentCandidate]:
        """从 RSS/Atom feed 发现候选文档。

        参数：
            source: 信息源配置
            config: 整体配置

        返回：
            DocumentCandidate 列表
        """

        feed_url = source.feed_url or source.url
        if not feed_url:
            raise ValueError(
                f"source [{source.source_id}] podcast_feed 缺少 feed_url"
            )

        feed_content = self._fetch_html(feed_url, source, config)
        if not feed_content:
            raise ValueError(
                f"source [{source.source_id}] podcast feed 内容为空: {feed_url}"
            )

        parsed = feedparser.parse(feed_content)
        if parsed.get("bozo") and not parsed.get("entries"):
            bozo_exc = parsed.get("bozo_exception")
            raise ValueError(
                f"source [{source.source_id}] podcast feed 解析失败: {bozo_exc}"
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
            # enclosure 通常是音频文件
            audio_url = None
            for enc in entry.get("enclosures", []) or []:
                audio_url = enc.get("href") or enc.get("url")
                if audio_url:
                    break

            # transcript URL：优先 links 中 type=text/html 的，否则用 link
            transcript_url = link
            for l in entry.get("links", []) or []:
                if l.get("type", "").startswith("text/"):
                    transcript_url = l.get("href") or transcript_url
                    break

            if not transcript_url:
                continue

            canonical = canonicalize_research_url(transcript_url)
            candidates.append(
                DocumentCandidate(
                    source_id=source.source_id,
                    source_name=source.source_name,
                    source_type="podcast_transcript",
                    title=title or transcript_url,
                    url=transcript_url,
                    canonical_url=canonical,
                    published_at=published or None,
                    author=author or None,
                    summary=summary or None,
                    language=None,
                    legal_profile=source.legal_profile,
                    tags=list(source.tags),
                    raw_entry={
                        "episode_url": link or transcript_url,
                        "transcript_url": transcript_url,
                        "audio_url": audio_url,
                        "feed_guid": entry.get("id") or entry.get("guid"),
                        "profile": "podcast_feed",
                    },
                )
            )

        return candidates

    # ------------------------------------------------------------------
    # 候选文档构造
    # ------------------------------------------------------------------

    def _items_to_candidates(
        self,
        items: list[dict],
        source: ResearchSourceConfig,
        config: ResearchArchiveConfig,
        list_url: str,
        profile: str,
    ) -> list[DocumentCandidate]:
        """把原始 item dict 列表转成 DocumentCandidate 列表。

        参数：
            items: 原始 item dict 列表
            source: 信息源配置
            config: 整体配置
            list_url: 列表页 URL（用于解析相对链接）
            profile: extraction_profile 名称

        返回：
            DocumentCandidate 列表
        """

        max_items = source.max_items or config.defaults.max_items_per_source
        candidates: list[DocumentCandidate] = []
        seen_urls: set[str] = set()

        for item in items[:max_items]:
            url = item.get("url")
            if not url:
                continue
            # 相对 URL 转 absolute
            abs_url = urljoin(list_url, url)
            canonical = canonicalize_research_url(abs_url)

            # 同一列表页内去重
            if canonical in seen_urls:
                continue
            seen_urls.add(canonical)

            candidates.append(
                DocumentCandidate(
                    source_id=source.source_id,
                    source_name=source.source_name,
                    source_type="podcast_transcript",
                    title=item.get("title") or abs_url,
                    url=abs_url,
                    canonical_url=canonical,
                    published_at=item.get("published_at"),
                    author=item.get("author"),
                    summary=item.get("summary"),
                    language=item.get("language"),
                    legal_profile=source.legal_profile,
                    tags=list(source.tags),
                    raw_entry={
                        "episode_url": abs_url,
                        "transcript_url": abs_url,
                        "duration": item.get("duration"),
                        "episode_id": item.get("episode_id"),
                        "profile": profile,
                    },
                )
            )

        return candidates

    # ------------------------------------------------------------------
    # HTML 抓取
    # ------------------------------------------------------------------

    def _fetch_html(
        self,
        url: str,
        source: ResearchSourceConfig,
        config: ResearchArchiveConfig,
    ) -> str:
        """获取 HTML/XML 内容。

        参数：
            url: 页面/feed URL
            source: 信息源配置
            config: 整体配置

        返回：
            HTML/XML 字符串；失败返回空字符串

        说明：
            优先使用构造时注入的 html_by_url（测试用）。
            本地文件路径直接读取。
            生产环境用 httpx 下载。
        """

        # 测试注入优先
        if self._html_by_url is not None:
            return self._html_by_url(url) or ""

        # 本地文件路径直接读取
        if url.startswith(("./", "../", "/")) or not url.startswith(("http://", "https://")):
            p = Path(url)
            if p.exists():
                return p.read_text(encoding="utf-8")
            return ""

        # 真实 HTTP 下载
        from ..fetcher import fetch_url

        result = fetch_url(
            url,
            timeout=config.defaults.fetch_timeout_seconds,
            user_agent=config.defaults.user_agent,
        )
        return result.html if result.ok else ""

    # ------------------------------------------------------------------
    # 字段提取工具（复用 official_public 的模式）
    # ------------------------------------------------------------------

    def _extract_text(self, tag) -> str:
        """提取标签内的纯文本，去掉首尾空白。"""
        if tag is None:
            return ""
        return tag.get_text(strip=True)

    def _extract_title_from_container(self, container) -> str:
        """从容器里找标题（h1/h2/h3/h4）。"""
        for tag_name in ("h1", "h2", "h3", "h4"):
            title_tag = container.find(tag_name)
            if title_tag:
                return self._extract_text(title_tag)
        return ""

    def _extract_published_at(self, container) -> str | None:
        """从容器里提取发布时间。

        查找顺序：
            1. <time datetime="..."> 的 datetime 属性
            2. <meta name="date" content="...">
            3. class 含 "date" / "time" 的元素文本
        """

        if container is None:
            return None

        time_tag = container.find("time")
        if time_tag:
            dt = time_tag.get("datetime")
            if dt:
                return dt.strip()
            text = self._extract_text(time_tag)
            if text:
                return text

        meta_date = container.find("meta", attrs={"name": "date"})
        if meta_date and meta_date.get("content"):
            return meta_date["content"].strip()

        for cls_tag in container.find_all(class_=True):
            classes = cls_tag.get("class", [])
            if isinstance(classes, list):
                classes_str = " ".join(classes).lower()
            else:
                classes_str = str(classes).lower()
            if "date" in classes_str or "time" in classes_str:
                text = self._extract_text(cls_tag)
                if text:
                    return text

        return None

    def _extract_summary(self, container, link) -> str | None:
        """从容器里提取摘要。

        查找顺序：
            1. class 含 "summary" / "description" / "excerpt" 的元素
            2. <p> 标签文本（取第一个非空且非链接文本）
        """

        if container is None:
            return None

        for cls_tag in container.find_all(class_=True):
            classes = cls_tag.get("class", [])
            if isinstance(classes, list):
                classes_str = " ".join(classes).lower()
            else:
                classes_str = str(classes).lower()
            if any(k in classes_str for k in ("summary", "description", "excerpt")):
                text = self._extract_text(cls_tag)
                if text:
                    return text

        for p in container.find_all("p"):
            text = self._extract_text(p)
            if text and len(text) > 10:
                return text

        return None

    def _extract_author(self, container) -> str | None:
        """从容器里提取作者。

        查找顺序：
            1. <meta name="author">
            2. class 含 "author" 的元素
        """

        if container is None:
            return None

        meta_author = container.find("meta", attrs={"name": "author"})
        if meta_author and meta_author.get("content"):
            return meta_author["content"].strip()

        for cls_tag in container.find_all(class_=True):
            classes = cls_tag.get("class", [])
            if isinstance(classes, list):
                classes_str = " ".join(classes).lower()
            else:
                classes_str = str(classes).lower()
            if "author" in classes_str:
                text = self._extract_text(cls_tag)
                if text:
                    return text

        return None

    def _extract_language(self, soup: BeautifulSoup) -> str | None:
        """从 <html lang="..."> 提取页面语言。"""
        html_tag = soup.find("html")
        if html_tag and html_tag.get("lang"):
            return html_tag["lang"].strip()
        return None

    def _extract_duration(self, container) -> str | None:
        """从容器里提取时长。

        查找顺序：
            1. class 含 "duration" / "length" 的元素
            2. <meta name="duration">
        """

        if container is None:
            return None

        for cls_tag in container.find_all(class_=True):
            classes = cls_tag.get("class", [])
            if isinstance(classes, list):
                classes_str = " ".join(classes).lower()
            else:
                classes_str = str(classes).lower()
            if "duration" in classes_str or "length" in classes_str:
                text = self._extract_text(cls_tag)
                if text:
                    return text

        meta_dur = container.find("meta", attrs={"name": "duration"})
        if meta_dur and meta_dur.get("content"):
            return meta_dur["content"].strip()

        return None

    def _extract_episode_id(self, container) -> str | None:
        """从容器里提取 episode ID。

        查找顺序：
            1. data-episode-id 属性
            2. class 含 "episode-id" 的元素
        """

        if container is None:
            return None

        # data-episode-id 属性
        tag_with_id = container.find(attrs={"data-episode-id": True})
        if tag_with_id:
            return tag_with_id["data-episode-id"].strip()

        for cls_tag in container.find_all(class_=True):
            classes = cls_tag.get("class", [])
            if isinstance(classes, list):
                classes_str = " ".join(classes).lower()
            else:
                classes_str = str(classes).lower()
            if "episode-id" in classes_str:
                text = self._extract_text(cls_tag)
                if text:
                    return text

        return None
