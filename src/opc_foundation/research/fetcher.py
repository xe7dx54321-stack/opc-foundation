"""HTTP 抓取层 —— 基础 HTTP 请求与错误分类。

功能说明（小白解读）：
    提供一个 fetch_url() 函数，用 httpx 下载网页 HTML。
    支持 timeout、user_agent，捕获异常并分类错误。
    失败时返回 retryable 标记，供上层决定是否重试。

    合规边界：
    - 不绕过 paywall
    - 不保存 cookie/token
    - 不伪装机构客户
    - 检测到登录页/paywall 时标记 access_denied
"""
from __future__ import annotations

from dataclasses import dataclass

import httpx

from ..run.time_utils import utcnow_iso


@dataclass
class RawFetchResult:
    """一次 HTTP 抓取的结果。

    字段说明：
        url:           请求的 URL
        final_url:     最终 URL（可能经过重定向）
        status_code:   HTTP 状态码
        content_type:  响应 Content-Type
        html:          响应正文（HTML 字符串）
        fetched_at:    抓取时间（UTC ISO-8601）
        error:         错误信息（成功时为 None）
        error_type:    错误分类（timeout/connection/http_4xx/http_5xx/parse/access_denied/unknown）
        retryable:     是否可重试
        ok:            是否成功
    """

    url: str
    final_url: str
    status_code: int | None
    content_type: str | None
    html: str
    fetched_at: str
    error: str | None
    error_type: str | None
    retryable: bool
    ok: bool


def fetch_url(
    url: str,
    timeout: int = 20,
    user_agent: str = "Mozilla/5.0",
    html_content: str | None = None,
) -> RawFetchResult:
    """抓取一个 URL 的 HTML 内容。

    参数：
        url:         要抓取的 URL
        timeout:     超时秒数
        user_agent:  User-Agent 字符串
        html_content: 测试用注入的 HTML（非 None 时跳过真实 HTTP）

    返回：
        RawFetchResult 对象，永不抛异常
    """

    now = utcnow_iso()

    # 测试注入模式
    if html_content is not None:
        return RawFetchResult(
            url=url,
            final_url=url,
            status_code=200,
            content_type="text/html",
            html=html_content,
            fetched_at=now,
            error=None,
            error_type=None,
            retryable=False,
            ok=True,
        )

    # 本地文件路径（file:// 或 ./ 开头）
    if url.startswith(("./", "../", "/")) or url.startswith("file://"):
        return _fetch_local_file(url, now)

    # 真实 HTTP
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url, headers={"User-Agent": user_agent})
            resp.raise_for_status()
            html = resp.text
            content_type = resp.headers.get("content-type", "")

            # 简单的 paywall/登录页检测
            err = _detect_access_denied(html, resp.status_code)
            if err:
                return RawFetchResult(
                    url=url,
                    final_url=str(resp.url),
                    status_code=resp.status_code,
                    content_type=content_type,
                    html=html,
                    fetched_at=now,
                    error=err,
                    error_type="access_denied",
                    retryable=False,
                    ok=False,
                )

            return RawFetchResult(
                url=url,
                final_url=str(resp.url),
                status_code=resp.status_code,
                content_type=content_type,
                html=html,
                fetched_at=now,
                error=None,
                error_type=None,
                retryable=False,
                ok=True,
            )
    except httpx.TimeoutException as exc:
        return RawFetchResult(
            url=url, final_url=url, status_code=None, content_type=None,
            html="", fetched_at=now, error=f"请求超时: {exc}",
            error_type="timeout", retryable=True, ok=False,
        )
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        error_type = "http_4xx" if status < 500 else "http_5xx"
        retryable = status == 429 or status >= 500
        return RawFetchResult(
            url=url, final_url=str(exc.response.url), status_code=status,
            content_type=exc.response.headers.get("content-type"),
            html=exc.response.text if status < 500 else "",
            fetched_at=now, error=f"HTTP {status}: {exc}",
            error_type=error_type, retryable=retryable, ok=False,
        )
    except httpx.RequestError as exc:
        return RawFetchResult(
            url=url, final_url=url, status_code=None, content_type=None,
            html="", fetched_at=now, error=f"连接错误: {exc}",
            error_type="connection", retryable=True, ok=False,
        )
    except Exception as exc:
        return RawFetchResult(
            url=url, final_url=url, status_code=None, content_type=None,
            html="", fetched_at=now, error=f"未知错误: {exc}",
            error_type="unknown", retryable=False, ok=False,
        )


def _fetch_local_file(url: str, now: str) -> RawFetchResult:
    """读取本地文件作为 HTML 内容。"""

    from pathlib import Path
    path_str = url.replace("file://", "")
    p = Path(path_str)
    if not p.exists():
        return RawFetchResult(
            url=url, final_url=url, status_code=404, content_type=None,
            html="", fetched_at=now, error=f"本地文件不存在: {p}",
            error_type="http_4xx", retryable=False, ok=False,
        )
    try:
        html = p.read_text(encoding="utf-8")
        return RawFetchResult(
            url=url, final_url=url, status_code=200, content_type="text/html",
            html=html, fetched_at=now, error=None, error_type=None,
            retryable=False, ok=True,
        )
    except Exception as exc:
        return RawFetchResult(
            url=url, final_url=url, status_code=None, content_type=None,
            html="", fetched_at=now, error=f"读取本地文件失败: {exc}",
            error_type="parse", retryable=False, ok=False,
        )


def _detect_access_denied(html: str, status_code: int) -> str | None:
    """简单检测 paywall/登录页。

    返回错误信息字符串；正常页面返回 None。
    """

    if status_code == 401 or status_code == 403:
        return f"访问被拒绝（HTTP {status_code}），可能需要登录"
    html_lower = html.lower()[:5000]
    # 简单关键词检测（不做复杂判断）
    if "paywall" in html_lower and "subscribe" in html_lower:
        return "检测到 paywall，不绕过"
    return None
