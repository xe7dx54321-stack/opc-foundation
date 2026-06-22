"""HTML 噪声清洗。

功能说明（小白解读）：
    公众号文章 HTML 中经常有一些尾部噪声：
    - "阅读原文"链接
    - "扫码关注"二维码块
    - "商务合作"区块
    - "往期推荐"列表
    - "免责声明"段落
    - 空白的 <p></p> / <br /> 等

    本文件提供可配置的清洗规则，默认会处理上面这些常见噪声。
"""
from __future__ import annotations

import re
from typing import Any

from .models import ExtractedContent


# ---------------------------------------------------------------------------
# 默认规则：关键词匹配的容器/段落
# ---------------------------------------------------------------------------

_DEFAULT_NOISE_KEYWORDS = [
    "阅读原文",
    "扫码关注",
    "长按识别",
    "关注公众号",
    "商务合作",
    "商业转载",
    "往期推荐",
    "免责声明",
    "本文作者",
    "资料来源",
    "推荐阅读",
    "相关文章",
    "编辑：",
    "排版：",
    "未经授权禁止转载",
]


def _strip_html_block_tags(html: str) -> str:
    r"""对外部传入的正文 HTML 做一次外层剥离，避免

    '<div id="js_content">...</div>' 自己被删掉。
    这里我们保留原始结构，仅做子块处理。
    """

    return html


def _html_segments(html: str) -> list[str]:
    """把 HTML 切成若干"顶层段落块"，便于逐段判断是否为噪声。

    策略：
        - 先按块级标签（<div>, <section>, <p>, <ul>, <ol>, <figure>, <blockquote>
          <h1>..<h6>, <header>）分段
        - 文本/内联标签合并为一段
    """

    segments: list[str] = []
    i = 0
    buf: list[str] = []

    block_tags = {
        "div", "section", "p", "ul", "ol", "li", "figure",
        "blockquote", "h1", "h2", "h3", "h4", "h5", "h6",
        "header", "footer", "aside",
    }
    self_close = {"br", "img", "hr"}

    pattern = re.compile(
        r"""<\s*(/?)\s*([a-zA-Z][a-zA-Z0-9-]*)\b([^>]*)>""",
        re.IGNORECASE | re.DOTALL,
    )

    while i < len(html):
        m = pattern.search(html, i)
        if not m:
            buf.append(html[i:])
            break

        # 标签之前的文本先累积到 buf
        if m.start() > i:
            buf.append(html[i : m.start()])

        is_close = bool(m.group(1))
        tag_name = m.group(2).lower()
        full_tag = m.group(0)

        if tag_name in self_close:
            # 自闭合标签算一段文本的一部分
            buf.append(full_tag)
        elif tag_name in block_tags and not is_close:
            # 先把之前累积的 buf 单独成段
            text_before = "".join(buf).strip()
            if text_before:
                segments.append(text_before)
            buf = []
            # 找到闭合位置
            close_pos = _find_matching_close_position(html, tag_name, m.end())
            if close_pos is None:
                # 匹配不到闭合，就把剩下内容整段放进来
                block = html[m.start():]
                segments.append(block)
                break
            block = html[m.start() : close_pos]
            segments.append(block)
            i = close_pos
            continue
        elif tag_name in block_tags and is_close:
            # 单独的结束标签（不常见），忽略
            pass
        else:
            # 内联标签：加入 buf
            buf.append(full_tag)
        i = m.end()

    # 最后把 buf 里剩下的内容当成一段
    tail = "".join(buf).strip()
    if tail:
        segments.append(tail)
    return segments


def _find_matching_close_position(html: str, tag_name: str, start: int) -> int | None:
    depth = 1
    i = start
    pattern = re.compile(
        r"""<\s*(/?)\s*(""" + re.escape(tag_name) + r""")\b[^>]*>""",
        re.IGNORECASE,
    )
    while i < len(html):
        m = pattern.search(html, i)
        if not m:
            return None
        if m.group(1) == "/":
            depth -= 1
            if depth == 0:
                return m.end()
        else:
            depth += 1
        i = m.end()
    return None


def _block_text(block: str) -> str:
    """从一个 HTML 块里拿出纯文本用于关键词匹配。"""

    text = re.sub(r"<[^>]+>", " ", block)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_wechat_content(
    content: ExtractedContent,
    rules: dict[str, Any] | None = None,
) -> ExtractedContent:
    """对正文 HTML 进行噪声清洗。

    参数：
        content: 从 extractor 得到的 ExtractedContent
        rules:   可选，形如：
                 {
                   "noise_keywords": ["阅读原文", ...],  # 自定义噪声关键词
                   "remove_empty_paragraphs": True,
                   "remove_style_attrs": True,
                   "extra_keywords": ["其他自定义关键词"],
                 }

    返回：
        清洗后的 ExtractedContent（新对象）
    """

    if not content.html:
        return content

    rules = rules or {}
    noise_keywords = list(rules.get("noise_keywords") or _DEFAULT_NOISE_KEYWORDS)
    if rules.get("extra_keywords"):
        noise_keywords.extend(list(rules.get("extra_keywords")))  # type: ignore[arg-type]

    remove_empty = rules.get("remove_empty_paragraphs", True)
    remove_style = rules.get("remove_style_attrs", True)

    # 先分段，再逐段判断是否要丢弃
    segments = _html_segments(content.html)
    kept: list[str] = []
    for seg in segments:
        text = _block_text(seg)
        if not text:
            if remove_empty:
                continue
            kept.append(seg)
            continue

        # 关键词命中 => 丢弃该段
        hit = any(kw and kw in text for kw in noise_keywords)
        if hit:
            continue

        # 全是 "点击" / "展开" 之类的小按钮段也去掉
        short_noise_keywords = ["点击", "展开", "收起", "关注", "点赞", "在看"]
        if len(text) <= 12 and any(k in text for k in short_noise_keywords):
            continue

        kept.append(seg)

    cleaned_html = "\n".join(kept)

    # 去掉 style 属性（可选，默认 True）
    if remove_style:
        cleaned_html = re.sub(
            r"""\s+style\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+)""",
            "",
            cleaned_html,
            flags=re.IGNORECASE,
        )

    # 折叠多余空行
    cleaned_html = re.sub(r"\n\s*\n+", "\n", cleaned_html).strip()

    # 纯文本重新生成
    text = re.sub(r"<[^>]+>", " ", cleaned_html)
    text = re.sub(r"\s+", " ", text).strip()

    # 图片 URL 重新从清洗后的 HTML 里提取一次
    # 使用 extractor.py 公开导出的 extract_image_urls_from_html，保持模块边界干净
    from .extractor import extract_image_urls_from_html
    image_urls = extract_image_urls_from_html(cleaned_html, "")

    return ExtractedContent(
        title=content.title,
        author=content.author,
        publish_time=content.publish_time,
        digest=content.digest,
        html=cleaned_html,
        text=text,
        image_urls=image_urls,
        cover_url=content.cover_url,
    )
