# Research Source Foundation Spec

> 中文名：全球研究信息源采集与归档底座
> 英文名：Research Source Foundation
> 所属项目：`opc-foundation`
> 模块路径（规划）：`src/opc_foundation/research/`
> 变更类型：新增能力底座（ADD）

---

## Why

`opc-foundation` 目前已经有 `wechat`（微信公众号归档）、`sources` / `sources_v2`（通用信号采集）、`signals`（去重）、`web`（正文抽取）等基础能力，但**没有一个统一的“研究型信息源”采集与归档底座**。

下游多个项目（`th_capital_stock`、`thcapital-content-department`、`opc_Demand_Radar`、未来的行业研究 / 一级市场 / 竞争情报系统）都需要消费来自投行官网、播客文字稿、会议纪要、分析师评级、媒体引用、微信公众号归档等多种研究型信息源。

如果每个下游项目各自抓取、各自归档、各自去重，会出现：

1. 重复抓取同一个源，浪费带宽和被 ban 风险
2. 去重逻辑分散，同一篇文档被多个系统重复存储
3. 正文抽取规则不一致，下游拿到的数据质量参差不齐
4. 源健康状态无人统一监控，某个源挂了所有下游都不知道
5. 合规边界不清晰，容易触碰付费研报 / paywall

因此需要一个**通用底层能力**：把外部研究信息源稳定、合规、结构化地搬回本地，形成可被下游系统消费的标准文档资产。下游系统只读取 Foundation 输出的标准索引，按自己的业务规则做分析判断。

**Foundation 提供基础设施，项目保留判断力。**

---

## What Changes

### 新增（ADDED）

- 新增 `opc_foundation.research` 子包，作为 Research Source Foundation 的实现入口
- 新增 Source Registry 配置体系（`configs/research_sources.example.yaml`），统一管理研究信息源
- 新增 Connector Framework，支持 9 类 source type 的采集连接器
- 新增 Fetch Layer（HTTP 抓取 + timeout/retry/rate-limit/error-classification）
- 新增 Extraction Layer（HTML 正文 / RSS item / Podcast transcript / Metadata 抽取，PDF 预留接口）
- 新增 Normalization Layer（统一文档模型 `NormalizedDocument` + URL canonicalization + content_hash）
- 新增 Storage Layer（`data/research_archive/` 目录体系 + JSONL index + SQLite seen store + failed queue + run log + source health）
- 新增 Report Layer（中文日报 + 源健康报告 + 失败报告）
- 新增 CLI（`validate-config` / `dry-run` / `run` / `retry-failed` / `report` / `source-health`）
- 新增下游消费契约：`data/research_archive/index/documents.jsonl`
- 新增合规与来源可信度体系（`legal_profile`）
- 新增质量控制字段（采集质量，非投研质量）
- 新增失败与降级策略（fail-soft + exit code 规范）
- 新增文档：`docs/research_source_foundation.md`

### 复用（REUSED）

- 复用现有 `opc_foundation.wechat` 模块的归档产物（通过 `WeChatArchiveConnector` 读取，不重写）
- 复用现有 `opc_foundation.web` 模块的正文抽取能力（`TrafilaturaExtractor`）
- 复用现有 `opc_foundation.storage` 的 JSONL / CSV 读写能力
- 复用现有 `opc_foundation.run` 的 RunContext / RunLog / ArtifactManifest 能力
- 复用现有 `opc_foundation.signals` 的 SeenStore 去重思路（research 模块会有自己的 seen store，但思路一致）

### 不修改（NOT MODIFIED）

- 不修改 `opc_foundation.wechat` 模块
- 不修改 `th_capital_stock`
- 不修改 `opc_Demand_Radar`
- 不修改现有 `sources` / `sources_v2` 模块（research 是平行的能力底座，不强行合并）

### 不做（NOT DOING）

- 不做投研判断（股票买卖、行业投资价值、target price、watchlist 映射、预期差评分等）
- 不做 LLM 投研评分
- 不做交易信号
- 不做行业景气度判断
- 不做大规模分布式爬虫
- 不做实时毫秒级更新
- 不做搜索引擎级全文检索
- 不做多用户权限系统

---

## Impact

### Affected specs

- 无现有 spec 受影响（这是新增能力底座）

### Affected code

- **新增**：`src/opc_foundation/research/`（整个子包）
- **新增**：`configs/research_sources.example.yaml`
- **新增**：`docs/research_source_foundation.md`
- **新增**：`tests/research/`（测试目录）
- **可能新增**：`tests/research/fixtures/`（测试夹具）
- **不修改**：`src/opc_foundation/wechat/`
- **不修改**：`src/opc_foundation/sources/`、`src/opc_foundation/sources_v2/`
- **可能修改**：`src/opc_foundation/__init__.py`（导出 research 模块公共 API）
- **可能修改**：`src/opc_foundation/cli.py`（注册 research 子命令，或由 research 模块自带 CLI）
- **可能修改**：`README.md`（在 Public API 和模块列表中加入 research）
- **可能修改**：`pyproject.toml`（如有新依赖，但本 SPEC 不引入新依赖）

### Downstream impact

- `th_capital_stock`：可读取 `data/research_archive/index/documents.jsonl` 作为投研信息源
- `thcapital-content-department`：可读取标准索引作为内容素材源
- `opc_Demand_Radar`：可读取标准索引作为需求信号补充源
- 未来行业研究 / 一级市场 / 竞争情报系统：统一消费入口

---

## 项目核心定位

### 1. Foundation 的角色

`opc-foundation` 在本项目中的角色是：

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

### 2. Foundation 不负责什么

它不负责投研判断。**严禁**在 `opc-foundation` 中实现：

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

## 完整形态下的目标

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

并统一输出为本地标准文档资产：

```text
data/research_archive/
  documents/
  index/documents.jsonl
  state/seen.sqlite
  state/run_log.jsonl
  state/failed_queue.jsonl
  state/source_health.jsonl
  reports/daily_capture_YYYY-MM-DD.md
```

下游系统不直接扫乱七八糟的网页和文件夹，而是读取 Foundation 生成的标准索引：

```text
index/documents.jsonl
```

然后按自己的业务规则做分析。

---

## ADDED Requirements

### Requirement: Source Registry（信息源注册表）

系统 SHALL 提供一个 Source Registry，用于集中管理所有研究信息源的配置。

#### Scenario: 加载 source registry 配置
- **WHEN** 用户通过 CLI 或 Python API 加载 `configs/research_sources.yaml`
- **THEN** 系统解析 YAML，校验字段，返回 `ResearchSourceConfig` 列表
- **AND** 校验失败时返回明确的字段级错误信息

#### Scenario: 启用 / 禁用 source
- **WHEN** 某个 source 的 `enabled` 字段为 `false`
- **THEN** 该 source 在 `run` / `dry-run` 中被跳过
- **AND** 在 source health 中标记为 `disabled`

#### Scenario: source_id 唯一性
- **WHEN** 配置中出现重复 `source_id`
- **THEN** `validate-config` 报错，列出重复的 source_id

---

### Requirement: Connector Framework（连接器框架）

系统 SHALL 提供一个可扩展的 Connector Framework，支持 9 类 source type。每个 connector 实现统一接口，将外部信息源转换为 `NormalizedDocument` 候选。

#### 支持的 source types

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

#### Scenario: RSS 连接器解析 feed
- **WHEN** `RSSConnector` 处理一个 `rss_feed` 类型的 source
- **THEN** 解析 RSS / Atom，提取 title / link / published / summary / author
- **AND** 受 `max_items_per_source` 限制
- **AND** 兼容 feedparser 解析行为

#### Scenario: WeChatArchive 连接器复用已有归档
- **WHEN** `WeChatArchiveConnector` 处理一个 `wechat_archive` 类型的 source
- **THEN** 读取 `data/wechat_archive/index/articles.jsonl`（或 `data/wechat_live_smoke_archive/index/articles.jsonl`）
- **AND** 将每条记录转换为 `NormalizedDocument` 候选
- **AND** **不**重新抓取微信，**不**修改 wechat 模块

#### Scenario: 单个 connector 失败隔离
- **WHEN** 某个 connector 抛出异常或返回错误
- **THEN** 该 source 标记为失败，记录到 `failed_queue.jsonl` 和 `source_health.jsonl`
- **AND** **不**影响其他 source 的执行
- **AND** 整个 run 继续完成

---

### Requirement: Fetch Layer（抓取层）

系统 SHALL 提供统一的 Fetch Layer，处理所有 HTTP 抓取。

#### Scenario: 超时与重试
- **WHEN** HTTP 请求超时
- **THEN** 按 `fetch_profile` 配置的重试次数和退避策略重试
- **AND** 全部失败后记录到 `RawFetchResult.error`，`retryable` 标记为 `true`

#### Scenario: User-Agent 与 rate limit
- **WHEN** 发起 HTTP 请求
- **THEN** 使用配置的 `user_agent`
- **AND** 遵守 `rate_limit`（同源请求间隔）
- **AND** 收到 429 时记录 `rate_limit` 警告并退避

#### Scenario: 错误分类
- **WHEN** 抓取失败
- **THEN** 将错误分类为 `timeout` / `connection` / `http_4xx` / `http_5xx` / `parse` / `unknown`
- **AND** 记录到 `RawFetchResult.error` 和 `RawFetchResult.retryable`

#### Scenario: 合规边界
- **WHEN** 检测到需要登录 / paywall / cookie / token 的页面
- **THEN** **不**绕过，**不**保存 cookie/token，**不**伪装机构客户
- **AND** 标记为 `access_denied`，记录到 failed queue

---

### Requirement: Extraction Layer（抽取层）

系统 SHALL 提供统一的 Extraction Layer，从原始抓取结果中抽取正文和元数据。

#### Scenario: HTML 正文提取
- **WHEN** 处理一个 HTML 页面
- **THEN** 使用 `TrafilaturaExtractor`（复用现有 `opc_foundation.web`）提取正文
- **AND** 输出 markdown 和 cleaned html
- **AND** 评估 `extraction_quality`（high / medium / low / empty / unknown）

#### Scenario: RSS item 解析
- **WHEN** 处理一个 RSS feed item
- **THEN** 提取 title / link / published / summary / author
- **AND** 如 summary 不含正文，可选抓取 link 详情页

#### Scenario: Podcast transcript 抽取
- **WHEN** 处理一个 `podcast_transcript` source
- **THEN** 优先抽取公开 transcript 页面
- **AND** 如只有音频，**不**强制做语音转文字（标记为 `partial`，保留 episode metadata）

#### Scenario: PDF 文本抽取（预留接口）
- **WHEN** 处理一个 PDF 文档
- **THEN** 调用预留的 PDF 抽取接口（本阶段可不实现具体逻辑，仅预留接口和 `extraction_quality=unknown`）
- **AND** 不引入新依赖

#### Scenario: Metadata 抽取
- **WHEN** 处理任何文档
- **THEN** 抽取 title / author / published_at / canonical_url / language
- **AND** 写入 `metadata.json`

---

### Requirement: Normalization Layer（标准化层）

系统 SHALL 提供统一的 Normalization Layer，将所有 source 的输出标准化为 `NormalizedDocument`。

#### Scenario: URL canonicalization
- **WHEN** 处理一个文档的 URL
- **THEN** 规范化 URL（去除 tracking 参数、统一 scheme、统一 host 大小写）
- **AND** 生成 `canonical_url`，作为去重 key 之一

#### Scenario: content_hash 计算
- **WHEN** 文档正文提取完成
- **THEN** 对正文（markdown 或 text）计算 `content_hash`（SHA-256）
- **AND** 用于内容级去重

#### Scenario: 统一时间字段
- **WHEN** 文档标准化完成
- **THEN** `captured_at` 设置为本次运行时间（UTC ISO-8601）
- **AND** `published_at` 尽量从源页面解析，解析失败则为 `None`
- **AND** `updated_at` 可选

#### Scenario: source metadata 标准化
- **WHEN** 文档标准化完成
- **THEN** `source_id` / `source_name` / `source_type` / `legal_profile` / `tags` 从 SourceRegistry 配置继承
- **AND** `content_type` 标记为 `markdown` / `html` / `pdf` / `json` / `podcast` / `rss` 等

---

### Requirement: Storage Layer（存储层）

系统 SHALL 提供统一的 Storage Layer，将标准化文档归档到本地。

#### 目录结构

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
    documents.jsonl                    # 全量索引（追加写）
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

#### Scenario: 文档归档
- **WHEN** 一篇文档标准化完成且通过去重
- **THEN** 在 `documents/YYYY/MM/YYYY-MM-DD__source_slug__title_slug/` 下创建目录
- **AND** 写入 `document.md` / `document.html` / `raw.html` / `metadata.json`
- **AND** 如有图片 / 附件，写入 `images/` / `attachments/`

#### Scenario: JSONL 索引追加
- **WHEN** 一篇文档归档完成
- **THEN** 将 `NormalizedDocument` 序列化为一行 JSON，追加到 `index/documents.jsonl`
- **AND** 同时写入 `index/documents.latest.jsonl`（本次 run 的快照）

#### Scenario: SQLite 去重
- **WHEN** 一篇文档候选进入去重检查
- **THEN** 查询 `state/seen.sqlite`，按 `canonical_url` 和 `content_hash` 判断是否已存在
- **AND** 已存在则标记 `status=duplicate`，不重复归档
- **AND** 不存在则归档并写入 seen store

#### Scenario: failed queue
- **WHEN** 一篇文档抓取或抽取失败
- **THEN** 写入 `state/failed_queue.jsonl`，包含足够信息供 `retry-failed` 重跑
- **AND** 不影响其他文档

#### Scenario: run log
- **WHEN** 一次 run 完成
- **THEN** 将 `RunSummary` 追加到 `state/run_log.jsonl`
- **AND** 包含 run_id / mode / started_at / finished_at / 各类计数 / exit_code

#### Scenario: source health 更新
- **WHEN** 一次 run 完成
- **THEN** 更新 `state/source_health.jsonl` 中每个 source 的健康状态
- **AND** 记录 `last_success_at` / `last_failure_at` / `consecutive_failures` / `last_error`

---

### Requirement: Report Layer（报告层）

系统 SHALL 提供中文 Markdown 报告。

#### Scenario: 日报生成
- **WHEN** 一次 run 完成
- **THEN** 生成 `reports/daily_capture_YYYY-MM-DD.md`
- **AND** 包含：本日源数量、成功源数量、失败源数量、新增文档数、partial 文档数、failed 文档数、duplicate 文档数、source health 异常、failed queue 摘要

#### Scenario: 源健康报告
- **WHEN** 用户执行 `source-health` 命令
- **THEN** 生成 `reports/source_health_YYYY-MM-DD.md`
- **AND** 列出每个 source 的 status / last_success_at / consecutive_failures / last_error

#### Scenario: 失败报告
- **WHEN** 存在失败队列
- **THEN** 日报中包含 failed queue 摘要（按 source 分组，列出错误类型和数量）

---

### Requirement: CLI（命令行接口）

系统 SHALL 提供统一的 CLI 入口。

#### 命令清单

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

#### Scenario: validate-config
- **WHEN** 用户执行 `validate-config`
- **THEN** 校验 YAML 语法、字段类型、source_id 唯一性、必填字段
- **AND** 输出校验结果（OK / 错误列表）
- **AND** exit code: 0=成功, 1=配置错误

#### Scenario: dry-run
- **WHEN** 用户执行 `dry-run`
- **THEN** 只发现候选，不保存正文，不写 seen store
- **AND** 输出：source_count / candidate_count / new_candidate_count / failed_source_count / warnings
- **AND** exit code: 0=成功, 1=配置错误, 2=部分失败, 3=致命错误

#### Scenario: run
- **WHEN** 用户执行 `run`
- **THEN** 完整执行：fetch → extract → normalize → dedupe → archive → index → report → health update
- **AND** 输出 RunSummary
- **AND** exit code: 0=成功, 1=配置错误, 2=部分失败, 3=致命错误

#### Scenario: retry-failed
- **WHEN** 用户执行 `retry-failed`
- **THEN** 读取 `state/failed_queue.jsonl`，逐条重试
- **AND** 成功的条目从 failed queue 移除，失败的保留并增加 `retry_count`

#### Scenario: report
- **WHEN** 用户执行 `report --date YYYY-MM-DD`
- **THEN** 读取该日期的 run log，生成中文日报

#### Scenario: source-health
- **WHEN** 用户执行 `source-health`
- **THEN** 读取 `state/source_health.jsonl`，输出每个 source 的健康状态

#### Exit Code 规范

```text
0 = success
1 = config error
2 = partial failure（部分 source / 文档失败，但整体完成）
3 = fatal runtime error（无法继续运行）
```

---

### Requirement: Downstream Consumption Contract（下游消费契约）

系统 SHALL 通过 `data/research_archive/index/documents.jsonl` 向下游系统提供标准消费入口。

#### 契约规则

```text
1. 下游系统只读取 index/documents.jsonl，不直接扫 documents/ 目录
2. 每一行是一个 NormalizedDocument 的 JSON 序列化
3. 下游系统根据自己的业务规则消费，Foundation 不记录哪个下游处理过哪篇文档
4. 下游系统应维护自己的处理状态（例如 th_capital_stock/data/research_ingest_state.sqlite）
5. documents.jsonl 支持增量消费（按 captured_at 或 document_id 排序）
```

#### 下游可用的字段

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

#### Scenario: 下游增量消费
- **WHEN** 下游系统读取 `documents.jsonl`
- **THEN** 按自身已处理的 `document_id` 集合过滤新增文档
- **AND** Foundation 不负责记录下游处理状态

#### Scenario: Foundation 不输出业务字段
- **WHEN** Foundation 输出 NormalizedDocument
- **THEN** **不**包含 `affected_tickers` / `investment_rating` / `expectation_delta` / `trade_signal` 等业务字段
- **AND** 这些字段由下游业务系统自行计算

---

### Requirement: Compliance & Legal Profile（合规与来源可信度）

系统 SHALL 内置 source legal profile，但**不做法律结论**。

#### legal_profile 取值

| legal_profile | 含义 | 示例 |
|---|---|---|
| `official_public` | 机构自己公开发布 | 投行官网公开文章、官方 podcast transcript、官方公开 reports 页面 |
| `public_ir` | 上市公司 IR 页面公开材料 | conference transcript、presentation、webcast replay page |
| `licensed_media` | 媒体公开报道 | Reuters、MarketWatch、Yahoo Finance、CNBC |
| `rebroadcast` | 二次转载或中文传播 | 微信公众号摘要、中文财经媒体转述 |
| `user_provided` | 用户手工提供 URL 或本地文件 | manual_url、local_document |
| `unknown` | 来源不明确 | 无法归类的源 |

#### 合规要求（强制）

```text
1. 不要抓取需要登录的付费研报全文
2. 不要绕过 paywall
3. 不要保存 cookie/token
4. 不要伪装成机构客户
5. 不要抓取明显泄露的研报包
6. 对 rebroadcast/unknown 源做标记，供下游决定是否使用
```

#### Scenario: 标记 legal_profile
- **WHEN** 配置 source 时
- **THEN** 必须填写 `legal_profile` 字段
- **AND** `validate-config` 校验该字段取值合法

#### Scenario: 下游根据 legal_profile 决策
- **WHEN** 下游系统读取 NormalizedDocument
- **THEN** 可根据 `legal_profile` 决定是否使用该文档
- **AND** Foundation 不做使用决策

---

### Requirement: Quality Control（质量控制）

系统 SHALL 提供采集质量字段（非投研质量字段）。

#### 质量维度

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

#### extraction_quality 取值

```text
high    - 正文提取完整，有标题、有发布时间、有正文
medium  - 正文提取基本完整，缺少部分字段
low     - 正文提取不完整，正文很短或噪声多
empty   - 正文提取为空
unknown - 无法评估（如 PDF 预留接口）
```

#### Scenario: 日报包含质量统计
- **WHEN** 生成日报
- **THEN** 包含：本日源数量、成功源数量、失败源数量、新增文档数、partial 文档数、failed 文档数、duplicate 文档数、source health 异常、failed queue 摘要

---

### Requirement: Failure & Degradation（失败与降级）

系统 SHALL 支持 fail-soft，确保局部失败不影响整体。

#### Scenario: 单 source 失败隔离
- **WHEN** 单个 source 失败
- **THEN** 不影响整个批次
- **AND** 记录到 failed_queue 和 source_health

#### Scenario: 单文档失败隔离
- **WHEN** 单篇文档失败
- **THEN** 不影响其他文档
- **AND** 记录到 failed_queue

#### Scenario: 正文提取失败降级
- **WHEN** 正文提取失败
- **THEN** 保存 raw/html，标记 `status=partial`，`extraction_quality=low` 或 `empty`
- **AND** 仍写入 index（下游可决定是否使用）

#### Scenario: 图片 / 附件下载失败
- **WHEN** 图片或附件下载失败
- **THEN** 不影响正文保存
- **AND** 在 metadata 中记录失败信息

#### Scenario: failed queue 重试
- **WHEN** 用户执行 `retry-failed`
- **THEN** 逐条重试 failed_queue
- **AND** 成功的条目移除，失败的保留并增加 retry_count

#### Scenario: source_health 连续失败追踪
- **WHEN** 某个 source 连续失败
- **THEN** `consecutive_failures` 递增
- **AND** status 在 `degraded`（连续失败 1-2 次）和 `failed`（连续失败 ≥3 次）之间转换

#### Exit Code 规范

```text
0 = success
1 = config error
2 = partial failure
3 = fatal runtime error
```

---

### Requirement: Testing（测试）

系统 SHALL 提供完整测试，**全部使用 fixture，不访问真实网络**。

#### Unit Tests

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

#### Connector Tests（全部使用 fixture）

```text
sample RSS
sample official research HTML
sample podcast transcript page
sample conference transcript page
sample analyst rating table
sample wechat_archive index
sample manual URL fixture
```

#### Integration Tests

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

#### Non-goals for tests

```text
不访问真实 Goldman/Morgan/JPM 页面
不访问真实微信公众号
不访问真实付费源
不依赖外部网络
```

---

### Requirement: WeChat Archive Reuse（与现有 wechat 模块的关系）

系统 SHALL 通过 `WeChatArchiveConnector` 复用现有 `opc_foundation.wechat` 模块的归档产物，**不重写** wechat 模块。

#### 数据流

```text
wechat_archive（由 opc_foundation.wechat 模块产生）
  ↓
WeChatArchiveConnector（读取 index/articles.jsonl）
  ↓
research_archive（转换为 NormalizedDocument）
  ↓
downstream systems
```

#### Scenario: 读取 wechat archive 索引
- **WHEN** `WeChatArchiveConnector` 处理一个 `wechat_archive` source
- **THEN** 读取 `data/wechat_archive/index/articles.jsonl`
- **AND** 也支持读取 `data/wechat_live_smoke_archive/index/articles.jsonl`
- **AND** 将每条 `ArchivedArticle` 转换为 `NormalizedDocument` 候选
- **AND** **不**重新抓取微信

#### Scenario: 不修改 wechat 模块
- **WHEN** 实现 Research Source Foundation
- **THEN** **不**修改 `src/opc_foundation/wechat/` 下的任何文件
- **AND** 仅通过读取其输出索引来复用

---

## 统一数据模型

> 本阶段只定义模型，不写代码。模型用 pydantic BaseModel 实现（与现有 wechat 模块一致）。

### 1. ResearchSourceConfig（信息源配置）

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

### 2. RawFetchResult（原始抓取结果）

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

### 3. NormalizedDocument（核心标准文档模型）

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

#### status 取值

```text
saved      - 成功保存正文、元数据
duplicate  - 已在之前运行中被保存
partial    - 正文提取失败，但仍保存了原始 HTML
failed     - 抓取或写入过程中出错（进入 failed queue）
skipped    - 被跳过（如 disabled source）
```

#### extraction_quality 取值

```text
high    - 正文提取完整
medium  - 正文提取基本完整，缺少部分字段
low     - 正文提取不完整
empty   - 正文提取为空
unknown - 无法评估
```

### 4. SourceHealth（源健康状态）

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

#### status 取值

```text
healthy   - 最近运行成功
degraded  - 连续失败 1-2 次
failed    - 连续失败 ≥3 次
disabled  - 配置中 enabled=false
unknown   - 尚未运行过
```

### 5. RunSummary（运行摘要）

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

## 配置文件设计

### 配置路径

```text
configs/research_sources.example.yaml    # 示例配置（公开 URL，不含敏感源）
configs/research_sources.local.yaml      # 本地实际配置（gitignore）
```

### 配置结构

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

## Connector 设计

### 1. RSSConnector

- **输入**：`feed_url`
- **输出**：`NormalizedDocument` 候选
- **能力**：RSS / Atom 解析、title/link/published/summary/author 提取、`max_items_per_source`、feedparser 兼容

### 2. WebPageConnector

- **输入**：`url`
- **能力**：抓取网页、发现文章列表、提取详情页链接、正文抽取

### 3. PodcastTranscriptConnector

- **输入**：`podcast page / feed`
- **能力**：发现最新 episode、抽取 transcript、保存 episode metadata

### 4. ConferenceTranscriptConnector

- **输入**：`公司 IR event 页面`
- **能力**：发现 webcast/transcript/presentation、保存 transcript 或 presentation metadata

### 5. AnalystActionConnector

- **输入**：`公开 analyst rating 页面`
- **能力**：抓取评级变化表、标准化为 document
- **注意**：如果最终认为 analyst action 更适合 event schema，可标记为 future extension

### 6. WeChatArchiveConnector

- **输入**：`wechat_archive/index/articles.jsonl`
- **能力**：读取已有微信公众号归档索引、转换为 NormalizedDocument、**不**重新抓微信

### 7. ManualURLConnector

- **输入**：`manual_urls.txt`（或 CSV）
- **能力**：逐条抓取 URL、正文抽取、保存归档

### 8. LocalDocumentConnector

- **输入**：`本地文件目录`
- **能力**：登记本地文档、hash、metadata、索引

---

## 与 th_capital_stock 的集成边界

### Foundation 输出（示例）

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

## 性能与规模目标

### 完整形态目标

```text
1. 单次运行支持 50-200 个 source
2. 单 source 默认最多抓 20-50 条候选
3. 每日新增文档 100-1000 条以内可稳定处理
4. 所有文档本地归档
5. 去重必须稳定
6. source health 可追踪 30 天以上
```

### 不要求

```text
1. 大规模分布式爬虫
2. 实时毫秒级更新
3. 搜索引擎级全文检索
4. 多用户权限系统
```

---

## Non-Goals（非目标）

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

## 未来开发阶段建议

> 此处仅作建议，SPEC 的重点是 whole picture，不局限于第一阶段。

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

## 文档产出要求

本次 SPEC 阶段产出：

```text
docs/research_source_foundation.md    # 完整 SPEC 文档（实现阶段创建）
configs/research_sources.example.yaml # 示例配置（实现阶段创建，仅公开 URL）
```

文档必须包含以下章节：

```text
1. 项目目标
2. 项目边界
3. 完整形态
4. 支持 source types
5. 数据模型
6. 目录结构
7. 配置结构
8. connector 设计
9. CLI 设计
10. 下游消费契约
11. 合规与来源可信度
12. 质量控制
13. 测试策略
14. 失败降级策略
15. 与 wechat archive 的关系
16. 与 th_capital_stock 的集成边界
17. 非目标
18. 未来开发阶段建议
```

注意："未来开发阶段建议"可以有，但不能把文档写成只服务第一阶段的开发计划。这个 SPEC 的重点是 whole picture。

---

## 本次 SPEC 阶段不做

```text
1. 不实现代码
2. 不新增真实抓取逻辑
3. 不访问真实网站
4. 不引入新依赖
5. 不修改现有 wechat 模块
6. 不修改 th_capital_stock
7. 不写投研评分规则
8. 不把 Wall Street Radar 业务逻辑写进 foundation
9. 不提交真实数据
10. 不 tag
```
