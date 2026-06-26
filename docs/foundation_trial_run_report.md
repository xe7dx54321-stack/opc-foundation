# OPC Foundation M3C-2D-URLFix Trial Run Report

> **版本**：2.0
> **生成时间**：2026-06-26（最新：M3C-2D-URLFix URL 修复后重跑）
> **Trial 说明**：本报告为 M3C-2D-URLFix trial-only 试运行结果，**不代表最终 production TRAE 接管**。

## 1. 执行摘要

- **执行时间**：M3C-2D-URLFix 后重跑（2026-06-26）
- **Trial Source 总数**：15（原 16，移除 1 个）
- **Dry-run**：否
- **Proxy 启用**：否
- **Proxy 模式**：none

### 1.1 运行结果

| 状态 | 数量 |
|---|---|
| 总计 | 15 |
| Success | 14 |
| Empty | 0 |
| Failed | 1（疑似临时网络 timeout） |
| Skipped | 0 |

### 1.2 M3C-2D-URLFix 变更

| source_id | 原状态 | 修复动作 |
|---|---|---|
| goldman_sachs_research | HTTP 404 | 修复：feed_url 改为 `https://www.goldmansachs.com/insights` → 200 OK |
| goldman_sachs_reports | HTTP 404 | 修复：feed_url 改为 `https://www.goldmansachs.com/insights/reports` → 200 OK |
| microsoft_ir | HTTP 403（Akamai bot 保护） | 移出 trial，进入 url_backlog |

## 2. Source 状态明细

### success (14)

| source_id | source_name | candidates |
|---|---|---|
| goldman_sachs_research | Goldman Sachs Research | 1（修复后 success） |
| goldman_sachs_reports | Goldman Sachs Reports | 1（修复后 success） |
| goldman_sachs_top_of_mind | Goldman Sachs Top of Mind | 1 |
| goldman_sachs_insights | Goldman Sachs Insights | 1 |
| barclays_our_insights | Barclays Our Insights | 5 |
| yahoo_finance | Yahoo Finance | 5 |
| business_insider | Business Insider | 5 |
| markets_insider | Markets Insider | 5 |
| the_fly | The Fly | 3 |
| briefing_com_upgrades | Briefing.com Upgrades/Downgrades | 1 |
| wallstreet_cn | 华尔街见闻 | 5 |
| wind_public | Wind 万得公开内容 | 1 |
| gelonghui | 格隆汇 | 0 |
| zhitong_caijing | 智通财经 | 5 |

### url_error (1)

| source_id | source_name | 说明 |
|---|---|---|
| cls_cn | 财联社 | 疑似临时网络 timeout；单独 curl 验证 cls.cn 本身返回 200 OK |

## 3. 移出 Trial 的源

### microsoft_ir（url_backlog）

- **原因**：HTTP 403 Forbidden（Akamai bot 保护）
- **尝试的 URL**：`https://www.microsoft.com/investor`, `https://www.microsoft.com/en-us/Investor/earnings` 均返回 403
- **状态**：**still_403_move_to_backlog**
- **后续**：需探索替代公开入口或 connector

## 4. Trial 配置信息

- **Allowlist**：configs/foundation_trial_source_allowlist.example.yaml（15 个 trial source）
- **Trial Config**：configs/trae_foundation_trial_sources.example.yaml（15 个源，microsoft_ir 已注释掉）
- **输出目录**：data\foundation_trial

## 5. M3C-3 建议

- **可进入 TRAE trial scheduling 的源数**：15 个
- **暂缓源**：microsoft_ir（url_backlog，需 M3C-2D-MSIR-Fix 探索替代入口）
- **后续工作**：M3C-3 基于 15 个验证通过源配置正式 TRAE production 调度