# Tasks

> 变更 ID：`add-research-source-foundation`
> 模块：`src/opc_foundation/research/`
> 原则：先文档后代码，先骨架后扩展，先 MVP 后完整形态。

---

## Phase 0：SPEC 与文档落地（已完成）

- [x] Task 0.1：创建 SPEC 三件套（spec.md / tasks.md / checklist.md）
  - [x] SubTask 0.1.1：撰写 `spec.md`（完整 whole picture）
  - [x] SubTask 0.1.2：撰写 `tasks.md`（分阶段任务清单）
  - [x] SubTask 0.1.3：撰写 `checklist.md`（验证检查清单）
  - [x] SubTask 0.1.4：用 NotifyUser 通知用户审批 SPEC
- [x] Task 0.2：审批通过后，创建对外文档 `docs/research_source_foundation.md`
  - [x] SubTask 0.2.1：将 spec.md 的内容整理为对外文档（含全部 18 个章节）
  - [x] SubTask 0.2.2：确保文档重点是 whole picture，不局限于第一阶段
- [x] Task 0.3：创建示例配置 `configs/research_sources.example.yaml`
  - [x] SubTask 0.3.1：仅使用公开示例 URL，不写真实敏感源
  - [x] SubTask 0.3.2：覆盖至少 4 种 source_type（实际覆盖 6 种：official_public_research / rss_feed / podcast_transcript / wechat_archive / manual_url / local_document）

> Phase 0 完成说明：本次任务只落 SPEC，不进入功能开发。Phase 1-5 为后续实现阶段任务，待用户明确指示后启动。

---

## Phase 1：MVP 骨架（核心数据模型 + Storage + 2 个 Connector + 基础 CLI）

- [ ] Task 1.1：创建 `src/opc_foundation/research/` 子包骨架
  - [ ] SubTask 1.1.1：创建 `__init__.py`（模块说明 + 公共 API 导出）
  - [ ] SubTask 1.1.2：创建子模块空文件：`models.py` / `config.py` / `storage.py` / `cli.py` / `connectors/` / `reports.py`
- [ ] Task 1.2：实现数据模型 `models.py`
  - [ ] SubTask 1.2.1：`ResearchSourceConfig`（含 source_id 唯一性校验）
  - [ ] SubTask 1.2.2：`RawFetchResult`
  - [ ] SubTask 1.2.3：`NormalizedDocument`（含 status / extraction_quality 枚举校验）
  - [ ] SubTask 1.2.4：`SourceHealth`（含 status 枚举校验）
  - [ ] SubTask 1.2.5：`RunSummary`（含 exit_code 校验）
- [ ] Task 1.3：实现配置加载与校验 `config.py`
  - [ ] SubTask 1.3.1：`load_research_config(path)` 加载 YAML
  - [ ] SubTask 1.3.2：`validate_config(config)` 校验字段、source_id 唯一性、legal_profile 合法性
  - [ ] SubTask 1.3.3：支持 `defaults` 全局默认参数
- [ ] Task 1.4：实现 Storage Layer `storage.py`
  - [ ] SubTask 1.4.1：目录结构生成（`documents/YYYY/MM/YYYY-MM-DD__source_slug__title_slug/`）
  - [ ] SubTask 1.4.2：文档归档写入（document.md / document.html / raw.html / metadata.json）
  - [ ] SubTask 1.4.3：JSONL index 追加写（`index/documents.jsonl` + `documents.latest.jsonl`）
  - [ ] SubTask 1.4.4：SQLite seen store（`state/seen.sqlite`，按 canonical_url + content_hash 去重）
  - [ ] SubTask 1.4.5：failed queue（`state/failed_queue.jsonl`）
  - [ ] SubTask 1.4.6：run log（`state/run_log.jsonl`）
  - [ ] SubTask 1.4.7：source health（`state/source_health.jsonl`）
- [ ] Task 1.5：实现 Connector Framework 基类 `connectors/base.py`
  - [ ] SubTask 1.5.1：定义 `ResearchConnector` 协议（统一接口）
  - [ ] SubTask 1.5.2：定义 connector 注册机制
- [ ] Task 1.6：实现 `RSSConnector`（`connectors/rss.py`）
  - [ ] SubTask 1.6.1：RSS / Atom 解析（复用 feedparser 思路）
  - [ ] SubTask 1.6.2：title / link / published / summary / author 提取
  - [ ] SubTask 1.6.3：`max_items_per_source` 限制
  - [ ] SubTask 1.6.4：转换为 `NormalizedDocument` 候选
- [ ] Task 1.7：实现 `WeChatArchiveConnector`（`connectors/wechat_archive.py`）
  - [ ] SubTask 1.7.1：读取 `data/wechat_archive/index/articles.jsonl`
  - [ ] SubTask 1.7.2：也支持 `data/wechat_live_smoke_archive/index/articles.jsonl`
  - [ ] SubTask 1.7.3：将 `ArchivedArticle` 转换为 `NormalizedDocument` 候选
  - [ ] SubTask 1.7.4：**不**重新抓微信，**不**修改 wechat 模块
- [ ] Task 1.8：实现 Normalization Layer（`normalize.py`）
  - [ ] SubTask 1.8.1：URL canonicalization（去 tracking 参数、统一 scheme/host）
  - [ ] SubTask 1.8.2：content_hash 计算（SHA-256）
  - [ ] SubTask 1.8.3：captured_at / published_at / updated_at 统一
- [ ] Task 1.9：实现 Fetch Layer（`fetch.py`）
  - [ ] SubTask 1.9.1：HTTP 请求 + timeout / retry / backoff
  - [ ] SubTask 1.9.2：user_agent / rate_limit
  - [ ] SubTask 1.9.3：错误分类（timeout / connection / http_4xx / http_5xx / parse / unknown）
  - [ ] SubTask 1.9.4：合规边界（不绕 paywall、不存 cookie/token）
- [ ] Task 1.10：实现主运行器 `runner.py`
  - [ ] SubTask 1.10.1：`run_research_capture(config)` 串联 fetch → extract → normalize → dedupe → archive → index
  - [ ] SubTask 1.10.2：单 source 失败隔离
  - [ ] SubTask 1.10.3：单文档失败隔离
  - [ ] SubTask 1.10.4：RunSummary 生成 + run_log 写入
  - [ ] SubTask 1.10.5：source_health 更新
- [ ] Task 1.11：实现基础 CLI `cli.py`
  - [ ] SubTask 1.11.1：`validate-config --config <path>`
  - [ ] SubTask 1.11.2：`dry-run --config <path>`
  - [ ] SubTask 1.11.3：`run --config <path>`
  - [ ] SubTask 1.11.4：exit code 规范（0 / 1 / 2 / 3）
- [ ] Task 1.12：实现基础日报 `reports.py`
  - [ ] SubTask 1.12.1：`daily_capture_YYYY-MM-DD.md` 中文日报
  - [ ] SubTask 1.12.2：包含源数量 / 成功 / 失败 / 新增 / partial / failed / duplicate 统计
- [ ] Task 1.13：Phase 1 测试
  - [ ] SubTask 1.13.1：Unit test - config loading & validation
  - [ ] SubTask 1.13.2：Unit test - RSS parsing（fixture）
  - [ ] SubTask 1.13.3：Unit test - URL canonicalization
  - [ ] SubTask 1.13.4：Unit test - dedupe（SQLite seen store）
  - [ ] SubTask 1.13.5：Unit test - storage write/read
  - [ ] SubTask 1.13.6：Unit test - document model validation
  - [ ] SubTask 1.13.7：Integration test - dry-run with fixture config
  - [ ] SubTask 1.13.8：Integration test - run with fixture（duplicate run 第二次应全 duplicate）
  - [ ] SubTask 1.13.9：Integration test - WeChatArchiveConnector 读取 fixture jsonl
  - [ ] SubTask 1.13.10：Integration test - source failure isolation

---

## Phase 2：扩展 Connector + 失败重试 + 源健康

- [ ] Task 2.1：实现 `WebPageConnector`（`connectors/webpage.py`）
  - [ ] SubTask 2.1.1：抓取网页、发现文章列表
  - [ ] SubTask 2.1.2：提取详情页链接
  - [ ] SubTask 2.1.3：正文抽取（复用 `opc_foundation.web.TrafilaturaExtractor`）
- [ ] Task 2.2：实现 `ManualURLConnector`（`connectors/manual_url.py`）
  - [ ] SubTask 2.2.1：读取 `manual_urls.txt` / CSV
  - [ ] SubTask 2.2.2：逐条抓取 + 正文抽取
- [ ] Task 2.3：实现 `LocalDocumentConnector`（`connectors/local_document.py`）
  - [ ] SubTask 2.3.1：扫描本地文件目录
  - [ ] SubTask 2.3.2：hash + metadata + 索引
- [ ] Task 2.4：实现 `PodcastTranscriptConnector`（`connectors/podcast.py`）
  - [ ] SubTask 2.4.1：发现最新 episode
  - [ ] SubTask 2.4.2：抽取公开 transcript
  - [ ] SubTask 2.4.3：只有音频时标记 partial，不强制语音转文字
- [ ] Task 2.5：实现 `retry-failed` CLI 命令
  - [ ] SubTask 2.5.1：读取 `state/failed_queue.jsonl`
  - [ ] SubTask 2.5.2：逐条重试，成功移除，失败保留并增加 retry_count
- [ ] Task 2.6：实现 `source-health` CLI 命令
  - [ ] SubTask 2.6.1：读取 `state/source_health.jsonl`
  - [ ] SubTask 2.6.2：输出每个 source 健康状态
  - [ ] SubTask 2.6.3：生成 `reports/source_health_YYYY-MM-DD.md`
- [ ] Task 2.7：实现 `report --date` CLI 命令
  - [ ] SubTask 2.7.1：按日期读取 run_log
  - [ ] SubTask 2.7.2：生成中文日报
- [ ] Task 2.8：Phase 2 测试
  - [ ] SubTask 2.8.1：Connector test - WebPageConnector（fixture HTML）
  - [ ] SubTask 2.8.2：Connector test - ManualURLConnector（fixture）
  - [ ] SubTask 2.8.3：Connector test - LocalDocumentConnector（fixture）
  - [ ] SubTask 2.8.4：Connector test - PodcastTranscriptConnector（fixture）
  - [ ] SubTask 2.8.5：Integration test - retry-failed
  - [ ] SubTask 2.8.6：Integration test - report --date
  - [ ] SubTask 2.8.7：Integration test - source-health
  - [ ] SubTask 2.8.8：Integration test - partial extraction（正文提取失败降级为 partial）

---

## Phase 3：研究型源 Connector

- [ ] Task 3.1：实现 `ConferenceTranscriptConnector`（`connectors/conference.py`）
  - [ ] SubTask 3.1.1：发现 IR event 页面 webcast/transcript/presentation
  - [ ] SubTask 3.1.2：保存 transcript 或 presentation metadata
- [ ] Task 3.2：实现 `AnalystActionConnector`（`connectors/analyst_action.py`）
  - [ ] SubTask 3.2.1：抓取公开 analyst rating 页面
  - [ ] SubTask 3.2.2：标准化为 document（如更适合 event schema，标记 future extension）
- [ ] Task 3.3：实现 `official_public_research` 专用抽取 profile
  - [ ] SubTask 3.3.1：投行官网文章列表发现
  - [ ] SubTask 3.3.2：详情页正文抽取
- [ ] Task 3.4：实现 `media_mention` connector（`connectors/media_mention.py`）
  - [ ] SubTask 3.4.1：抓取媒体对投行观点的公开引用
  - [ ] SubTask 3.4.2：不抓取付费研报全文
- [ ] Task 3.5：Phase 3 测试
  - [ ] SubTask 3.5.1：Connector test - ConferenceTranscriptConnector（fixture）
  - [ ] SubTask 3.5.2：Connector test - AnalystActionConnector（fixture）
  - [ ] SubTask 3.5.3：Connector test - official_public_research（fixture HTML）
  - [ ] SubTask 3.5.4：Connector test - media_mention（fixture HTML）

---

## Phase 4：质量控制 + 运维优化

- [ ] Task 4.1：实现 `extraction_quality` 自动评估
  - [ ] SubTask 4.1.1：基于 has_title / has_published_at / content_length 评估
  - [ ] SubTask 4.1.2：输出 high / medium / low / empty / unknown
- [ ] Task 4.2：PDF 抽取接口预留落地（如需引入依赖，单独评估）
  - [ ] SubTask 4.2.1：预留接口
  - [ ] SubTask 4.2.2：标记 extraction_quality=unknown
- [ ] Task 4.3：性能优化
  - [ ] SubTask 4.3.1：单次运行支持 50-200 个 source
  - [ ] SubTask 4.3.2：source health 追踪 30 天以上
- [ ] Task 4.4：Phase 4 测试
  - [ ] SubTask 4.4.1：Unit test - extraction_quality 评估
  - [ ] SubTask 4.4.2：Performance test - 50 source 稳定运行（fixture）

---

## Phase 5：下游集成验证

- [ ] Task 5.1：与 `th_capital_stock` 集成验证
  - [ ] SubTask 5.1.1：th_capital_stock 读取 `documents.jsonl` 增量消费
  - [ ] SubTask 5.1.2：th_capital_stock 维护自己的 ingest state
  - [ ] SubTask 5.1.3：验证 Foundation 不输出业务字段（affected_tickers / investment_rating 等）
- [ ] Task 5.2：与 `thcapital-content-department` 集成验证
- [ ] Task 5.3：与 `opc_Demand_Radar` 集成验证
- [ ] Task 5.4：下游消费契约文档化
  - [ ] SubTask 5.4.1：在 `docs/research_source_foundation.md` 中明确契约
  - [ ] SubTask 5.4.2：可选：`docs/integration/research_foundation_integration_guide.md`

---

## Task Dependencies

- Task 0.x（SPEC 与文档）→ 所有后续 Phase
- Task 1.1（子包骨架）→ Task 1.2 ~ 1.13
- Task 1.2（数据模型）→ Task 1.3 ~ 1.10
- Task 1.4（Storage）→ Task 1.10（runner）
- Task 1.5（Connector 基类）→ Task 1.6 ~ 1.7
- Task 1.6（RSSConnector）+ Task 1.7（WeChatArchiveConnector）→ Task 1.10（runner）
- Task 1.8（Normalization）+ Task 1.9（Fetch）→ Task 1.10（runner）
- Task 1.10（runner）→ Task 1.11（CLI）+ Task 1.12（日报）
- Task 1.13（Phase 1 测试）依赖 Task 1.1 ~ 1.12 全部完成
- Phase 2 依赖 Phase 1 完成
- Phase 3 依赖 Phase 2 完成（Connector 框架已稳定）
- Phase 4 依赖 Phase 3 完成
- Phase 5 依赖 Phase 1 ~ 4 至少 MVP 可用

---

## 并行化建议

- Task 1.2（数据模型）与 Task 1.4（Storage）可并行（Storage 依赖模型，但可先写接口）
- Task 1.6（RSSConnector）与 Task 1.7（WeChatArchiveConnector）可并行
- Phase 2 的 Task 2.1 / 2.2 / 2.3 / 2.4 可并行（不同 connector 互不依赖）
- Phase 3 的 Task 3.1 / 3.2 / 3.3 / 3.4 可并行
- 测试任务（Task 1.13 / 2.8 / 3.5 / 4.4）在对应 Phase 实现完成后并行执行

---

## 验证原则

每个 Task 完成后必须满足：

```text
1. 代码通过 lint（ruff）和 typecheck（mypy / pyright）
2. 对应的单元测试 / 集成测试通过
3. 不引入新依赖（除非 SPEC 明确允许，如 Phase 4 的 PDF 抽取单独评估）
4. 不修改 wechat 模块、th_capital_stock、opc_Demand_Radar
5. 不包含投研评分 / 交易信号 / watchlist 映射等业务逻辑
6. 函数级注释完整（功能 / 参数 / 返回值 / 异常处理，小白话术）
```
