"""Analyst Action 连接器 —— 采集分析师评级变动 / 目标价调整等公开事件。

功能说明（小白解读）：
    分析师动作（analyst action）包括 upgrade / downgrade / initiated / reiterate /
    maintain / price target raised / lowered / set / rating change / coverage resumed /
    coverage suspended 等公开事件。本 connector 负责从评级变动表格、卡片、新闻列表
    或单篇详情页中发现候选文档。

    本 connector 支持 4 种 extraction_profile：
        - analyst_action_table:     评级变动表格（HTML <table>）
        - analyst_action_cards:     卡片式 analyst action 页面
        - analyst_action_news_list: 新闻列表式 analyst action 页面
        - analyst_action_detail:    单篇 analyst action 详情页

    本阶段只负责"发现"候选文档，生成 DocumentCandidate。
    后续的正文抓取/抽取/归档由 archiver + fetcher + extractor + storage 完成。

合规边界：
    - 不访问真实网站（测试用 fixture）
    - 不写针对真实网站的硬编码规则
    - 不做 LLM 分析
    - 不做 affected_tickers / expectation_delta / trade_signal
    - 不做 buy/sell/hold 投资建议
    - 不把 price target / rating_to 当投资建议
    - 不保存 cookie/token/API key
    - 不绕过 paywall
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
# action_type 识别关键词
# ---------------------------------------------------------------------------


_ACTION_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("upgrade", ("upgrade", "upgraded", "raises rating")),
    ("downgrade", ("downgrade", "downgraded", "cuts rating")),
    ("initiated", ("initiated", "initiates", "initiate coverage", "launches coverage")),
    ("reiterate", ("reiterate", "reiterates", "reiterated")),
    ("maintain", ("maintain", "maintains", "maintained")),
    ("raise_target", ("raises target", "raise target", "target raised", "price target raised")),
    ("lower_target", ("lowers target", "lower target", "target lowered", "price target lowered")),
    ("set_target", ("sets target", "set target", "target set", "price target set")),
    ("resume", ("resume", "resumes", "resumed coverage")),
    ("suspend", ("suspend", "suspends", "suspended coverage")),
]


def _guess_action_type(text: str) -> str:
    """从文本中轻量识别 action_type。

    参数：
        text: 原始文本（标题 / 摘要 / 卡片内容）

    返回：
        action_type 字符串；未识别返回 "unknown"

    小白解读：
        只做关键词匹配，不做语义判断。
        不判断 upgrade 是否利好，也不判断 downgrade 是否利空。
    """
    if not text:
        return "unknown"
    lower = text.lower()
    for action_type, keywords in _ACTION_KEYWORDS:
        for kw in keywords:
            if kw in lower:
                return action_type
    return "unknown"


def _guess_currency(text: str) -> str:
    """从文本中识别货币符号。

    返回值：USD / HKD / CNY / unknown

    小白解读：
        注意判断顺序：HK$ 包含 $，所以要先检查 HK$ 再检查 $。
        RMB / ¥ 也需要先检查，避免被 $ 误判。
    """
    if not text:
        return "unknown"
    lower = text.lower()
    # 先检查 HK$ / HKD（因为 HK$ 包含 $，要先检查避免被 USD 误判）
    if "hk$" in lower or "hkd" in lower:
        return "HKD"
    if "rmb" in lower or "cny" in lower or "¥" in text:
        return "CNY"
    # 最后检查 $ / USD
    if "$" in text or "usd" in lower:
        return "USD"
    return "unknown"


# ---------------------------------------------------------------------------
# 主类
# ---------------------------------------------------------------------------


class AnalystActionConnector(BaseResearchConnector):
    """分析师动作连接器。

    处理 source_type = analyst_action 的信息源。

    支持三种入口：
        - 入口 A：analyst action table（extraction_profile=analyst_action_table）
        - 入口 B：analyst action cards / news list（extraction_profile=analyst_action_cards / analyst_action_news_list）
        - 入口 C：single analyst action detail page（extraction_profile=analyst_action_detail）

    测试注入：
        构造时传 html_by_url（按 URL 返回 HTML 字符串），跳过真实 HTTP。
    """

    connector_id = "analyst_action"

    def __init__(
        self,
        html_by_url: HtmlInjector | None = None,
    ) -> None:
        """初始化 AnalystActionConnector。

        参数：
            html_by_url: 测试用注入函数，按 URL 返回 HTML 内容
        """
        self._html_by_url = html_by_url

    def discover(
        self,
        source: ResearchSourceConfig,
        config: ResearchArchiveConfig,
    ) -> list[DocumentCandidate]:
        """从分析师动作信息源发现候选文档。

        参数：
            source: 信息源配置
            config: 整体配置

        返回：
            DocumentCandidate 列表

        异常：
            缺少 url 时抛出 ValueError
            内容为空时抛出 ValueError
        """
        profile = source.extraction_profile or "analyst_action_table"

        # 单页 profile：analyst_action_detail
        if profile == "analyst_action_detail":
            return self._discover_from_detail_page(source, config, profile)

        # 列表页 profile：analyst_action_table / analyst_action_cards / analyst_action_news_list
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
                f"source [{source.source_id}] analyst_action 缺少 url"
            )

        html = self._fetch_html(list_url, source, config)
        if not html or not html.strip():
            raise ValueError(
                f"source [{source.source_id}] analyst action 列表页内容为空: {list_url}"
            )

        if profile == "analyst_action_table":
            raw_items = self._parse_table(html, list_url)
        elif profile == "analyst_action_cards":
            raw_items = self._parse_cards(html, list_url)
        else:
            # analyst_action_news_list
            raw_items = self._parse_news_list(html, list_url)

        return self._items_to_candidates(raw_items, source, config, list_url, profile)

    def _parse_table(
        self,
        html: str,
        list_url: str,
    ) -> list[dict]:
        """解析评级变动表格。

        解析策略：
            1. 找 <table>
            2. 识别表头（date/company/ticker/broker/analyst/action/rating/price target/url）
            3. 逐行解析 <tr>
            4. 跳过缺少 title 或 url 的行（若无 detail link，用 source.url + row metadata 构造 title）

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

        tables = soup.find_all("table")
        if not tables:
            return []

        # 收集所有表格的所有行
        items: list[dict] = []
        for table in tables:
            # 识别表头
            header_map = self._parse_table_header(table)
            if not header_map:
                # 没有表头，跳过这个表
                continue

            rows = table.find_all("tr")
            for row in rows:
                # 跳过表头行
                if row.find("th"):
                    continue
                cells = row.find_all("td")
                if len(cells) < 2:
                    continue

                item = self._parse_table_row(row, header_map, list_url)
                if item:
                    items.append(item)

        return items

    def _parse_table_header(self, table) -> dict[str, int]:
        """解析表格表头，返回字段名到列索引的映射。

        参数：
            table: BeautifulSoup <table> tag

        返回：
            {字段名: 列索引} 字典
        """
        header_map: dict[str, int] = {}
        header_row = table.find("tr")
        if not header_row:
            return header_map

        ths = header_row.find_all("th")
        if not ths:
            return header_map

        for idx, th in enumerate(ths):
            text = (th.get_text(strip=True) or "").lower()
            if not text:
                continue
            if any(k in text for k in ("date", "time")):
                header_map["date"] = idx
            elif "company" in text:
                header_map["company"] = idx
            elif "ticker" in text or "symbol" in text:
                header_map["ticker"] = idx
            elif "broker" in text or "firm" in text:
                header_map["broker"] = idx
            elif "analyst" in text:
                header_map["analyst"] = idx
            elif "action" in text:
                header_map["action"] = idx
            elif "rating" in text:
                if "from" in text:
                    header_map["rating_from"] = idx
                elif "to" in text:
                    header_map["rating_to"] = idx
                else:
                    header_map["rating"] = idx
            elif "target" in text or "price" in text:
                if "from" in text:
                    header_map["price_target_from"] = idx
                elif "to" in text:
                    header_map["price_target_to"] = idx
                else:
                    header_map["price_target"] = idx
            elif "url" in text or "link" in text or "detail" in text:
                header_map["url"] = idx
            elif "title" in text or "headline" in text:
                header_map["title"] = idx

        return header_map

    def _parse_table_row(
        self,
        row,
        header_map: dict[str, int],
        list_url: str,
    ) -> dict | None:
        """解析表格的一行，返回 item dict。

        参数：
            row: BeautifulSoup <tr> tag
            header_map: 表头字段映射
            list_url: 列表页 URL（用于解析相对链接）

        返回：
            item dict；无法解析返回 None
        """
        cells = row.find_all("td")
        if len(cells) < 2:
            return None

        def cell_text(key: str) -> str:
            idx = header_map.get(key)
            if idx is None or idx >= len(cells):
                return ""
            return cells[idx].get_text(strip=True)

        def cell_link(key: str) -> str:
            idx = header_map.get(key)
            if idx is None or idx >= len(cells):
                return ""
            a = cells[idx].find("a")
            if a and a.get("href"):
                return a["href"].strip()
            return ""

        # 提取字段
        date_str = cell_text("date")
        company = cell_text("company")
        ticker = cell_text("ticker")
        broker = cell_text("broker")
        analyst = cell_text("analyst")
        action_str = cell_text("action")
        rating_from = cell_text("rating_from") or cell_text("rating")
        rating_to = cell_text("rating_to")
        price_target_from = cell_text("price_target_from") or cell_text("price_target")
        price_target_to = cell_text("price_target_to")
        title = cell_text("title") or cell_text("headline")

        # URL：优先从 url 列找，其次从 title 列找链接
        url = cell_link("url") or cell_link("title")
        if not url:
            # 行内无 detail link，用 list_url 作为 url，但 title 必须唯一
            url = list_url

        # 构造唯一 title
        if not title:
            parts = [action_str, company, ticker, broker, rating_to, price_target_to]
            title = " ".join(p for p in parts if p)
        if not title:
            return None

        # action_type 识别
        action_type = _guess_action_type(action_str) if action_str else _guess_action_type(title)

        # 货币识别
        currency = _guess_currency(f"{price_target_from} {price_target_to}")

        return {
            "url": url,
            "title": title,
            "published_at": date_str or None,
            "action_date": date_str or None,
            "company": company or None,
            "ticker": ticker or None,
            "broker": broker or None,
            "analyst": analyst or None,
            "action_type": action_type,
            "rating_from": rating_from or None,
            "rating_to": rating_to or None,
            "price_target_from": price_target_from or None,
            "price_target_to": price_target_to or None,
            "currency": currency if currency != "unknown" else None,
            "summary": None,
            "language": None,
            "document_kind": "analyst_action",
        }

    def _parse_cards(
        self,
        html: str,
        list_url: str,
    ) -> list[dict]:
        """解析卡片式 analyst action 页面。

        解析策略：
            找 class 含 card/rating-card/analyst-card/action-card 的元素

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
                for k in ("card", "rating-card", "analyst-card", "action-card")
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

            text = container.get_text(" ", strip=True)
            action_type = _guess_action_type(text)
            currency = _guess_currency(text)

            item = {
                "url": url,
                "title": title,
                "published_at": self._extract_published_at(container),
                "action_date": self._extract_published_at(container),
                "company": self._extract_by_class_keyword(container, "company"),
                "ticker": self._extract_by_class_keyword(container, "ticker"),
                "broker": self._extract_by_class_keyword(container, "broker"),
                "analyst": self._extract_by_class_keyword(container, "analyst"),
                "action_type": action_type,
                "rating_from": self._extract_by_class_keyword(container, "rating-from"),
                "rating_to": self._extract_by_class_keyword(container, "rating-to"),
                "price_target_from": self._extract_by_class_keyword(container, "target-from"),
                "price_target_to": self._extract_by_class_keyword(container, "target-to"),
                "currency": currency if currency != "unknown" else None,
                "summary": self._extract_summary(container, link),
                "language": self._extract_language(soup),
                "document_kind": "analyst_action_card",
            }
            items.append(item)

        return items

    def _parse_news_list(
        self,
        html: str,
        list_url: str,
    ) -> list[dict]:
        """解析新闻列表式 analyst action 页面。

        解析策略：
            1. 优先找 <article>
            2. 再找 <li>
            3. 再找 class/id 含 analyst/rating/upgrade/downgrade/coverage/target 的块

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
                    for k in ("analyst", "rating", "upgrade", "downgrade", "coverage", "target")
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

            text = container.get_text(" ", strip=True)
            action_type = _guess_action_type(text)
            currency = _guess_currency(text)

            item = {
                "url": url,
                "title": title,
                "published_at": self._extract_published_at(container),
                "action_date": self._extract_published_at(container),
                "company": self._extract_by_class_keyword(container, "company"),
                "ticker": self._extract_by_class_keyword(container, "ticker"),
                "broker": self._extract_by_class_keyword(container, "broker"),
                "analyst": self._extract_by_class_keyword(container, "analyst"),
                "action_type": action_type,
                "rating_from": self._extract_by_class_keyword(container, "rating-from"),
                "rating_to": self._extract_by_class_keyword(container, "rating-to"),
                "price_target_from": self._extract_by_class_keyword(container, "target-from"),
                "price_target_to": self._extract_by_class_keyword(container, "target-to"),
                "currency": currency if currency != "unknown" else None,
                "summary": self._extract_summary(container, link),
                "language": self._extract_language(soup),
                "document_kind": "analyst_action_news",
            }
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
        """从单篇 analyst action 详情页发现候选文档。

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
                f"source [{source.source_id}] analyst_action 缺少 url"
            )

        html = self._fetch_html(page_url, source, config)
        if not html or not html.strip():
            raise ValueError(
                f"source [{source.source_id}] analyst action 页面内容为空: {page_url}"
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
        action_type = _guess_action_type(text)
        currency = _guess_currency(text)

        candidate = DocumentCandidate(
            source_id=source.source_id,
            source_name=source.source_name,
            source_type="analyst_action",
            title=title,
            url=page_url,
            canonical_url=canonical,
            published_at=self._extract_published_at(soup),
            author=self._extract_by_class_keyword(soup, "broker")
            or self._extract_by_class_keyword(soup, "analyst"),
            summary=self._extract_summary(soup, None),
            language=self._extract_language(soup),
            legal_profile=source.legal_profile,
            tags=list(source.tags),
            raw_entry={
                "document_kind": "analyst_action_detail",
                "action_date": self._extract_published_at(soup),
                "company": self._extract_by_class_keyword(soup, "company"),
                "ticker": self._extract_by_class_keyword(soup, "ticker"),
                "broker": self._extract_by_class_keyword(soup, "broker"),
                "analyst": self._extract_by_class_keyword(soup, "analyst"),
                "action_type": action_type,
                "rating_from": self._extract_by_class_keyword(soup, "rating-from"),
                "rating_to": self._extract_by_class_keyword(soup, "rating-to"),
                "price_target_from": self._extract_by_class_keyword(soup, "target-from"),
                "price_target_to": self._extract_by_class_keyword(soup, "target-to"),
                "currency": currency if currency != "unknown" else None,
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

            # 同一列表页内去重（按 canonical_url + title 双重去重，因为表格行可能共用 list_url）
            dedup_key = f"{canonical}::{item.get('title', '')}"
            if dedup_key in seen_urls:
                continue
            seen_urls.add(dedup_key)

            # author 优先 broker，其次 analyst
            author = item.get("broker") or item.get("analyst")

            candidates.append(
                DocumentCandidate(
                    source_id=source.source_id,
                    source_name=source.source_name,
                    source_type="analyst_action",
                    title=item.get("title") or abs_url,
                    url=abs_url,
                    canonical_url=canonical,
                    published_at=item.get("published_at") or item.get("action_date"),
                    author=author,
                    summary=item.get("summary"),
                    language=item.get("language"),
                    legal_profile=source.legal_profile,
                    tags=list(source.tags),
                    raw_entry={
                        "document_kind": item.get("document_kind") or "analyst_action",
                        "action_date": item.get("action_date"),
                        "company": item.get("company"),
                        "ticker": item.get("ticker"),
                        "broker": item.get("broker"),
                        "analyst": item.get("analyst"),
                        "action_type": item.get("action_type") or "unknown",
                        "rating_from": item.get("rating_from"),
                        "rating_to": item.get("rating_to"),
                        "price_target_from": item.get("price_target_from"),
                        "price_target_to": item.get("price_target_to"),
                        "currency": item.get("currency"),
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

    def _extract_by_class_keyword(self, container, keyword: str) -> str | None:
        """从容器里按 class 关键词提取文本。

        参数：
            container: BeautifulSoup tag 或 soup
            keyword: class 关键词（如 company / ticker / broker）

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
