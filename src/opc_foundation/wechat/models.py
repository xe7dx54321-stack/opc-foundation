"""微信公众号归档的数据模型。

功能说明（小白解读）：
    本文件定义了本模块用到的几个核心数据结构：
    - WeChatAccountConfig: 描述一个公众号来源（名字、feed url、是否启用等）
    - WeChatDefaults: 全局默认参数（超时、文章数上限、是否下载图片等）
    - WeChatArchiveConfig: 一个完整的运行配置（包含 archive_root + defaults + accounts）
    - ArticleCandidate: 从 feed / 手工 URL 解析得到的"待归档文章"
    - ArchivedArticle: 完成本地归档后的文章记录（成功/失败/部分成功/重复都会写一条）
    - FailedArticle: 失败的文章，进入 failed queue，后续可重试
    - WeChatArchiveRunResult: 一次完整运行的汇总结果，用于生成日报

这些模型都用 pydantic BaseModel 实现，天然支持 JSON 序列化、字段校验、
与 YAML 字段映射，便于读写与测试。
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 账号与总配置
# ---------------------------------------------------------------------------


class WeChatAccountConfig(BaseModel):
    """一个公众号 / feed 来源的描述。

    字段说明：
        account_name: 易读的公众号名字（用于目录命名 & 日报展示）
        account_id:   可选的稳定 ID（可以和业务系统关联）
        feed_url:     feed 地址（RSS/Atom 或 werss 服务）
        source_type:  来源类型（rss / werss / manual）
        enabled:      是否启用（False 的账号会被跳过）
        tags:         标签列表（便于下游项目做分组 / 过滤）
        clean_rules:  该账号特有的清洗规则（可留空，使用默认）
        max_articles: 单次运行最多处理该账号多少篇文章（覆盖 defaults）
    """

    account_name: str
    account_id: str | None = None
    feed_url: str | None = None
    source_type: str = "rss"
    enabled: bool = True
    tags: list[str] = Field(default_factory=list)
    clean_rules: dict[str, Any] = Field(default_factory=dict)
    max_articles: int | None = None


class WeChatDefaults(BaseModel):
    """运行默认参数。

    字段说明：
        fetch_timeout_seconds: 抓取单篇文章正文的超时秒数
        max_articles_per_account: 每个账号一次最多归档多少篇
        download_images: 是否下载正文内联图片到本地
        save_html: 是否保存原始 HTML 文件
        save_markdown: 是否保存 Markdown 文件
        user_agent: HTTP 请求时使用的 User-Agent
        manual_urls_file: 可选的手工 URL 文本文件路径
    """

    fetch_timeout_seconds: int = 20
    max_articles_per_account: int = 20
    download_images: bool = True
    save_html: bool = True
    save_markdown: bool = True
    user_agent: str = "Mozilla/5.0 (compatible; opc-foundation-wechat/1.0)"
    manual_urls_file: str | None = None


class WeChatArchiveConfig(BaseModel):
    """一次运行的完整配置。

    字段说明：
        archive_root: 归档根目录（下面会生成 articles/index/state/reports 等子目录）
        defaults:     默认参数
        accounts:     要监控的账号列表
        raw:          原始配置 dict（方便在下游项目中读取额外字段）
    """

    archive_root: str
    defaults: WeChatDefaults = Field(default_factory=WeChatDefaults)
    accounts: list[WeChatAccountConfig] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# 文章模型
# ---------------------------------------------------------------------------


class ArticleCandidate(BaseModel):
    """待归档文章的候选信息。

    可能来自：
    - feed 解析（RSS/Atom）
    - 手工 URL 投喂

    字段说明：
        source:         来源描述（例如 'rss:xxx' 或 'manual'）
        account_name:   所属公众号（若有）
        account_id:     账号 ID（若有）
        title:          文章标题
        url:            文章原始 URL
        canonical_url:  规范化后的 URL（用于去重 key）
        published_at:   发布时间字符串（若能解析到）
        author:         作者（若能解析到）
        digest:         摘要（来自 feed summary/description）
        cover_url:      封面图 URL（若能解析到）
        raw_entry:      原始 entry（便于调试 / 二次处理）
    """

    source: str
    account_name: str | None = None
    account_id: str | None = None
    title: str
    url: str
    canonical_url: str
    published_at: str | None = None
    author: str | None = None
    digest: str | None = None
    cover_url: str | None = None
    raw_entry: dict[str, Any] = Field(default_factory=dict)


class ExtractedContent(BaseModel):
    """正文提取结果（在内部各阶段传递使用）。

    字段说明：
        title:       解析到的标题（可用于覆盖 feed 标题）
        author:      解析到的作者
        publish_time:文章内声明的发布时间
        digest:      摘要
        html:        正文 HTML（可能经过清洗）
        text:        纯文本（用于 content hash / 部分成功检测）
        image_urls:  正文中出现的图片 URL（去重后顺序列表）
        cover_url:   封面图 URL
    """

    title: str | None = None
    author: str | None = None
    publish_time: str | None = None
    digest: str | None = None
    html: str = ""
    text: str = ""
    image_urls: list[str] = Field(default_factory=list)
    cover_url: str | None = None


class ArchivedArticle(BaseModel):
    """完成本地归档后的文章记录。

    每篇文章都会写一条，无论成功/失败/重复。
    status 取值：
        'saved'      - 成功保存正文、元数据
        'partial'    - 正文提取失败，但仍保存了原始 HTML
        'duplicate'  - 已在之前运行中被保存
        'failed'     - 抓取或写入过程中出错（会进入 failed queue）

    字段说明：
        article_id:    内部稳定 ID（基于 canonical_url hash 生成）
        source:        来源描述
        account_name:  公众号名字
        account_id:    账号 ID
        title:         标题
        url:           原始 URL
        canonical_url: 规范化 URL
        published_at:  发布时间
        captured_at:   本次运行抓取时间
        author:        作者
        digest:        摘要
        content_hash:  正文内容 hash（用于内容级去重）
        status:        状态（saved / partial / duplicate / failed）
        archive_dir:   该文章的归档目录（相对/绝对路径都允许）
        metadata_path: metadata.json 的路径
        markdown_path: article.md 的路径（若 save_markdown=True）
        html_path:     article.html 的路径（若 save_html=True）
        cover_image_path: 封面图本地路径（若下载成功）
        image_count:   下载成功的正文内联图片数量
        error:         错误信息（仅当 failed/partial 时非空）
    """

    article_id: str
    source: str
    account_name: str | None = None
    account_id: str | None = None
    title: str
    url: str
    canonical_url: str
    published_at: str | None = None
    captured_at: str
    author: str | None = None
    digest: str | None = None
    content_hash: str = ""
    status: str = "saved"
    archive_dir: str
    metadata_path: str
    markdown_path: str | None = None
    html_path: str | None = None
    cover_image_path: str | None = None
    image_count: int = 0
    error: str | None = None


class FailedArticle(BaseModel):
    """失败队列条目。

    记录足够多的信息，便于 retry-failed 命令重跑。
    """

    article_id: str
    title: str
    url: str
    canonical_url: str
    source: str
    account_name: str | None = None
    account_id: str | None = None
    published_at: str | None = None
    author: str | None = None
    error: str | None = None
    failed_at: str
    retry_count: int = 0
    raw_entry: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# 运行结果汇总
# ---------------------------------------------------------------------------


class AccountRunStats(BaseModel):
    """单个账号在本次运行中的统计。"""

    account_name: str
    candidates: int = 0
    new_articles: int = 0
    saved: int = 0
    partial: int = 0
    failed: int = 0
    duplicate: int = 0
    last_success_at: str | None = None


class WeChatArchiveRunResult(BaseModel):
    """一次完整运行的汇总结果，用于 CLI 输出和日报生成。"""

    run_id: str
    started_at: str
    ended_at: str
    total_accounts: int = 0
    total_candidates: int = 0
    total_new_articles: int = 0
    total_saved: int = 0
    total_partial: int = 0
    total_failed: int = 0
    total_duplicate: int = 0
    archive_root: str
    reports: list[str] = Field(default_factory=list)
    accounts: list[AccountRunStats] = Field(default_factory=list)
    saved_articles: list[ArchivedArticle] = Field(default_factory=list)
    failed_articles: list[FailedArticle] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
