"""Trafilatura-based URL text extractor.

功能说明：
    使用 trafilatura 库从网页 URL 提取正文文本。
    改用 httpx 先下载 HTML（带 timeout 和 SSRF 校验），
    再传给 trafilatura 解析，避免 trafilatura.fetch_url 无 timeout 的问题。
"""
from __future__ import annotations

import httpx
import trafilatura

from .url_text_extractor import ExtractedPage
from .url_validator import validate_url, URLValidationError
from ..run.time_utils import utcnow_iso


class TrafilaturaExtractor:
    """Extracts page text via trafilatura.

    参数：
        timeout: 下载网页的超时秒数（默认 30）
        favor_recall: 是否偏向召回率（默认 True）
    """

    def __init__(self, timeout: int = 30, favor_recall: bool = True) -> None:
        self.timeout = timeout
        self.favor_recall = favor_recall

    def extract(self, url: str) -> ExtractedPage:
        """从 URL 提取网页正文文本。

        参数：
            url: 待提取的网页 URL

        返回：
            ExtractedPage 对象，包含 url、title、text、errors、fetched_at。
            永不抛异常，所有错误都放入 errors 列表。
        """
        errors: list[str] = []
        title: str | None = None
        text = ""

        # 校验 URL 安全性（SSRF 防护）
        try:
            validate_url(url)
        except URLValidationError as exc:
            errors.append(f"URL validation failed: {exc}")
            return ExtractedPage(url=url, text="", errors=errors, fetched_at=utcnow_iso())

        try:
            # 用 httpx 下载 HTML（带 timeout），替代 trafilatura.fetch_url
            with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
                resp = client.get(url)
                resp.raise_for_status()
                downloaded = resp.text

            if not downloaded:
                errors.append(f"Failed to download: {url}")
                return ExtractedPage(url=url, text="", errors=errors, fetched_at=utcnow_iso())

            metadata = trafilatura.extract_metadata(downloaded)
            if metadata:
                title = metadata.title

            text = trafilatura.extract(
                downloaded,
                favor_recall=self.favor_recall,
                include_comments=False,
                include_tables=True,
            ) or ""

            if not text.strip():
                errors.append(f"No text extracted from: {url}")
        except Exception as exc:
            errors.append(f"Extraction error for {url}: {exc}")
            text = ""

        return ExtractedPage(
            url=url,
            title=title,
            text=text,
            errors=errors,
            fetched_at=utcnow_iso(),
        )
