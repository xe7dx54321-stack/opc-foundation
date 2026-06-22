"""Conference Transcript 连接器 —— 采集会议 transcript / webcast / presentation 页面。

功能说明（小白解读）：
    投行会议（Morgan Stanley TMT、Goldman Sachs Communacopia、JPM Healthcare 等）
    和公司 IR event 通常会发布 transcript、webcast、presentation 材料。
    本 connector 负责从会议列表页或单篇页面发现候选文档。

    本 connector 支持 5 种 extraction_profile：
        - conference_event_list:  通用会议 / IR event 列表页（HTML）
        - event_cards:            卡片式 event 列表（HTML）
        - transcript_page:        单篇 transcript 页面（HTML）
        - presentation_page:      单篇 presentation / event materials 页面（HTML）
        - webcast_event_page:     webcast / event detail 页面（HTML）

    本阶段只负责"发现"候选文档，生成 DocumentCandidate。
    后续的正文抓取/抽取/归档由 archiver + fetcher + extractor + storage 完成。

合规边界：
    - 不访问真实网站（测试用 fixture）
    - 不写针对真实网站的硬编码规则
    - 不做 LLM 分析
    - 不做 affected_tickers / expectation_delta / trade_signal
    - 不保存 cookie/token/API key
    - 不绕过 paywall
    - 不下载 PDF（presentation_url 只作为 metadata 保存）
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable
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
# 主类
# ---------------------------------------------------------------------------


class ConferenceTranscriptConnector(BaseResearchConnector):
    """会议 transcript / webcast / presentation 连接器。

    处理 source_type = conference_transcript 的信息源。

    支持三种入口：
        - 入口 A：conference event list page（extraction_profile=conference_event_list/event_cards）
        - 入口 B：single transcript page（extraction_profile=transcript_page）
        - 入口 C：presentation / webcast event page（extraction_profile=presentation_page/webcast_event_page）

    测试注入：
        构造时传 html_by_url（按 URL 返回 HTML 字符串），跳过真实 HTTP。
    """

    connector_id = "conference_transcript"

    def __init__(
        self,
        html_by_url: HtmlInjector | None = None,
    ) -> None:
        """初始化 ConferenceTranscriptConnector。

        参数：
            html_by_url: 测试用注入函数，按 URL 返回 HTML 内容
        """
        self._html_by_url = html_by_url

    def discover(
        self,
        source: ResearchSourceConfig,
        config: ResearchArchiveConfig,
    ) -> list[DocumentCandidate]:
        """从会议信息源发现候选文档。

        参数：
            source: 信息源配置
            config: 整体配置

        返回：
            DocumentCandidate 列表

        异常：
            缺少 url 时抛出 ValueError
            内容为空时抛出 ValueError
        """

        profile = source.extraction_profile or "conference_event_list"

        # 单页 profile：transcript_page / presentation_page / webcast_event_page
        if profile in ("transcript_page", "presentation_page", "webcast_event_page"):
            return self._discover_from_single_page(source, config, profile)

        # 列表页 profile：conference_event_list / event_cards
        return self._discover_from_list(source, config, profile)

    # ------------------------------------------------------------------
    # 入口 A：列表页
    # ------------------------------------------------------------------

    def _discover_from_list(
        self,
        source: ResearchSourceConfig,
        config: ResearchArchiveConfig,
        profile: str,
    ) -> list[DocumentCandidate]:
        """从会议列表页发现候选文档。

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
                f"source [{source.source_id}] conference_transcript 缺少 url"
            )

        html = self._fetch_html(list_url, source, config)
        if not html or not html.strip():
            raise ValueError(
                f"source [{source.source_id}] conference 列表页内容为空: {list_url}"
            )

        if profile == "event_cards":
            raw_items = self._parse_event_cards(html, list_url)
        else:
            # 默认 conference_event_list
            raw_items = self._parse_event_list(html, list_url)

        return self._items_to_candidates(raw_items, source, config, list_url, profile)

    def _parse_event_list(
        self,
        html: str,
        list_url: str,
    ) -> list[dict]:
        """通用会议 event 列表解析。

        解析策略：
            1. 优先找 <article>
            2. 再找 <li>
            3. 再找 class/id 含 event/conference/webcast/transcript/presentation 的块
            4. 在块内找第一个有效 <a href>
            5. 提取 title / time / summary / company / speaker / event_name

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
            # 3. 再找 class/id 含 event/conference/webcast/transcript/presentation 的块
            containers = []
            for tag in soup.find_all(class_=True):
                classes = tag.get("class", [])
                if isinstance(classes, list):
                    classes_str = " ".join(classes).lower()
                else:
                    classes_str = str(classes).lower()
                if any(
                    k in classes_str
                    for k in ("event", "conference", "webcast", "transcript", "presentation")
                ):
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
                "company": self._extract_by_class_keyword(container, "company"),
                "speaker": self._extract_by_class_keyword(container, "speaker"),
                "event_name": self._extract_by_class_keyword(container, "event-name"),
                "event_date": self._extract_event_date(container),
                "language": self._extract_language(soup),
                "document_kind": self._guess_document_kind(container),
            }
            items.append(item)

        return items

    def _parse_event_cards(
        self,
        html: str,
        list_url: str,
    ) -> list[dict]:
        """卡片式 event 列表解析。

        解析策略：
            找 class 含 card/event-card/conference-card/webcast-card 的元素

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
                for k in ("card", "event-card", "conference-card", "webcast-card")
            ):
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
                "company": self._extract_by_class_keyword(container, "company"),
                "speaker": self._extract_by_class_keyword(container, "speaker"),
                "event_name": self._extract_by_class_keyword(container, "event-name"),
                "event_date": self._extract_event_date(container),
                "language": self._extract_language(soup),
                "document_kind": self._guess_document_kind(container),
            }
            items.append(item)

        return items

    # ------------------------------------------------------------------
    # 入口 B / C：单页
    # ------------------------------------------------------------------

    def _discover_from_single_page(
        self,
        source: ResearchSourceConfig,
        config: ResearchArchiveConfig,
        profile: str,
    ) -> list[DocumentCandidate]:
        """从单篇页面发现候选文档（transcript / presentation / webcast event）。

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
                f"source [{source.source_id}] conference_transcript 缺少 url"
            )

        html = self._fetch_html(page_url, source, config)
        if not html or not html.strip():
            raise ValueError(
                f"source [{source.source_id}] conference 页面内容为空: {page_url}"
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
            title = page_url  # 兜底用 URL

        canonical = canonicalize_research_url(page_url)

        # 根据 profile 提取不同的 metadata
        if profile == "transcript_page":
            document_kind = "transcript"
            transcript_url = page_url
            webcast_url = self._extract_link_by_text(soup, ("webcast", "listen", "audio"))
            presentation_url = self._extract_link_by_text(soup, ("presentation", "slides", "pdf"))
        elif profile == "presentation_page":
            document_kind = "presentation"
            transcript_url = self._extract_link_by_text(soup, ("transcript",)) or None
            webcast_url = self._extract_link_by_text(soup, ("webcast", "listen", "audio"))
            # presentation_page：优先从页面中找 PDF 链接
            presentation_url = (
                self._extract_pdf_link(soup)
                or self._extract_link_by_text(soup, ("presentation", "slides"))
                or page_url
            )
        else:  # webcast_event_page
            document_kind = "webcast_event"
            # 优先选择 transcript link 作为 candidate URL
            transcript_url = self._extract_link_by_text(soup, ("transcript",)) or page_url
            webcast_url = self._extract_link_by_text(soup, ("webcast", "listen", "audio"))
            presentation_url = self._extract_pdf_link(soup) or self._extract_link_by_text(
                soup, ("presentation", "slides")
            )
            # 如果找到了 transcript link，重新计算 canonical
            if transcript_url != page_url:
                canonical = canonicalize_research_url(urljoin(page_url, transcript_url))

        # candidate URL：优先 transcript_url
        candidate_url = transcript_url if transcript_url else page_url
        if candidate_url != page_url:
            candidate_url = urljoin(page_url, candidate_url)

        candidate = DocumentCandidate(
            source_id=source.source_id,
            source_name=source.source_name,
            source_type="conference_transcript",
            title=title,
            url=candidate_url,
            canonical_url=canonicalize_research_url(candidate_url),
            published_at=self._extract_published_at(soup),
            author=self._extract_author(soup),
            summary=self._extract_summary(soup, None),
            language=self._extract_language(soup),
            legal_profile=source.legal_profile,
            tags=list(source.tags),
            raw_entry={
                "event_url": page_url,
                "transcript_url": candidate_url if document_kind != "presentation" else (transcript_url or None),
                "webcast_url": webcast_url,
                "presentation_url": presentation_url,
                "event_name": self._extract_by_class_keyword(soup, "event-name"),
                "company": self._extract_by_class_keyword(soup, "company"),
                "speaker": self._extract_by_class_keyword(soup, "speaker"),
                "event_date": self._extract_event_date(soup),
                "document_kind": document_kind,
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

            # 同一列表页内去重
            if canonical in seen_urls:
                continue
            seen_urls.add(canonical)

            # author 优先 speaker，其次 company
            author = item.get("speaker") or item.get("company")

            candidates.append(
                DocumentCandidate(
                    source_id=source.source_id,
                    source_name=source.source_name,
                    source_type="conference_transcript",
                    title=item.get("title") or abs_url,
                    url=abs_url,
                    canonical_url=canonical,
                    published_at=item.get("published_at") or item.get("event_date"),
                    author=author,
                    summary=item.get("summary"),
                    language=item.get("language"),
                    legal_profile=source.legal_profile,
                    tags=list(source.tags),
                    raw_entry={
                        "event_url": abs_url,
                        "transcript_url": abs_url,
                        "event_name": item.get("event_name"),
                        "company": item.get("company"),
                        "speaker": item.get("speaker"),
                        "event_date": item.get("event_date"),
                        "document_kind": item.get("document_kind") or "event",
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

    def _extract_event_date(self, container) -> str | None:
        """从容器里提取 event 日期。

        查找顺序：
            1. class 含 "event-date" / "event-time" 的元素
            2. data-event-date 属性
            3. 退化到 _extract_published_at
        """

        if container is None:
            return None

        # data-event-date 属性
        tag_with_date = container.find(attrs={"data-event-date": True})
        if tag_with_date:
            return tag_with_date["data-event-date"].strip()

        for cls_tag in container.find_all(class_=True):
            classes = cls_tag.get("class", [])
            if isinstance(classes, list):
                classes_str = " ".join(classes).lower()
            else:
                classes_str = str(classes).lower()
            if "event-date" in classes_str or "event-time" in classes_str:
                text = self._extract_text(cls_tag)
                if text:
                    return text

        # 退化到 published_at
        return self._extract_published_at(container)

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
            3. class 含 "speaker" 的元素
            4. class 含 "company" 的元素
        """

        if container is None:
            return None

        meta_author = container.find("meta", attrs={"name": "author"})
        if meta_author and meta_author.get("content"):
            return meta_author["content"].strip()

        for keyword in ("author", "speaker", "company"):
            result = self._extract_by_class_keyword(container, keyword)
            if result:
                return result

        return None

    def _extract_by_class_keyword(self, container, keyword: str) -> str | None:
        """从容器里按 class 关键词提取文本。

        参数：
            container: BeautifulSoup tag 或 soup
            keyword: class 关键词（如 company / speaker / event-name）

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

    def _extract_language(self, soup: BeautifulSoup) -> str | None:
        """从 <html lang="..."> 提取页面语言。"""
        html_tag = soup.find("html")
        if html_tag and html_tag.get("lang"):
            return html_tag["lang"].strip()
        return None

    def _guess_document_kind(self, container) -> str:
        """根据容器内容猜测 document_kind。

        返回值：
            transcript / webcast / presentation / event
        """

        if container is None:
            return "event"

        text = container.get_text(" ", strip=True).lower()
        if "transcript" in text:
            return "transcript"
        if "webcast" in text:
            return "webcast"
        if "presentation" in text or "slides" in text:
            return "presentation"
        return "event"

    def _extract_link_by_text(self, soup: BeautifulSoup, keywords: tuple[str, ...]) -> str | None:
        """从页面中按链接文本关键词提取 URL。

        参数：
            soup: BeautifulSoup 对象
            keywords: 链接文本关键词（如 transcript / webcast / presentation）

        返回：
            匹配链接的 href；未找到返回 None
        """

        for a_tag in soup.find_all("a"):
            href = a_tag.get("href")
            if not href:
                continue
            link_text = self._extract_text(a_tag).lower()
            if any(k in link_text for k in keywords):
                return href.strip()

        return None

    def _extract_pdf_link(self, soup: BeautifulSoup) -> str | None:
        """从页面中提取 PDF 链接。

        查找顺序：
            1. <a href="*.pdf">
            2. <a> 链接文本含 "pdf"

        返回：
            PDF 链接；未找到返回 None
        """

        for a_tag in soup.find_all("a"):
            href = a_tag.get("href")
            if not href:
                continue
            if href.lower().endswith(".pdf"):
                return href.strip()
            link_text = self._extract_text(a_tag).lower()
            if "pdf" in link_text:
                return href.strip()

        return None
