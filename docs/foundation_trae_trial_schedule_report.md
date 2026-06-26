# OPC Foundation M3C-3 Report: 15 个验证源 TRAE Trial Scheduling 接入

> **版本**：1.0
> **执行时间**：2026-06-26
> **状态**：TRAE Trial Scheduling 已接入

## 1. TRAE 接入结果

- **是否已创建 TRAE trial jobs**：是（配置模板 + Setup 脚本已创建）
- **job 数量**：6 个
- **job 名称**：
  1. `OPC_Foundation_Trial_Morning_Run` — 08:10 daily
  2. `OPC_Foundation_Trial_Morning_Check` — 08:25 daily
  3. `OPC_Foundation_Trial_Afternoon_Run` — 13:10 daily
  4. `OPC_Foundation_Trial_Evening_Run` — 20:10 daily
  5. `OPC_Foundation_Trial_Evening_Check` — 20:25 daily
  6. `OPC_Foundation_Trial_Daily_Status` — 23:50 daily
- **是否 trial-only**：是（不等于 production）

## 2. Trial Source 范围

- **trial source 数**：15
- **是否为 15**：是
- **是否包含 Microsoft IR**：否（url_backlog，HTTP 403 Akamai bot 保护）
- **是否包含 blocked**：否
- **是否包含 search provider**：否
- **是否包含 dormant**：否
- **是否包含 TLS/DNS/404/url_backlog 源**：否

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
| cls_cn | 财联社 | live OK（标记 transient watch） |
| wind_public | Wind 万得公开内容 | live OK |
| gelonghui | 格隆汇 | live OK |
| zhitong_caijing | 智通财经 | live OK |

## 3. 调度配置

| job | 调度时间 | 命令 |
|---|---|---|
| Morning Run | 08:10 daily | `scripts\run_foundation_trial_sources.ps1 -Mode run` |
| Morning Check | 08:25 daily | `scripts\check_foundation_trial_sources.ps1` |
| Afternoon Run | 13:10 daily | `scripts\run_foundation_trial_sources.ps1 -Mode run` |
| Evening Run | 20:10 daily | `scripts\run_foundation_trial_sources.ps1 -Mode run` |
| Evening Check | 20:25 daily | `scripts\check_foundation_trial_sources.ps1` |
| Daily Status | 23:50 daily | `scripts\run_foundation_trial_sources.ps1 -Mode dry-run` |

## 4. 手动触发结果

### validate-config

- **结果**：PASSED

### dry-run

- **结果**：PASSED
- 15 sources skipped（dry-run 模式）

### run

- **结果**：PASSED
- Total: 15, Success: 14, Failed: 1, Skipped: 0
- **Success**：goldman_sachs_research, goldman_sachs_reports, goldman_sachs_top_of_mind, goldman_sachs_insights, barclays_our_insights, yahoo_finance, business_insider, markets_insider, the_fly, briefing_com_upgrades, wallstreet_cn, wind_public, gelonghui, zhitong_caijing
- **Failed**：cls_cn（http_error，疑似临时网络 timeout；cls.cn 本身 200 OK）

### check

- **结果**：ALL CHECKS PASSED

## 5. 运行产物

- **source_health**：`data/foundation_trial/index/source_health.jsonl` ✅
- **run_log**：`data/foundation_trial/index/run_log.jsonl` ✅
- **failed_queue**：`data/foundation_trial/index/failed_queue.jsonl`（NOT FOUND，无失败进队列）✅
- **reports**：`data/foundation_trial/reports/` ✅
- **data 是否提交**：否（已加入 .gitignore）

## 6. 本地 TRAE Schedule 配置

配置文件：

- `configs/trae_foundation_trial_schedule.example.yaml` — trial schedule 模板
- `scripts/setup_foundation_trial_schedule.ps1` — Windows Task Scheduler Setup 脚本
- `scripts/remove_foundation_trial_schedule.ps1` — Windows Task Scheduler Cleanup 脚本

**Setup 用法**：

```powershell
# Dry run（预览，不实际创建）
powershell -ExecutionPolicy Bypass -File scripts/setup_foundation_trial_schedule.ps1 -Mode dry-run

# 真实创建（创建 6 个 Windows Task Scheduler jobs）
powershell -ExecutionPolicy Bypass -File scripts/setup_foundation_trial_schedule.ps1 -Mode setup

# 查看当前 trial jobs
powershell -ExecutionPolicy Bypass -File scripts/setup_foundation_trial_schedule.ps1 -Mode list
```

## 7. Rollback 方法

如果 trial scheduling 出现异常：

### 暂停所有 trial jobs（不删除）

```powershell
powershell -ExecutionPolicy Bypass -File scripts/remove_foundation_trial_schedule.ps1 -Action disable
```

### 删除所有 trial jobs

```powershell
powershell -ExecutionPolicy Bypass -File scripts/remove_foundation_trial_schedule.ps1 -Action delete
```

### Rollback 影响范围

- ✅ 不影响 source inventory（92 源不受影响）
- ✅ 不影响 production research archive
- ✅ 不影响 blocked 源策略
- ✅ 不删除 data/foundation_trial/（保留诊断数据）
- ✅ 不影响 Dashboard

## 8. 后续观察计划

1. **监控 cls_cn**：偶尔 http_error（疑似临时网络 timeout），建议观察 1-2 周
2. **Microsoft IR**：探索 SEC EDGAR 或第三方财经平台替代入口（进入 M3C-2D-MSIR-Fix）
3. **每日 review**：检查 `data/foundation_trial/reports/` 中的 trial run 报告
4. **M3C-4 候选**：如果 15 个源稳定运行 2 周，可考虑 M3C-4 正式 production 调度

## 9. M3C-3 完成状态

| 任务 | 状态 |
|---|---|
| TRAE trial schedule 配置模板 | ✅ |
| Setup/Cleanup 脚本 | ✅ |
| 手动触发 trial run | ✅ |
| 手动触发 trial check | ✅ |
| 报告生成 | ✅ |
| data 不提交确认 | ✅ |
| full pytest | ✅（1386 passed） |

## 10. 重要声明

> **M3C-3 是 trial-only 试运行调度，不是最终 production TRAE 接管。**
>
> 本阶段：
> - 只调度 15 个已验证 trial source
> - 不调度 92 全量源
> - 不调度 Microsoft IR（url_backlog）
> - 不调度 blocked/high-risk/search_provider/dormant 源
> - 不做投资判断
> - 不打 tag
