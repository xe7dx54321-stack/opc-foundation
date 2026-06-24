# OPC Foundation Runtime Output Contract

更新时间：2026-06-24

## 1. Standard Output Files

| File | Purpose |
|---|---|
| `documents.jsonl` | append-only document records (Research / Document Extraction) |
| `documents.latest.jsonl` | latest document snapshot |
| `filings.jsonl` | append-only filing records (Official Filing) |
| `filings.latest.jsonl` | latest filing snapshot |
| `source_health.jsonl` | source health records |
| `failed_queue.jsonl` | failed item queue |
| `run_log.jsonl` | run history |
| `reports/` | human-readable reports |

所有文件使用 UTF-8 编码，JSONL 格式（每行一个 JSON 对象）。

## 2. Downstream Rule

Downstream systems should consume index files, not raw folders.

Recommended downstream entry points:

| Domain | Entry Point |
|---|---|
| Research documents | `data/research_archive/index/documents.latest.jsonl` |
| Official filings | `data/official_filings/index/filings.latest.jsonl` |
| Extracted documents | `data/document_extraction/index/documents.latest.jsonl` |

下游系统不应直接读取 raw / metadata / markdown / text 文件夹，而应通过 latest.jsonl 索引文件获取标准入口。

## 3. Stability Rule

Runtime helpers must not change existing schemas silently.

- 新增字段必须有默认值
- 不删除已有字段
- 不改变字段类型
- 不改变文件名
- 不改变目录结构

如果需要 breaking change，必须：
1. 先在文档中标注 deprecated
2. 提供迁移路径
3. 升级版本号

## 4. Business Logic Boundary

Runtime does not perform:

- ticker mapping
- investment scoring
- risk scoring
- valuation
- recommendation
- trade signal
- watchlist filtering
- opportunity scoring
- position sizing
- target price calculation

这些是下游业务系统的职责，不属于 foundation runtime 层。

## 5. JSONL Conventions

- 编码：UTF-8
- 格式：每行一个 JSON 对象，以 `\n` 分隔
- 中文：`ensure_ascii=False`，中文不转义
- 空文件：合法，表示无数据
- 坏行：fail-soft，跳过坏行不中断读取
- 追加模式：主索引文件用 append-only，快照文件用 overwrite

## 6. Related Documents

- [Runtime Foundation](runtime_foundation.md)
- [Foundation Capability Registry](foundation_capability_registry.md)
- [Foundation Readiness Summary](foundation_readiness_summary.md)
