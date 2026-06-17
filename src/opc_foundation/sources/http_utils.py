"""Shared HTTP fetch helper with timeout, retry, exponential backoff, and SSRF protection.

功能说明：
    提供 http_get_with_retry() 函数，统一处理 HTTP GET 请求的：
    - 超时（默认 15s）
    - 重试（默认 2 次，指数退避）
    - 错误分类（network / timeout / rate_limit / access_denied / http_error）
    - SSRF 防护（调用前校验 URL，重定向后也校验）
"""
from __future__ import annotations

import time
from typing import Any

import httpx
from pydantic import BaseModel

from ..web.url_validator import validate_url, URLValidationError


class HTTPFetchError(BaseModel):
    status_code: int | None = None
    error_type: str          # network | timeout | rate_limit | access_denied | http_error | unknown
    message: str


def _classify_error(exc: Exception, status_code: int | None = None) -> str:
    """根据异常和状态码分类错误类型。

    参数：
        exc: 捕获的异常对象
        status_code: HTTP 状态码（可选）

    返回：
        错误类型字符串：rate_limit / access_denied / http_error / timeout / network / unknown
    """
    if status_code == 429:
        return "rate_limit"
    if status_code == 403:
        return "access_denied"
    if status_code is not None and status_code >= 400:
        return "http_error"
    if isinstance(exc, httpx.TimeoutException):
        return "timeout"
    if isinstance(exc, httpx.NetworkError):
        return "network"
    return "unknown"


def _make_safety_hook(allow_private: bool = False):
    """创建 httpx event hook，在每次请求（含重定向）前校验 URL 安全性。

    参数：
        allow_private: 是否允许访问私网地址

    返回：
        一个可用于 httpx event_hooks 的回调函数
    """

    def hook(request: httpx.Request) -> None:
        try:
            validate_url(str(request.url), allow_private=allow_private)
        except URLValidationError:
            raise

    return hook


def http_get_with_retry(
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 15,
    max_retries: int = 2,
    backoff_base: float = 1.5,
    http_client: httpx.Client | None = None,
    allow_private: bool = False,
) -> tuple[dict[str, Any] | None, list[HTTPFetchError]]:
    """GET 请求，带重试/退避/SSRF 校验。返回 (json_data, errors)。

    参数：
        url: 请求 URL
        params: 查询参数
        headers: 请求头
        timeout: 超时秒数（默认 15）
        max_retries: 最大重试次数（默认 2）
        backoff_base: 退避基数（默认 1.5，即 1.5^attempt 秒）
        http_client: 外部传入的 httpx.Client（可选，传入则复用）
        allow_private: 是否允许访问私网地址（默认 False）

    返回：
        (json_data, errors)：成功时 json_data 是解析后的 JSON dict，失败时为 None；
        errors 是 HTTPFetchError 列表。

    异常：
        不抛异常，所有错误都通过 errors 列表返回。
        URLValidationError 也会被捕获并放入 errors。
    """
    errors: list[HTTPFetchError] = []

    # 请求前校验 URL 安全性
    try:
        validate_url(url, allow_private=allow_private)
    except URLValidationError as exc:
        errors.append(HTTPFetchError(error_type="unknown", message=f"URL validation failed: {exc}"))
        return None, errors

    safety_hook = _make_safety_hook(allow_private=allow_private)

    # 决定是否使用外部 client
    owns_client = http_client is None
    if owns_client:
        # 自建 client：配置 follow_redirects + event_hooks 实现重定向后校验
        client = httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            event_hooks={"request": [safety_hook]},
        )
    else:
        client = http_client

    try:
        for attempt in range(max_retries + 1):
            try:
                if owns_client:
                    resp = client.get(url, params=params, headers=headers)
                else:
                    # 外部 client：传 follow_redirects=True，响应后校验最终 URL
                    resp = client.get(url, params=params, headers=headers, follow_redirects=True)
                    # 只对真实的 httpx.Response 校验 resp.url（mock 对象跳过）
                    if isinstance(getattr(resp, "url", None), (str, httpx.URL)):
                        try:
                            validate_url(str(resp.url), allow_private=allow_private)
                        except URLValidationError as exc:
                            errors.append(HTTPFetchError(
                                error_type="unknown",
                                message=f"Redirect target blocked: {exc}",
                            ))
                            return None, errors

                if resp.status_code in (429, 403):
                    err = HTTPFetchError(
                        status_code=resp.status_code,
                        error_type=_classify_error(Exception(), resp.status_code),
                        message=f"HTTP {resp.status_code} from {url}",
                    )
                    errors.append(err)
                    # 403 不重试；429 重试一次
                    if resp.status_code == 403 or attempt >= max_retries:
                        return None, errors
                    wait = backoff_base ** attempt
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.json(), []
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
                code = getattr(getattr(exc, "response", None), "status_code", None)
                err = HTTPFetchError(
                    status_code=code,
                    error_type=_classify_error(exc, code),
                    message=f"{type(exc).__name__}: {exc}",
                )
                errors.append(err)
                if attempt < max_retries:
                    time.sleep(backoff_base ** attempt)
            except URLValidationError as exc:
                errors.append(HTTPFetchError(error_type="unknown", message=f"URL validation failed: {exc}"))
                return None, errors
            except Exception as exc:
                errors.append(HTTPFetchError(error_type="unknown", message=str(exc)))
                return None, errors

        return None, errors
    finally:
        if owns_client:
            client.close()
