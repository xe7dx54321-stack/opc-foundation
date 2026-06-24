# OPC Foundation Capability Registry

更新时间：2026-06-24  
状态：Three Foundation Tracks Production Trial Ready

## 1. Executive Summary

`opc-foundation` 当前包含三条 production-trial-ready 基础设施主线：

| Track | Status | Primary Output |
|---|---|---|
| Research Source Foundation | Production Trial Ready | `data/research_archive/index/documents.jsonl` |
| Official Filing Foundation | Production Trial Ready | `data/official_filings/index/filings.jsonl` |
| Document Extraction Foundation | Production Trial Ready | `data/document_extraction/index/documents.jsonl` |

Core principle:

```text
Foundation provides infrastructure.
Business systems keep judgment.
```

---

## 2. Capability Map

### 2.1 Research Source Foundation

**Status**: Production Trial Ready

Supported source types:

| Source Type              | Status             | Notes                                  |
| ------------------------ | ------------------ | -------------------------------------- |
| rss_feed                 | ready              | Public RSS/Atom feeds                  |
| official_public_research | ready with caveats | Static official research pages         |
| podcast_transcript       | ready with caveats | Public transcript pages                |
| conference_transcript    | ready with caveats | IR/events/webcast metadata             |
| analyst_action           | ready with caveats | Raw rating/target metadata only        |
| media_mention            | ready with caveats | Raw media mention metadata only        |
| manual_url               | optional fallback  | Manual URL ingestion                   |
| wechat_archive           | separate track     | Requires high-signal account selection |

Primary outputs:

```text
data/research_archive/index/documents.jsonl
data/research_archive/index/documents.latest.jsonl
data/research_archive/index/source_health.jsonl
data/research_archive/index/failed_queue.jsonl
data/research_archive/index/run_log.jsonl
data/research_archive/reports/
```

详细文档：
- [Research Source Foundation](research_source_foundation.md)
- [Research Source Production Readiness](research_source_production_readiness.md)
- [Research Source Live Smoke Registry](research_source_live_smoke_registry.md)

### 2.2 Official Filing Foundation

**Status**: Production Trial Ready

Supported source types:

| Source Type         | Market | Status             | Notes                               |
| ------------------- | ------ | ------------------ | ----------------------------------- |
| sec_edgar           | US     | ready              | Live smoke success                  |
| cninfo_announcement | CN     | ready              | Live smoke success                  |
| hkex_announcement   | HK     | degraded / limited | Client-side rendering; empty_source |

Primary outputs:

```text
data/official_filings/index/filings.jsonl
data/official_filings/index/filings.latest.jsonl
data/official_filings/index/source_health.jsonl
data/official_filings/index/failed_queue.jsonl
data/official_filings/index/run_log.jsonl
data/official_filings/reports/
```

详细文档：
- [Official Filing Foundation](official_filing_foundation.md)
- [Official Filing Production Readiness](official_filing_production_readiness.md)
- [Official Filing Live Smoke Registry](official_filing_live_smoke_registry.md)

### 2.3 Document Extraction Foundation

**Status**: Production Trial Ready

Supported document types:

| Type     | Status | Notes                                |
| -------- | ------ | ------------------------------------ |
| PDF      | ready  | Local/public documents; OCR disabled |
| HTML     | ready  | Local/public HTML                    |
| TXT      | ready  | Plain text extraction                |
| Markdown | ready  | Markdown preservation and text stats |

Primary outputs:

```text
data/document_extraction/index/documents.jsonl
data/document_extraction/index/documents.latest.jsonl
data/document_extraction/index/source_health.jsonl
data/document_extraction/index/failed_queue.jsonl
data/document_extraction/index/run_log.jsonl
data/document_extraction/reports/
data/document_extraction/metadata/
data/document_extraction/markdown/
data/document_extraction/text/
data/document_extraction/raw/
```

详细文档：
- [Document Extraction Foundation](document_extraction_foundation.md)
- [Document Extraction Production Readiness](document_extraction_production_readiness.md)
- [Document Extraction Live Smoke Registry](document_extraction_live_smoke_registry.md)

---

### 2.4 Shared Runtime Foundation

**Status**: MVP Ready

> Runtime Foundation is a shared utility layer, not a standalone data source.

Shared runtime primitives used by all foundation tracks:

| Capability | Description |
|---|---|
| RunMode | validate-config / dry-run / run / source-health / report / retry-failed |
| RuntimeStatus | success / partial / failed / skipped |
| HealthStatus | healthy / degraded / failed / disabled / unknown |
| ArchivePaths | Standard archive path builder |
| JSONL helper | append / read / snapshot / latest |
| FailedQueue helper | FailedQueueRecord / append / load |
| RunLog helper | RunLogRecord / append / load |

Module path: `src/opc_foundation/runtime/`

详细文档：
- [Runtime Foundation](runtime_foundation.md)
- [Runtime Output Contract](runtime_output_contract.md)

---

### 2.5 Foundation Control Center

**Status**: MVP Ready

> Control Center is a visualization layer, not a new data source track.

Local dashboard for visualizing foundation capabilities, health, and usage mapping.

- 启动方式：`streamlit run src/opc_foundation/dashboard/app.py`
- 能力台账：`configs/foundation_capabilities.yaml`
- 使用关系：`configs/capability_usage_registry.example.yaml`

详细文档：
- [Foundation Control Center](foundation_control_center.md)
- [Control Center 使用指南](foundation_control_center_usage.md)

---

## 3. Shared Operating Capabilities

三条主线共享以下操作模式：

```text
validate-config      # 验证配置文件
dry-run              # 试运行，不保存
run                  # 正式运行
source-health        # 查看源健康状态（文本）
source-health --format json  # 查看源健康状态（JSON）
report               # 生成日报
retry-failed         # 重试失败项
duplicate detection  # 去重检测
failed_queue         # 失败队列
run_log              # 运行日志
```

生产环境配套：

```text
production example config (all sources disabled)
PowerShell run/check scripts
local config pattern (never committed)
data/ in .gitignore
```

---

## 4. Downstream Consumption Contract

下游系统应该消费标准索引文件，而不是原始文件夹。

### Recommended Entry Points

| Domain              | Entry Point                                           |
| ------------------- | ----------------------------------------------------- |
| Research documents  | `data/research_archive/index/documents.latest.jsonl`  |
| Official filings    | `data/official_filings/index/filings.latest.jsonl`    |
| Extracted documents | `data/document_extraction/index/documents.latest.jsonl` |

### Downstream May Enrich With

下游系统可以在自己的代码中添加：

```text
ticker mapping           # ticker 映射
watchlist filtering      # 自选股过滤
importance scoring       # 重要性评分
expectation comparison   # 预期对比
valuation interpretation # 估值解读
risk interpretation      # 风险解读
report generation        # 报告生成
investment judgment      # 投资判断
```

**Foundation 绝不做这些事情。**

---

## 5. Forbidden Business Fields

以下字段**绝对不能**出现在 foundation 的模型 / schema / 输出中：

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

这些术语只能在文档中作为"禁止示例"出现，绝不能成为数据模型的一部分。

---

## 6. Current Limitations

| Area                     | Limitation                                                |
| ------------------------ | --------------------------------------------------------- |
| JS-rendered pages        | Not supported by default                                  |
| Anti-bot pages           | No bypass                                                 |
| Paywall/login            | No bypass                                                 |
| PDF OCR                  | Disabled / not implemented                                |
| Remote PDF bulk download | Not supported                                             |
| Audio transcription      | Not supported                                             |
| Investment judgment      | Out of scope                                              |
| HKEXnews                 | Current static path degraded due to client-side rendering |
| Market data              | Not implemented yet (M3 target)                           |
| Market flow              | Not implemented yet (M3 target)                           |

---

## 7. Next Recommended Tracks

推荐的后续路线图：

```text
M3: Market Data / Market Flow Foundation
M4: Research/News Source Harmonization
M5: Partial Candidates: procurement / IR interaction / vendor client
M6: th_capital_stock Consumption Bridge
```

**当前任务不启动 M3。**

---

## 8. Related Documents

### Foundation-Level
- [Foundation Readiness Summary](foundation_readiness_summary.md)
- [Cross-Repo Source Migration SPEC](source_migration_from_th_capital_stock.md)

### Per-Track Foundation Docs
- [Research Source Foundation](research_source_foundation.md)
- [Official Filing Foundation](official_filing_foundation.md)
- [Document Extraction Foundation](document_extraction_foundation.md)

### Per-Track Production Readiness
- [Research Source Production Readiness](research_source_production_readiness.md)
- [Official Filing Production Readiness](official_filing_production_readiness.md)
- [Document Extraction Production Readiness](document_extraction_production_readiness.md)

### Per-Track Live Smoke Registry
- [Research Source Live Smoke Registry](research_source_live_smoke_registry.md)
- [Official Filing Live Smoke Registry](official_filing_live_smoke_registry.md)
- [Document Extraction Live Smoke Registry](document_extraction_live_smoke_registry.md)

### Contracts & Guides
- [Raw Signal Contract](contracts/raw_signal_contract.md)
- [Source Connector Contract](contracts/source_connector_contract.md)
- [Connector Reliability Policy](contracts/connector_reliability_policy.md)
