"""统一的 URL 规范化工具 —— 供去重和搜索结果归一化共用。

功能说明：
    提供 canonicalize_url() 函数，统一 URL 规范化逻辑。
    之前 dedupe.py 和 search_result_normalizer.py 各有自己的规范化逻辑，
    导致同一 URL 在两个模块产生不同结果，跨模块去重会失效。

规范化规则：
    - 去掉 fragment（# 后面的部分）
    - 小写 scheme 和 netloc（域名不区分大小写）
    - 保留 path 原始大小写（某些服务器 path 区分大小写，如 GitHub raw 文件）
    - 去掉尾部斜杠
"""
from __future__ import annotations

from urllib.parse import urlparse, urlunparse


def canonicalize_url(url: str) -> str:
    """规范化 URL，用于去重和比较。

    参数：
        url: 待规范化的 URL 字符串

    返回：
        规范化后的 URL 字符串；如果解析失败返回 strip 后的原始 URL

    使用示例：
        >>> canonicalize_url("HTTPS://Example.COM/Article#section")
        'https://example.com/Article'
        >>> canonicalize_url("https://example.com/path/")
        'https://example.com/path'
    """
    try:
        p = urlparse(url.strip())
        norm = p._replace(
            fragment="",
            scheme=p.scheme.lower(),
            netloc=p.netloc.lower(),
        )
        return urlunparse(norm).rstrip("/")
    except Exception:
        return url.strip()
