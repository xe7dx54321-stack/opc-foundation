"""把文章正文 HTML 转成简易 Markdown。

功能说明（小白解读）：
    不追求完美 Markdown，只保证：
    1. 标题、公众号、原文链接、发布时间、抓取时间都在前面
    2. 段内 <strong>/<em>/<a> 等常见内联标签都做了转换
    3. 图片保留 ![](url)
    4. 标题标签 <h1>..<h6> 转成对应 # 数量
    5. 列表 <ul>/<ol> 转成 Markdown 列表
    6. <blockquote> 转成 > 块
    7. <br/> / </p> 都转换行，多个空行折叠
"""
from __future__ import annotations

import html
import re
from typing import Any

from .models import ExtractedContent


def _inline_to_md(text: str) -> str:
    """处理段内的内联标签（<strong>, <em>, <a>, <br>, <span> 等）。"""

    # <a href="URL">TEXT</a> -> [TEXT](URL)
    text = re.sub(
        r"""<a\b[^>]*href\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))[^>]*>(.*?)</a>""",
        lambda m: f"[{_strip_all_tags(m.group(4))}]({(m.group(1) or m.group(2) or m.group(3) or '').strip()})",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    # <strong>/<b>
    text = re.sub(r"<\s*(?:strong|b)\b[^>]*>(.*?)</\s*(?:strong|b)\s*>", r"**\1**",
                  text, flags=re.IGNORECASE | re.DOTALL)
    # <em>/<i>
    text = re.sub(r"<\s*(?:em|i)\b[^>]*>(.*?)</\s*(?:em|i)\s*>", r"*\1*",
                  text, flags=re.IGNORECASE | re.DOTALL)
    # <br />, <br/> 等
    text = re.sub(r"<\s*br\b[^>]*/?\s*>", "\n", text, flags=re.IGNORECASE)
    # <hr>
    text = re.sub(r"<\s*hr\b[^>]*/?\s*>", "\n---\n", text, flags=re.IGNORECASE)
    # 其他未知标签直接丢掉
    text = re.sub(r"<[^>]+>", "", text)
    # HTML 实体转义还原
    text = html.unescape(text)
    return text.strip()


def _strip_all_tags(text: str) -> str:
    """去掉所有 HTML 标签，返回纯文本。"""

    cleaned = re.sub(r"<[^>]+>", "", text or "")
    return html.unescape(cleaned).strip()


def _html_to_markdown(html: str) -> str:
    """把正文 HTML 转换成简易 Markdown。

    策略（轻量、不依赖第三方库）：
        - 切分成若干顶层块
        - 根据开头标签的不同选择不同转换：<h1>..<h6>, <ul>/<ol>, <blockquote>, <figure>, <p>...
        - 不认识的块用内联转换兜底
    """

    if not html:
        return ""

    blocks = _split_blocks(html)
    out_lines: list[str] = []
    for b in blocks:
        md = _block_to_markdown(b)
        if md:
            out_lines.append(md)
    # 折叠超过 2 个连续空行
    merged = "\n".join(out_lines)
    merged = re.sub(r"\n{3,}", "\n\n", merged).strip()
    return merged


_BLOCK_OPEN_RE = re.compile(
    r"""^\s*<\s*([a-zA-Z][a-zA-Z0-9-]*)\b([^>]*)>""",
    re.IGNORECASE | re.DOTALL,
)


def _split_blocks(html: str) -> list[str]:
    """把 HTML 切成若干顶层块（大致按块级标签切分）。"""

    html = html.strip()
    if not html:
        return []

    block_tags = {
        "h1", "h2", "h3", "h4", "h5", "h6",
        "p", "div", "section", "article",
        "ul", "ol", "li",
        "blockquote", "figure", "pre",
        "table", "header", "footer", "aside",
    }
    blocks: list[str] = []
    i = 0
    n = len(html)

    while i < n:
        # 跳过空白
        while i < n and html[i] in " \t\r\n":
            i += 1
        if i >= n:
            break

        if html[i] != "<":
            # 一段裸文本，直到下一个标签开始
            j = html.find("<", i)
            if j == -1:
                j = n
            blocks.append(html[i:j])
            i = j
            continue

        # 是一个标签
        m = _BLOCK_OPEN_RE.match(html, i)
        if not m:
            # 不是我们认识的块，读一个 tag 直接丢掉或当成文本
            end = html.find(">", i)
            if end == -1:
                break
            i = end + 1
            continue

        tag_name = m.group(1).lower()
        if tag_name in block_tags:
            close_pos = _find_block_close(html, tag_name, m.end())
            if close_pos is None:
                block = html[m.start():]
                blocks.append(block)
                break
            block = html[m.start():close_pos]
            blocks.append(block)
            i = close_pos
        else:
            # 非块级，读一个 tag 跳过
            end = html.find(">", m.start())
            if end == -1:
                break
            i = end + 1
    return blocks


def _find_block_close(html: str, tag_name: str, start: int) -> int | None:
    depth = 1
    i = start
    open_pat = re.compile(
        r"<\s*(" + re.escape(tag_name) + r")\b[^>]*>",
        re.IGNORECASE,
    )
    close_pat = re.compile(
        r"</\s*(" + re.escape(tag_name) + r")\b[^>]*>",
        re.IGNORECASE,
    )
    while i < len(html):
        co = close_pat.search(html, i)
        op = open_pat.search(html, i)
        if not co:
            return None
        # 看 open 和 close 谁更近
        if op and op.start() < co.start():
            depth += 1
            i = op.end()
            continue
        # co 是最近的
        depth -= 1
        if depth == 0:
            return co.end()
        i = co.end()
    return None


def _extract_inner(block: str, tag_name: str) -> str:
    """从 '<tag ...>inner</tag>' 中拿出 inner 内容。"""

    open_pat = re.compile(
        r"^<\s*" + re.escape(tag_name) + r"\b[^>]*>",
        re.IGNORECASE | re.DOTALL,
    )
    close_pat = re.compile(
        r"</\s*" + re.escape(tag_name) + r"\b[^>]*>\s*$",
        re.IGNORECASE | re.DOTALL,
    )
    inner = open_pat.sub("", block, count=1)
    inner = close_pat.sub("", inner, count=1)
    return inner.strip()


def _block_to_markdown(block: str) -> str:
    """把单个块转成对应 Markdown 行。"""

    m = _BLOCK_OPEN_RE.match(block)
    if not m:
        return _inline_to_md(block)

    tag = m.group(1).lower()

    if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
        level = int(tag[1])
        inner = _extract_inner(block, tag)
        return "#" * level + " " + _inline_to_md(inner)

    if tag in ("p", "div", "section", "article", "header", "footer", "aside"):
        inner = _extract_inner(block, tag)
        return _inline_to_md(inner)

    if tag in ("ul", "ol"):
        ordered = tag == "ol"
        inner = _extract_inner(block, tag)
        return _list_to_markdown(inner, ordered=ordered)

    if tag == "li":
        inner = _extract_inner(block, tag)
        return "- " + _inline_to_md(inner)

    if tag == "blockquote":
        inner = _extract_inner(block, tag)
        lines = _html_to_markdown(inner).splitlines()
        return "\n".join(("> " + line) if line.strip() else ">" for line in lines)

    if tag == "figure":
        inner = _extract_inner(block, tag)
        # figure 常见是 <img ...><figcaption>...</figcaption>
        return _inline_to_md(inner)

    if tag == "pre":
        inner = _extract_inner(block, tag)
        inner = html.unescape(re.sub(r"<[^>]+>", "", inner))
        return "```\n" + inner + "\n```"

    return _inline_to_md(block)


_LIST_ITEM_RE = re.compile(
    r"""<li\b[^>]*>(.*?)</li>""",
    re.IGNORECASE | re.DOTALL,
)


def _list_to_markdown(inner: str, ordered: bool) -> str:
    items = [m.group(1) for m in _LIST_ITEM_RE.finditer(inner)]
    lines: list[str] = []
    for idx, item in enumerate(items, start=1):
        text = _inline_to_md(item)
        if not text:
            continue
        if ordered:
            lines.append(f"{idx}. {text}")
        else:
            lines.append(f"- {text}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 图片 URL 改写
# ---------------------------------------------------------------------------


def rewrite_markdown_image_urls(markdown: str, url_map: dict[str, str]) -> str:
    """把 Markdown 中 ![](old_url) 里的 old_url 换成 url_map 中对应的新 URL。

    参数：
        markdown: 原始 Markdown
        url_map:  {原始_url: 本地相对路径}

    返回：
        替换后的 Markdown
    """

    if not url_map:
        return markdown

    # 按 key 长度降序，避免短 key 把长 key 误替换
    keys = sorted(url_map.keys(), key=len, reverse=True)

    def _repl(m: re.Match[str]) -> str:
        alt = m.group(1) or ""
        url = m.group(2) or ""
        new_url = url_map.get(url) or url
        return f"![{alt}]({new_url})"

    pattern = re.compile(r"!\[([^\]]*)\]\(([^)]*)\)")
    text = pattern.sub(_repl, markdown)

    # 兜底：直接把 URL 文本替换
    for k in keys:
        if k in text and url_map[k] != k:
            text = text.replace(k, url_map[k])
    return text


def rewrite_html_image_urls(html: str, url_map: dict[str, str]) -> str:
    """在 HTML 中把 <img src="x"> 的 src 替换成 url_map[x]。

    同时处理 data-src / data-original-src 等懒加载属性。
    """

    if not url_map:
        return html

    def _img_repl(m: re.Match[str]) -> str:
        attrs = m.group(1)
        # 对 src, data-src, data-original-src 做替换
        def _attr_repl(am: re.Match[str]) -> str:
            name = am.group(1)
            quote = am.group(2)
            val = am.group(3)
            if name.lower() not in {"src", "data-src", "data-original-src"}:
                return am.group(0)
            new_val = url_map.get(val, val)
            return f"{name}={quote}{new_val}{quote}"

        new_attrs = re.sub(
            r"""(src|data-src|data-original-src)\s*=\s*(["'])(.*?)\2""",
            _attr_repl,
            attrs,
            flags=re.IGNORECASE,
        )
        return f"<img{new_attrs}/>"

    return re.sub(
        r"""<img\b([^>]*)/?>""",
        _img_repl,
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )


# ---------------------------------------------------------------------------
# 对外 API
# ---------------------------------------------------------------------------


def html_to_markdown(content: ExtractedContent) -> str:
    """把正文内容转换成 Markdown。"""

    return _html_to_markdown(content.html or "")


def build_article_markdown(
    candidate: ArticleCandidateLike,
    content: ExtractedContent,
    captured_at: str | None = None,
) -> str:
    """生成最终归档用的 Markdown（包含文章头信息）。"""

    title = (content.title or candidate.title or "未命名文章").strip()
    author = content.author or candidate.author
    published_at = content.publish_time or candidate.published_at
    source = candidate.account_name or "未知公众号"  # type: ignore[attr-defined]
    url = candidate.url  # type: ignore[attr-defined]

    lines: list[str] = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"- 来源公众号：{source}")
    lines.append(f"- 原文链接：{url}")
    if published_at:
        lines.append(f"- 发布时间：{published_at}")
    if captured_at:
        lines.append(f"- 抓取时间：{captured_at}")
    if author:
        lines.append(f"- 作者：{author}")
    lines.append("")
    lines.append("---")
    lines.append("")
    body = html_to_markdown(content)
    lines.append(body)
    lines.append("")
    return "\n".join(lines)


# 允许外部传 ArticleCandidate 或具备相应属性的对象
ArticleCandidateLike = Any
