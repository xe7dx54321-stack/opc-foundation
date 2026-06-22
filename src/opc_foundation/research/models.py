"""Research Source Foundation 的数据模型。

功能说明（小白解读）：
    本文件定义 Research Source Foundation 用到的核心数据结构：
    - ResearchDefaults         全局默认参数（超时、文章数上限、是否保存 html 等）
    - ResearchSourceConfig     一个信息源的配置
    - ResearchArchiveConfig    一次运行的完整配置
    - DocumentCandidate        Connector 输出的候选文档
    - ExtractedResearchContent HTML 正文抽取结果
    - NormalizedDocument       归档后的标准文档（最核心输出）
    - FailedDocument           失败队列记录
    - SourceHealth             源健康状态
    - ResearchRunResult        一次运行的汇总结果

所有模型用 pydantic BaseModel 实现，与现有 wechat 模块风格一致。
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 默认参数与配置
# ---------------------------------------------------------------------------


class ResearchDefaults(BaseModel):
    """运行默认参数。

    字段说明：
        fetch_timeout_seconds: 抓取单篇文档的超时秒数
        max_items_per_source:  每个 source 一次最多处理多少条候选
        save_html:             是否保存清洗后的 HTML
        save_markdown:         是否保存 Markdown
        save_raw:              是否保存原始 HTML
        download_assets:       是否下载图片/附件（Phase 1 默认 False）
        user_agent:            HTTP 请求使用的 User-Agent
    """

    fetch_timeout_seconds: int = 20
    max_items_per_source: int = 20
    save_html: bool = True
    save_markdown: bool = True
    save_raw: bool = True
    download_assets: bool = False
    user_agent: str = "Mozilla/5.0 (compatible; opc-foundation-research/0.1)"


class ResearchSourceConfig(BaseModel):
    """一个研究信息源的配置。

    字段说明：
        source_id:      稳定唯一 ID
        source_name:    人类可读名称
        source_type:    rss_feed / wechat_archive / manual_url（Phase 1）
        enabled:        是否启用
        url:            采集入口（wechat_archive 时指向本地 jsonl）
        feed_url:       RSS/Atom feed 地址
        base_url:       基础 URL（用于相对链接解析）
        manual_urls_path: 手工 URL 文件路径（manual_url 类型用）
        update_frequency: 更新频率（daily/weekday/weekly/hourly/manual）
        tags:           主题标签
        legal_profile:  合规档案（official_public/public_ir/licensed_media/rebroadcast/user_provided/unknown）
        fetch_profile:  抓取参数 profile 名
        extraction_profile: 正文抽取 profile 名
        priority:       重要性（high/medium/low/normal），不等于业务价值
        owner_project:  下游主要使用方，可为空
        notes:          备注
        max_items:      覆盖 defaults.max_items_per_source
    """

    source_id: str
    source_name: str
    source_type: str
    enabled: bool = True

    url: str | None = None
    feed_url: str | None = None
    base_url: str | None = None
    manual_urls_path: str | None = None

    update_frequency: str | None = None
    tags: list[str] = Field(default_factory=list)
    legal_profile: str = "unknown"
    fetch_profile: str = "default"
    extraction_profile: str = "default"
    priority: str = "normal"
    owner_project: str | None = None
    notes: str | None = None

    max_items: int | None = None


class ResearchArchiveConfig(BaseModel):
    """一次运行的完整配置。

    字段说明：
        archive_root: 归档根目录
        defaults:     默认参数
        sources:      信息源列表
        raw:          原始配置 dict（方便下游读取额外字段）
    """

    archive_root: str
    defaults: ResearchDefaults = Field(default_factory=ResearchDefaults)
    sources: list[ResearchSourceConfig] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# 候选与抽取结果
# ---------------------------------------------------------------------------


class DocumentCandidate(BaseModel):
    """Connector 输出的候选文档。

    可能来自 RSS feed、wechat archive 索引、手工 URL 文件等。

    字段说明：
        source_id:      所属 source
        source_name:    source 人类可读名
        source_type:    source 类型
        title:          标题
        url:            原始 URL
        canonical_url:  规范化 URL（去重 key）
        published_at:   发布时间（若能解析到）
        author:         作者
        summary:        摘要
        language:       语言
        legal_profile:  合规档案
        tags:           标签
        raw_entry:      原始条目（便于调试/二次处理）
    """

    source_id: str
    source_name: str
    source_type: str

    title: str
    url: str
    canonical_url: str

    published_at: str | None = None
    author: str | None = None
    summary: str | None = None
    language: str | None = None

    legal_profile: str = "unknown"
    tags: list[str] = Field(default_factory=list)

    raw_entry: dict[str, Any] = Field(default_factory=dict)


class ExtractedResearchContent(BaseModel):
    """HTML 正文抽取结果。

    字段说明：
        title:             解析到的标题
        author:            解析到的作者
        published_at:      解析到的发布时间
        summary:           摘要
        html:              正文 HTML
        text:              纯文本（用于 content hash / 质量评估）
        language:          语言
        extraction_quality: 提取质量（high/medium/low/empty/unknown）
    """

    title: str | None = None
    author: str | None = None
    published_at: str | None = None
    summary: str | None = None
    html: str = ""
    text: str = ""
    language: str | None = None
    extraction_quality: str = "unknown"


# ---------------------------------------------------------------------------
# 归档后的标准文档
# ---------------------------------------------------------------------------


class NormalizedDocument(BaseModel):
    """归档后的标准文档模型，是 Phase 1 最核心输出。

    每篇文档都会写一条到 documents.jsonl，无论 saved/partial/duplicate/failed。

    status 取值：
        saved      - 成功保存正文、元数据
        duplicate  - 已在之前运行中被保存
        partial    - 正文提取失败，但仍保存了原始 HTML
        failed     - 抓取或写入过程中出错（进入 failed queue）
        skipped    - 被跳过（如 disabled source）

    extraction_quality 取值：
        high    - 正文提取完整
        medium  - 正文提取基本完整，缺少部分字段
        low     - 正文提取不完整
        empty   - 正文提取为空
        unknown - 无法评估
    """

    document_id: str

    source_id: str
    source_name: str
    source_type: str

    title: str
    url: str
    canonical_url: str

    published_at: str | None = None
    captured_at: str
    updated_at: str | None = None

    author: str | None = None
    summary: str | None = None
    language: str | None = None

    content_type: str
    legal_profile: str
    tags: list[str] = Field(default_factory=list)

    content_hash: str
    status: str

    markdown_path: str | None = None
    html_path: str | None = None
    raw_path: str | None = None
    metadata_path: str

    attachments: list[dict[str, Any]] = Field(default_factory=list)
    extraction_quality: str | None = None
    error: str | None = None


class FailedDocument(BaseModel):
    """失败队列条目。

    记录足够多的信息，便于 retry-failed 命令重跑。
    """

    source_id: str
    source_name: str
    source_type: str
    title: str | None = None
    url: str
    canonical_url: str
    failed_at: str
    error: str
    retryable: bool = True
    retry_count: int = 0
    raw_entry: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# 源健康与运行结果
# ---------------------------------------------------------------------------


class SourceHealth(BaseModel):
    """源健康状态。

    status 取值：
        healthy   - 最近运行成功
        degraded  - 连续失败 1-2 次
        failed    - 连续失败 ≥3 次
        disabled  - 配置中 enabled=false
        unknown   - 尚未运行过
    """

    source_id: str
    source_name: str
    checked_at: str
    status: str

    last_success_at: str | None = None
    last_failure_at: str | None = None
    consecutive_failures: int = 0
    last_error: str | None = None

    candidate_count_last_run: int = 0
    saved_count_last_run: int = 0


class ResearchRunResult(BaseModel):
    """一次完整运行的汇总结果，用于 CLI 输出和日报生成。"""

    run_id: str
    mode: str
    archive_root: str
    started_at: str
    finished_at: str

    source_count: int = 0
    enabled_source_count: int = 0

    candidate_count: int = 0
    new_count: int = 0
    saved_count: int = 0
    partial_count: int = 0
    failed_count: int = 0
    duplicate_count: int = 0
    skipped_count: int = 0

    source_stats: list[dict[str, Any]] = Field(default_factory=list)
    saved_documents: list[NormalizedDocument] = Field(default_factory=list)
    failed_documents: list[FailedDocument] = Field(default_factory=list)
    source_health: list[SourceHealth] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    report_path: str | None = None
    exit_code: int = 0
