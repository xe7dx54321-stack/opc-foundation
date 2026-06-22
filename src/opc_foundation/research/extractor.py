"""HTML 正文抽取层 —— 从原始 HTML 提取标题、作者、正文、语言等。

功能说明（小白解读）：
    网页 HTML 里有很多导航栏、广告、侧边栏，我们只想要"正文"。
    本模块用 trafilatura（一个开源的正文抽取库）做主要抽取，
    再用 BeautifulSoup 做一些补充字段（标题、作者、发布时间）。

    Phase 1 不做复杂站点定制，能从普通文章页提取到标题和正文即可。
    正文过短时标记 low/empty，下游可据此判断质量。

合规边界：
    - 不调用任何 LLM
    - 不做站点定制绕过 paywall
    - 只处理已经抓取下来的 HTML 字符串
"""
from __future__ import annotations

from typing import Any

from bs4 import BeautifulSoup

from .models import ExtractedResearchContent


# 正文长度阈值（字符数），用于判定抽取质量
_HIGH_MIN_CHARS = 400
_MEDIUM_MIN_CHARS = 120
_LOW_MIN_CHARS = 30


def extract_html_document(html: str, url: str) -> ExtractedResearchContent:
    """从一段 HTML 抽取研究文档正文。

    参数：
        html: 原始 HTML 字符串
        url:  来源 URL（仅用于异常日志，不发起请求）

    返回：
        ExtractedResearchContent 对象，永不抛异常。
        失败时返回空正文 + extraction_quality="empty"。
    """
    if not html or not html.strip():
        return ExtractedResearchContent(
            html="", text="", extraction_quality="empty",
        )

    # 1. 先用 trafilatura 抽取正文（最关键的一步）
    text, tra_meta = _extract_with_trafilatura(html, url)

    # 2. 用 BeautifulSoup 补充/兜底元数据
    soup_meta = _extract_meta_with_bs4(html)

    # 合并字段：trafilatura 优先，bs4 兜底
    title = (tra_meta.get("title") or soup_meta.get("title") or "").strip() or None
    author = (tra_meta.get("author") or soup_meta.get("author") or "").strip() or None
    published_at = (
        tra_meta.get("published_at") or soup_meta.get("published_at") or ""
    ).strip() or None
    summary = (tra_meta.get("summary") or "").strip() or None
    language = (tra_meta.get("language") or soup_meta.get("language") or "").strip() or None

    # 3. 正文 HTML：trafilatura 不直接返回 HTML，用 bs4 简单提取 <article> 或 <main>
    body_html = _extract_body_html(html)

    # 4. 根据正文长度判定抽取质量
    quality = _judge_quality(text)

    return ExtractedResearchContent(
        title=title,
        author=author,
        published_at=published_at,
        summary=summary,
        html=body_html,
        text=text,
        language=language,
        extraction_quality=quality,
    )


def _extract_with_trafilatura(html: str, url: str) -> tuple[str, dict[str, Any]]:
    """用 trafilatura 抽取正文与元数据。

    返回：
        (纯文本正文, 元数据 dict)
        失败时返回 ("", {})
    """
    try:
        import trafilatura
    except ImportError:
        return "", {}

    try:
        # extract：返回纯文本，include_comments=False 不要评论
        text = trafilatura.extract(
            html,
            include_comments=False,
            include_tables=True,
            favor_recall=True,
            url=url,
        ) or ""
        # extract_metadata：返回 Metadata 对象，含 title/author/date/summary/language
        meta_obj = trafilatura.extract_metadata(html, default_url=url)
        meta: dict[str, Any] = {}
        if meta_obj is not None:
            meta = {
                "title": getattr(meta_obj, "title", None) or None,
                "author": getattr(meta_obj, "author", None) or None,
                "published_at": getattr(meta_obj, "date", None) or None,
                "summary": getattr(meta_obj, "description", None) or None,
                "language": getattr(meta_obj, "language", None) or None,
            }
        return text, meta
    except Exception:
        # 任何抽取异常都不影响主流程
        return "", {}


def _extract_meta_with_bs4(html: str) -> dict[str, Any]:
    """用 BeautifulSoup 提取元数据作为兜底。

    主要看 <title>、<meta> 标签。
    """
    meta: dict[str, Any] = {}
    try:
        soup = BeautifulSoup(html, "html.parser")

        # 标题：优先 og:title，再 <title>
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            meta["title"] = og_title["content"].strip()
        elif soup.title and soup.title.string:
            meta["title"] = soup.title.string.strip()

        # 作者：author / article:author
        for prop in ("author", "article:author", "twitter:creator"):
            tag = soup.find("meta", attrs={"name": prop}) or soup.find(
                "meta", attrs={"property": prop}
            )
            if tag and tag.get("content"):
                meta["author"] = tag["content"].strip()
                break

        # 发布时间：article:published_time / date
        for prop in ("article:published_time", "date", "pubdate"):
            tag = soup.find("meta", attrs={"name": prop}) or soup.find(
                "meta", attrs={"property": prop}
            )
            if tag and tag.get("content"):
                meta["published_at"] = tag["content"].strip()
                break
        # <time datetime="...">
        time_tag = soup.find("time")
        if time_tag and time_tag.get("datetime") and "published_at" not in meta:
            meta["published_at"] = time_tag["datetime"].strip()

        # 语言：html lang= 或 og:locale
        html_tag = soup.find("html")
        if html_tag and html_tag.get("lang"):
            meta["language"] = html_tag["lang"].strip()
        else:
            og_locale = soup.find("meta", property="og:locale")
            if og_locale and og_locale.get("content"):
                meta["language"] = og_locale["content"].split("_")[0]
    except Exception:
        pass
    return meta


def _extract_body_html(html: str) -> str:
    """简单提取正文 HTML 片段。

    优先级（Phase 2B 增强：优先识别 transcript 容器）：
        0. class/id 含 transcript / episode-transcript 的容器
        1. class/id 含 article-body / content / body 的容器
        2. <article>
        3. <main>
        4. <body>
        5. 原 HTML
    """
    try:
        soup = BeautifulSoup(html, "html.parser")

        # Phase 2B：优先找 transcript 容器
        for keyword in ("transcript", "episode-transcript", "article-body", "content", "body"):
            # class 匹配
            for tag in soup.find_all(class_=True):
                classes = tag.get("class", [])
                if isinstance(classes, list):
                    classes_str = " ".join(classes).lower()
                else:
                    classes_str = str(classes).lower()
                if keyword in classes_str:
                    for t in tag.find_all(["script", "style", "nav", "footer", "aside"]):
                        t.decompose()
                    text = tag.get_text(strip=True)
                    if len(text) >= _LOW_MIN_CHARS:
                        return str(tag)
            # id 匹配
            for tag in soup.find_all(id=True):
                id_val = (tag.get("id") or "").lower()
                if keyword in id_val:
                    for t in tag.find_all(["script", "style", "nav", "footer", "aside"]):
                        t.decompose()
                    text = tag.get_text(strip=True)
                    if len(text) >= _LOW_MIN_CHARS:
                        return str(tag)

        # 退化到标准标签
        for selector in ("article", "main", "body"):
            node = soup.find(selector)
            if node:
                # 移除 script/style/nav/footer/aside
                for tag in node.find_all(["script", "style", "nav", "footer", "aside"]):
                    tag.decompose()
                text = node.get_text(strip=True)
                if len(text) >= _LOW_MIN_CHARS:
                    return str(node)
        return ""
    except Exception:
        return ""


def _judge_quality(text: str) -> str:
    """根据纯文本长度判定抽取质量。

    返回值：
        high:   >= 400 字符
        medium: >= 120 字符
        low:    >= 30 字符
        empty:  空或几乎空
        unknown: 理论上不会返回
    """
    if not text:
        return "empty"
    n = len(text.strip())
    if n >= _HIGH_MIN_CHARS:
        return "high"
    if n >= _MEDIUM_MIN_CHARS:
        return "medium"
    if n >= _LOW_MIN_CHARS:
        return "low"
    return "empty"
