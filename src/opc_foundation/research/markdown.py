"""Markdown 生成层 —— 把候选文档 + 抽取结果组装成 Markdown 文件。

功能说明（小白解读）：
    归档时除了保存原始 HTML，还要生成一份 Markdown 给人看/给下游用。
    本模块负责拼出统一格式的 Markdown 字符串，再由 storage 层写入文件。

    格式：
        # 标题

        - 来源：xxx
        - Source ID：xxx
        - Source Type：xxx
        - 原文链接：xxx
        - 发布时间：xxx
        - 抓取时间：xxx
        - Legal Profile：xxx
        - Tags：xxx

        ---

        正文
"""
from __future__ import annotations

from typing import Any

from .models import DocumentCandidate, ExtractedResearchContent


def build_document_markdown(
    candidate: DocumentCandidate,
    extracted: ExtractedResearchContent,
    metadata: dict[str, Any] | None = None,
) -> str:
    """生成一篇文档的 Markdown 字符串。

    参数：
        candidate: 候选文档（含 source 信息、标题、URL 等）
        extracted: 抽取结果（含正文、作者、发布时间等）
        metadata:  额外元数据（如 captured_at、document_id），可选

    返回：
        Markdown 字符串
    """
    metadata = metadata or {}

    # 标题：优先用抽取到的，其次用 candidate 自带的
    title = (extracted.title or candidate.title or "（无标题）").strip()

    # 元数据字段
    source_name = candidate.source_name
    source_id = candidate.source_id
    source_type = candidate.source_type
    url = candidate.url
    canonical_url = candidate.canonical_url
    published_at = extracted.published_at or candidate.published_at or "未知"
    captured_at = metadata.get("captured_at", "未知")
    legal_profile = candidate.legal_profile
    tags = ", ".join(candidate.tags) if candidate.tags else ""
    author = extracted.author or candidate.author or ""
    language = extracted.language or candidate.language or ""
    extraction_quality = extracted.extraction_quality

    # 组装头部
    lines: list[str] = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"- 来源：{source_name}")
    lines.append(f"- Source ID：{source_id}")
    lines.append(f"- Source Type：{source_type}")
    lines.append(f"- 原文链接：{url}")
    if canonical_url and canonical_url != url:
        lines.append(f"- 规范化链接：{canonical_url}")
    lines.append(f"- 发布时间：{published_at}")
    lines.append(f"- 抓取时间：{captured_at}")
    lines.append(f"- Legal Profile：{legal_profile}")
    if tags:
        lines.append(f"- Tags：{tags}")
    if author:
        lines.append(f"- 作者：{author}")
    if language:
        lines.append(f"- 语言：{language}")
    if extraction_quality:
        lines.append(f"- 抽取质量：{extraction_quality}")
    if "document_id" in metadata:
        lines.append(f"- Document ID：{metadata['document_id']}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # 正文：优先用纯文本，没有就用 HTML
    body = (extracted.text or "").strip()
    if not body:
        # 退化到 HTML 文本
        body = _html_to_plain(extracted.html)
    if not body:
        body = "（正文抽取为空，请参考 raw.html 或 metadata.json）"

    lines.append(body)
    lines.append("")

    return "\n".join(lines)


def _html_to_plain(html: str) -> str:
    """简单把 HTML 转成纯文本（去标签）。

    作为正文抽取失败时的兜底，不做复杂处理。
    """
    if not html:
        return ""
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        # 去掉 script/style
        for tag in soup.find_all(["script", "style"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)
    except Exception:
        return html
