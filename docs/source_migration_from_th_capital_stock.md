# Cross-Repo Source Migration SPEC: th_capital_stock → opc-foundation

## 1. Purpose

核心原则：

```text
Foundation 提供基础设施；
业务系统保留判断力。
```

`opc-foundation` 可以承接：

```text
公开信息源采集
官方披露归档
公开文档抽取
基础 market data 采集
source registry
fetch policy
source health
freshness metadata
标准化索引
```

`opc-foundation` 不承接：

```text
投资判断
机会发现
估值判断
风险判断
watchlist mapping
ticker impact
trade signal
position sizing
paper portfolio
```

## 2. Source Audit Summary

列出 `th_capital_stock` 的 source family：

| Family               | Examples                           | Decision                                |
| -------------------- | ---------------------------------- | --------------------------------------- |
| market_data          | ah_daily_bar, us_daily_bar         | yes, later                              |
| official_filing      | cninfo, hkex, sec                  | yes, P0                                 |
| news                 | eastmoney_news, yahoo_finance_rss  | partial                                 |
| research_report      | eastmoney_report                   | partial, copyright-sensitive            |
| analyst_signal       | marketscreener_analyst             | yes, via analyst_action                 |
| transcript           | public_transcript_fool             | partial                                 |
| market_flow          | stock_connect_flow, margin_balance | yes, later                              |
| official_ir          | official_ir_page                   | yes, via existing research source types |
| factor               | trend/fundamental/us_linkage       | no, not now                             |
| procurement          | cn_tender_procurement              | partial, decouple keywords first        |
| ir_interaction       | irm_interaction                    | partial, decouple ticker first          |
| vendor               | iFinD adapters                     | client-only, later                      |
| financials/valuation | mock adapters                      | no, not now                             |

## 2.5 Current Foundation Capability Status

As of 2026-06-24, completed foundation tracks:

| Track | Status |
|---|---|
| Research Source Foundation | Production Trial Ready |
| Official Filing Foundation | Production Trial Ready |
| Document Extraction Foundation | Production Trial Ready |

Next recommended track: **M3 Market Data / Market Flow Foundation**

Foundation-level registry docs have been added:

- [Foundation Capability Registry](foundation_capability_registry.md)
- [Foundation Readiness Summary](foundation_readiness_summary.md)

## 3. Migration Decision Matrix

| Source Family                 | Decision              | Priority | Target Foundation Module |
| ----------------------------- | --------------------- | -------: | ------------------------ |
| official_filing               | migrate               |       P0 | `official_filings`       |
| document_extraction           | migrate generic layer |       P1 | `document_extraction`    |
| market_data                   | migrate later         |       P1 | `market_data`            |
| market_flow                   | migrate later         |    P1/P2 | `market_flow`            |
| research/news harmonization   | selectively migrate   |       P2 | existing `research`      |
| procurement                   | partial               |       P2 | `procurement`            |
| ir_interaction                | partial               |       P2 | `ir_interaction`         |
| vendor/iFinD                  | client only           |       P3 | `vendors/ifind`          |
| factors                       | do not migrate now    |       No | N/A                      |
| financials/valuation          | do not migrate now    |       No | N/A                      |
| opportunity/risk/report logic | never migrate         |       No | N/A                      |

## 3.5 M2 Status: Document Extraction Foundation

**M2 (Document Extraction Foundation): Production Trial Ready**

```text
状态: Production Trial Ready for local/public documents with OCR disabled
模块: src/opc_foundation/document_extraction/
能力: 本地 PDF / HTML / TXT / Markdown 抽取
边界: 不做 OCR / 不做浏览器自动化 / 不下载远程 PDF / 不做投资判断
```

详细说明见：
- [Document Extraction Foundation](document_extraction_foundation.md)
- [Production Readiness](document_extraction_production_readiness.md)

## 4. P0 Target: Official Filing Foundation

第一批真正开发目标：

```text
Official Filing Foundation
```

覆盖：

```text
SEC EDGAR
CNINFO
HKEXnews
```

建议目标模块：

```text
src/opc_foundation/official_filings/
```

Foundation 负责：

```text
filing discovery
filing metadata
issuer/company name
market
filing type
filing date
source URL
document URL
raw HTML/PDF/JSON archive
content hash
dedupe
source health
failed queue
filings.jsonl
optional documents.jsonl bridge
```

Foundation 不负责：

```text
是否利好
是否超预期
影响哪个 ticker
是否影响估值
是否进入交易机会
是否触发报告
```

建议后续 phases：

```text
M1A: Official Filing Foundation SPEC
M1B: SEC EDGAR MVP
M1C: CNINFO MVP
M1D: HKEX MVP
M1E: source health + production live smoke
M1F: th_capital_stock consumption bridge
```

建议优先从 SEC 开始，因为 SEC 官方 JSON/API 更规范、合规边界清楚、无需登录和 key。

## 5. P1 Target: Document Extraction Foundation

目标模块：

```text
src/opc_foundation/document_extraction/
```

迁移方向：

```text
公告 PDF
IR presentation PDF
SEC filing exhibits
公开白皮书
公开行业报告
```

允许：

```text
PDF metadata
text extraction
page count
document hash
markdown conversion
extraction_quality
failed queue
```

默认禁止：

```text
OCR
付费研报下载
疑似泄露报告包
绕过权限
cookie/token
批量抓取灰色 PDF
```

OCR 只能作为未来人工开启的可选能力。

## 6. P1/P2 Target: Market Data / Market Flow

目标模块：

```text
src/opc_foundation/market_data/
src/opc_foundation/market_flow/
```

候选：

```text
ah_daily_bar
us_daily_bar
trading calendar
stock_connect_flow
margin_balance
```

注意：

```text
不要塞进 research module。
```

Foundation 负责：

```text
原始行情/资金流采集
标准化时间戳
market/session metadata
freshness
health
sqlite/parquet/jsonl 输出
```

Foundation 不负责：

```text
trend factor
risk signal
opportunity score
position sizing
trade action
```

## 7. P2 Target: Research / News Harmonization

候选：

```text
eastmoney_news_search
eastmoney_news_article
eastmoney_report_search
eastmoney_report_article
marketscreener_analyst
public_transcript_fool
official_ir_page
```

处理方式不是直接迁脚本，而是先判断现有 Research Source Foundation 是否已覆盖：

| th_capital_stock Source         | Foundation Handling                                           |
| ------------------------------- | ------------------------------------------------------------- |
| eastmoney_news_search/article   | `media_mention` / future `news_article`                       |
| yahoo_finance_rss               | existing `rss_feed`                                           |
| eastmoney_report_search/article | copyright-sensitive, possible future `research_report_index`  |
| marketscreener_analyst          | existing `analyst_action`                                     |
| public_transcript_fool          | existing `conference_transcript`                              |
| official_ir_page                | existing `official_public_research` / `conference_transcript` |

提醒：

```text
Eastmoney report / report PDF sources must be treated as copyright-sensitive.
Do not bulk archive paid or authorization-unclear report PDFs.
Prefer metadata and public article pages.
```

## 8. Partial Migration Candidates

### procurement

候选：

```text
cn_tender_procurement
```

问题：

```text
业务关键词耦合
```

Foundation 可迁：

```text
招标公告采集
标题
发布日期
采购方
金额
链接
正文
source health
```

业务系统保留：

```text
AI 光模块关键词
公司相关性
机会判断
行业解释
```

### IR interaction

候选：

```text
irm_interaction
```

问题：

```text
ticker 耦合
```

Foundation 可迁：

```text
问答平台采集
question
answer
company_name
published_at
url
```

业务系统保留：

```text
ticker mapping
是否重要
是否说明订单/产能/客户
投资含义
```

### iFinD vendor client

未来只可迁：

```text
IFindClient
auth/token refresh
request wrapper
rate limiting
raw response handling
error handling
```

禁止迁：

```text
固定 ticker
业务 lane/domain
dirty inbox
估值判断
投资逻辑
```

## 9. Do Not Migrate

明确不要迁：

```text
trend_factor
fundamental_factor
us_linkage_factor
valuation adapters
financial mock adapters
opportunity_radar
risk_agent
report agent logic
expectation_delta
investment_rating
trade_signal
watchlist mapping
position sizing
paper portfolio
```

原因：

```text
这些是业务判断、派生特征或交易实验能力，不是通用信息源采集能力。
```

## 10. Target Architecture

写入长期目标架构：

```text
opc-foundation
  ├── research/
  ├── official_filings/
  │   ├── sec
  │   ├── cninfo
  │   └── hkex
  ├── document_extraction/
  ├── market_data/
  ├── market_flow/
  ├── vendors/
  │   └── ifind
  └── shared/
      ├── fetching
      ├── source_health
      ├── dedupe
      ├── freshness
      └── registry
```

注意：这只是长期目标架构，本阶段不实现。

## 11. Downstream Consumption Contract

未来 `th_capital_stock` 应从 foundation 消费标准输出。

建议 contract：

```text
research:
data/research_archive/index/documents.jsonl
data/research_archive/index/documents.latest.jsonl

official_filings:
data/official_filings/index/filings.jsonl
data/official_filings/index/filings.latest.jsonl

market_data:
data/market_data/bars.sqlite or bars.parquet
data/market_data/health.jsonl

market_flow:
data/market_flow/flow.sqlite or flow.jsonl
```

业务系统可以做：

```text
ticker mapping
watchlist filtering
importance scoring
expectation comparison
valuation impact
risk interpretation
report generation
```

业务系统不应该重复做：

```text
同一公开源原始抓取
重复去重
重复 source health
重复 failed queue
重复 raw archive
```

## 12. Forbidden Business Fields

以下字段不得进入 foundation 核心模型或标准输出：

```text
affected_tickers
expectation_delta
investment_rating
trade_signal
watchlist
action_decision
recommendation
opportunity_score
risk_score
position_size
target_price
```

允许这些词出现在文档禁止项里，但不得成为 model/schema/output 字段。

## 13. Recommended Roadmap

最终路线图：

```text
M0: Cross-Repo Source Migration SPEC

M1: Official Filing Foundation
  M1A: Official Filing Foundation SPEC
  M1B: SEC EDGAR MVP
  M1C: CNINFO MVP
  M1D: HKEX MVP
  M1E: production health + live smoke

M2: Document Extraction Foundation

M3: Market Data / Market Flow Foundation

M4: Research/News Source Harmonization

M5: Partial Candidates
  procurement
  IR interaction
  vendor clients

M6: th_capital_stock Consumption Bridge
```

第一批进入开发的必须是：

```text
M1A: Official Filing Foundation SPEC
```


---

## 附录 C：M1 进展更新（Official Filing Foundation 已新增）

### M1 状态：✅ 已完成 MVP

M1 = **Official Filing Foundation** 已作为独立模块新增到 opc-foundation。

### 已实现内容

| 模块 | 说明 |
|------|------|
| `official_filings` 模块 | 独立的官方披露归档模块 |
| 数据模型 | FilingSourceConfig / FilingCandidate / NormalizedFiling / FilingSourceHealth |
| Connector Protocol | OfficialFilingConnector 基类 + get_connector 注册 |
| SEC EDGAR connector | submissions JSON 解析，fixture 注入模式 |
| CNINFO connector | 公告列表 JSON 解析，fixture 注入模式 |
| HKEX connector | 公告列表 HTML 解析，fixture 注入模式 |
| Storage / Index | filings.jsonl / filings.latest.jsonl / metadata sidecar |
| Dedupe | canonical_key + content_hash 去重 |
| Source Health | healthy/degraded/failed/disabled/unknown |
| Failed Queue | 失败记录 + retryable 标记 |
| Daily Report | 中文 Markdown 日报 |
| CLI | validate-config / dry-run / run / source-health / report / retry-failed |
| 测试 | 10 个测试文件，覆盖 models/config/connectors/storage/reports/cli/docs |

### 文档

- `docs/official_filing_foundation.md` — Foundation 主文档
- `docs/official_filing_production_run.md` — 生产运行指南
- `configs/official_filings.example.yaml` — 示例配置（全部 enabled=false）

### MVP 边界

- 仅支持 fixture 注入模式，不包含真实网络抓取
- 不做正文提取（只做元数据归档）
- 不下载 PDF（只存 PDF URL）
- 不做投资判断（严格遵守 foundation 边界）

### 后续方向

M1 后续可扩展：
1. 真实 HTTP fetcher（接入网络抓取）
2. 更多披露源（上交所、深交所等）
3. 正文提取（HTML/PDF 文本抽取）
4. XBRL 解析（SEC 财务数据结构化）
5. 增量同步（基于日期的增量抓取）


---

## 附录 D：M1 Official Filing Foundation 完成

### Production Trial Ready

Official Filing Foundation 已达到 **Production Trial Ready** 状态。

### Live Smoke 结果

| Source | Result | Health | Production |
|--------|--------|--------|------------|
| SEC EDGAR | 5/5 saved | healthy | ready |
| CNINFO | 5/5 saved | healthy | ready |
| HKEXnews | 0 candidates | degraded | limited |

### HKEXnews 限制

港交所页面使用 JavaScript 动态加载数据，当前为 **degraded + empty_source**。

### 下一步

```
M2: Document Extraction Foundation
```

考虑：
- PDF 正文文本提取
- HTML 正文文本抽取
- 结构化字段增强
