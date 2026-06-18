"""URL 安全校验器 —— 防止 SSRF（服务端请求伪造）攻击。

功能说明：
    在发起任何对外 HTTP 请求前，校验 URL 是否安全。
    防止攻击者通过 file:///etc/passwd 读取本地文件，
    或通过 http://169.254.169.254/ 访问云元数据端点。

校验规则：
    1. 只允许 http/https 协议
    2. 禁止 file:// / ftp:// / data: / javascript: 等非 HTTP 协议
    3. 禁止 localhost / 0.0.0.0
    4. 禁止私网 IPv4（10.x / 172.16-31.x / 192.168.x）
    5. 禁止 link-local 地址（169.254.x，含云元数据 169.254.169.254）
    6. 禁止 IPv6 私网（fc00::/7）、link-local（fe80::/10）、环回（::1）
    7. 禁止 hostname DNS 解析后落到上述任何地址
    8. 默认不允许访问内网，除非显式传 allow_private=True
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


class URLValidationError(ValueError):
    """URL 未通过安全校验时抛出的异常。"""
    pass


# 只允许这两个协议
_ALLOWED_SCHEMES = {"http", "https"}

# 直接字符串匹配禁止的 hostname
_BLOCKED_HOSTNAMES = {"localhost", "0.0.0.0"}


def _is_ip_private_or_blocked(ip_str: str) -> bool:
    """检查 IP 地址是否属于不应访问的范围。

    参数：
        ip_str: IP 地址字符串，如 "127.0.0.1" 或 "::1"

    返回：
        True 表示该 IP 不应被访问（私网/环回/link-local/组播/保留地址）
        False 表示该 IP 是公网地址，可以访问
    """
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        # 无法解析的 IP 视为不安全
        return True

    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _check_hostname(hostname: str, allow_private: bool, check_dns: bool) -> None:
    """校验 hostname 是否安全。

    参数：
        hostname: 主机名，如 "example.com" 或 "127.0.0.1"
        allow_private: 是否允许访问私网地址（True 则跳过所有检查）
        check_dns: 是否对域名做 DNS 解析检查

    异常：
        URLValidationError: 当 hostname 不安全时抛出
    """
    if allow_private:
        return

    hostname = hostname.lower()

    # 检查直接字符串匹配的禁止 hostname
    if hostname in _BLOCKED_HOSTNAMES:
        raise URLValidationError(f"Blocked hostname: {hostname}")

    # 尝试把 hostname 当作 IP 地址解析
    try:
        ip = ipaddress.ip_address(hostname)
        if _is_ip_private_or_blocked(str(ip)):
            raise URLValidationError(f"Blocked IP address: {hostname}")
        # 是公网 IP，通过
        return
    except ValueError:
        pass  # 不是 IP 地址，是域名，继续做 DNS 检查

    # DNS 解析检查：解析域名，看解析出的 IP 是否落在私网
    if check_dns:
        # DNS 解析可能阻塞，设置 5 秒 timeout 防止恶意慢响应 DNS 服务器导致 DoS
        # socket.getaddrinfo 本身不接受 timeout 参数，用 setdefaulttimeout 临时设置
        old_timeout = socket.getdefaulttimeout()
        try:
            socket.setdefaulttimeout(5)
            try:
                infos = socket.getaddrinfo(hostname, None)
            except (socket.gaierror, socket.timeout, OSError) as exc:
                # fail-closed：DNS 解析失败视为不安全
                # 小白解读：如果连域名都解析不出来，说明这个域名可能有问题，
                # 直接拒绝比放行更安全（放行的话请求发出去也会失败，还可能被利用）
                raise URLValidationError(
                    f"DNS resolution failed for {hostname}: {exc}"
                ) from exc
            for _family, _type, _proto, _canon, sockaddr in infos:
                ip_str = sockaddr[0]
                if _is_ip_private_or_blocked(ip_str):
                    raise URLValidationError(
                        f"Hostname {hostname} resolves to blocked IP: {ip_str}"
                    )
        finally:
            # 恢复原来的全局 timeout 设置
            socket.setdefaulttimeout(old_timeout)


def validate_url(
    url: str,
    allow_private: bool = False,
    check_dns: bool = True,
) -> str:
    """校验 URL 是否安全可访问，防止 SSRF 攻击。

    参数：
        url: 待校验的 URL 字符串
        allow_private: 是否允许访问私网/内网地址（默认 False，业务项目一般不用）
        check_dns: 是否对域名做 DNS 解析检查（默认 True）

    返回：
        校验通过后返回原始 URL 字符串

    异常：
        URLValidationError: 当 URL 不安全时抛出

    使用示例：
        >>> validate_url("https://example.com/article")
        'https://example.com/article'
        >>> validate_url("file:///etc/passwd")
        Traceback (most recent call last):
            ...
        URLValidationError: Blocked scheme: file
        >>> validate_url("http://127.0.0.1/admin")
        Traceback (most recent call last):
            ...
        URLValidationError: Blocked IP address: 127.0.0.1
    """
    if not url or not url.strip():
        raise URLValidationError("Empty URL")

    parsed = urlparse(url.strip())

    # 检查协议：只允许 http/https
    scheme = (parsed.scheme or "").lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise URLValidationError(f"Blocked scheme: {scheme or '(none)'}")

    # 检查 hostname
    hostname = parsed.hostname
    if not hostname:
        raise URLValidationError(f"No hostname in URL: {url}")

    _check_hostname(hostname, allow_private=allow_private, check_dns=check_dns)

    return url
