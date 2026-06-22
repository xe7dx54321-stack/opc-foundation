"""Official Public Research 连接器 —— 采集官方公开研究页面。

功能说明（小白解读）：
    很多金融机构、研究机构、监管机构都会在官网上发布公开研究报告。
    这些页面通常是"列表页 + 详情页"两段式结构：
        - 列表页：展示最近发布的研究文章，含标题、链接、发布日期、摘要
        - 详情页：点进去是完整文章正文

    本 connector 只负责"发现"列表页上的候选文档，生成 DocumentCandidate。
    后续的正文抓取/抽取/归档由 archiver + fetcher + extractor + storage 完成。

支持的 extraction_profile（列表页解析策略）：
    - generic_article_list: 通用文章列表，找 <article> / <li> 里的 <a> 链接
    - simple_card_list:     卡片式列表，找带 class 含 "card" 的元素里的链接
    - link_list:            最朴素，列出页面所有 <a> 链接（带标题文本）

    不为真实网站写硬编码规则，只基于通用 HTML 结构解析。

合规边界：
    - 不访问真实网站（测试用 fixture）
    - 不写投行业务逻辑（不判断 Goldman/Morgan/JPM 哪个更重要）
    - 不做 affected_tickers / expectation_delta / trade_signal
    - 只采集公开可访问的列表页
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


ListHtmlInjector = Callable[[str], str | None]
# 签名：接受 list page URL，返回预先准备好的 HTML 字符串。返回 None 表示走真实 HTTP。


# ---------------------------------------------------------------------------
# 主类
# ---------------------------------------------------------------------------


class OfficialPublicResearchConnector(BaseResearchConnector):
    """官方公开研究页面连接器。

    处理 source_type = official_public_research 的信息源。

    使用方式：
        1. 在 source 配置里指定 url（列表页地址）和 extraction_profile
        2. connector 读取列表页 HTML，解析出候选文档
        3. 候选文档交给 archiver 抓取详情页正文

    测试注入：
        构造时传 list_html_by_url（按 URL 返回 HTML 字符串），跳过真实 HTTP。
    """

    connector_id = "official_public_research"

    def __init__(
        self,
        list_html_by_url: ListHtmlInjector | None = None,
    ) -> None:
        """初始化 connector。

        参数：
            list_html_by_url: 测试用注入函数，按 URL 返回列表页 HTML
        """
        self._list_html_by_url = list_html_by_url

    def discover(
        self,
        source: ResearchSourceConfig,
        config: ResearchArchiveConfig,
    ) -> list[DocumentCandidate]:
        """从官方研究列表页发现候选文档。

        参数：
            source: 信息源配置（使用 source.url 作为列表页地址）
            config: 整体配置

        返回：
            DocumentCandidate 列表

        异常：
            缺少 url 时抛出 ValueError
            列表页内容为空时抛出 ValueError
        """

        list_url = source.url or source.base_url
        if not list_url:
            raise ValueError(
                f"source [{source.source_id}] official_public_research 缺少 url"
            )

        # 获取列表页 HTML
        html = self._fetch_list_html(list_url, source, config)
        if not html or not html.strip():
            raise ValueError(
                f"source [{source.source_id}] 列表页内容为空: {list_url}"
            )

        # 根据 extraction_profile 选择解析策略
        profile = source.extraction_profile or "generic_article_list"
        raw_items = self._parse_list_html(html, profile, list_url, source)

        # 转成 DocumentCandidate
        max_items = source.max_items or config.defaults.max_items_per_source
        candidates: list[DocumentCandidate] = []
        seen_urls: set[str] = set()

        for item in raw_items[:max_items]:
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
                    source_type=source.source_type,
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
                        "list_url": list_url,
                        "extraction_profile": profile,
                        "original_url": url,
                    },
                )
            )

        return candidates

    # ------------------------------------------------------------------
    # HTML 抓取
    # ------------------------------------------------------------------

    def _fetch_list_html(
        self,
        list_url: str,
        source: ResearchSourceConfig,
        config: ResearchArchiveConfig,
    ) -> str:
        """获取列表页 HTML 内容。

        参数：
            list_url: 列表页 URL
            source:   信息源配置
            config:   整体配置

        返回：
            HTML 字符串；失败返回空字符串

        说明：
            优先使用构造时注入的 list_html_by_url（测试用）。
            本地文件路径直接读取。
            生产环境用 httpx 下载（复用 fetcher 的能力）。
        """

        # 测试注入优先
        if self._list_html_by_url is not None:
            return self._list_html_by_url(list_url) or ""

        # 本地文件路径直接读取
        if list_url.startswith(("./", "../", "/")) or not list_url.startswith(("http://", "https://")):
            p = Path(list_url)
            if p.exists():
                return p.read_text(encoding="utf-8")
            return ""

        # 真实 HTTP 下载
        from ..fetcher import fetch_url

        result = fetch_url(
            list_url,
            timeout=config.defaults.fetch_timeout_seconds,
            user_agent=config.defaults.user_agent,
        )
        return result.html if result.ok else ""

    # ------------------------------------------------------------------
    # HTML 解析
    # ------------------------------------------------------------------

    def _parse_list_html(
        self,
        html: str,
        profile: str,
        list_url: str,
        source: ResearchSourceConfig,
    ) -> list[dict]:
        """根据 extraction_profile 解析列表页 HTML。

        参数：
            html:    列表页 HTML 字符串
            profile: extraction_profile 名称
            list_url: 列表页 URL（用于解析相对链接）
            source:  信息源配置

        返回：
            dict 列表，每个 dict 含 url / title / published_at / summary / author / language
        """

        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception:
            return []

        if profile == "simple_card_list":
            return self._parse_card_list(soup, list_url)
        if profile == "link_list":
            return self._parse_link_list(soup, list_url)
        # 默认 generic_article_list
        return self._parse_generic_article_list(soup, list_url)

    def _parse_generic_article_list(
        self,
        soup: BeautifulSoup,
        list_url: str,
    ) -> list[dict]:
        """通用文章列表解析：找 <article> / <li> 里的 <a> 链接。

        参数：
            soup: BeautifulSoup 对象
            list_url: 列表页 URL

        返回：
            dict 列表
        """

        items: list[dict] = []
        # 优先找 <article> 元素
        containers = soup.find_all("article")
        if not containers:
            # 退化到 <li>
            containers = soup.find_all("li")

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
            }
            items.append(item)

        return items

    def _parse_card_list(
        self,
        soup: BeautifulSoup,
        list_url: str,
    ) -> list[dict]:
        """卡片式列表解析：找 class 含 "card" 的元素。

        参数：
            soup: BeautifulSoup 对象
            list_url: 列表页 URL

        返回：
            dict 列表
        """

        items: list[dict] = []
        # 找 class 含 "card" 的元素
        # BeautifulSoup 的 find_all(class_=...) 回调对多 class 元素会传多次
        # 这里手动遍历所有带 class 的元素
        containers = []
        for tag in soup.find_all(class_=True):
            classes = tag.get("class", [])
            if isinstance(classes, list):
                classes_str = " ".join(classes).lower()
            else:
                classes_str = str(classes).lower()
            if "card" in classes_str:
                containers.append(tag)

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
            }
            items.append(item)

        return items

    def _parse_link_list(
        self,
        soup: BeautifulSoup,
        list_url: str,
    ) -> list[dict]:
        """最朴素的链接列表解析：列出所有 <a> 链接。

        参数：
            soup: BeautifulSoup 对象
            list_url: 列表页 URL

        返回：
            dict 列表
        """

        items: list[dict] = []
        for link in soup.find_all("a"):
            href = link.get("href")
            if not href:
                continue
            href = href.strip()
            # 跳过锚点 / javascript / mailto
            if href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue
            title = self._extract_text(link)
            if not title:
                continue

            item = {
                "url": href,
                "title": title,
                "published_at": self._extract_published_at(link.parent) if link.parent else None,
                "summary": None,
                "author": None,
                "language": self._extract_language(soup),
            }
            items.append(item)

        return items

    # ------------------------------------------------------------------
    # 字段提取工具
    # ------------------------------------------------------------------

    def _extract_text(self, tag) -> str:
        """提取标签内的纯文本，去掉首尾空白。"""
        if tag is None:
            return ""
        text = tag.get_text(strip=True)
        return text

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

        # <time datetime="...">
        time_tag = container.find("time")
        if time_tag:
            dt = time_tag.get("datetime")
            if dt:
                return dt.strip()
            text = self._extract_text(time_tag)
            if text:
                return text

        # <meta name="date">
        meta_date = container.find("meta", attrs={"name": "date"})
        if meta_date and meta_date.get("content"):
            return meta_date["content"].strip()

        # class 含 date / time
        for cls_tag in container.find_all(class_=True):
            classes = " ".join(cls_tag.get("class", [])).lower()
            if "date" in classes or "time" in classes:
                text = self._extract_text(cls_tag)
                if text:
                    return text

        return None

    def _extract_summary(self, container, link) -> str | None:
        """从容器里提取摘要。

        查找顺序：
            1. <p> 标签文本（取第一个非空且非链接文本）
            2. class 含 "summary" / "description" / "excerpt" 的元素
        """

        if container is None:
            return None

        # class 含 summary / description / excerpt
        for cls_tag in container.find_all(class_=True):
            classes = " ".join(cls_tag.get("class", [])).lower()
            if any(k in classes for k in ("summary", "description", "excerpt")):
                text = self._extract_text(cls_tag)
                if text:
                    return text

        # <p> 标签
        for p in container.find_all("p"):
            text = self._extract_text(p)
            if text and len(text) > 10:  # 太短的不算摘要
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
            classes = " ".join(cls_tag.get("class", [])).lower()
            if "author" in classes:
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
