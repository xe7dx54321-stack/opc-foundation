# OPC Foundation Runtime Foundation

更新时间：2026-06-24  
状态：MVP Ready

## 1. Purpose

Shared runtime primitives for foundation modules.

Core principle:

```text
Foundation provides infrastructure. Business systems keep judgment.
```

Runtime Foundation 是一个横向支撑层，不是第四条数据源主线。它为 Research Source / Official Filing / Document Extraction 三条主线提供通用的运行时契约和工具。

## 2. What Runtime Provides

- **Run modes** — validate-config / dry-run / run / source-health / report / retry-failed
- **Runtime status** — success / partial / failed / skipped
- **Health status** — healthy / degraded / failed / disabled / unknown
- **Standard index filenames** — documents.jsonl / filings.jsonl / source_health.jsonl / failed_queue.jsonl / run_log.jsonl
- **Archive path helper** — build_archive_paths / ensure_archive_dirs
- **JSONL helper** — append / read / snapshot / latest
- **Failed queue helper** — FailedQueueRecord / append / load
- **Run log helper** — RunLogRecord / append / load
- **Shared CLI operation vocabulary** — STANDARD_COMMANDS

## 3. What Runtime Does Not Provide

- connector implementation
- market data source
- investment judgment
- ticker mapping
- watchlist logic
- opportunity scoring
- valuation
- trading signal
- browser automation
- OCR
- LLM summarization

## 4. Standard Archive Pattern

```text
archive_root/
  index/
    documents.jsonl or filings.jsonl
    documents.latest.jsonl or filings.latest.jsonl
    source_health.jsonl
    failed_queue.jsonl
    run_log.jsonl
  reports/
```

不同模块的主索引文件名可能不同：
- Research Source → `documents.jsonl` / `documents.latest.jsonl`
- Document Extraction → `documents.jsonl` / `documents.latest.jsonl`
- Official Filing → `filings.jsonl` / `filings.latest.jsonl`

但 `source_health.jsonl` / `failed_queue.jsonl` / `run_log.jsonl` 是统一的。

## 5. Standard Commands

```text
validate-config      # 验证配置文件
dry-run              # 试运行，不保存
run                  # 正式运行
source-health        # 查看源健康状态
source-health --format json  # JSON 格式输出
report               # 生成日报
retry-failed         # 重试失败项
```

## 6. Standard Health Semantics

```text
healthy
degraded
failed
disabled
unknown
```

Recommended semantics:

```text
enabled + candidates > 0 + no failures    → healthy
enabled + candidates > 0 + partial/failed → degraded
enabled + candidates = 0                  → degraded + empty_source
connector/runtime exception               → failed or degraded
disabled source                           → disabled
```

## 7. Adoption Policy

Existing modules do not need to be fully migrated immediately.

Allowed adoption:

- use constants
- use path helpers
- use JSONL helper
- use failed queue helper
- use run log helper

Migration must preserve existing output schema and CLI behavior.

**当前阶段不强制迁移已有模块。** Runtime 层先作为 MVP 提供，新模块可以直接使用，已有模块按需逐步接入。

## 8. Forbidden Fields

以下字段不得作为 runtime model/schema/helper 标准字段：

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

这些术语只能在文档中作为 forbidden fields 示例出现。

## 9. Module Structure

```text
src/opc_foundation/runtime/
  __init__.py       # 包入口，导出所有公共 API
  models.py         # RunMode / RuntimeStatus / HealthStatus / RuntimeIndexFiles / RuntimeCommandResult
  constants.py      # 标准文件名 / 目录名 / 命令列表
  paths.py          # ArchivePaths / build_archive_paths / ensure_archive_dirs
  jsonl.py          # append_jsonl / read_jsonl / write_jsonl_snapshot / read_latest_jsonl
  queue.py          # FailedQueueRecord / append_failed_record / load_failed_records
  run_log.py        # RunLogRecord / append_run_log / load_run_log
```

## 10. Related Documents

- [Runtime Output Contract](runtime_output_contract.md)
- [Foundation Capability Registry](foundation_capability_registry.md)
- [Foundation Readiness Summary](foundation_readiness_summary.md)
