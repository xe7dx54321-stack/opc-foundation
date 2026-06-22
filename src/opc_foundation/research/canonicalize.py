"""URL 规范化工具 —— 供 research 模块去重和索引共用。

功能说明（小白解读）：
    把不同写法但指向同一资源的 URL 统一成同一个字符串，
    这样去重时才不会把同一篇文章当成两篇。

规范化规则：
    - 去掉 fragment（# 后面的部分）
    - 小写 scheme 和 netloc（域名不区分大小写）
    - 去掉尾部斜杠
    - 移除常见 tracking 参数（utm_*、fbclid、gclid 等）
    - 剩余 query 参数按 key 排序
"""
from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from ..web.url_utils import canonicalize_url


# 常见 tracking 参数名（全小写匹配）
_TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "gbraid",
    "wbraid",
    "ref",
    "ref_src",
    "spm",
    "from",
    "scenes",
    "clicktime",
    "enterid",
    "forceh5",
}


def canonicalize_research_url(url: str) -> str:
    """规范化 URL，用于 research 模块去重。

    参数：
        url: 待规范化的 URL 字符串

    返回：
        规范化后的 URL 字符串；如果解析失败返回 strip 后的原始 URL

    使用示例：
        >>> canonicalize_research_url("HTTPS://Example.COM/Article?utm_source=x#section")
        'https://example.com/Article'
    """

    base = canonicalize_url(url or "")
    try:
        parsed = urlparse(base)
        # 过滤掉 tracking 参数
        qs = [
            (k, v)
            for k, v in parse_qsl(parsed.query)
            if k.lower() not in _TRACKING_PARAMS
        ]
        qs.sort(key=lambda kv: kv[0])
        new_query = urlencode(qs)
        norm = parsed._replace(query=new_query)
        return urlunparse(norm)
    except Exception:
        return base
