# Checklist

> 变更 ID：`add-research-source-foundation`
> 用于系统性验证 SPEC 与后续实现是否满足要求。

---

## SPEC 阶段验证（本次任务 - 已完成）

### 文档完整性

- [x] `spec.md` 已创建于 `.trae/specs/add-research-source-foundation/spec.md`
- [x] `tasks.md` 已创建于 `.trae/specs/add-research-source-foundation/tasks.md`
- [x] `checklist.md` 已创建于 `.trae/specs/add-research-source-foundation/checklist.md`
- [x] 三份文档均使用中文撰写（专有名词除外）

### SPEC 内容覆盖（18 个必备章节）

- [x] 1. 项目目标 - 已覆盖（Why + 完整形态下的目标）
- [x] 2. 项目边界 - 已覆盖（Foundation 负责 / 不负责 + Non-Goals）
- [x] 3. 完整形态 - 已覆盖（完整形态下的目标）
- [x] 4. 支持 source types - 已覆盖（9 类 source type 表格）
- [x] 5. 数据模型 - 已覆盖（5 个核心模型：ResearchSourceConfig / RawFetchResult / NormalizedDocument / SourceHealth / RunSummary）
- [x] 6. 目录结构 - 已覆盖（data/research_archive/ 完整目录树）
- [x] 7. 配置结构 - 已覆盖（YAML 示例 + 配置规则）
- [x] 8. connector 设计 - 已覆盖（8 个 connector 设计说明）
- [x] 9. CLI 设计 - 已覆盖（6 个命令 + exit code 规范）
- [x] 10. 下游消费契约 - 已覆盖（documents.jsonl 契约 + 不输出业务字段）
- [x] 11. 合规与来源可信度 - 已覆盖（6 类 legal_profile + 合规要求）
- [x] 12. 质量控制 - 已覆盖（采集质量维度 + extraction_quality 取值）
- [x] 13. 测试策略 - 已覆盖（Unit / Connector / Integration / Non-goals）
- [x] 14. 失败降级策略 - 已覆盖（fail-soft + exit code）
- [x] 15. 与 wechat archive 的关系 - 已覆盖（WeChatArchiveConnector 复用，不重写）
- [x] 16. 与 th_capital_stock 的集成边界 - 已覆盖（Foundation 输出 vs th_capital_stock 负责 vs Foundation 不应输出）
- [x] 17. 非目标 - 已覆盖（Non-Goals 章节，16 条）
- [x] 18. 未来开发阶段建议 - 已覆盖（Phase 1-5，且 SPEC 重点是 whole picture 不局限于第一阶段）

### SPEC 边界合规

- [x] SPEC 不包含投研判断逻辑（股票买卖 / target price / watchlist / 预期差评分）
- [x] SPEC 不包含 LLM 投研评分
- [x] SPEC 不包含交易信号
- [x] SPEC 不包含行业景气度判断
- [x] SPEC 不包含针对 th_capital_stock 的业务逻辑硬编码
- [x] SPEC 不要求修改 wechat 模块
- [x] SPEC 不要求修改 th_capital_stock
- [x] SPEC 不要求引入新依赖（Phase 4 PDF 抽取单独评估除外）
- [x] SPEC 不要求访问真实网站 / 真实微信公众号 / 真实付费源
- [x] SPEC 不要求提交真实数据
- [x] SPEC 不要求打 tag

### SPEC 阶段不做

- [x] 未实现任何代码
- [x] 未新增真实抓取逻辑
- [x] 未访问真实网站
- [x] 未引入新依赖
- [x] 未修改现有 wechat 模块
- [x] 未修改 th_capital_stock
- [x] 未写投研评分规则
- [x] 未把 Wall Street Radar 业务逻辑写进 foundation
- [x] 未提交真实数据
- [x] 未打 tag

---

## 实现阶段验证（后续 Phase 完成后逐项检查）

### Phase 0：文档落地（已完成）

- [x] `docs/research_source_foundation.md` 已创建，包含全部 18 个章节
- [x] `configs/research_sources.example.yaml` 已创建，仅使用公开示例 URL
- [x] 示例配置覆盖至少 4 种 source_type（实际覆盖 6 种）
- [x] 文档重点是 whole picture，不局限于第一阶段

### Phase 1：MVP 骨架

- [ ] `src/opc_foundation/research/` 子包已创建
- [ ] 5 个核心数据模型已实现（pydantic BaseModel）
- [ ] 配置加载与校验已实现（`validate-config` 命令可用）
- [ ] Storage Layer 已实现（目录结构 + JSONL index + SQLite seen store + failed queue + run log + source health）
- [ ] Connector Framework 基类已实现
- [ ] `RSSConnector` 已实现并测试通过
- [ ] `WeChatArchiveConnector` 已实现并测试通过
- [ ] Normalization Layer 已实现（URL canonicalization + content_hash）
- [ ] Fetch Layer 已实现（timeout / retry / error classification / 合规边界）
- [ ] 主运行器已实现（单 source / 单文档失败隔离）
- [ ] CLI `validate-config` / `dry-run` / `run` 已实现
- [ ] exit code 规范（0 / 1 / 2 / 3）已实现
- [ ] 基础中文日报已实现
- [ ] Phase 1 全部测试通过（unit + integration）
- [ ] 测试全部使用 fixture，不访问真实网络

### Phase 2：扩展 Connector + 失败重试

- [ ] `WebPageConnector` 已实现并测试通过
- [ ] `ManualURLConnector` 已实现并测试通过
- [ ] `LocalDocumentConnector` 已实现并测试通过
- [ ] `PodcastTranscriptConnector` 已实现并测试通过（只有音频时标记 partial）
- [ ] `retry-failed` CLI 命令已实现并测试通过
- [ ] `source-health` CLI 命令已实现并测试通过
- [ ] `report --date` CLI 命令已实现并测试通过
- [ ] partial extraction 降级逻辑已测试通过

### Phase 3：研究型源 Connector

- [ ] `ConferenceTranscriptConnector` 已实现并测试通过
- [ ] `AnalystActionConnector` 已实现并测试通过
- [ ] `official_public_research` 专用抽取 profile 已实现
- [ ] `media_mention` connector 已实现（不抓付费研报全文）

### Phase 4：质量控制 + 运维优化

- [ ] `extraction_quality` 自动评估已实现
- [ ] PDF 抽取接口已预留（如引入依赖，已单独评估）
- [ ] 单次运行支持 50-200 个 source
- [ ] source health 可追踪 30 天以上

### Phase 5：下游集成验证

- [ ] `th_capital_stock` 可读取 `documents.jsonl` 增量消费
- [ ] `th_capital_stock` 维护自己的 ingest state
- [ ] Foundation 不输出业务字段（affected_tickers / investment_rating / expectation_delta / trade_signal）
- [ ] `thcapital-content-department` 集成验证通过
- [ ] `opc_Demand_Radar` 集成验证通过
- [ ] 下游消费契约已文档化

---

## 全局合规验证（每个 Phase 都必须满足）

### 边界合规

- [ ] 不包含投研判断逻辑
- [ ] 不包含 LLM 投研评分
- [ ] 不包含交易信号
- [ ] 不包含 watchlist 映射
- [ ] 不包含预期差评分
- [ ] 不包含针对 th_capital_stock 的业务逻辑硬编码
- [ ] 不修改 `src/opc_foundation/wechat/`
- [ ] 不修改 th_capital_stock
- [ ] 不修改 opc_Demand_Radar
- [ ] 不引入新依赖（除非 SPEC 明确允许）

### 合规要求

- [ ] 不抓取需要登录的付费研报全文
- [ ] 不绕过 paywall
- [ ] 不保存 cookie/token
- [ ] 不伪装成机构客户
- [ ] 不抓取明显泄露的研报包
- [ ] 对 rebroadcast/unknown 源做 legal_profile 标记

### 代码质量

- [ ] 代码通过 lint（ruff）
- [ ] 代码通过 typecheck
- [ ] 函数级注释完整（功能 / 参数 / 返回值 / 异常处理，小白话术）
- [ ] 测试全部使用 fixture，不访问真实网络
- [ ] 不访问真实 Goldman/Morgan/JPM 页面
- [ ] 不访问真实微信公众号
- [ ] 不访问真实付费源

### 下游契约

- [ ] 下游只读取 `index/documents.jsonl`
- [ ] `documents.jsonl` 每行是一个 `NormalizedDocument`
- [ ] Foundation 不记录下游处理状态
- [ ] NormalizedDocument 不包含业务字段（affected_tickers / investment_rating / expectation_delta / trade_signal）

### 失败降级

- [ ] 单 source 失败不影响整个批次
- [ ] 单文档失败不影响其他文档
- [ ] 正文提取失败保存 raw/html 并标记 partial
- [ ] 图片/附件下载失败不影响正文保存
- [ ] failed_queue 支持 retry
- [ ] source_health 记录连续失败
- [ ] CLI exit code 区分成功 / 配置错误 / 部分失败 / 严重失败（0 / 1 / 2 / 3）
