"""HKEXnews 港交所披露易连接器 —— 采集香港上市公司公告。

功能说明（小白解读）：
    港交所披露易（HKEXnews）是香港上市公司的官方披露平台。
    本 connector 支持解析港交所公告列表的 HTML fixture 结构。

    从公告列表中提取：
        - 股份代号
        - 公司名称
        - 公告标题
        - 公告类别
        - 发布日期
        - 公告 URL
        - PDF URL

MVP 范围：
    - 解析港交所公告列表 HTML 结构的 fixture
    - 生成 FilingCandidate 列表
    - 支持 max_items 限制
    - 支持 filing_types 过滤

不做：
    - 浏览器自动化
    - 验证码绕过
    - PDF OCR
    - 投资含义判断
    - 投资建议
"""
from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..models import FilingArchiveConfig, FilingCandidate, FilingSourceConfig
from .base import OfficialFilingConnector


class HKEXFilingConnector(OfficialFilingConnector):
    """HKEXnews 港交所披露易公告连接器。

    处理 source_type = hkex_announcement 的信息源。

    使用方式：
        1. 在 source 配置里指定 endpoint_url（公告列表页 URL）
        2. connector 读取公告列表 HTML，解析出候选披露
        3. 候选披露交给 archiver 做后续归档

    测试注入：
        构造时传 html_by_url（按 URL 返回 HTML 字符串），跳过真实 HTTP。
    """

    connector_id = "hkex_announcement"

    def discover(
        self,
        source: FilingSourceConfig,
        config: FilingArchiveConfig,
    ) -> list[FilingCandidate]:
        """从 HKEX 公告列表 HTML 发现候选披露。

        参数：
            source: 信息源配置
            config: 整体配置

        返回：
            FilingCandidate 列表

        异常：
            缺少 endpoint_url 时抛出 ValueError
            解析失败时抛出异常（由上层 fail-soft 捕获）
        """
        endpoint = source.endpoint_url or source.base_url
        if not endpoint:
            raise ValueError(
                f"HKEX source [{source.source_id}] 缺少 endpoint_url 或 base_url"
            )

        # 获取 HTML 数据（优先用注入的 fixture）
        html_content = None
        if self._html_by_url is not None:
            html_content = self._html_by_url(endpoint)

        if html_content is None:
            raise ValueError(
                f"HKEX connector MVP 仅支持 fixture 注入模式，"
                f"请传入 html_by_url 或配置 endpoint_url"
            )

        return self._parse_announcements_html(source, config, html_content, endpoint)

    def _parse_announcements_html(
        self,
        source: FilingSourceConfig,
        config: FilingArchiveConfig,
        html: str,
        source_url: str,
    ) -> list[FilingCandidate]:
        """解析 HKEX 公告列表 HTML。

        HKEX 公告列表页典型结构：
            - 表格形式：每一行是一条公告
            - 包含：股份代号、公司名称、公告标题、公告类别、发布日期、链接

        参数：
            source:     source 配置
            config:     整体配置
            html:       公告列表 HTML
            source_url: 来源 URL

        返回：
            FilingCandidate 列表
        """
        from ...run.time_utils import utcnow_iso

        candidates: list[FilingCandidate] = []

        soup = BeautifulSoup(html, "html.parser")
        base_hkex = source.base_url or "https://www.hkexnews.hk"

        # 查找表格行：尝试多种可能的选择器
        rows = (
            soup.select("table tr")
            or soup.select(".announcement-item")
            or soup.select(".newsItem")
            or soup.select("li.announcement")
            or []
        )

        max_items = source.max_items or config.defaults.max_items_per_source
        allowed_types = set(source.filing_types or [])
        now_str = utcnow_iso()

        for row in rows:
            if len(candidates) >= max_items:
                break

            # 跳过表头
            if row.find("th"):
                continue

            # 提取所有文本
            all_text = row.get_text(" ", strip=True)
            if not all_text:
                continue

            # 提取链接
            link = row.find("a", href=True)
            doc_url = None
            if link:
                href = link["href"]
                if href.startswith("http"):
                    doc_url = href
                else:
                    doc_url = urljoin(base_hkex, href)

            # 尝试从结构化单元格提取
            cells = row.find_all("td")
            if len(cells) >= 3:
                stock_code = cells[0].get_text(strip=True)
                company_name = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                title_cell = cells[2] if len(cells) > 2 else row
                title = title_cell.get_text(" ", strip=True)
                ann_type = cells[3].get_text(strip=True) if len(cells) > 3 else ""
                date_str = cells[-1].get_text(strip=True)
            else:
                # 非结构化：用链接文本作为标题
                stock_code = ""
                company_name = ""
                title = link.get_text(strip=True) if link else all_text
                ann_type = ""
                date_str = ""

            # 解析日期
            filing_date = self._parse_hkex_date(date_str)

            # 判断 PDF URL
            pdf_url = None
            if doc_url and doc_url.lower().endswith(".pdf"):
                pdf_url = doc_url

            # filing_types 过滤
            if allowed_types and ann_type and ann_type not in allowed_types:
                continue

            # 至少要有标题或 URL
            if not title and not doc_url:
                continue

            # 生成一个简单的 announcement_id（从 URL 中提取，或用 hash）
            ann_id = None
            if doc_url:
                import hashlib
                ann_id = hashlib.md5(doc_url.encode()).hexdigest()[:16]

            candidate = FilingCandidate(
                source_id=source.source_id,
                source_type="hkex_announcement",
                market=source.market or "HK",
                jurisdiction=source.jurisdiction or "HK",
                issuer_name=company_name,
                issuer_code=stock_code,
                filing_type=ann_type,
                filing_title=title,
                filing_date=filing_date,
                announcement_id=ann_id,
                source_url=source_url,
                document_url=doc_url,
                pdf_url=pdf_url,
                raw_entry={
                    "stock_code": stock_code,
                    "company_name": company_name,
                    "title": title,
                    "ann_type": ann_type,
                    "date": date_str,
                    "url": doc_url,
                },
                discovered_at=now_str,
            )
            candidates.append(candidate)

        return candidates

    @staticmethod
    def _parse_hkex_date(date_str: str) -> str | None:
        """解析 HKEX 日期格式。

        HKEX 常用格式：
            - DD/MM/YYYY
            - YYYY-MM-DD
            - DD-MM-YYYY
        """
        from datetime import datetime

        if not date_str:
            return None

        date_str = date_str.strip()

        for fmt in [
            "%d/%m/%Y",
            "%Y-%m-%d",
            "%d-%m-%Y",
            "%Y/%m/%d",
            "%Y年%m月%d日",
        ]:
            try:
                dt = datetime.strptime(date_str[:10], fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

        return None
