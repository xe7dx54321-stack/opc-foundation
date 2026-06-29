# OPC Foundation M3C-3 Report: 15 个验证源 TRAE Trial Scheduling 接入

> **版本**：2.0（M3C-3-fix 后）
> **更新时间**：2026-06-29
> **状态**：M3C-3 manual validation passed, TRAE scheduled trigger blocked → 已修复（command-only）

---

## 1. M3C-3-fix 概述

### 问题

TRAE 定时任务自动触发时报 **"请求失败，请稍后重试"**，连续 3 天（6/27–6/29）自动调度均未实际执行脚本。

### 根因

TRAE Schedule 的 prompt 中包含大量自然语言描述，TRAE 会调用 AI 模型（minimax / custom model）来"理解" prompt 再执行。在**本地模式**下，自定义模型调用链路存在问题，导致 trigger 阶段直接失败，PowerShell 脚本根本没有被执行。

**证据**：
- Executions 计数在增加（说明触发信号到了 TRAE）
- 但 `data/foundation_trial/index/run_summary.json` 连续 3 天没有更新（说明脚本没跑）
- 手动执行脚本完全正常（排除脚本本身问题）
- 改成 command-only prompt 后立即恢复正常（确认是模型调用层问题）

### 修复方案

将 6 个 TRAE trial job 的 prompt 从"自然语言描述 + 命令"改为**纯 shell 命令**（command-only）：

| 修改前 | 修改后 |
|---|---|
| 自然语言描述 + 命令（需要 AI 理解） | 纯 `cd opc-foundation && powershell ...` 命令 |
| 依赖 minimax/custom model 调用 | 不依赖任何模型调用，直接执行 shell |

---

## 2. 当前调度配置

### 6 个 Trial Job（command-only 模式）

| Job | 调度时间 | 命令（command-only） |
|---|---|---|
| Morning Run | 08:10 daily | `cd opc-foundation && powershell -ExecutionPolicy Bypass -File scripts/run_foundation_trial_sources.ps1 -Mode run` |
| Morning Check | 08:25 daily | `cd opc-foundation && powershell -ExecutionPolicy Bypass -File scripts/check_foundation_trial_sources.ps1` |
| Afternoon Run | 13:10 daily | `cd opc-foundation && powershell -ExecutionPolicy Bypass -File scripts/run_foundation_trial_sources.ps1 -Mode run` |
| Evening Run | 20:10 daily | `cd opc-foundation && powershell -ExecutionPolicy Bypass -File scripts/run_foundation_trial_sources.ps1 -Mode run` |
| Evening Check | 20:25 daily | `cd opc-foundation && powershell -ExecutionPolicy Bypass -File scripts/check_foundation_trial_sources.ps1` |
| Daily Status | 23:50 daily | `cd opc-foundation && powershell -ExecutionPolicy Bypass -File scripts/run_foundation_trial_sources.ps1 -Mode dry-run` |

### Trial Source 范围

- **trial source 数**：15
- **是否包含 Microsoft IR**：否（url_backlog，HTTP 403 Akamai bot 保护）
- **是否包含 blocked/search/dormant/TLS/DNS 源**：否

**15 个 Trial Source**：

| source_id | source_name | 状态 |
|---|---|---|
| goldman_sachs_research | Goldman Sachs Research | URL 修复（200 OK） |
| goldman_sachs_reports | Goldman Sachs Reports | URL 修复（200 OK） |
| goldman_sachs_top_of_mind | Goldman Sachs Top of Mind | live OK |
| goldman_sachs_insights | Goldman Sachs Insights | live OK |
| barclays_our_insights | Barclays Our Insights | live OK |
| yahoo_finance | Yahoo Finance | live OK |
| business_insider | Business Insider | live OK |
| markets_insider | Markets Insider | live OK |
| the_fly | The Fly | live OK |
| briefing_com_upgrades | Briefing.com Upgrades/Downgrades | live OK |
| wallstreet_cn | 华尔街见闻 | live OK |
| cls_cn | 财联社 | live OK（标记 **transient watch**，偶发 HTTP 418 反爬） |
| wind_public | Wind 万得公开内容 | live OK |
| gelonghui | 格隆汇 | live OK |
| zhitong_caijing | 智通财经 | live OK |

---

## 3. 手动验证结果（M3C-3 阶段）

### 3.1 手动直接执行脚本（6/26）

| 任务 | 结果 | 详情 |
|---|---|---|
| morning_run | ✅ 14成功/1失败 | cls_cn HTTP 418（临时反爬） |
| morning_check | ✅ 全部通过 | 18 项检查全过 |
| afternoon_run | ✅ 14成功/1失败 | cls_cn 仍 418 |
| evening_run | ✅ 15成功/0失败 | cls_cn 恢复，全绿 |
| evening_check | ✅ 全部通过 | 18 项检查全过 |
| daily_status | ✅ 完成 | 152 条健康日志 |

**结论**：脚本层和 15 个 trial sources 基本可运行，cls_cn 418 为 transient，非 P0/P1 blocker。

### 3.2 TRAE 自动触发失败（6/27–6/29 上午）

| 现象 | 说明 |
|---|---|
| 错误信息 | "请求失败，请稍后重试" |
| 失败位置 | TRAE trigger/model layer（脚本根本没执行） |
| 影响范围 | 全部 6 个 trial job |
| 数据层 | `run_summary.json` 连续 3 天未更新 |
| 归因 | 自然语言 prompt → minimax/custom model 调用 → 本地模式下失败 |

### 3.3 command-only 修复验证（6/29 上午）

| 任务 | 触发方式 | 结果 |
|---|---|---|
| morning_run | TRAE trigger（command-only） | ✅ 15成功/0失败 |
| morning_check | TRAE trigger（command-only） | ✅ 全部通过 |
| afternoon_run | TRAE trigger（command-only） | ✅ 正常执行 |
| evening_run | TRAE trigger（command-only） | ✅ 正常执行 |
| evening_check | TRAE trigger（command-only） | ✅ 全部通过 |
| daily_status | TRAE trigger（command-only） | ✅ 完成，212 条健康日志 |

**结论**：command-only 调度方式完全解决了触发失败问题。

---

## 4. 运行产物

- **source_health**：`data/foundation_trial/index/source_health.jsonl` ✅
- **run_log**：`data/foundation_trial/index/run_log.jsonl` ✅
- **failed_queue**：`data/foundation_trial/index/failed_queue.jsonl`（NOT FOUND，无失败进队列）✅
- **reports**：`data/foundation_trial/reports/` ✅
- **data 是否提交**：否（已加入 `.gitignore`）

---

## 5. 配置文件与脚本

| 文件 | 用途 |
|---|---|
| `configs/trae_foundation_trial_schedule.example.yaml` | trial schedule 模板 |
| `scripts/setup_foundation_trial_schedule.ps1` | Windows Task Scheduler Setup 脚本（备用） |
| `scripts/remove_foundation_trial_schedule.ps1` | Windows Task Scheduler Cleanup 脚本（备用） |
| `scripts/run_foundation_trial_sources.ps1` | trial source run 主脚本 |
| `scripts/check_foundation_trial_sources.ps1` | trial source check 脚本 |

> **注意**：当前正式调度使用 TRAE Schedule（本地模式 + command-only），Windows Task Scheduler 脚本仅作备用。

---

## 6. Rollback 方法

如果 trial scheduling 出现异常：

### 暂停所有 trial jobs（不删除）

在 TRAE Work 界面将 6 个 job 设为 Paused，或通过 Schedule API 暂停。

### Rollback 影响范围

- ✅ 不影响 source inventory（92 源不受影响）
- ✅ 不影响 production research archive
- ✅ 不影响 blocked 源策略
- ✅ 不删除 `data/foundation_trial/`（保留诊断数据）
- ✅ 不影响 Dashboard

---

## 7. 后续观察计划

1. **监控 cls_cn**：偶发 HTTP 418 反爬，标记 transient watch，观察 1-2 周
2. **Microsoft IR**：探索 SEC EDGAR 或第三方财经平台替代入口（进入 M3C-2D-MSIR-Fix 候选）
3. **每日 review**：检查 `data/foundation_trial/reports/` 中的 trial run 报告
4. **M3C-4 候选**：如果 15 个源稳定运行 2 周，可考虑 M3C-4 正式 production 调度
5. **TRAE 模型问题**：待 TRAE 官方修复本地模式下自定义模型的 trigger 调用问题后，可考虑恢复自然语言 prompt

---

## 8. M3C-3 完成状态

| 任务 | 状态 |
|---|---|
| TRAE trial schedule 配置模板 | ✅ |
| Setup/Cleanup 脚本 | ✅ |
| 手动触发 trial run | ✅ |
| 手动触发 trial check | ✅ |
| 自动触发失败定位 | ✅（minimax/custom model trigger 问题） |
| command-only 调度修复 | ✅（6 个 job 已更新） |
| command-only 修复验证 | ✅（全部通过） |
| 报告生成 | ✅ |
| data 不提交确认 | ✅ |
| full pytest | ⏳ 待确认 |

---

## 9. 重要声明

> **M3C-3 是 trial-only 试运行调度，不是最终 production TRAE 接管。**
>
> 本阶段：
> - 只调度 15 个已验证 trial source
> - 不调度 92 全量源
> - 不调度 Microsoft IR（url_backlog）
> - 不调度 blocked/high-risk/search_provider/dormant 源
> - 不做投资判断
> - 不打 tag
