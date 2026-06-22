"""微信文章归档消费契约的数据模型。

功能说明（小白解读）：
    本文件定义"归档消费契约"用到的两个核心数据结构：
    - ArticleRef: 一篇已归档文章的"只读视图"，给下游业务系统读取用
    - ConsumerReceipt: 某个业务线对某篇文章的消费回执（consumed / skipped / failed）

为什么需要这两个结构？
    opc-foundation 只负责"把文章作为标准资产采集、归档、去重、标准化输出"。
    下游业务线（content_agent / demand_radar / investment_agent 等）需要：
    1. 一个稳定的、不依赖内部实现的文章视图 → ArticleRef
    2. 一个属于自己（per-consumer）的消费状态记录 → ConsumerReceipt

重要原则：
    - foundation 不做业务判断（不评估文章价值、不决定是否进入业务流程）
    - 不做全局 consumed（同一篇文章可被多个 consumer 分别消费）
    - ArticleRef 是只读的（frozen=True）
    - ConsumerReceipt 中 decision / metadata 字段对 foundation 是 opaque（不解释）
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# ArticleRef：归档文章的只读视图
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ArticleRef:
    """一篇已归档文章的只读视图，供下游业务系统读取。

    字段说明：
        article_id:    文章唯一 ID（基于 canonical_url 的 sha256 前缀）
        source:        来源描述（例如 'rss:xxx' 或 'manual'）
        account_name:  所属公众号名字（可能为 None）
        account_id:    公众号 ID（可能为 None）
        title:         文章标题
        url:           原始 URL
        canonical_url: 规范化 URL（去重 key）
        published_at:  发布时间字符串（ISO 格式，可能为 None）
        captured_at:   归档抓取时间字符串（ISO 格式）
        status:        归档状态（saved / partial / duplicate / failed）
        content_hash:  正文内容 hash（用于检测内容变化）
        archive_dir:   该文章的归档目录路径
        metadata_path: metadata.json 的路径
        markdown_path: article.md 的路径（可能为 None）
        html_path:     article.html 的路径（可能为 None）
        tags:          标签列表（来自归档时的 account 配置，可能为空）
        raw_metadata:  完整原始 metadata dict（包含 articles.jsonl 全部字段）

    设计要点：
        - frozen=True：实例不可变，避免下游误改
        - raw_metadata 保留原始 JSON 全部字段，便于下游读取扩展信息
        - 路径字段保留原始字符串形式，下游可自行 Path() 解析
    """

    article_id: str
    source: str
    account_name: str | None
    account_id: str | None
    title: str
    url: str
    canonical_url: str
    published_at: str | None
    captured_at: str
    status: str
    content_hash: str
    archive_dir: str
    metadata_path: str
    markdown_path: str | None
    html_path: str | None
    tags: list[str] = field(default_factory=list)
    raw_metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# ConsumerReceipt：业务消费回执
# ---------------------------------------------------------------------------


# foundation 只识别这三种通用状态
# 业务线自己的判断（如 selected_for_topic / investment_signal_high）放在 decision 字段
RECEIPT_STATUS_CONSUMED = "consumed"
RECEIPT_STATUS_SKIPPED = "skipped"
RECEIPT_STATUS_FAILED = "failed"
VALID_RECEIPT_STATUSES = frozenset(
    {RECEIPT_STATUS_CONSUMED, RECEIPT_STATUS_SKIPPED, RECEIPT_STATUS_FAILED}
)


@dataclass(frozen=True)
class ConsumerReceipt:
    """某个业务线对某篇文章的消费回执。

    字段说明：
        consumer:      业务消费者名称（例如 content_agent / demand_radar）
        article_id:    文章唯一 ID
        canonical_url: 规范化 URL（辅助追踪，可能为 None）
        content_hash:  正文 hash（辅助检测内容变化，可能为 None）
        status:        通用状态（consumed / skipped / failed）
                       foundation 只识别这三种，不做业务解释
        received_at:   回执写入时间（ISO 格式字符串）
        reason:        可读原因（例如 "processed by downstream"）
        decision:      下游业务线自己的业务判断（opaque，foundation 不解释）
                       例如 "selected_for_topic" / "investment_signal_high"
        metadata:      业务线可写入的其他信息（opaque，foundation 只保存不解释）

    设计要点：
        - frozen=True：实例不可变
        - 同一 consumer 对同一 article_id 可有多条 receipt（append-only）
          读取时取最后一条作为当前状态
        - decision / metadata 对 foundation 是 opaque（不解释、不校验内容）
    """

    consumer: str
    article_id: str
    canonical_url: str | None
    content_hash: str | None
    status: str
    received_at: str
    reason: str | None = None
    decision: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
