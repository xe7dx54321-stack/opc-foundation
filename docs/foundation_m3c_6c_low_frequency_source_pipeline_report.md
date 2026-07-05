# OPC Foundation M3C-6C Low-frequency Source Pipeline Report

## 1. 执行前状态

- **master path:** `/Users/apple/Documents/一人公司OPC/opc-foundation`
- **starting master commit:** 1df34e8 (after 6F.1 merge)
- **6F.1 merge commit:** 1df34e8
- **6C branch:** feature/m3c-6c-low-frequency-source-pipeline
- **git status:** clean
- **trial_v2 source_count:** 9
- **production_enabled:** false

## 2. 为什么建立 low-frequency pipeline

当前 trial_v2 high-frequency pipeline 有 9 个源，每日 3 批，要求稳定 dated items。

M3C-6F.1 发现 merck_ir 有真实 IR 内容（15 valid items）但无法从列表页 HTML 提取日期（dated=0）。merck_ir 不满足 trial_v2 high-frequency 条件，但也不应被放弃——它是高价值 IR 源，只是更新频率低、日期提取需要更复杂的方式。

因此建立第二条 source pipeline：

```
trial_v2_high_frequency: 每日 3 批，当前 9 源
low_frequency_sources: 每日 1 次 / 每周若干次 / 事件型观察
```

## 3. 为什么 merck_ir 是第一个样板源

1. **M3C-5B1 曾达到 content_ready**（score 90）
2. **M3C-6F.1 专门 IR 提取验证**：15 个真实 IR items（财报电话会议、医疗健康会议）
3. **无 login/paywall/captcha 阻断**
4. **dated=0 但有 discovered_at fallback**：timestamp_confidence=LOW
5. **更新频率低**：IR 事件不是每日发生，适合 weekly 观察

## 4. merck_ir 的 6F.1 证据摘要

| 指标 | 值 |
|---|---|
| HTTP status | 200 |
| valid_item_count | 15 |
| dated_item_count | 0 |
| rejected_navigation_count | 0 |
| 样本内容 | Q3/Q2/Q1 2026 Earnings Call, Goldman Sachs Conference, Jefferies Conference |
| login_required | false |
| paywall_observed | false |
| captcha_or_antibot_observed | false |

## 5. low-frequency 与 high-frequency 的边界

| 维度 | trial_v2 high-frequency | low-frequency |
|---|---|---|
| 频率 | 每日 3 批 | 每日 1 次 / 每周 |
| date_text 要求 | 必须 | 可选 |
| dated_item_count 要求 | >= 2 | 可为 0 |
| timestamp_confidence | HIGH/MEDIUM | LOW 可接受 |
| discovered_at fallback | 不需要 | 必须 |
| allowlist | trial_v2 allowlist | low_frequency_sources |
| 当前源数 | 9 | 1 (merck_ir) |

## 6. date_text 缺失时的处理策略

```
if date_text is empty:
    -> use discovered_at as fallback timestamp
    -> timestamp_confidence = LOW
    -> date_missing_reason = "date not extractable from listing page HTML"
    -> still valid for low-frequency pipeline
    -> NOT valid for trial_v2 high-frequency
```

## 7. Dry-run / Run-once 结果

| mode | status | valid_items | dated_items | missing_date_count | timestamp_confidence | notes |
|---|---|---:|---:|---:|---|---|
| dry-run | success | 15 | 0 | 15 | LOW | No runtime data written |
| run-once | success | 15 | 0 | 15 | LOW | Runtime data written to gitignored dir |

## 8. 样本 items

| title | url | date_text | discovered_at | timestamp_confidence |
|---|---|---|---|---|
| Q3 2026 Earnings Call | https://www.merck.com/events/q3-2026-earnings-call/ | - | 2026-07-05T03:06:57Z | LOW |
| Q2 2026 Earnings Call | https://www.merck.com/events/q2-2026-earnings-call/ | - | 2026-07-05T03:06:57Z | LOW |
| 47th Annual Goldman Sachs Global Healthcare Conference | https://www.merck.com/events/47th-annual-goldman-sachs-global-healthcare-conference/ | - | 2026-07-05T03:06:57Z | LOW |
| Jefferies Global Healthcare Conference | https://www.merck.com/events/jefferies-global-healthcare-conference/ | - | 2026-07-05T03:06:57Z | LOW |
| Q1 2026 Earnings Call | https://www.merck.com/events/q1-2026-earnings-call/ | - | 2026-07-05T03:06:57Z | LOW |

## 9. Check 结果

- **config check:** PASS
- **runtime data check:** PASS (gitignored)
- **production_enabled:** false
- **affects_trial_v2_allowlist:** false
- **affects_trae_scheduling:** false
- **creates_permanent_automation:** false

## 10. 是否修改 trial_v2 allowlist

否。trial_v2 allowlist 仍为 9 源。

## 11. 是否修改 TRAE scheduling

否。不创建真实 TRAE scheduled task。只生成 proposal 文档。

## 12. 是否配置 production

否。production_enabled = false。

## 13. 是否提交 data/local/secrets

否。runtime data 在 `data/foundation_low_frequency_sources/` 目录，已被 `.gitignore` 忽略。

## 14. 测试结果

- **tests/source_inventory:** 57 passed (model tests)
- **tests/scripts:** 31 passed (config + script boundary tests)
- **tests/dashboard:** all passed
- **full pytest:** (待运行)

## 15. 边界确认

- **是否修改 TRAE scheduling:** 否
- **是否修改 TRAE local config:** 否
- **是否创建永久自动化任务:** 否
- **是否修改 trial_v2 allowlist:** 否
- **是否配置 production:** 否
- **是否提交 data/local/secrets:** 否
- **是否提交 proxy URL:** 否
- **是否提交 cookie/token:** 否
- **是否提交 raw HTML:** 否
- **是否提交 screenshot:** 否
- **是否引入 Playwright/Selenium:** 否
- **是否恢复已删除 Dashboard 页面:** 否
- **是否打 tag:** 否
