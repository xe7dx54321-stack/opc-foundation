"""WeChat Archive 连接器 —— 复用已有微信公众号归档结果。

功能说明（小白解读）：
    这个 connector 不重新抓微信，而是读取 opc_foundation.wechat 模块
    已经归档好的 index/articles.jsonl，把每条 ArchivedArticle 转换成
    DocumentCandidate。

    这样可以避免重复抓取，下游系统能统一从 research_archive 消费。

数据流：
    wechat_archive（由 opc_foundation.wechat 模块产生）
      ↓
    WeChatArchiveConnector（读取 index/articles.jsonl）
      ↓
    research_archive（转换为 NormalizedDocument）
      ↓
    downstream systems
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..canonicalize import canonicalize_research_url
from ..models import DocumentCandidate, ResearchArchiveConfig, ResearchSourceConfig
from .base import BaseResearchConnector


class WeChatArchiveConnector(BaseResearchConnector):
    """读取已有 wechat archive 索引的连接器。

    处理 source_type = wechat_archive 的信息源。
    """

    connector_id = "wechat_archive"

    def discover(
        self,
        source: ResearchSourceConfig,
        config: ResearchArchiveConfig,
    ) -> list[DocumentCandidate]:
        """从 wechat archive 索引读取候选文档。

        参数：
            source: 信息源配置（source.url 指向本地 articles.jsonl）
            config: 整体配置

        返回：
            DocumentCandidate 列表

        异常：
            文件不存在或格式错误时抛出 ValueError
        """

        if not source.url:
            raise ValueError(f"source [{source.source_id}] wechat_archive 缺少 url")

        # 解析本地 jsonl 路径（支持相对路径，相对于 archive_root）
        jsonl_path = self._resolve_jsonl_path(source.url, config)
        if not jsonl_path.exists():
            raise ValueError(
                f"source [{source.source_id}] wechat archive 索引不存在: {jsonl_path}"
            )

        max_items = source.max_items or config.defaults.max_items_per_source
        candidates: list[DocumentCandidate] = []
        count = 0

        with open(jsonl_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if count >= max_items:
                    break

                cand = self._article_to_candidate(data, source, jsonl_path)
                if cand is not None:
                    candidates.append(cand)
                    count += 1

        return candidates

    def _resolve_jsonl_path(self, url: str, config: ResearchArchiveConfig) -> Path:
        """解析 wechat archive jsonl 的本地路径。

        参数：
            url:    source.url（可能是相对路径或绝对路径）
            config: 整体配置

        返回：
            Path 对象
        """

        p = Path(url)
        if p.is_absolute():
            return p
        # 相对路径相对于 archive_root 解析（但 wechat archive 通常在另一个目录）
        # 如果相对路径以 ./data/ 开头，相对于当前工作目录
        if url.startswith("./data/") or url.startswith("../"):
            return Path(url)
        # 否则相对于 archive_root
        return Path(config.archive_root) / url

    def _article_to_candidate(
        self,
        data: dict[str, Any],
        source: ResearchSourceConfig,
        jsonl_path: Path,
    ) -> DocumentCandidate | None:
        """把一条 wechat ArchivedArticle 记录转成 DocumentCandidate。

        参数：
            data:       articles.jsonl 中的一行 JSON
            source:     信息源配置
            jsonl_path: 索引文件路径（用于计算原始归档目录的相对路径）

        返回：
            DocumentCandidate；跳过无效记录返回 None
        """

        url = data.get("url") or ""
        title = data.get("title") or url or "untitled"
        if not url:
            return None

        canonical = canonicalize_research_url(url)

        # 保留原始归档路径，后续 storage 可以直接引用而不重复保存正文
        archive_dir = data.get("archive_dir") or ""
        markdown_path = data.get("markdown_path") or ""
        html_path = data.get("html_path") or ""

        raw_entry: dict[str, Any] = {
            "wechat_archive_dir": archive_dir,
            "wechat_markdown_path": markdown_path,
            "wechat_html_path": html_path,
            "wechat_article_id": data.get("article_id"),
            "wechat_account_name": data.get("account_name"),
            "wechat_account_id": data.get("account_id"),
            "wechat_content_hash": data.get("content_hash"),
            "wechat_status": data.get("status"),
            "source_jsonl": str(jsonl_path),
        }

        return DocumentCandidate(
            source_id=source.source_id,
            source_name=source.source_name,
            source_type=source.source_type,
            title=title,
            url=url,
            canonical_url=canonical,
            published_at=data.get("published_at"),
            author=data.get("author"),
            summary=data.get("digest"),
            legal_profile=source.legal_profile,
            tags=list(source.tags),
            raw_entry=raw_entry,
        )
