"""Connector 基类与注册机制。

功能说明（小白解读）：
    定义所有 connector 的统一接口：discover()。
    discover() 接收一个 source 配置，返回候选文档列表。
    失败时返回空列表并抛出异常由上层捕获，不影响其他 source。
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import DocumentCandidate, ResearchArchiveConfig, ResearchSourceConfig


class BaseResearchConnector(ABC):
    """所有 research connector 的基类。

    子类必须实现 discover() 方法。
    """

    connector_id: str = "base"

    @abstractmethod
    def discover(
        self,
        source: ResearchSourceConfig,
        config: ResearchArchiveConfig,
    ) -> list[DocumentCandidate]:
        """从外部信息源发现候选文档。

        参数：
            source:  信息源配置
            config:  整体配置（含 defaults）

        返回：
            候选文档列表；失败时返回空列表或抛出异常由上层捕获
        """
        ...


def get_connector(source_type: str) -> BaseResearchConnector | None:
    """根据 source_type 返回对应的 connector 实例。

    参数：
        source_type: 信息源类型

    返回：
        connector 实例；未实现的类型返回 None（上层会标记 skipped）
    """

    # 延迟导入避免循环依赖
    if source_type == "rss_feed":
        from .rss import RSSConnector
        return RSSConnector()
    if source_type == "wechat_archive":
        from .wechat_archive import WeChatArchiveConnector
        return WeChatArchiveConnector()
    if source_type == "manual_url":
        from .manual_url import ManualURLConnector
        return ManualURLConnector()
    if source_type == "official_public_research":
        from .official_public import OfficialPublicResearchConnector
        return OfficialPublicResearchConnector()
    if source_type == "podcast_transcript":
        from .podcast_transcript import PodcastTranscriptConnector
        return PodcastTranscriptConnector()
    if source_type == "conference_transcript":
        from .conference_transcript import ConferenceTranscriptConnector
        return ConferenceTranscriptConnector()
    if source_type == "analyst_action":
        from .analyst_action import AnalystActionConnector
        return AnalystActionConnector()
    if source_type == "media_mention":
        from .media_mention import MediaMentionConnector
        return MediaMentionConnector()
    return None
