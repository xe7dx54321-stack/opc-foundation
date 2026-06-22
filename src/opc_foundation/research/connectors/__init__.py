"""Research Source Foundation 的连接器子包。

功能说明（小白解读）：
    每种 source_type 对应一个 connector，负责从外部信息源"发现"候选文档。
    所有 connector 实现统一接口 BaseResearchConnector.discover()。

Phase 1 已实现：
    - RSSConnector          处理 rss_feed
    - WeChatArchiveConnector 处理 wechat_archive
    - ManualURLConnector    处理 manual_url

Phase 2A 已实现：
    - OfficialPublicResearchConnector 处理 official_public_research

Phase 2B 已实现：
    - PodcastTranscriptConnector 处理 podcast_transcript
"""
from __future__ import annotations

from .base import BaseResearchConnector, get_connector
from .manual_url import ManualURLConnector
from .official_public import OfficialPublicResearchConnector
from .podcast_transcript import PodcastTranscriptConnector
from .rss import RSSConnector
from .wechat_archive import WeChatArchiveConnector

__all__ = [
    "BaseResearchConnector",
    "get_connector",
    "RSSConnector",
    "WeChatArchiveConnector",
    "ManualURLConnector",
    "OfficialPublicResearchConnector",
    "PodcastTranscriptConnector",
]
