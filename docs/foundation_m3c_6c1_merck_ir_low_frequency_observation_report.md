# OPC Foundation M3C-6C.1 Merck IR Low-frequency Observation Report

## 1. 执行前状态

- **master path:** `/Users/apple/Documents/一人公司OPC/opc-foundation`
- **starting master commit:** a5b7f06 (after 6C merge)
- **6C merge commit:** a5b7f06
- **6C.1 branch:** feature/m3c-6c1-merck-ir-low-frequency-observation
- **git status:** clean
- **trial_v2 source_count:** 9
- **production_enabled:** false

## 2. 为什么做 low-frequency observation

M3C-6C 建立了 low-frequency pipeline v1，merck_ir 作为第一个样板源（15 valid items, 0 dated, weekly）。但在创建真实 TRAE scheduled task 之前，需要验证 merck_ir 低频 runner 是否可以连续稳定运行。

M3C-6C.1 建立 7 天 observation harness，记录每日 run 结果，检测 navigation regression 和 blocking errors。

## 3. 为什么只观察 merck_ir

merck_ir 是唯一已完成低频样板验证的源。其他源（the_fly, yahoo_finance 等）仍在 backlog，不适合本阶段纳入。

## 4. merck_ir 的 M3C-6C 证据摘要

| 指标 | 值 |
|---|---|
| valid_item_count | 15 |
| dated_item_count | 0 |
| timestamp_confidence | LOW |
| recommended_frequency | weekly |
| low_frequency_allowed_now | true |

## 5. Observation Harness 设计

### 状态机

```
pending -> active -> completed_7d | partial_observation | failed
```

### Daily Run 记录

每个 run 记录：source_id, run_id, run_date, valid_item_count, dated_item_count, missing_date_count, navigation_rejected_count, timestamp_confidence_distribution, sample_items, status

### 7-Day Summary

汇总 7 天数据：observed_days, successful_days, partial_days, failed_days, total_runs, navigation_regression_count, blocking_error_count, final_observation_status

## 6. Dry-run / Run-once / Summarize 结果

| mode | status | valid_items | dated_items | missing_date_count | timestamp_confidence | runtime_written |
|---|---|---:|---:|---:|---|---|
| dry-run | success | 15 | 0 | 15 | LOW | no |
| run-once | success | 15 | 0 | 15 | LOW | yes (gitignored) |
| summarize | partial_observation | - | - | - | LOW | yes (gitignored) |

## 7. Observation Summary

- **target_days:** 7
- **observed_days:** 1
- **successful_days:** 1
- **partial_days:** 0
- **failed_days:** 0
- **total_runs:** 1
- **current_observation_status:** partial_observation
- **completed_7d:** false
- **missing_to_complete:** 6 more days of observation

## 8. 样本 items

| title | url | date_text | discovered_at | timestamp_confidence |
|---|---|---|---|---|
| Q3 2026 Earnings Call | https://www.merck.com/events/q3-2026-earnings-call/ | - | 2026-07-05T03:11:XXZ | LOW |
| Q2 2026 Earnings Call | https://www.merck.com/events/q2-2026-earnings-call/ | - | 2026-07-05T03:11:XXZ | LOW |
| 47th Annual Goldman Sachs Global Healthcare Conference | https://www.merck.com/events/47th-annual-goldman-sachs-global-healthcare-conference/ | - | 2026-07-05T03:11:XXZ | LOW |
| Jefferies Global Healthcare Conference | https://www.merck.com/events/jeffries-global-healthcare-conference/ | - | 2026-07-05T03:11:XXZ | LOW |
| Q1 2026 Earnings Call | https://www.merck.com/events/q1-2026-earnings-call/ | - | 2026-07-05T03:11:XXZ | LOW |

## 9. Check 结果

- **config check:** PASS
- **runtime data check:** PASS (gitignored)
- **production_enabled:** false
- **affects_trial_v2_allowlist:** false
- **affects_trae_scheduling:** false
- **creates_permanent_automation:** false

## 10. 是否创建真实 TRAE task

否。只生成 proposal 文档。需要完成 7 天 observation 后人工批准。

## 11. 是否修改 trial_v2 allowlist

否。trial_v2 allowlist 仍为 9 源。

## 12. 是否修改 TRAE scheduling

否。

## 13. 是否配置 production

否。

## 14. 是否提交 data/local/secrets

否。runtime data 在 `data/foundation_low_frequency_observation/` 目录，已被 `.gitignore` 忽略。

## 15. 测试结果

- **tests/source_inventory:** 48 passed (model tests)
- **tests/scripts:** 25 passed (config + script boundary tests)
- **tests/dashboard:** all passed
- **full pytest:** (待运行)
