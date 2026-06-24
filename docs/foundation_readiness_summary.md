# OPC Foundation Readiness Summary

## 1. Current Readiness

As of 2026-06-24, `opc-foundation` has three production-trial-ready foundation tracks:

```text
Research Source Foundation     → Production Trial Ready
Official Filing Foundation     → Production Trial Ready
Document Extraction Foundation → Production Trial Ready
```

总览详见：[Foundation Capability Registry](foundation_capability_registry.md)

---

## 2. Readiness Table

| Track                          | Implementation | Live/Local Smoke | Production Scripts | Readiness              |
| ------------------------------ | -------------- | ---------------- | ------------------ | ---------------------- |
| Research Source Foundation     | complete       | complete         | complete           | Production Trial Ready |
| Official Filing Foundation     | complete       | complete         | complete           | Production Trial Ready |
| Document Extraction Foundation | complete       | complete         | complete           | Production Trial Ready |
| Shared Runtime Foundation       | MVP complete   | N/A (utility)    | N/A (utility)      | MVP Ready              |
| Foundation Control Center        | MVP complete   | N/A (visualization) | N/A (visualization) | MVP Ready              |

---

## 3. What Is Ready

### Research Source Foundation

Ready for:

```text
public RSS feeds
official static research pages
public podcast transcript pages
public conference transcript pages
public media mentions
analyst action metadata (raw only)
manual URL fallback
wechat archive downstream consumption
```

Notable: analyst_action and media_mention only record raw public metadata. They do NOT perform investment judgment or rating interpretation.

### Official Filing Foundation

Ready for:

```text
SEC EDGAR (live smoke verified)
CNINFO (live smoke verified)
HKEXnews fail-soft tracking
filings index with deduplication
source health monitoring
failed queue management
daily reports
```

Notable: HKEXnews is currently degraded due to client-side rendering. It works with static HTML fixtures but live sites require JS rendering (not supported).

### Document Extraction Foundation

Ready for:

```text
local/public PDF (text + metadata + page_count)
local/public HTML (text extraction)
plain text (TXT)
Markdown (preservation + stats)
document hash (SHA256)
content hash (SHA256)
markdown output
metadata sidecar
raw file copy
failed queue
daily reports
```

Notable: OCR is disabled by default and not implemented. Only local files — no remote PDF download.

---

### Shared Runtime Foundation

Ready for:

```text
standard run modes / status / health enums
archive path helpers
JSONL read/write helpers
failed queue helper
run log helper
shared CLI command vocabulary
```

Note: Runtime Foundation is a shared utility layer, not a standalone data source. It supports the three data source tracks above.

详见 [Runtime Foundation](runtime_foundation.md) 和 [Runtime Output Contract](runtime_output_contract.md)。

### Foundation Control Center

Ready for:

```text
capability visualization
maturity status display
runtime health monitoring
usage mapping (project → workflow → stage → agent → capability)
docs hub
config validation
```

Note: Control Center is a visualization layer, not a new data source track.

详见 [Foundation Control Center](foundation_control_center.md)。

## 4. What Is Not Ready / Out of Scope

以下能力**尚未实现**或**明确不在范围内**：

```text
market_data foundation       # 计划中 M3
market_flow foundation       # 计划中 M3
factor engine                # 不在 foundation 范围
valuation logic              # 下游业务逻辑
financial statement adapters # 不在 foundation 范围
iFinD business adapters      # client-only / 下游
procurement business matching # 部分候选，M5
IR interaction ticker mapping # 部分候选，M5
opportunity scoring          # 下游业务逻辑
risk scoring                 # 下游业务逻辑
trade signals                # 下游业务逻辑
report agents                # 下游业务逻辑
```

These may be future modules or downstream business logic, but are NOT part of current foundation readiness.

---

## 5. Production Pilot Rules

所有生产试运行都必须遵守：

```text
small source set                     # 少量 source 起步
low max_items / max_documents        # 小批量起步
download_pdfs=false unless approved  # 默认不下载 PDF
ocr_enabled=false                    # 默认关闭 OCR
no browser automation                # 不做浏览器自动化
no cookie/token                      # 不保存凭证
no paywall bypass                    # 不绕过付费墙
no investment judgment               # 不做投资判断
source-health reviewed after each run  # 每次运行后检查健康状态
failed_queue reviewed after each run   # 每次运行后检查失败队列
local config and data never committed  # 绝不提交 local config 和数据
```

---

## 6. Downstream Integration Guidance

`th_capital_stock` 和其他下游系统应该：

```text
consume latest JSONL indexes              # 消费 latest 索引文件
perform business mapping downstream       # 在下游做业务映射
maintain their own watchlist / ticker logic  # 自己维护自选股/ticker 逻辑
perform opportunity/risk/valuation analysis downstream  # 在下游做分析
avoid duplicating raw public-source fetching if foundation already provides the data
# 如果 foundation 已有数据，不要重复抓
```

Foundation 是**基础设施**，下游是**业务判断**。

---

## 7. Final Decision

Current decision:

```text
OPC Foundation is ready as a reusable infrastructure layer for:
1. research source archiving
2. official filing archiving
3. document extraction

It is NOT a business judgment or investment decision system.
```

**Foundation provides infrastructure. Business systems keep judgment.**

---

## 8. Related Documents

- [Foundation Capability Registry](foundation_capability_registry.md)
- [Cross-Repo Source Migration SPEC](source_migration_from_th_capital_stock.md)
- [Research Source Production Readiness](research_source_production_readiness.md)
- [Official Filing Production Readiness](official_filing_production_readiness.md)
- [Document Extraction Production Readiness](document_extraction_production_readiness.md)
