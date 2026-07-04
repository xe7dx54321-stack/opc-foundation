"""Global test fixtures and utilities for OPC Foundation tests.

功能说明：
    解决当前 macOS 测试环境中 example.com / hn.algolia.com 等测试域名
    解析到被阻止的私有 IP（如 198.18.0.x）导致大量测试失败的问题。
    通过 session-scoped autouse fixture 在测试会话期间 mock DNS 解析，
    让已知测试域名返回安全的公网 IP，从而通过 url_validator 的 SSRF 检查。
    不影响生产代码，仅作用于测试环境。
"""
import socket
import pytest

# 在当前 macOS 测试环境中解析到被阻止 IP 的测试域名
_BLOCKED_TEST_HOSTS = {
    "example.com",
    "hn.algolia.com",
}

# example.com 的真实公网 IP，用于通过 url_validator 的 _is_ip_private_or_blocked 检查
_SAFE_PUBLIC_IP = "93.184.216.34"


@pytest.fixture(autouse=True, scope="session")
def mock_blocked_test_dns():
    """Mock DNS resolution for test hosts blocked in this environment.

    在当前测试环境中，example.com 和 hn.algolia.com 会被 DNS 解析到
    198.18.0.x（私有/保留地址），导致 url_validator 的 SSRF 防护将其阻止，
    进而导致大量依赖这些域名的 mock 测试失败。

    此 fixture 在测试会话期间临时替换 socket.getaddrinfo，对已知测试域名
    返回一个安全的公网 IP，使 url_validator 能够通过检查，让测试进入
    真正的 mock HTTP client 阶段。

    不影响真实网络请求（其他域名仍走原始 DNS 解析），也不影响生产代码。
    """
    original_getaddrinfo = socket.getaddrinfo

    def _mock_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        if host in _BLOCKED_TEST_HOSTS:
            return [
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", (_SAFE_PUBLIC_IP, port))
            ]
        return original_getaddrinfo(host, port, family, type, proto, flags)

    socket.getaddrinfo = _mock_getaddrinfo
    yield
    socket.getaddrinfo = original_getaddrinfo
