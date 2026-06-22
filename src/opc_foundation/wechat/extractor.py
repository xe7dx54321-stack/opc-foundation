"""微信文章 HTML 正文提取与基础清洗。

功能说明（小白解读）：
    本文件从一个完整的 HTML 页面中提取"可阅读正文"。
    针对 mp.weixin.qq.com 公众号文章，我们用几个常见的容器 id/class 来定位正文：
        - #js_content
        - #article
        - .rich_media_content
        - article / .article-content / .content

    对于其他页面（例如测试 fixture），会回退到 <article> / 最大 <div> 文本块策略。

    另外：
    - 解析 <h1> / <meta property="og:title"> / <title> 作为标题
    - 解析 meta 标签里的发布时间（若有）
    - 提取所有 <img> 的 src/data-src 作为正文图片
    - 用 trafilatura 做兜底提取（如果仓库里的版本可用）
"""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin, urlparse

from .models import ExtractedContent


# ---------------------------------------------------------------------------
# HTML 工具
# ---------------------------------------------------------------------------

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _strip_tags(html: str) -> str:
    """极简版去除 HTML 标签，仅用于生成纯文本。"""

    text = _TAG_RE.sub(" ", html or "")
    text = _WS_RE.sub(" ", text).strip()
    return text


def _attr(attrs_str: str, name: str) -> str | None:
    """从一个形如 'id="foo" class="bar"' 的字符串里解析某个属性值。"""

    # 手写一个小解析器，避免引入额外依赖（例如 BeautifulSoup）
    pattern = re.compile(
        r"""(?:^|\s)""" + re.escape(name) + r"""\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""",
        re.IGNORECASE,
    )
    m = pattern.search(attrs_str)
    if not m:
        return None
    return (m.group(1) or m.group(2) or m.group(3) or "").strip() or None


def _parse_tag(tag_html: str) -> tuple[str, dict[str, str], bool, str]:
    """把一个 '<div id="x" class="y">' 这种字符串解析成 (tag_name, attrs, is_closing, rest)。"""

    m = re.match(r"<\s*/?\s*([a-zA-Z][a-zA-Z0-9-]*)([^>]*)>", tag_html, re.IGNORECASE)
    if not m:
        return "", {}, False, tag_html
    name = m.group(1).lower()
    attrs_str = m.group(2)
    is_close = "/" in tag_html[:4]

    attrs: dict[str, str] = {}
    for match in re.finditer(
        r"""([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""",
        attrs_str,
    ):
        key = match.group(1).lower()
        val = (match.group(2) or match.group(3) or match.group(4) or "").strip()
        attrs[key] = val
    return name, attrs, is_close, tag_html


def _resolve_img_url(attrs: dict[str, str], base_url: str) -> str | None:
    """从 <img> 的属性里找出最可能的真实图片 URL。

    微信常用 data-src / data-srcset 做懒加载，真实链接一般在 data-src 里。
    """

    for key in ("data-src", "data-original-src", "src"):
        v = attrs.get(key)
        if v and v.strip():
            url = v.strip()
            if url.startswith(("http://", "https://")):
                return url
            if url.startswith("//"):
                return "https:" + url
            # 相对路径
            if base_url:
                return urljoin(base_url + "/", url)
            return url
    return None


# ---------------------------------------------------------------------------
# 元数据解析
# ---------------------------------------------------------------------------

_META_RE = re.compile(
    r"""<meta\s+([^>]*)/?>""",
    re.IGNORECASE | re.DOTALL,
)


def _parse_meta(html: str) -> dict[str, str]:
    """从 HTML 里提取 meta 标签的 property/name -> content。"""

    result: dict[str, str] = {}
    for m in _META_RE.finditer(html):
        attrs_str = m.group(1)
        key = (
            _attr(attrs_str, "property")
            or _attr(attrs_str, "name")
            or ""
        ).lower()
        val = _attr(attrs_str, "content")
        if key and val:
            result[key] = val
    return result


_TITLE_TAG_RE = re.compile(
    r"""<title[^>]*>(.*?)</title>""",
    re.IGNORECASE | re.DOTALL,
)
_H1_RE = re.compile(
    r"""<h1[^>]*>(.*?)</h1>""",
    re.IGNORECASE | re.DOTALL,
)
_H2_RE = re.compile(
    r"""<h2[^>]*>(.*?)</h2>""",
    re.IGNORECASE | re.DOTALL,
)


def _extract_title(html: str, meta: dict[str, str]) -> str | None:
    """从 HTML 里尽力提取标题。"""

    if meta.get("og:title"):
        t = _strip_tags(meta["og:title"])
        if t:
            return t

    # 公众号常见：<h1 class="rich_media_title" ...>
    for pat in (_H1_RE, _H2_RE, _TITLE_TAG_RE):
        m = pat.search(html)
        if m:
            t = _strip_tags(m.group(1))
            if t:
                return t
    return None


_PUBLISH_TIME_RE = re.compile(
    r"""(?:publish_time|pub_time|发布时间)["\']?\s*[:=]\s*["\']?([0-9T\-:\s]{6,}?)["\']""",
    re.IGNORECASE,
)


def _extract_publish_time(html: str, meta: dict[str, str]) -> str | None:
    """尽力提取文章内的发布时间。"""

    if meta.get("article:published_time"):
        return meta["article:published_time"].strip()
    if meta.get("weibo:article:publish_time"):
        return meta["weibo:article:publish_time"].strip()
    if meta.get("pub_date"):
        return meta["pub_date"].strip()

    m = _PUBLISH_TIME_RE.search(html)
    if m:
        return m.group(1).strip()
    return None


_AUTHOR_RE = re.compile(
    r"""(?:author|作者)["\']?\s*[:=]\s*["\']?([^\s"'<>][^"'<>]{0,80}?)["\']""",
    re.IGNORECASE,
)


def _extract_author(html: str, meta: dict[str, str]) -> str | None:
    if meta.get("author"):
        return meta["author"].strip()
    if meta.get("og:article:author"):
        return meta["og:article:author"].strip()

    # 公众号常见：<a class="rich_media_meta_nickname">公众号昵称</a>
    nickname = re.search(
        r"""<a[^>]+class="[^"]*rich_media_meta_nickname[^"]*"[^>]*>([^<]+)</a>""",
        html,
        re.IGNORECASE | re.DOTALL,
    )
    if nickname:
        return nickname.group(1).strip()

    m = _AUTHOR_RE.search(html)
    if m:
        return m.group(1).strip()
    return None


# ---------------------------------------------------------------------------
# 正文区域提取
# ---------------------------------------------------------------------------

# 可能包含正文的容器 id / class 关键字（按优先级从高到低）
_BODY_CONTAINER_HINTS = [
    ("id", "js_content"),
    ("id", "article-content"),
    ("id", "articleBody"),
    ("id", "article_body"),
    ("class", "rich_media_content"),
    ("class", "article-content"),
    ("class", "article_content"),
    ("id", "article"),
    ("class", "article"),
]


def _extract_container_html(html: str) -> str | None:
    """从页面 HTML 里找到一段最可能是正文的容器 HTML。

    我们不用 BeautifulSoup，自己做一个轻量的扫描：
    1) 找到目标容器的开始标签（带 id/class 关键字）
    2) 做括号匹配，找到对应的结束标签
    3) 返回该容器内部 HTML
    """

    lower_html = html.lower()
    best_inner: str | None = None
    best_score = 0

    for attr_type, keyword in _BODY_CONTAINER_HINTS:
        # 用正则定位目标标签：<div id="js_content" ...> 或 <section class="rich_media_content" ...>
        pattern = re.compile(
            r"""<([a-zA-Z][a-zA-Z0-9-]*)([^>]*\b""" + re.escape(attr_type)
            + r"""\s*=\s*(?:""" + re.escape(keyword) + r"""|"[^"]*\b"""
            + re.escape(keyword) + r"""\b[^"]*"|'[^']*\b""" + re.escape(keyword)
            + r"""\b[^']*'|[^\s>"'`][^\s>"']*))[^>]*>""",
            re.IGNORECASE | re.DOTALL,
        )
        m = pattern.search(html)
        if not m:
            # 也允许 keyword 直接出现在属性里
            pat2 = re.compile(
                r"""<([a-zA-Z][a-zA-Z0-9-]*)([^>]*\b""" + re.escape(keyword) + r"""\b[^>]*)>""",
                re.IGNORECASE | re.DOTALL,
            )
            m = pat2.search(html)
            if not m:
                continue
        tag_name = m.group(1).lower()
        start = m.end()
        end = _find_matching_close(html, tag_name, start)
        if end is None:
            continue
        inner_html = html[start:end]
        # 用"纯文本长度"和"图片数量"做一个简单打分
        text_len = len(_strip_tags(inner_html))
        img_count = inner_html.lower().count("<img")
        score = text_len + img_count * 20
        if score > best_score:
            best_score = score
            best_inner = inner_html

    # 兜底策略：找 <article> 标签
    if best_inner is None:
        art_match = re.search(
            r"""<article([^>]*)>(.*?)</article>""", html, re.IGNORECASE | re.DOTALL
        )
        if art_match:
            inner_html = art_match.group(2)
            text_len = len(_strip_tags(inner_html))
            if text_len > best_score:
                best_inner = inner_html

    return best_inner


def _find_matching_close(html: str, tag_name: str, start: int) -> int | None:
    """在 html 中从 start 位置开始，找到与 tag_name 匹配的闭合标签位置。"""

    depth = 1
    i = start
    pattern = re.compile(r"<\s*(/?)\s*(" + re.escape(tag_name) + r")\b[^>]*>", re.IGNORECASE)
    while i < len(html):
        m = pattern.search(html, i)
        if not m:
            return None
        is_close = bool(m.group(1))
        if is_close:
            depth -= 1
            if depth == 0:
                return m.start()
        else:
            depth += 1
        i = m.end()
    return None


# ---------------------------------------------------------------------------
# 提取图片
# ---------------------------------------------------------------------------

_IMG_RE = re.compile(r"""<img([^>]*)/?>""", re.IGNORECASE | re.DOTALL)


def _extract_image_urls(inner_html: str, base_url: str) -> list[str]:
    """从 inner_html 中提取去重后的图片 URL 列表。"""

    urls: list[str] = []
    seen: set[str] = set()
    for m in _IMG_RE.finditer(inner_html):
        attrs = {}
        attrs_str = m.group(1)
        for am in re.finditer(
            r"""([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))""",
            attrs_str,
        ):
            attrs[am.group(1).lower()] = (
                am.group(2) or am.group(3) or am.group(4) or ""
            ).strip()

        url = _resolve_img_url(attrs, base_url)
        if url and url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


# ---------------------------------------------------------------------------
# 对外 API
# ---------------------------------------------------------------------------


def extract_main_content(html: str, url: str = "") -> ExtractedContent:
    """从一个完整的 HTML 页面提取文章正文。

    参数：
        html: 完整 HTML 页面（字符串）
        url:  原始 URL（用于相对链接解析，可选）

    返回：
        ExtractedContent（标题/作者/发布时间/HTML/纯文本/图片 URL 等）
    """

    if not html:
        return ExtractedContent()

    meta = _parse_meta(html)
    title = _extract_title(html, meta)
    publish_time = _extract_publish_time(html, meta)
    author = _extract_author(html, meta)

    inner_html = _extract_container_html(html)

    if inner_html:
        image_urls = _extract_image_urls(inner_html, url or "")
        text = _strip_tags(inner_html)
        return ExtractedContent(
            title=title,
            author=author,
            publish_time=publish_time,
            html=inner_html.strip(),
            text=text,
            image_urls=image_urls,
            cover_url=meta.get("og:image"),
            digest=meta.get("description") or (text[:180] + "…") if text else None,
        )

    # 提取不到正文容器：回退成"全文"（后续 cleaner 会做噪声清洗）
    image_urls = _extract_image_urls(html, url or "")
    text = _strip_tags(html)
    return ExtractedContent(
        title=title,
        author=author,
        publish_time=publish_time,
        html=html.strip(),
        text=text,
        image_urls=image_urls,
        cover_url=meta.get("og:image"),
        digest=meta.get("description"),
    )


# ---------------------------------------------------------------------------
# 公开图片提取函数（cleaner.py 等模块使用）
# ---------------------------------------------------------------------------


def extract_image_urls_from_html(html: str, base_url: str = "") -> list[str]:
    """从任意 HTML 片段中提取去重后的图片 URL 列表。

    参数：
        html:     HTML 字符串（可以是完整页面或正文片段）
        base_url: 基准 URL（用于解析相对路径，可选）

    返回：
        唯一图片 URL 列表

    说明（小白解读）：
        这个函数不依赖 BeautifulSoup，只用正则扫描 <img> 标签，
        支持常见懒加载属性（data-src / data-original-src / src），
        由 extractor.extract_main_content 内部使用，也可被 cleaner.py 等模块公开调用。
    """
    return _extract_image_urls(html, base_url)
