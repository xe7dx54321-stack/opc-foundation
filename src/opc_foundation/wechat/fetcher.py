"""文章正文抓取（HTTP）。

功能说明（小白解读）：
    对给定的文章 URL 发起 HTTP GET 请求，返回 HTML 文本。
    为了方便测试，提供 `html_content` 参数直接注入内容而不发真实请求。
"""
from __future__ import annotations

import httpx


class FetchResult:
    """一次 HTTP 抓取的结果。"""

    def __init__(
        self,
        url: str,
        html: str,
        final_url: str | None = None,
        error: str | None = None,
    ) -> None:
        self.url = url
        self.html = html
        self.final_url = final_url or url
        self.error = error

    @property
    def ok(self) -> bool:
        return not self.error and bool(self.html)


def fetch_article_html(
    url: str,
    timeout: int = 20,
    user_agent: str = "Mozilla/5.0",
    html_content: str | bytes | None = None,
) -> FetchResult:
    """抓取一篇文章的 HTML。

    参数：
        url:           目标 URL
        timeout:       超时秒数
        user_agent:    HTTP User-Agent
        html_content:  测试用。提供后不会发真实请求，直接用此内容作为返回结果。

    返回：
        FetchResult，含 html 文本与错误信息（如果有）
    """

    if html_content is not None:
        if isinstance(html_content, bytes):
            try:
                text = html_content.decode("utf-8")
            except UnicodeDecodeError:
                text = html_content.decode("utf-8", errors="ignore")
        else:
            text = html_content
        return FetchResult(url=url, html=text, final_url=url)

    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(
                url,
                headers={"User-Agent": user_agent},
            )
            resp.raise_for_status()
            # 微信文章默认是 UTF-8，但服务器也可能没返回 charset，
            # 这里显式尝试 utf-8 解析，失败时退到 apparent_encoding。
            resp.encoding = resp.encoding or "utf-8"
            try:
                html = resp.text
            except Exception:
                html = resp.content.decode("utf-8", errors="ignore")
            return FetchResult(url=url, html=html, final_url=str(resp.url))
    except Exception as exc:
        return FetchResult(url=url, html="", error=f"HTTP 请求失败: {exc}")
