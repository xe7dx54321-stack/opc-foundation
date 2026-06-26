"""URL Verification 工具。

功能说明（小白解读）：
    对那些 DNS 失败、404、TLS 握手失败的源，用更详细的方法做验证：
    - DNS 解析检查（域名能不能解析）
    - curl 轻量访问（看看 curl 能不能访问，对比 urllib）
    - browser-like User-Agent 测试（换个 UA 会不会好一点）
    
    注意：这个模块是诊断用的，不引入 Playwright 之类的重武器。
    只用来判断"到底是 Python 的问题还是网站真的不能访问"。
"""

from __future__ import annotations

import subprocess
import sys
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Any


@dataclass
class UrlVerifyResult:
    """URL 验证结果。

    功能说明（小白解读）：
        记录一个 URL 的验证结果，包括 DNS、curl、不同 UA 下的表现。

    参数：
        url:                 被验证的 URL
        dns_resolvable:      DNS 能不能解析
        dns_error:           DNS 解析错误信息（如果有）
        urllib_status:       urllib 访问的 HTTP 状态码（0 表示失败）
        urllib_error:        urllib 错误信息
        curl_status:         curl 访问的 HTTP 状态码（0 表示失败）
        curl_error:          curl 错误信息
        curl_browser_ua_status:   curl 用浏览器 UA 的 HTTP 状态码
        curl_browser_ua_error:    curl 用浏览器 UA 的错误信息
        final_verdict:       最终判断（见下）
        notes:               备注

    final_verdict 取值：
        - reachable: 可正常访问
        - dns_failed: DNS 解析失败
        - tls_handshake_failed: TLS 握手失败
        - http_4xx: HTTP 4xx 错误
        - http_5xx: HTTP 5xx 错误
        - python_client_limited: Python urllib 不行但 curl 可以
        - browser_like_needed: 需要浏览器式 UA
        - unreachable: 完全访问不了
    """

    url: str = ""
    dns_resolvable: bool = False
    dns_error: str = ""
    urllib_status: int = 0
    urllib_error: str = ""
    curl_status: int = 0
    curl_error: str = ""
    curl_browser_ua_status: int = 0
    curl_browser_ua_error: str = ""
    final_verdict: str = "unreachable"
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        """转字典。"""
        return {
            "url": self.url,
            "dns_resolvable": self.dns_resolvable,
            "dns_error": self.dns_error,
            "urllib_status": self.urllib_status,
            "urllib_error": self.urllib_error,
            "curl_status": self.curl_status,
            "curl_error": self.curl_error,
            "curl_browser_ua_status": self.curl_browser_ua_status,
            "curl_browser_ua_error": self.curl_browser_ua_error,
            "final_verdict": self.final_verdict,
            "notes": self.notes,
        }


BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def check_dns(url: str) -> tuple[bool, str]:
    """检查 URL 的域名能不能解析。

    功能说明（小白解读）：
        从 URL 里提取域名，然后用 socket 做 DNS 解析。
        能解析说明域名还活着，不能解析说明域名可能过期或写错了。

    Args:
        url: 要检查的 URL

    Returns:
        tuple[bool, str]: (能不能解析, 错误信息)
    """
    import socket
    from urllib.parse import urlparse

    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        if not hostname:
            return False, "无法从 URL 中提取域名"
        socket.getaddrinfo(hostname, None)
        return True, ""
    except Exception as e:
        return False, str(e)


def check_urllib(url: str, timeout: int = 15, user_agent: str = "") -> tuple[int, str]:
    """用 Python urllib 访问 URL。

    功能说明（小白解读）：
        用 Python 内置的 urllib 去访问 URL，看看返回什么状态码或错误。
        这是最基础的访问方式，很多网站会拦截它。

    Args:
        url: 要访问的 URL
        timeout: 超时秒数
        user_agent: User-Agent 字符串（空的话用默认）

    Returns:
        tuple[int, str]: (HTTP 状态码, 错误信息)
            状态码 0 表示连接层面就失败了
    """
    try:
        headers = {}
        if user_agent:
            headers["User-Agent"] = user_agent
        else:
            headers["User-Agent"] = "OPC-Foundation-URLVerify/1.0"

        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, ""
    except urllib.error.HTTPError as e:
        return e.code, f"HTTP Error: {e.code}"
    except Exception as e:
        return 0, str(e)[:200]


def check_curl(url: str, timeout: int = 15, user_agent: str = "") -> tuple[int, str]:
    """用系统 curl 命令访问 URL。

    功能说明（小白解读）：
        调用系统的 curl.exe 来访问 URL。
        curl 的 TLS 实现和 Python urllib 不一样，
        有些网站 urllib 访问不了但 curl 可以，
        这样就能判断是不是 Python 客户端的问题。

    Args:
        url: 要访问的 URL
        timeout: 超时秒数
        user_agent: User-Agent 字符串（空的话用 curl 默认）

    Returns:
        tuple[int, str]: (HTTP 状态码, 错误信息)
            状态码 0 表示 curl 本身执行失败
    """
    cmd = ["curl", "-s", "-w", "%{http_code}", "--max-time", str(timeout), "-L"]

    if user_agent:
        cmd.extend(["-A", user_agent])

    # Windows 上用 curl.exe
    if sys.platform == "win32":
        cmd[0] = "curl.exe"

    # 输出到空设备（Windows 用 NUL，Linux/Mac 用 /dev/null）
    null_device = "NUL" if sys.platform == "win32" else "/dev/null"
    cmd.extend(["-o", null_device])

    cmd.append(url)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 5,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip() or result.stdout.strip() or f"curl exit code {result.returncode}"
            return 0, stderr[:200]

        # 从 stdout 读取 HTTP 状态码
        status_str = result.stdout.strip()
        try:
            status = int(status_str)
            return status, ""
        except ValueError:
            return 0, f"无法解析 curl 输出: {status_str[:100]}"
    except subprocess.TimeoutExpired:
        return 0, "curl timeout"
    except FileNotFoundError:
        return 0, "curl 命令未找到"
    except Exception as e:
        return 0, str(e)[:200]


def verify_url(url: str, timeout: int = 15) -> UrlVerifyResult:
    """对一个 URL 做完整验证。

    功能说明（小白解读）：
        依次做 DNS 检查、urllib 访问、curl 默认访问、curl 浏览器 UA 访问，
        最后综合判断这个 URL 到底是什么问题。

    综合判断逻辑：
        1. DNS 都解析不了 → dns_failed
        2. curl 能正常访问（200/301/302/403 等），但 urllib 不行 → python_client_limited
        3. curl 用浏览器 UA 能访问，但默认 curl 不行 → browser_like_needed
        4. curl 也 TLS 失败 → tls_handshake_failed
        5. curl 返回 4xx → http_4xx
        6. curl 返回 5xx → http_5xx
        7. 都不行 → unreachable

    Args:
        url: 要验证的 URL
        timeout: 每个检查的超时秒数

    Returns:
        UrlVerifyResult: 验证结果
    """
    result = UrlVerifyResult(url=url)

    # 1. DNS 检查
    dns_ok, dns_err = check_dns(url)
    result.dns_resolvable = dns_ok
    result.dns_error = dns_err

    if not dns_ok:
        result.final_verdict = "dns_failed"
        result.notes = "DNS 解析失败，域名可能不存在或已变更"
        return result

    # 2. urllib 访问
    urllib_status, urllib_err = check_urllib(url, timeout)
    result.urllib_status = urllib_status
    result.urllib_error = urllib_err

    # 3. curl 默认 UA 访问
    curl_status, curl_err = check_curl(url, timeout)
    result.curl_status = curl_status
    result.curl_error = curl_err

    # 4. curl 浏览器 UA 访问
    curl_browser_status, curl_browser_err = check_curl(url, timeout, BROWSER_USER_AGENT)
    result.curl_browser_ua_status = curl_browser_status
    result.curl_browser_ua_error = curl_browser_err

    # 5. 综合判断
    # curl 能拿到状态码（不管是 200/301/403 都说明网络通了）
    curl_reachable = curl_status > 0
    curl_browser_reachable = curl_browser_status > 0
    urllib_reachable = urllib_status > 0

    if curl_reachable and 200 <= curl_status < 400:
        # curl 能正常访问
        if not urllib_reachable:
            result.final_verdict = "python_client_limited"
            result.notes = "curl 可访问但 Python urllib 不行，可能是 TLS 客户端指纹问题"
        else:
            result.final_verdict = "reachable"
            result.notes = "可正常访问"
    elif curl_browser_reachable and 200 <= curl_browser_status < 400 and not curl_reachable:
        # 浏览器 UA 才能访问
        result.final_verdict = "browser_like_needed"
        result.notes = "需要浏览器式 User-Agent 才能访问"
    elif curl_reachable and 400 <= curl_status < 500:
        result.final_verdict = "http_4xx"
        result.notes = f"HTTP {curl_status}"
    elif curl_reachable and 500 <= curl_status < 600:
        result.final_verdict = "http_5xx"
        result.notes = f"HTTP {curl_status}"
    elif not curl_reachable and ("SSL" in curl_err or "ssl" in curl_err.lower() or "tls" in curl_err.lower()):
        result.final_verdict = "tls_handshake_failed"
        result.notes = "curl 也 TLS 握手失败"
    elif not curl_reachable:
        result.final_verdict = "unreachable"
        result.notes = f"curl 无法访问: {curl_err[:80]}"
    else:
        result.final_verdict = "unreachable"
        result.notes = "未知原因"

    return result
