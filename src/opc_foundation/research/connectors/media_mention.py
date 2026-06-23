"""Media Mention 连接器 —— 采集公开媒体对投行观点 / 研报 / 分析师的引用。

功能说明（小白解读）：
    媒体引用（media mention）指 Reuters / MarketWatch / Yahoo Finance / CNBC /
    Investing.com / Barron's / Business Insider 等公开媒体对投行研报、分析师观点、
    评级变动、目标价、会议观点的二次引用内容。

    本 connector 只负责"发现"候选文档，不做投研判断，不判断利好利空。

    本 connector 支持 4 种 extraction_profile：
        - media_mention_article_list: 通用媒体文章列表（<article> / <li>）
        - media_mention_cards:         卡片式媒体新闻页面
        - media_mention_news_list:     新闻列表式媒体页面
        - media_mention_detail:        单篇媒体报道详情页

合规边界：
    - 不访问真实网站（测试用 fixture）
    - 不写针对真实网站的硬编码规则
    - 不做 LLM 分析
    - 不做 affected_tickers / expectation_delta / trade_signal
    - 不做 buy/sell/hold 投资建议
    - 不把 mentioned_tickers 当 affected_tickers
    - 不把 price_target_mention 当投资建议
    - 不保存 cookie/token/API key
    - 不绕过 paywall
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..canonicalize import canonicalize_research_url
from ..models import DocumentCandidate, ResearchArchiveConfig, ResearchSourceConfig
from .base import BaseResearchConnector


# ---------------------------------------------------------------------------
# 类型别名
# ---------------------------------------------------------------------------


HtmlInjector = Callable[[str], str | None]
# 签名：接受 URL，返回预先准备好的 HTML 字符串。返回 None 表示走真实 HTTP。


# ---------------------------------------------------------------------------
# 公开机构名识别（轻量关键词匹配，不做来源质量评分）
# ---------------------------------------------------------------------------


_INSTITUTION_KEYWORDS: tuple[str, ...] = (
    "Goldman Sachs",
    "Morgan Stanley",
    "J.P. Morgan",
    "JPMorgan",
    "Bank of America",
    "BofA",
    "Citi",
    "Citigroup",
    "UBS",
    "Barclays",
    "Deutsche Bank",
    "Bernstein",
    "Jefferies",
    "Mizuho",
    "Evercore",
    "Needham",
    "Wedbush",
)


# ---------------------------------------------------------------------------
# mention_type 识别关键词
# ---------------------------------------------------------------------------


_MENTION_TYPE_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    # 顺序很重要：更具体的类型优先匹配，analyst_quote 作为兜底放后面
    # price_target_mention 放在 rating_action 之前，因为很多评级变动文章同时提到目标价
    ("research_citation", ("research note", "research report", "in a report")),
    ("price_target_mention", ("price target", "target price")),
    (
        "rating_action",
        ("upgrade", "downgrade", "initiated", "reiterate", "maintain", "cuts rating", "raises rating"),
    ),
    ("conference_commentary", ("conference", "webcast", "summit")),
    ("market_commentary", ("market commentary", "outlook", "forecast")),
    # analyst_quote 放最后，因为 analyst/strategist/economist 经常出现在其他类型的文章中
    ("analyst_quote", ("analyst", "strategist", "economist")),
]


def _guess_mention_type(text: str) -> str:
    """从文本中轻量识别 mention_type。

    参数：
        text: 原始文本（标题 / 摘要 / 卡片内容）

    返回：
        mention_type 字符串；未识别返回 "unknown"

    小白解读：
        只做关键词匹配，不做语义判断。
        不判断 rating_action 是否利好，也不判断 price_target_mention 是否利空。
    """
    if not text:
        return "unknown"
    lower = text.lower()
    for mention_type, keywords in _MENTION_TYPE_KEYWORDS:
        for kw in keywords:
            if kw in lower:
                return mention_type
    return "unknown"


def _extract_mentioned_institutions(text: str) -> list[str]:
    """从文本中识别公开机构名。

    参数：
        text: 原始文本

    返回：
        机构名列表（按出现顺序去重）

    小白解读：
        只识别文本中提到的机构名，不代表来源质量评分，不代表观点重要性。
    """
    if not text:
        return []
    seen: set[str] = set()
    result: list[str] = []
    for inst in _INSTITUTION_KEYWORDS:
        if inst in text and inst not in seen:
            seen.add(inst)
            result.append(inst)
    return result


def _extract_mentioned_tickers(text: str) -> list[str]:
    """从文本中识别被提及的 ticker（大写字母组合，2-5 个字符）。

    参数：
        text: 原始文本

    返回：
        ticker 列表（去重）

    小白解读：
        只识别媒体报道原文提到的 ticker，不等同于 watchlist 映射，
        也不是 affected_tickers。
    """
    if not text:
        return []
    import re

    # 匹配全大写字母组合，2-5 个字符，前后是非字母字符或字符串边界
    pattern = re.compile(r"\b[A-Z]{2,5}\b")
    matches = pattern.findall(text)
    seen: set[str] = set()
    result: list[str] = []
    for m in matches:
        if m not in seen:
            seen.add(m)
            result.append(m)
    return result


# ---------------------------------------------------------------------------
# 主类
# ---------------------------------------------------------------------------


class MediaMentionConnector(BaseResearchConnector):
    """媒体引用连接器。

    处理 source_type = media_mention 的信息源。

    支持三种入口：
        - 入口 A：media article list page（extraction_profile=media_mention_article_list）
        - 入口 B：media cards / news list（extraction_profile=media_mention_cards / media_mention_news_list）
        - 入口 C：single media mention detail page（extraction_profile=media_mention_detail）

    测试注入：
        构造时传 html_by_url（按 URL 返回 HTML 字符串），跳过真实 HTTP。
    """

    connector_id = "media_mention"

    def __init__(
        self,
        html_by_url: HtmlInjector | None = None,
    ) -> None:
        """初始化 MediaMentionConnector。

        参数：
            html_by_url: 测试用注入函数，按 URL 返回 HTML 内容
        """
        self._html_by_url = html_by_url

    def discover(
        self,
        source: ResearchSourceConfig,
        config: ResearchArchiveConfig,
    ) -> list[DocumentCandidate]:
        """从媒体引用信息源发现候选文档。

        参数：
            source: 信息源配置
            config: 整体配置

        返回：
            DocumentCandidate 列表

        异常：
            缺少 url 时抛出 ValueError
            内容为空时抛出 ValueError
        """
        profile = source.extraction_profile or "media_mention_article_list"

        # 单页 profile：media_mention_detail
        if profile == "media_mention_detail":
            return self._discover_from_detail_page(source, config, profile)

        # 列表页 profile：media_mention_article_list / media_mention_cards / media_mention_news_list
        return self._discover_from_list(source, config, profile)

    # ------------------------------------------------------------------
    # 入口 A/B：列表页
    # ------------------------------------------------------------------

    def _discover_from_list(
        self,
        source: ResearchSourceConfig,
        config: ResearchArchiveConfig,
        profile: str,
    ) -> list[DocumentCandidate]:
        """从列表页发现候选文档。

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
                f"source [{source.source_id}] media_mention 缺少 url"
            )

        html = self._fetch_html(list_url, source, config)
        if not html or not html.strip():
            raise ValueError(
                f"source [{source.source_id}] media mention 列表页内容为空: {list_url}"
            )

        if profile == "media_mention_cards":
            raw_items = self._parse_cards(html, list_url)
        elif profile == "media_mention_news_list":
            raw_items = self._parse_news_list(html, list_url)
        else:
            # media_mention_article_list
            raw_items = self._parse_article_list(html, list_url)

        return self._items_to_candidates(raw_items, source, config, list_url, profile)

    def _parse_article_list(
        self,
        html: str,
        list_url: str,
    ) -> list[dict]:
        """解析通用媒体文章列表。

        解析策略：
            1. 优先找 <article>
            2. 再找 <li>
            3. 再找 class/id 含 news/article/story/market/research/analyst/bank/broker/rating/report 的块

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

        containers = soup.find_all("article")
        if not containers:
            containers = soup.find_all("li")
        if not containers:
            containers = []
            for tag in soup.find_all(class_=True):
                classes = tag.get("class", [])
                if isinstance(classes, list):
                    classes_str = " ".join(classes).lower()
                else:
                    classes_str = str(classes).lower()
                if any(
                    k in classes_str
                    for k in (
                        "news",
                        "article",
                        "story",
                        "market",
                        "research",
                        "analyst",
                        "bank",
                        "broker",
                        "rating",
                        "report",
                    )
                ):
                    containers.append(tag)

        items: list[dict] = []
        for container in containers:
            link = container.find("a")
            if not link or not link.get("href"):
                continue
            url = link["href"].strip()
            if not url:
                continue
            title = self._extract_text(link) or self._extract_title_from_container(container)
            if not title:
                continue

            text = container.get_text(" ", strip=True)
            item = self._build_item_dict(
                url=url,
                title=title,
                container=container,
                soup=soup,
                text=text,
                document_kind="media_mention",
            )
            items.append(item)

        return items

    def _parse_cards(
        self,
        html: str,
        list_url: str,
    ) -> list[dict]:
        """解析卡片式媒体新闻页面。

        解析策略：
            找 class 含 card/news-card/story-card/article-card/media-card 的元素

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
            if any(
                k in classes_str
                for k in ("card", "news-card", "story-card", "article-card", "media-card")
            ):
                containers.append(tag)

        items: list[dict] = []
        for container in containers:
            link = container.find("a")
            if not link or not link.get("href"):
                continue
            url = link["href"].strip()
            if not url:
                continue
            title = self._extract_text(link) or self._extract_title_from_container(container)
            if not title:
                continue

            text = container.get_text(" ", strip=True)
            item = self._build_item_dict(
                url=url,
                title=title,
                container=container,
                soup=soup,
                text=text,
                document_kind="media_mention_card",
            )
            items.append(item)

        return items

    def _parse_news_list(
        self,
        html: str,
        list_url: str,
    ) -> list[dict]:
        """解析新闻列表式媒体页面。

        解析策略：
            1. 优先找 <article>
            2. 再找 <li>
            3. 再找 class/id 含 news/headline/story/market/analyst/broker/research/rating/target 的块

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

        containers = soup.find_all("article")
        if not containers:
            containers = soup.find_all("li")
        if not containers:
            containers = []
            for tag in soup.find_all(class_=True):
                classes = tag.get("class", [])
                if isinstance(classes, list):
                    classes_str = " ".join(classes).lower()
                else:
                    classes_str = str(classes).lower()
                if any(
                    k in classes_str
                    for k in (
                        "news",
                        "headline",
                        "story",
                        "market",
                        "analyst",
                        "broker",
                        "research",
                        "rating",
                        "target",
                    )
                ):
                    containers.append(tag)

        items: list[dict] = []
        for container in containers:
            link = container.find("a")
            if not link or not link.get("href"):
                continue
            url = link["href"].strip()
            if not url:
                continue
            title = self._extract_text(link) or self._extract_title_from_container(container)
            if not title:
                continue

            text = container.get_text(" ", strip=True)
            item = self._build_item_dict(
                url=url,
                title=title,
                container=container,
                soup=soup,
                text=text,
                document_kind="media_mention_news",
            )
            items.append(item)

        return items

    # ------------------------------------------------------------------
    # 入口 C：单页
    # ------------------------------------------------------------------

    def _discover_from_detail_page(
        self,
        source: ResearchSourceConfig,
        config: ResearchArchiveConfig,
        profile: str,
    ) -> list[DocumentCandidate]:
        """从单篇媒体报道详情页发现候选文档。

        参数：
            source: 信息源配置
            config: 整体配置
            profile: extraction_profile 名称

        返回：
            DocumentCandidate 列表
        """
        page_url = source.url or source.base_url
        if not page_url:
            raise ValueError(
                f"source [{source.source_id}] media_mention 缺少 url"
            )

        html = self._fetch_html(page_url, source, config)
        if not html or not html.strip():
            raise ValueError(
                f"source [{source.source_id}] media mention 页面内容为空: {page_url}"
            )

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
            title = page_url

        canonical = canonicalize_research_url(page_url)
        text = soup.get_text(" ", strip=True)

        # 提取 metadata
        published_at = self._extract_published_at(soup)
        author = self._extract_author(soup)
        media_outlet = self._extract_media_outlet(soup)
        summary = self._extract_summary(soup, None)
        mentioned_institutions = _extract_mentioned_institutions(text)
        mentioned_analysts = self._extract_mentioned_analysts(soup, text)
        mentioned_research = self._extract_mentioned_research(soup, text)
        mention_type = _guess_mention_type(f"{title} {summary or ''} {text}")
        mentioned_tickers = _extract_mentioned_tickers(text)

        candidate = DocumentCandidate(
            source_id=source.source_id,
            source_name=source.source_name,
            source_type="media_mention",
            title=title,
            url=page_url,
            canonical_url=canonical,
            published_at=published_at,
            author=author,
            summary=summary,
            language=self._extract_language(soup),
            legal_profile=source.legal_profile,
            tags=list(source.tags),
            raw_entry={
                "document_kind": "media_mention_detail",
                "published_at": published_at,
                "media_outlet": media_outlet,
                "author": author,
                "mentioned_institutions": mentioned_institutions,
                "mentioned_analysts": mentioned_analysts,
                "mentioned_research": mentioned_research,
                "mention_type": mention_type,
                "mentioned_tickers": mentioned_tickers,
                "detail_url": page_url,
                "profile": profile,
            },
        )
        return [candidate]

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

            # 同一列表页内去重（按 canonical_url + title 双重去重）
            dedup_key = f"{canonical}::{item.get('title', '')}"
            if dedup_key in seen_urls:
                continue
            seen_urls.add(dedup_key)

            candidates.append(
                DocumentCandidate(
                    source_id=source.source_id,
                    source_name=source.source_name,
                    source_type="media_mention",
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
                        "document_kind": item.get("document_kind") or "media_mention",
                        "published_at": item.get("published_at"),
                        "media_outlet": item.get("media_outlet"),
                        "author": item.get("author"),
                        "mentioned_institutions": item.get("mentioned_institutions") or [],
                        "mentioned_analysts": item.get("mentioned_analysts") or [],
                        "mentioned_research": item.get("mentioned_research"),
                        "mention_type": item.get("mention_type") or "unknown",
                        "mentioned_tickers": item.get("mentioned_tickers") or [],
                        "detail_url": abs_url,
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
        """获取 HTML 内容。

        参数：
            url: 页面 URL
            source: 信息源配置
            config: 整体配置

        返回：
            HTML 字符串；失败返回空字符串

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
    # 字段提取工具
    # ------------------------------------------------------------------

    def _build_item_dict(
        self,
        url: str,
        title: str,
        container,
        soup: BeautifulSoup,
        text: str,
        document_kind: str,
    ) -> dict:
        """构造单个 item dict（列表页通用）。

        参数：
            url: 链接 URL
            title: 标题
            container: BeautifulSoup 容器 tag
            soup: 整个页面的 BeautifulSoup 对象
            text: 容器内全部文本
            document_kind: 文档类型标识

        返回：
            item dict
        """
        published_at = self._extract_published_at(container)
        author = self._extract_author(container) or self._extract_by_class_keyword(container, "author")
        media_outlet = self._extract_media_outlet(container)
        summary = self._extract_summary(container, None)
        mentioned_institutions = _extract_mentioned_institutions(text)
        mentioned_analysts = self._extract_mentioned_analysts(container, text)
        mentioned_research = self._extract_mentioned_research(container, text)
        mention_type = _guess_mention_type(f"{title} {summary or ''} {text}")
        mentioned_tickers = _extract_mentioned_tickers(text)

        return {
            "url": url,
            "title": title,
            "published_at": published_at,
            "author": author,
            "media_outlet": media_outlet,
            "summary": summary,
            "language": self._extract_language(soup),
            "mentioned_institutions": mentioned_institutions,
            "mentioned_analysts": mentioned_analysts,
            "mentioned_research": mentioned_research,
            "mention_type": mention_type,
            "mentioned_tickers": mentioned_tickers,
            "document_kind": document_kind,
        }

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
            3. <meta property="article:published_time" content="...">
            4. class 含 "date" / "time" 的元素文本
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

        meta_pub = container.find("meta", attrs={"property": "article:published_time"})
        if meta_pub and meta_pub.get("content"):
            return meta_pub["content"].strip()

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

    def _extract_author(self, container) -> str | None:
        """从容器里提取作者。

        查找顺序：
            1. class 含 "author" 的元素
            2. <meta name="author" content="...">
            3. <meta property="article:author" content="...">
        """
        if container is None:
            return None

        # class 含 author
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

        # meta 标签
        meta_author = container.find("meta", attrs={"name": "author"})
        if meta_author and meta_author.get("content"):
            return meta_author["content"].strip()

        meta_article_author = container.find("meta", attrs={"property": "article:author"})
        if meta_article_author and meta_article_author.get("content"):
            return meta_article_author["content"].strip()

        return None

    def _extract_media_outlet(self, container) -> str | None:
        """从容器里提取媒体机构名（media_outlet）。

        查找顺序：
            1. class 含 "media-outlet" / "outlet" / "source" 的元素
            2. <meta property="og:site_name" content="...">
        """
        if container is None:
            return None

        for cls_tag in container.find_all(class_=True):
            classes = cls_tag.get("class", [])
            if isinstance(classes, list):
                classes_str = " ".join(classes).lower()
            else:
                classes_str = str(classes).lower()
            if any(k in classes_str for k in ("media-outlet", "outlet", "source")):
                text = self._extract_text(cls_tag)
                if text:
                    return text

        meta_site = container.find("meta", attrs={"property": "og:site_name"})
        if meta_site and meta_site.get("content"):
            return meta_site["content"].strip()

        return None

    def _extract_summary(self, container, link) -> str | None:
        """从容器里提取摘要。

        查找顺序：
            1. class 含 "summary" / "description" / "excerpt" 的元素
            2. <meta name="description" content="...">
            3. <p> 标签文本（取第一个非空且非链接文本）
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

        meta_desc = container.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            return meta_desc["content"].strip()

        for p in container.find_all("p"):
            text = self._extract_text(p)
            if text and len(text) > 10:
                return text

        return None

    def _extract_by_class_keyword(self, container, keyword: str) -> str | None:
        """从容器里按 class 关键词提取文本。

        参数：
            container: BeautifulSoup tag 或 soup
            keyword: class 关键词

        返回：
            匹配元素的文本；未找到返回 None
        """
        if container is None:
            return None

        for cls_tag in container.find_all(class_=True):
            classes = cls_tag.get("class", [])
            if isinstance(classes, list):
                classes_str = " ".join(classes).lower()
            else:
                classes_str = str(classes).lower()
            if keyword in classes_str:
                text = self._extract_text(cls_tag)
                if text:
                    return text

        return None

    def _extract_mentioned_analysts(self, container, text: str) -> list[str]:
        """从容器里提取被提及的分析师名。

        解析策略：
            1. class 含 "analyst" 的元素文本
            2. 文本中识别 "analyst Jane Doe" / "strategist John Smith" / "economist Bob Wang" 模式

        参数：
            container: BeautifulSoup 容器
            text: 容器内全部文本

        返回：
            分析师名列表（去重）
        """
        if container is None:
            return []

        seen: set[str] = set()
        result: list[str] = []

        # 1. class 含 analyst
        for cls_tag in container.find_all(class_=True):
            classes = cls_tag.get("class", [])
            if isinstance(classes, list):
                classes_str = " ".join(classes).lower()
            else:
                classes_str = str(classes).lower()
            if "analyst" in classes_str:
                t = self._extract_text(cls_tag)
                if t and t not in seen:
                    seen.add(t)
                    result.append(t)

        # 2. 文本模式匹配：analyst/strategist/economist + Name
        if text:
            import re

            # 匹配 "analyst Jane Doe" / "strategist John Smith" / "economist Bob Wang"
            pattern = re.compile(
                r"\b(?:analyst|strategist|economist)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)"
            )
            for m in pattern.finditer(text):
                name = m.group(1).strip()
                if name not in seen:
                    seen.add(name)
                    result.append(name)

        return result

    def _extract_mentioned_research(self, container, text: str) -> str | None:
        """从容器里提取被提及的研报/研究主题。

        解析策略：
            1. class 含 "research" / "report" / "note" 的元素文本
            2. 文本中识别 "research note" / "research report" / "in a report" 上下文

        参数：
            container: BeautifulSoup 容器
            text: 容器内全部文本

        返回：
            研报描述字符串；未找到返回 None
        """
        if container is None:
            return None

        # 1. class 含 research/report/note
        for cls_tag in container.find_all(class_=True):
            classes = cls_tag.get("class", [])
            if isinstance(classes, list):
                classes_str = " ".join(classes).lower()
            else:
                classes_str = str(classes).lower()
            if any(k in classes_str for k in ("research", "report", "note")):
                t = self._extract_text(cls_tag)
                if t:
                    return t

        # 2. 文本中找 "research note" / "research report" 上下文
        if text:
            lower = text.lower()
            for kw in ("research note", "research report", "in a report"):
                idx = lower.find(kw)
                if idx >= 0:
                    # 截取关键词前后 80 字符作为上下文
                    start = max(0, idx - 40)
                    end = min(len(text), idx + len(kw) + 80)
                    return text[start:end].strip()

        return None

    def _extract_language(self, soup: BeautifulSoup) -> str | None:
        """从 <html lang="..."> 提取页面语言。"""
        html_tag = soup.find("html")
        if html_tag and html_tag.get("lang"):
            return html_tag["lang"].strip()
        return None
