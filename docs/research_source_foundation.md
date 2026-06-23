# Research Source Foundation

> 中文名：全球研究信息源采集与归档底座
> 英文名：Research Source Foundation
> 所属项目：`opc-foundation`
> 规划模块路径：`src/opc_foundation/research/`
> 文档版本：v0.9（Phase 2H 已实现）

---

## 0. 实现状态

### Phase 1 MVP 已实现

```text
Phase 1 MVP implemented:
- rss_feed connector
- wechat_archive connector
- manual_url connector
- NormalizedDocument 标准文档模型
- documents.jsonl 下游主入口索引
- SQLite 去重（seen.sqlite）
- 本地归档（document.md / document.html / raw.html / metadata.json）
- run_log.jsonl / failed_queue.jsonl / source_health.jsonl
- 中文日报（daily_capture_YYYY-MM-DD.md）
- CLI：validate-config / dry-run / run / retry-failed / report / source-health
```

### Phase 2A 已实现

```text
Phase 2A implemented:
- official_public_research connector
- 支持 extraction_profile: generic_article_list / simple_card_list / link_list
- 两段式流程：list page → article detail page
- fixture-based tests
```

### Phase 2B 已实现

```text
Phase 2B implemented:
- podcast_transcript connector
- 支持 extraction_profile: podcast_episode_list / simple_episode_cards / podcast_feed / transcript_page
- 两种入口：HTML 页面 / RSS feed
- transcript 容器识别（extractor.py 增强）
- fixture-based tests
```

### Phase 2C 已实现

```text
Phase 2C implemented:
- conference_transcript connector
- 支持 extraction_profile: conference_event_list / event_cards / transcript_page / presentation_page / webcast_event_page
- 三种入口：event list page / single transcript page / presentation / webcast event page
- conference / transcript / presentation 容器识别（extractor.py 增强）
- presentation / PDF 链接只保存 metadata，不下载 PDF
- fixture-based tests
```

### Phase 2D 已实现

```text
Phase 2D implemented:
- analyst_action connector
- 支持 extraction_profile: analyst_action_table / analyst_action_cards / analyst_action_news_list / analyst_action_detail
- 三种入口：rating table / cards / news list / single detail page
- 事件字段：action_date / company / ticker / broker / analyst / action_type / rating_from / rating_to / price_target_from / price_target_to / currency
- analyst action 容器识别（extractor.py 增强）
- fixture-based tests
```

注意：

```text
analyst_action 只记录公开事件 metadata，不做投资建议，不判断利好利空。
price target / rating_to 只是事件字段，不是买入/卖出/持有建议。
```

### Phase 2E 已实现

```text
Phase 2E implemented:
- media_mention source_type
- media article list discovery
- media card discovery
- media news list discovery
- media detail page candidate generation
- mentioned institution / analyst / research / ticker metadata extraction
- fixture-based tests
```

注意：

```text
media_mention 只记录公开媒体报道与被提及对象 metadata，不做投资建议，不判断利好利空。
mentioned_tickers 只是媒体报道原文提及的 ticker metadata，不等同于 watchlist 映射。
mention_type 只是媒体引用类型，不是投资判断。
price_target_mention 只是表示媒体文章提到了目标价，不是投资建议。
```

Phase 2E 暂未实现（已在模型中预留）：

```text
- local_document
- PDF extraction
- LLM analysis
```

CLI run 时遇到未实现的 source_type 会标记 skipped/failed，不会崩溃。

### Phase 2F 已实现

```text
Phase 2F implemented:
- production source registry template
- source health hardening
- source-level run stats
- daily report hardening
- production run/check scripts
```

Phase 2F 重点：

```text
1. 新增 configs/research_sources.production.example.yaml 生产配置模板
2. SourceHealth 模型增强：source_type / last_error_type / new_count_last_run / partial_count_last_run / failed_count_last_run / duplicate_count_last_run / skipped_count_last_run / last_run_id / last_report_path
3. FailedDocument 模型增强：error_type / run_id
4. status 标准化：healthy / degraded / failed / disabled / unknown
5. error_type 标准化：config_error / connector_error / fetch_error / parse_error / extract_error / storage_error / empty_source / unsupported_source_type / unknown_error
6. run_summary 包含 source_stats（每个 source 的运行统计）
7. daily report 增强：Source 健康概览 / Partial/Failed 表格 / 下游消费入口
8. source-health CLI 增强：--status 过滤 / --format text|json
9. 新增 scripts/run_research_archive.ps1 和 scripts/check_research_archive.ps1
10. 新增 docs/research_source_production_run.md 生产运行指南
```

边界声明：

```text
Phase 2F 仍不接 th_capital_stock。
research module 只负责采集、标准化、归档，不做投研判断。
下游项目只消费 documents.jsonl / documents.latest.jsonl。
不提交 local config / data / secrets。
```

### Phase 2H 已实现

```text
Phase 2H implemented:
- Live Smoke Registry 文档
- Production Readiness Summary 文档
- 6 类非微信自动源真实公开源 live smoke 结果沉淀
- source_type 状态表
- source pattern 推荐/谨慎/不适合分类
- 生产试运行选源建议
- 系统边界固化
```

Phase 2H 重点：

```text
1. 新增 docs/research_source_live_smoke_registry.md
2. 新增 docs/research_source_production_readiness.md
3. 更新 docs/research_source_foundation.md 加入 Phase 2H 状态
4. 更新 docs/research_source_production_run.md 加入生产选源建议
5. 更新 configs/research_sources.production.example.yaml 补全 source_type 示例
6. 新增 tests/research/test_live_smoke_registry_docs.py
```

结论：

```text
非微信自动源主线已完成真实公开源 live smoke，达到 production trial ready。
```

已验证 source_type：

```text
- official_public_research
- podcast_transcript
- conference_transcript
- analyst_action
- media_mention
- rss_feed
```

可跳过：

```text
- manual_url，人工兜底入口，不属于自动源主线
```

待处理：

```text
- wechat_archive，后续单独处理
```

#### Source Type 状态表

| Source Type | Implementation Status | Live Smoke Status | Production Trial Status |
|---|---|---|---|
| official_public_research | implemented | completed | ready with caveats |
| podcast_transcript | implemented | completed | ready with caveats |
| conference_transcript | implemented | completed | ready with caveats |
| analyst_action | implemented | completed | ready with caveats |
| media_mention | implemented | completed | ready with caveats |
| rss_feed | implemented | completed | ready |
| manual_url | implemented | skipped by decision | optional fallback |
| wechat_archive | implemented | pending | separate track |

边界声明：

```text
Phase 2H 仍不接 th_capital_stock。
research module 只负责采集、标准化、归档，不做投研判断。
下游项目只消费 documents.jsonl / documents.latest.jsonl。
不提交 local config / data / secrets。
不做 JS 渲染、不绕过 paywall、不下载 PDF、不 OCR、不下载音频、不转写音频。
```

### Phase 1 模块结构

```text
src/opc_foundation/research/
  __init__.py
  models.py          # 8 个核心数据模型
  config.py          # 配置加载与校验
  canonicalize.py    # URL 规范化
  connectors/
    __init__.py
    base.py          # BaseResearchConnector
    rss.py           # RSSConnector
    wechat_archive.py # WeChatArchiveConnector
    manual_url.py    # ManualURLConnector
  fetcher.py         # HTTP 抓取层
  extractor.py       # HTML 正文抽取（trafilatura + BeautifulSoup）
  markdown.py        # Markdown 生成
  dedupe.py          # SQLite 去重 SeenStore
  storage.py         # 本地归档存储
  reports.py         # 中文日报生成
  archiver.py        # 主流程编排（dry_run / run / retry_failed）
  cli.py             # 6 个 CLI 命令
```

### Phase 1 使用方式

```bash
# 校验配置
python -m opc_foundation.research.cli validate-config \
  --config configs/research_sources.example.yaml

# 试运行（只发现候选，不抓正文）
python -m opc_foundation.research.cli dry-run \
  --config configs/research_sources.example.yaml

# 完整运行
python -m opc_foundation.research.cli run \
  --config configs/research_sources.example.yaml

# 重试失败队列
python -m opc_foundation.research.cli retry-failed \
  --archive-root ./data/research_archive

# 按日期生成日报
python -m opc_foundation.research.cli report \
  --archive-root ./data/research_archive \
  --date YYYY-MM-DD

# 查看 source 健康状态
python -m opc_foundation.research.cli source-health \
  --archive-root ./data/research_archive
```

Exit code：0 = 成功，1 = 配置错误，2 = 部分失败，3 = 严重错误。

---

## 1. 项目目标

`Research Source Foundation` 是 `opc-foundation` 的一个通用底层能力，用于为多个下游项目提供"研究型信息源"的采集、标准化、归档、去重、健康检查和索引输出能力。

本项目不是二级市场投研系统，也不是内容生产系统，也不是 Demand Radar。它只负责把外部研究信息稳定、合规、结构化地搬回本地，形成可被下游系统消费的标准文档资产。

### 下游系统

```text
1. th_capital_stock：二级市场投研 Agent
2. thcapital-content-department：内容生产 Agent
3. opc_Demand_Radar：需求雷达
4. 未来行业研究、一级市场项目研究、竞争情报系统
```

### Foundation 的角色

```text
信息源连接器
正文抽取器
本地归档器
去重器
运行日志记录器
source health 监控器
标准化索引生成器
```

它负责回答：

```text
从哪里抓？
怎么抓？
抓到了什么？
是否是新内容？
正文是否成功提取？
文件保存在哪里？
这次运行是否成功？
哪个源失败了？
这个源最近是否健康？
下游系统应该读取哪些新增文档？
```

### 核心原则

**Foundation 提供基础设施，项目保留判断力。**

---

## 2. 项目边界

### Foundation 负责

```text
1. Source Registry - 管理信息源配置
2. Connector Framework - RSS / Web / Podcast / Conference / Analyst / WeChat / Manual / Local
3. Fetch Layer - HTTP 请求、timeout/retry、user-agent、rate limit、error classification
4. Extraction Layer - HTML 正文提取、RSS item 解析、Podcast transcript 抽取、PDF 接口预留、Metadata 抽取
5. Normalization Layer - 统一文档模型、URL canonicalization、content_hash、source metadata 标准化
6. Storage Layer - markdown/html/raw/metadata 保存、JSONL index、SQLite seen store、failed queue、run log、source health
7. Report Layer - daily capture report、source health report、failure report
8. CLI - dry-run / run / retry-failed / report / source-health / validate-config
```

### Foundation 不负责

```text
1. 华尔街大行观点是否重要
2. 哪篇研报影响哪个股票
3. 哪个行业有投资机会
4. 预期差是否形成
5. 是否进入投研日报
6. 是否触发研究任务
7. 股票池 / watchlist / portfolio 逻辑
8. LLM 投研评分
9. 交易信号
10. 行业景气度判断
```

严禁在 `opc-foundation` 中实现：

```text
1. 股票买卖判断
2. 行业投资价值判断
3. 个股利好 / 利空判断
4. target price 判断
5. watchlist 映射
6. 预期差评分
7. 研报观点是否重要的业务判断
8. 是否进入投研日报的最终判断
9. 是否触发深度研究任务
10. 针对 th_capital_stock 的业务逻辑硬编码
```

这些应该放在下游业务系统中，例如 `th_capital_stock`。

---

## 3. 完整形态

本项目最终形态是：

```text
一个可配置、可扩展、可审计、可复用的研究信息源采集底座。
```

它可以每天自动采集多种研究型信息源，包括：

```text
1. 官方公开研究页面
2. RSS / Atom feed
3. Podcast transcript
4. 投行公开观点页面
5. 公司 IR conference transcript
6. 分析师评级变动页面
7. 新闻媒体对投行研报的二次引用
8. 微信公众号文章归档结果
9. 手工 URL 投喂
10. PDF / HTML / JSON / Markdown 文档
```

并统一输出为本地标准文档资产，下游系统不直接扫乱七八糟的网页和文件夹，而是读取 Foundation 生成的标准索引 `index/documents.jsonl`，然后按自己的业务规则做分析。

### 性能与规模目标

```text
1. 单次运行支持 50-200 个 source
2. 单 source 默认最多抓 20-50 条候选
3. 每日新增文档 100-1000 条以内可稳定处理
4. 所有文档本地归档
5. 去重必须稳定
6. source health 可追踪 30 天以上
```

---

## 4. 支持 source types

完整形态下，支持以下 9 类 source type：

| source_type | 说明 | 典型来源 |
|---|---|---|
| `official_public_research` | 官方公开研究页面 | Goldman Sachs / Morgan Stanley / J.P. Morgan / BofA / Citi / UBS / Barclays Insights |
| `rss_feed` | RSS / Atom feed | 官方博客、新闻源、研究机构公开 feed、Podcast feed、公司 IR feed |
| `podcast_transcript` | 播客文字稿 | Morgan Stanley Thoughts on the Market、BofA Global Research Unlocked、UBS Global Research Pod Hub、Goldman Sachs Exchanges |
| `conference_transcript` | 投行会议 / 公司 IR 活动纪要 | MS TMT / GS Communacopia / JPM Healthcare / UBS Global Tech / BofA Global Tech / Barclays Global Tech / DB Tech / Bernstein Strategic Decisions |
| `analyst_action` | 分析师评级 / 目标价 / 覆盖变化公开摘要 | MarketWatch / Investing.com / Benzinga / TipRanks / Yahoo Finance / The Fly / StreetInsider 公开页面 |
| `media_mention` | 媒体对投行观点的公开引用 | Reuters / MarketWatch / Yahoo Finance / Business Insider / CNBC / Investing.com news |
| `wechat_archive` | 微信公众号归档结果 | 消费 `data/wechat_archive/index/articles.jsonl`，不重新抓微信 |
| `manual_url` | 手工投喂 URL | 用户把单篇网页 / 报告 / 文章链接放入队列 |
| `local_document` | 本地已有文件 | 用户手工下载的 PDF / HTML / Markdown / TXT |

Foundation 只负责采集、抽取、归档，**不判断观点价值**。

---

## 5. 数据模型

> 模型用 pydantic BaseModel 实现（与现有 wechat 模块一致）。

### 5.1 ResearchSourceConfig（信息源配置）

```python
class ResearchSourceConfig:
    source_id: str           # 稳定唯一 ID
    source_name: str         # 人类可读名称
    source_type: str         # official_public_research / rss_feed / podcast_transcript / ...
    enabled: bool            # 是否启用
    url: str | None          # 采集入口
    feed_url: str | None     # RSS/Atom feed 地址（若适用）
    base_url: str | None     # 基础 URL（用于相对链接解析）
    update_frequency: str | None  # daily / weekday / weekly / hourly
    tags: list[str]          # 主题标签，如 wall_street_research、ai、macro
    legal_profile: str       # official_public / licensed_media / public_ir / rebroadcast / user_provided / unknown
    fetch_profile: str       # 默认抓取参数 profile 名
    extraction_profile: str  # 正文抽取 profile 名
    priority: str            # source 重要性（high / medium / low），不等于业务价值
    owner_project: str | None  # 下游主要使用方，可为空
    notes: str | None        # 备注
```

### 5.2 RawFetchResult（原始抓取结果）

```python
class RawFetchResult:
    fetch_id: str
    source_id: str
    url: str
    canonical_url: str
    status_code: int | None
    content_type: str | None
    fetched_at: str          # UTC ISO-8601
    raw_path: str | None     # 原始内容保存路径
    error: str | None
    retryable: bool
```

### 5.3 NormalizedDocument（核心标准文档模型）

```python
class NormalizedDocument:
    document_id: str
    source_id: str
    source_name: str
    source_type: str
    title: str
    url: str
    canonical_url: str
    published_at: str | None
    captured_at: str         # UTC ISO-8601
    updated_at: str | None
    author: str | None
    summary: str | None
    language: str | None
    content_type: str        # markdown / html / pdf / json / podcast / rss
    legal_profile: str
    tags: list[str]
    content_hash: str        # SHA-256
    status: str              # saved / duplicate / partial / failed / skipped
    markdown_path: str | None
    html_path: str | None
    raw_path: str | None
    metadata_path: str
    attachments: list[dict]
    extraction_quality: str | None  # high / medium / low / empty / unknown
    error: str | None
```

**status 取值：**

```text
saved      - 成功保存正文、元数据
duplicate  - 已在之前运行中被保存
partial    - 正文提取失败，但仍保存了原始 HTML
failed     - 抓取或写入过程中出错（进入 failed queue）
skipped    - 被跳过（如 disabled source）
```

**extraction_quality 取值：**

```text
high    - 正文提取完整，有标题、有发布时间、有正文
medium  - 正文提取基本完整，缺少部分字段
low     - 正文提取不完整，正文很短或噪声多
empty   - 正文提取为空
unknown - 无法评估（如 PDF 预留接口）
```

### 5.4 SourceHealth（源健康状态）

```python
class SourceHealth:
    source_id: str
    source_name: str
    checked_at: str
    status: str              # healthy / degraded / failed / disabled / unknown
    last_success_at: str | None
    last_failure_at: str | None
    consecutive_failures: int
    last_error: str | None
    candidate_count_last_run: int
    saved_count_last_run: int
```

**status 取值：**

```text
healthy   - 最近运行成功
degraded  - 连续失败 1-2 次
failed    - 连续失败 ≥3 次
disabled  - 配置中 enabled=false
unknown   - 尚未运行过
```

### 5.5 RunSummary（运行摘要）

```python
class RunSummary:
    run_id: str
    mode: str                # dry-run / run / retry-failed
    started_at: str
    finished_at: str
    source_count: int
    enabled_source_count: int
    candidate_count: int
    new_count: int
    saved_count: int
    partial_count: int
    failed_count: int
    duplicate_count: int
    skipped_count: int
    exit_code: int           # 0 / 1 / 2 / 3
    report_path: str | None
```

---

## 6. 目录结构

```text
data/research_archive/
  config/                              # 运行时配置快照（可选）
  documents/
    2026/
      06/
        2026-06-22__source_slug__title_slug/
          document.md
          document.html
          raw.html
          metadata.json
          attachments/
          images/
  index/
    documents.jsonl                    # 全量索引（追加写）—— 下游消费主入口
    documents.latest.jsonl             # 最近一次运行的索引（覆盖写）
  state/
    seen.sqlite                        # 去重数据库（canonical_url + content_hash）
    processing_state.sqlite            # 处理状态（可选，用于断点续跑）
    run_log.jsonl                      # 运行级 summary 日志
    failed_queue.jsonl                 # 失败队列
    source_health.jsonl                # 源健康状态
  reports/
    daily_capture_2026-06-22.md        # 中文日报
    source_health_2026-06-22.md        # 源健康报告
```

### 关键要求

```text
1. documents/ 保存人类可读和机器可读文档资产
2. index/documents.jsonl 是下游消费主入口
3. state/seen.sqlite 负责去重
4. state/run_log.jsonl 记录运行级 summary
5. state/failed_queue.jsonl 支持失败重试
6. state/source_health.jsonl 记录 source 健康状态
7. reports/ 输出中文日报
```

---

## 7. 配置结构

### 配置路径

```text
configs/research_sources.example.yaml    # 示例配置（公开 URL，不含敏感源）
configs/research_sources.local.yaml      # 本地实际配置（gitignore）
```

### 配置结构示例

```yaml
archive_root: "./data/research_archive"

defaults:
  fetch_timeout_seconds: 20
  max_items_per_source: 20
  save_html: true
  save_markdown: true
  save_raw: true
  download_assets: false
  user_agent: "Mozilla/5.0"

sources:
  - source_id: "goldman_sachs_reports"
    source_name: "Goldman Sachs Reports"
    source_type: "official_public_research"
    url: "https://www.goldmansachs.com/insights/reports"
    enabled: true
    legal_profile: "official_public"
    fetch_profile: "default_web"
    extraction_profile: "article_page"
    update_frequency: "daily"
    tags: ["wall_street_research", "official", "macro", "equity"]

  - source_id: "morgan_stanley_thoughts_on_market"
    source_name: "Morgan Stanley Thoughts on the Market"
    source_type: "podcast_transcript"
    url: "https://www.morganstanley.com/insights/podcasts/thoughts-on-the-market"
    enabled: true
    legal_profile: "official_public"
    fetch_profile: "default_web"
    extraction_profile: "podcast_transcript"
    update_frequency: "weekday"
    tags: ["wall_street_research", "official", "podcast", "transcript"]

  - source_id: "wechat_wall_street_research"
    source_name: "WeChat Wall Street Research Archive"
    source_type: "wechat_archive"
    url: "./data/wechat_archive/index/articles.jsonl"
    enabled: true
    legal_profile: "rebroadcast"
    fetch_profile: "local_index"
    extraction_profile: "metadata_passthrough"
    update_frequency: "daily"
    tags: ["wechat", "rebroadcast", "chinese"]
```

### 配置规则

```text
1. 该配置只是 source registry，不包含任何投研评分规则
2. source_id 必须全局唯一
3. legal_profile 必填，取值必须合法
4. url / feed_url / base_url 至少一个非空（wechat_archive 除外，它用 url 指向本地 jsonl）
5. fetch_profile / extraction_profile 引用 defaults 或自定义 profile
```

---

## 8. Connector 设计

### 8.1 RSSConnector

- **输入**：`feed_url`
- **输出**：`NormalizedDocument` 候选
- **能力**：RSS / Atom 解析、title/link/published/summary/author 提取、`max_items_per_source`、feedparser 兼容

### 8.2 WebPageConnector

- **输入**：`url`
- **能力**：抓取网页、发现文章列表、提取详情页链接、正文抽取

### 8.3 PodcastTranscriptConnector

- **输入**：`podcast page / feed`
- **能力**：发现最新 episode、抽取 transcript、保存 episode metadata
- **注意**：如果只有音频，不强制做语音转文字，优先处理公开 transcript

### 8.4 ConferenceTranscriptConnector

- **输入**：`公司 IR event 页面`
- **能力**：发现 webcast/transcript/presentation、保存 transcript 或 presentation metadata

### 8.5 AnalystActionConnector

- **输入**：`公开 analyst rating 页面`
- **能力**：抓取评级变化表、标准化为 document
- **注意**：如果最终认为 analyst action 更适合 event schema，可标记为 future extension

### 8.6 WeChatArchiveConnector

- **输入**：`wechat_archive/index/articles.jsonl`
- **能力**：读取已有微信公众号归档索引、转换为 NormalizedDocument、**不**重新抓微信

### 8.7 ManualURLConnector

- **输入**：`manual_urls.txt`（或 CSV）
- **能力**：逐条抓取 URL、正文抽取、保存归档

### 8.8 LocalDocumentConnector

- **输入**：`本地文件目录`
- **能力**：登记本地文档、hash、metadata、索引

---

## 9. CLI 设计

### 命令清单

```bash
# 校验配置
python -m opc_foundation.research.cli validate-config \
  --config configs/research_sources.example.yaml

# 试运行（只发现候选，不保存正文）
python -m opc_foundation.research.cli dry-run \
  --config configs/research_sources.local.yaml

# 完整运行
python -m opc_foundation.research.cli run \
  --config configs/research_sources.local.yaml

# 重试失败队列
python -m opc_foundation.research.cli retry-failed \
  --archive-root ./data/research_archive

# 按日期生成日报
python -m opc_foundation.research.cli report \
  --archive-root ./data/research_archive \
  --date YYYY-MM-DD

# 查看源健康状态
python -m opc_foundation.research.cli source-health \
  --archive-root ./data/research_archive
```

### 命令说明

| 命令 | 功能 |
|---|---|
| `validate-config` | 校验 YAML 语法、字段类型、source_id 唯一性、必填字段 |
| `dry-run` | 只发现候选，不保存正文，不写 seen store |
| `run` | 完整执行：fetch → extract → normalize → dedupe → archive → index → report → health update |
| `retry-failed` | 读取 failed_queue.jsonl，逐条重试 |
| `report` | 按日期读取 run log，生成中文日报 |
| `source-health` | 读取 source_health.jsonl，输出每个 source 健康状态 |

### dry-run 输出

```text
source_count
candidate_count
new_candidate_count
failed_source_count
warnings
```

### Exit Code 规范

```text
0 = success
1 = config error
2 = partial failure（部分 source / 文档失败，但整体完成）
3 = fatal runtime error（无法继续运行）
```

---

## 10. 下游消费契约

### 契约规则

```text
1. 下游系统只读取 index/documents.jsonl，不直接扫 documents/ 目录
2. 每一行是一个 NormalizedDocument 的 JSON 序列化
3. 下游系统根据自己的业务规则消费，Foundation 不记录哪个下游处理过哪篇文档
4. 下游系统应维护自己的处理状态（例如 th_capital_stock/data/research_ingest_state.sqlite）
5. documents.jsonl 支持增量消费（按 captured_at 或 document_id 排序）
```

### 下游可用的字段

```text
document_id
captured_at
published_at
content_hash
source_id
source_type
status
tags
markdown_path
metadata_path
```

### Foundation 输出示例

```json
{
  "document_id": "doc_xxx",
  "source_id": "morgan_stanley_thoughts_on_market",
  "source_type": "podcast_transcript",
  "title": "AI infrastructure spending remains strong",
  "url": "...",
  "published_at": "2026-06-22",
  "captured_at": "2026-06-22T08:00:00",
  "markdown_path": "documents/2026/06/...",
  "content_hash": "...",
  "tags": ["wall_street_research", "podcast", "ai"]
}
```

### Foundation 不应输出

```json
{
  "affected_tickers": ["NVDA", "AVGO"],
  "investment_rating": "high",
  "expectation_delta": "positive",
  "trade_signal": "buy"
}
```

这些字段属于业务系统。

---

## 11. 合规与来源可信度

本项目必须内置 source legal profile，但**不做法律结论**。

### legal_profile 取值

| legal_profile | 含义 | 示例 |
|---|---|---|
| `official_public` | 机构自己公开发布 | 投行官网公开文章、官方 podcast transcript、官方公开 reports 页面 |
| `public_ir` | 上市公司 IR 页面公开材料 | conference transcript、presentation、webcast replay page |
| `licensed_media` | 媒体公开报道 | Reuters、MarketWatch、Yahoo Finance、CNBC |
| `rebroadcast` | 二次转载或中文传播 | 微信公众号摘要、中文财经媒体转述 |
| `user_provided` | 用户手工提供 URL 或本地文件 | manual_url、local_document |
| `unknown` | 来源不明确 | 无法归类的源 |

### 合规要求（强制）

```text
1. 不要抓取需要登录的付费研报全文
2. 不要绕过 paywall
3. 不要保存 cookie/token
4. 不要伪装成机构客户
5. 不要抓取明显泄露的研报包
6. 对 rebroadcast/unknown 源做标记，供下游决定是否使用
```

---

## 12. 质量控制

Foundation 提供采集质量字段（非投研质量字段）。

### 质量维度

```text
fetch_status              # 抓取状态
extraction_quality        # 提取质量: high / medium / low / empty / unknown
content_length            # 正文长度
has_title                 # 是否有标题
has_published_at          # 是否有发布时间
has_canonical_url         # 是否有规范化 URL
has_markdown              # 是否有 markdown 正文
has_metadata              # 是否有 metadata.json
source_health             # 源健康状态
duplicate_status          # 去重状态
```

### 日报包含的统计

```text
1. 本日源数量
2. 成功源数量
3. 失败源数量
4. 新增文档数
5. partial 文档数
6. failed 文档数
7. duplicate 文档数
8. source health 异常
9. failed queue 摘要
```

---

## 13. 测试策略

### Unit Tests

```text
config loading
source registry validation
RSS parsing
URL canonicalization
dedupe
document model validation
storage write/read
JSONL append
failed queue
run summary
source health update
report generation
```

### Connector Tests（全部使用 fixture，不访问真实网络）

```text
sample RSS
sample official research HTML
sample podcast transcript page
sample conference transcript page
sample analyst rating table
sample wechat_archive index
sample manual URL fixture
```

### Integration Tests

```text
dry-run with fixture config
run with fixture HTTP client
retry-failed
report --date
source-health
duplicate run（同一 config 跑两次，第二次应全部 duplicate）
partial extraction
source failure isolation
```

### Non-goals for tests

```text
不访问真实 Goldman/Morgan/JPM 页面
不访问真实微信公众号
不访问真实付费源
不依赖外部网络
```

---

## 14. 失败降级策略

完整形态必须支持 fail-soft。

### 要求

```text
1. 单个 source 失败不影响整个批次
2. 单篇 document 失败不影响其他 document
3. 正文提取失败可以保存 raw/html 并标记 partial
4. 图片/附件下载失败不影响正文保存
5. failed_queue 支持 retry
6. source_health 记录连续失败
7. CLI exit code 区分成功、部分失败、严重失败
```

### Exit Code 规范

```text
0 = success
1 = config error
2 = partial failure
3 = fatal runtime error
```

### source_health 连续失败追踪

```text
consecutive_failures 递增
status 在 degraded（连续失败 1-2 次）和 failed（连续失败 ≥3 次）之间转换
```

---

## 15. 与 wechat archive 的关系

当前 `opc-foundation` 已有 `src/opc_foundation/wechat/` 模块，它是专门的微信公众号文章归档能力。

Research Source Foundation **不重写**它。

### 数据流

```text
wechat_archive（由 opc_foundation.wechat 模块产生）
  ↓
WeChatArchiveConnector（读取 index/articles.jsonl）
  ↓
research_archive（转换为 NormalizedDocument）
  ↓
downstream systems
```

### 复用方式

```text
wechat module:
  负责从 WeRSS / we-mp-rss / manual URL 归档微信公众号文章

research module:
  通过 WeChatArchiveConnector 读取 wechat archive 的 index/articles.jsonl
  把微信公众号文章转换为 NormalizedDocument
  输出到 research_archive/index/documents.jsonl
```

这样可以避免重复抓微信。

### 不修改 wechat 模块

实现 Research Source Foundation 时，**不**修改 `src/opc_foundation/wechat/` 下的任何文件，仅通过读取其输出索引来复用。

---

## 16. 与 th_capital_stock 的集成边界

### Foundation 输出

```json
{
  "document_id": "doc_xxx",
  "source_id": "morgan_stanley_thoughts_on_market",
  "source_type": "podcast_transcript",
  "title": "AI infrastructure spending remains strong",
  "url": "...",
  "published_at": "2026-06-22",
  "captured_at": "2026-06-22T08:00:00",
  "markdown_path": "documents/2026/06/...",
  "content_hash": "...",
  "tags": ["wall_street_research", "podcast", "ai"]
}
```

### th_capital_stock 负责

```text
读取新增 document
LLM triage
主题分类
watchlist 映射
行业变量映射
预期差判断
evidence packet
daily brief
research task trigger
```

### Foundation 不应输出

```json
{
  "affected_tickers": ["NVDA", "AVGO"],
  "investment_rating": "high",
  "expectation_delta": "positive",
  "trade_signal": "buy"
}
```

这些字段属于业务系统。

---

## 17. 非目标

```text
1. 不做投研判断（股票买卖、行业投资价值、target price、watchlist 映射、预期差评分）
2. 不做 LLM 投研评分
3. 不做交易信号
4. 不做行业景气度判断
5. 不做大规模分布式爬虫
6. 不做实时毫秒级更新
7. 不做搜索引擎级全文检索
8. 不做多用户权限系统
9. 不抓取需要登录的付费研报全文
10. 不绕过 paywall
11. 不保存 cookie/token
12. 不伪装成机构客户
13. 不抓取明显泄露的研报包
14. 不修改现有 wechat 模块
15. 不修改 th_capital_stock
16. 不引入新依赖（本阶段）
```

---

## 18. 未来开发阶段建议

> 此处仅作建议，本 SPEC 的重点是 whole picture，不局限于第一阶段。

### Phase 1：MVP 骨架

- 项目骨架：`src/opc_foundation/research/` 子包
- 数据模型：`ResearchSourceConfig` / `NormalizedDocument` / `RunSummary` / `SourceHealth`
- 配置加载与校验：`validate-config`
- Storage Layer：目录结构 + JSONL index + SQLite seen store
- 1-2 个 connector：`RSSConnector` + `WeChatArchiveConnector`（复用现有归档）
- CLI：`validate-config` + `dry-run` + `run`
- 日报：基础中文 Markdown
- 测试：fixture-based unit + integration

### Phase 2：扩展 connector

- `WebPageConnector`
- `ManualURLConnector`
- `LocalDocumentConnector`
- `PodcastTranscriptConnector`
- `failed_queue` + `retry-failed`
- `source_health` 追踪

### Phase 3：研究型源

- `ConferenceTranscriptConnector`
- `AnalystActionConnector`
- `official_public_research` 专用抽取 profile
- `media_mention` connector

### Phase 4：质量与运维

- `extraction_quality` 自动评估
- `report` 按日期生成
- `source-health` 报告
- 性能优化（50-200 source 稳定运行）
- PDF 抽取接口落地（如需引入依赖，单独评估）

### Phase 5：下游集成

- 与 `th_capital_stock` 的集成验证
- 与 `thcapital-content-department` 的集成验证
- 与 `opc_Demand_Radar` 的集成验证
- 下游消费契约文档化

---

## 附录：与 opc-foundation 现有能力的关系

### 复用

- 复用 `opc_foundation.wechat` 模块的归档产物（通过 `WeChatArchiveConnector` 读取）
- 复用 `opc_foundation.web` 模块的正文抽取能力（`TrafilaturaExtractor`）
- 复用 `opc_foundation.storage` 的 JSONL / CSV 读写能力
- 复用 `opc_foundation.run` 的 RunContext / RunLog / ArtifactManifest 能力
- 复用 `opc_foundation.signals` 的 SeenStore 去重思路

### 不修改

- 不修改 `opc_foundation.wechat` 模块
- 不修改 `th_capital_stock`
- 不修改 `opc_Demand_Radar`
- 不修改现有 `sources` / `sources_v2` 模块（research 是平行的能力底座，不强行合并）

### 不引入新依赖

本阶段不引入新依赖。如 Phase 4 的 PDF 抽取需要新依赖，单独评估。


---

## Cross-Repo Source Migration

`th_capital_stock` 仓库中存在部分可复用信息源能力，但迁移必须遵守 foundation 边界。

迁移路线图详见：

- docs/source_migration_from_th_capital_stock.md

当前决策：

| Family | Decision | Priority |
|---|---|---|
| official_filing | migrate first | P0 |
| document_extraction | migrate later | P1 |
| market_data | separate module later | P1 |
| market_flow | separate module later | P1/P2 |
| research/news harmonization | selective | P2 |
| procurement | partial, decouple first | P2 |
| ir_interaction | partial, decouple first | P2 |
| vendor/iFinD | client only | P3 |
| factor/valuation/opportunity/risk/signal | do not migrate | No |

Next recommended phase:

M1A: Official Filing Foundation SPEC

---

## 十二、Official Filing Foundation（M1 新增）

### 12.1 模块定位

Official Filing Foundation 是与 Research Source Foundation 并列的独立模块，专注于**官方披露/公告**的归档。

- **Research Source Foundation**：研究内容归档（研报、博客、公众号、播客等）
- **Official Filing Foundation**：官方披露归档（SEC EDGAR / CNINFO / HKEX 等）

两者都是 foundation 层基础设施，遵循相同的设计原则：

> Foundation 提供基础设施；业务系统保留判断力。

### 12.2 已实现 Source

| source_type | 名称 | 市场 | 状态 |
|-------------|------|------|------|
| `sec_edgar` | SEC EDGAR | US | ✅ MVP 已实现 |
| `cninfo_announcement` | CNINFO 巨潮资讯 | CN | ✅ MVP 已实现 |
| `hkex_announcement` | HKEXnews 港交所披露易 | HK | ✅ MVP 已实现 |

### 12.3 核心能力

- 官方披露发现（discover）
- 标准化元数据模型
- 本地归档存储（raw / metadata / index）
- canonical_key + content_hash 去重
- Source Health 监控
- Failed Queue 失败重试
- 中文日报
- CLI 命令行工具

### 12.4 文档入口

- **主文档**：[official_filing_foundation.md](./official_filing_foundation.md)
- **生产运行**：[official_filing_production_run.md](./official_filing_production_run.md)
- **示例配置**：`configs/official_filings.example.yaml`

### 12.5 与 Research Source 的关系

| 维度 | Research Source | Official Filing |
|------|-----------------|-----------------|
| 内容类型 | 研究文章、博客、播客等 | 官方监管披露、公司公告 |
| 权威性 | 各有不同 | 官方发布，权威性高 |
| 时效性 | 各有不同 | 法定披露，时效性强 |
| 结构化程度 | 半结构化/非结构化 | 相对结构化 |
| 典型用途 | 研究参考、观点汇总 | 事实核查、基本面分析 |

两个模块共享底层基础设施（JSONL 存储、pydantic 模型、typer CLI 等），但上层模型和 connector 各自独立。
