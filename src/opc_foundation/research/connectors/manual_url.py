"""Manual URL 连接器 —— 读取手工 URL 文件。

功能说明（小白解读）：
    用户可以把想归档的网页 URL 直接写到一个 txt 里，每行一条。
    本 connector 读取这些 URL，生成 DocumentCandidate。
    后续由 archiver/fetcher 抓取正文。

    文件格式：
        - 每行一个 URL
        - 以 # 开头的行是注释，跳过
        - 空行跳过
        - 重复 URL 去重
"""
from __future__ import annotations

from pathlib import Path

from ..canonicalize import canonicalize_research_url
from ..models import DocumentCandidate, ResearchArchiveConfig, ResearchSourceConfig
from .base import BaseResearchConnector


class ManualURLConnector(BaseResearchConnector):
    """手工 URL 连接器。

    处理 source_type = manual_url 的信息源。
    """

    connector_id = "manual_url"

    def discover(
        self,
        source: ResearchSourceConfig,
        config: ResearchArchiveConfig,
    ) -> list[DocumentCandidate]:
        """从手工 URL 文件读取候选。

        参数：
            source: 信息源配置（使用 source.manual_urls_path 或 source.url）
            config: 整体配置

        返回：
            DocumentCandidate 列表

        异常：
            文件不存在时抛出 ValueError
        """

        path_str = source.manual_urls_path or source.url
        if not path_str:
            raise ValueError(
                f"source [{source.source_id}] manual_url 缺少 manual_urls_path / url"
            )

        path = Path(path_str)
        if not path.is_absolute():
            path = Path(config.archive_root) / path

        if not path.exists():
            raise ValueError(
                f"source [{source.source_id}] manual URL 文件不存在: {path}"
            )

        urls = self._load_urls(path)
        max_items = source.max_items or config.defaults.max_items_per_source
        candidates: list[DocumentCandidate] = []

        for url in urls[:max_items]:
            canonical = canonicalize_research_url(url)
            candidates.append(
                DocumentCandidate(
                    source_id=source.source_id,
                    source_name=source.source_name,
                    source_type=source.source_type,
                    title=url,  # 标题先放 URL，正文抓取后会回填
                    url=url,
                    canonical_url=canonical,
                    legal_profile=source.legal_profile,
                    tags=list(source.tags),
                    raw_entry={"original_url": url},
                )
            )

        return candidates

    def _load_urls(self, path: Path) -> list[str]:
        """读取 URL 文件，返回去重后的 URL 列表。

        参数：
            path: 文件路径

        返回：
            URL 列表（按文件顺序，去重）
        """

        urls: list[str] = []
        seen: set[str] = set()
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if line in seen:
                    continue
                seen.add(line)
                urls.append(line)
        return urls
