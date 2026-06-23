# Research Source Foundation - 生产运行指南

> Phase 2F 文档：把 research module 从"功能可用"推进到"可长期稳定运行、可巡检、可诊断、可生产配置"。

## 1. Phase 2F 目标

Phase 2F 不新增 connector，而是做生产化加固：

- production source registry 配置模板
- local production config 模板
- source health 状态与失败原因标准化
- source-level 运行统计增强
- daily report 人工巡检增强
- source-health CLI 输出增强
- failed queue 可诊断性增强
- documents.jsonl 下游消费契约进一步固化
- 不接入 th_capital_stock，但为后续消费做准备

## 2. production config 与 example config 的区别

| 文件 | 用途 | 是否提交 git |
|---|---|---|
| `configs/research_sources.example.yaml` | 开发示例，展示所有 source_type | 是 |
| `configs/research_sources.production.example.yaml` | 生产配置模板，展示生产环境如何组织 source groups | 是 |
| `configs/research_sources.local.yaml` | 开发用 local config（真实 URL） | **否** |
| `configs/research_sources.production.local.yaml` | 生产用 local config（真实 URL） | **否** |

**关键区别**：
- example 文件用 `example.com` 占位，所有 `enabled: false`
- local 文件填真实 URL，由本地运维维护，不提交 git

## 3. 如何创建 local config

```powershell
# 复制模板
Copy-Item configs/research_sources.production.example.yaml configs/research_sources.production.local.yaml

# 编辑 local config，填入真实 source URL
notepad configs/research_sources.production.local.yaml
```

编辑时：
- 把 `url` / `base_url` 改成真实地址
- 把 `enabled` 改成 `true`
- 不要写入 cookie/token/API key
- 不要绕过 paywall

## 4. 如何 dry-run

```powershell
# 方式 1：直接 CLI
python -m opc_foundation.research.cli dry-run --config configs/research_sources.production.local.yaml

# 方式 2：用脚本
.\scripts\run_research_archive.ps1 -Mode dry-run
```

dry-run 行为：
- discover candidates
- 不抓取详情页正文
- 不写 documents.jsonl
- 写 run_log summary
- 写 report

## 5. 如何正式 run

```powershell
# 方式 1：直接 CLI
python -m opc_foundation.research.cli run --config configs/research_sources.production.local.yaml

# 方式 2：用脚本
.\scripts\run_research_archive.ps1 -Mode run
```

run 行为：
- discover candidates
- seen store 去重
- 抓取详情页
- extractor 抽取正文
- markdown/storage 归档
- documents.jsonl 写入
- source_health 更新
- failed_queue 写入失败项

## 6. 如何查看 source health

```powershell
# 方式 1：直接 CLI
python -m opc_foundation.research.cli source-health --archive-root ./data/research_archive

# 方式 2：用脚本
.\scripts\run_research_archive.ps1 -Mode source-health

# 方式 3：检查脚本（会自动调用 source-health）
.\scripts\check_research_archive.ps1
```

支持参数：
- `--status failed` 只看失败的 source
- `--status degraded` 只看降级的 source
- `--format json` 输出 JSON 格式

## 7. 如何查看 daily report

日报位置：`data/research_archive/reports/daily_capture_YYYY-MM-DD.md`

日报结构：
1. 总览（source 数、候选数、新文档数、失败数、source 健康分布）
2. Source 健康概览（表格）
3. 新保存文档（表格）
4. Partial / Failed（表格）
5. Warnings
6. 下游消费入口

要求：
- 没有新文档也要输出日报
- 没有失败也要明确写"无"
- source health 异常要显眼
- 不输出正文全文
- 不输出 secrets

## 8. 如何理解 healthy/degraded/failed/disabled/unknown

| status | 含义 |
|---|---|
| `healthy` | source enabled，最近一次运行成功，且 failed_count_last_run = 0 |
| `degraded` | source enabled，能 discover 或部分保存，但存在 partial/failed/warnings |
| `failed` | source enabled，connector 失败、fetch 失败、config invalid、连续失败 |
| `disabled` | source.enabled = false |
| `unknown` | 没有足够运行信息 |

## 9. 如何处理 failed_queue

failed_queue 位置：`data/research_archive/state/failed_queue.jsonl`

每条记录包含：
- `source_id` / `source_name` / `source_type`
- `title` / `url` / `canonical_url`
- `failed_at` / `error` / `error_type`
- `retryable` / `retry_count` / `run_id`
- `raw_entry`（不记录正文/secrets）

重试失败队列：
```powershell
python -m opc_foundation.research.cli retry-failed --config configs/research_sources.production.local.yaml
```

error_type 标准化取值：
- `config_error` - 配置错误
- `connector_error` - connector 异常
- `fetch_error` - 抓取失败
- `parse_error` - HTML 解析失败
- `extract_error` - 正文抽取失败
- `storage_error` - 写文件失败
- `empty_source` - source 无候选
- `unsupported_source_type` - 不支持的 source_type
- `unknown_error` - 未知错误

## 10. 下游只消费 documents.jsonl

下游项目（如 th_capital_stock）**只**消费：
- `data/research_archive/index/documents.jsonl`
- `data/research_archive/index/documents.latest.jsonl`

不要消费：
- `state/run_log.jsonl`（运行日志，结构可能变化）
- `state/source_health.jsonl`（运维用）
- `state/failed_queue.jsonl`（运维用）
- `reports/`（人工巡检用）
- `documents/` 下的正文（结构可能变化）

## 11. 不提交 local config / data / secrets

`.gitignore` 已配置：
- `data/research_archive/`
- `configs/research_sources.local.yaml`
- `configs/research_sources.production.local.yaml`

**严禁**提交：
- 真实 source URL
- cookie/token/API key
- 真实媒体报道正文
- 真实投研数据

## 12. 当前仍不接 th_capital_stock

Phase 2F 仍然不接入 `th_capital_stock`。

research module 只负责：
- 采集公开信息源
- 标准化为 DocumentCandidate → NormalizedDocument
- 归档为 markdown + documents.jsonl

是否消费、如何消费、做什么投研判断，由下游项目决定。

research module 不做：
- affected_tickers
- expectation_delta
- investment_rating
- trade_signal
- watchlist mapping
- buy/sell/hold recommendation

## 13. Production Source Selection After Live Smoke

Phase 2H 完成 6 类非微信自动源的真实公开源 live smoke 验证。
基于 live smoke 结果，给出以下生产试运行选源建议。

### Recommended initial production trial source types

1. rss_feed
2. official_public_research
3. podcast_transcript
4. conference_transcript
5. analyst_action
6. media_mention

manual_url is optional and only needed for manual one-off URL ingestion.

wechat_archive should be handled separately after high-signal WeChat source selection.

### Suggested source count for pilot

```text
official_public_research: 2-3 sources
rss_feed: 2-3 sources
podcast_transcript: 1-2 sources
conference_transcript: 1-2 sources
analyst_action: 1-2 sources
media_mention: 1-2 sources
```

### Source patterns to prefer

- official static HTML pages
- valid RSS/Atom feed
- institution-owned public pages
- pages with direct article/event/episode links
- pages with text body in HTML

### Source patterns to avoid

- JS-only pages
- anti-bot pages
- social platform redirects
- PDF-only repositories
- audio-only pages
- paywalled content
- low signal-to-noise WeChat official broker accounts

### Reference documents

- `docs/research_source_live_smoke_registry.md` - live smoke 结果汇总
- `docs/research_source_production_readiness.md` - 生产试运行准备就绪说明
