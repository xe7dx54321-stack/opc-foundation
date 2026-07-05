# M3C-6C.1 TRAE Low-frequency Observation Proposal

## 1. 为什么 M3C-6C.1 只做 observation harness

M3C-6C 建立了 low-frequency pipeline v1，`merck_ir` 作为第一个样板源（15 valid items, 0 dated, weekly, timestamp_confidence=LOW）。但单次 run 成功不足以证明稳定性，可能出现：

- 某些时段抓到的是导航页而非 IR/events/presentations 内容
- 某些时段 valid_item_count 退化为 < 3
- 某些时段出现 login/paywall/captcha/anti-bot 阻断
- date_text 全部缺失但未正确记录 timestamp_confidence

M3C-6C.1 通过 7 天连续 observation harness 在创建真实 TRAE scheduled task 之前回答上述问题。

## 2. 为什么本阶段不创建真实 TRAE scheduled task

### 2.1 边界约束

- `production_enabled: false`
- `create_trae_task_now: false`
- `manual_approval_required_before_scheduling: true`
- 不修改 TRAE scheduling 时间
- 不修改 TRAE scheduling 命令
- 不修改 TRAE local config
- 不创建永久自动化任务

### 2.2 原因

1. **稳定性未验证**：单次成功不等于连续 7 天稳定
2. **需要观察退化**：navigation regression 需要多次 run 才能识别
3. **需要 blocking error 检测**：login/paywall/captcha 可能在某些时段出现
4. **需要 timestamp confidence 验证**：date_text 缺失时 timestamp_confidence=LOW 是否稳定记录
5. **production 未启用**：低频任务仍为 proposal only

## 3. 人工批准后建议命令

### 3.1 Observation 运行（人工触发）

```bash
# Dry-run（不写 runtime data）
python scripts/run_foundation_low_frequency_observation.py --source merck_ir --dry-run

# Run once（写 runtime data，gitignored）
python scripts/run_foundation_low_frequency_observation.py --source merck_ir --run-once

# Summarize（读取 runtime data 并输出 7-day summary）
python scripts/run_foundation_low_frequency_observation.py --source merck_ir --summarize
```

### 3.2 Boundary check（每次运行后）

```bash
python scripts/check_foundation_low_frequency_observation.py
```

### 3.3 真实 TRAE scheduled task（人工批准后）

人工审核通过后，用户在本地 TRAE 任务管理中创建定时任务：

```powershell
# Command-only（不要填自然语言 prompt）
powershell -ExecutionPolicy Bypass -File scripts/run_foundation_low_frequency_observation.py --source merck_ir --run-once
```

注意：
- 真实启用只发生在本地 TRAE
- 不提交 local config 到 Git
- 命令必须是 command-only，不允许自然语言 prompt

## 4. 建议频率

### 4.1 初始 observation 阶段

```
frequency: daily
duration: 7 days
minimum_runs_per_day: 1
```

每日执行 1 次 `--run-once`，连续 7 天。

### 4.2 正式 low-frequency 阶段（待 7 天结果后决定）

| 选项 | 频率 | 适用场景 |
|---|---|---|
| weekly | 每周 1 次 | merck_ir IR 事件更新频率低，dated=0 仍存在 |
| daily low-priority | 每日 1 次（非高峰时段） | 若 7 天观察中 valid_item_count 波动较大，需更频繁监控 |

正式频率由 7 天 observation 结果决定，本阶段不预先承诺。

## 5. 与 trial_v2 每日三批任务的隔离方式

### 5.1 任务隔离

| 维度 | trial_v2 高频任务 | low-frequency observation |
|---|---|---|
| 源数 | 9 | 1 (merck_ir) |
| 频率 | 每日 3 批 | 每日 1 次（observation 阶段） |
| 允许清单 | trial_v2 allowlist（9 源） | low_frequency_sources（仅 merck_ir） |
| runtime data | `data/foundation_trial_v2/` | `data/foundation_low_frequency_observation/` |
| script | `scripts/run_foundation_trial_v2_content_ready.ps1` | `scripts/run_foundation_low_frequency_observation.py` |
| check script | `scripts/check_foundation_trial_v2_content_ready.ps1` | `scripts/check_foundation_low_frequency_observation.py` |
| production_enabled | false | false |

### 5.2 不影响 trial_v2 的保证

- 不修改 trial_v2 allowlist（仍为 9 源）
- 不修改 trial_v2 scheduling 时间
- 不修改 trial_v2 scheduling 命令
- 不修改 trial_v2 local config
- 不修改 trial_v1（15 源）

## 6. Runtime data 路径

```
data/foundation_low_frequency_observation/
  ├── runs/
  │   └── merck_ir_<timestamp>.json
  └── summary/
      └── merck_ir_latest_summary.json
```

`.gitignore` 必须包含：

```gitignore
data/foundation_low_frequency_observation/
```

## 7. Check 命令

```bash
python scripts/check_foundation_low_frequency_observation.py
```

### 7.1 Check 项

| 检查项 | 期望 |
|---|---|
| config production_enabled | false |
| creates_permanent_automation | false |
| affects_trial_v2_allowlist | false |
| affects_trae_scheduling | false |
| 当前 only merck_ir | true |
| trial_v2_allowlist_allowed_now | false |
| low_frequency_allowed_now | true |
| runtime data gitignored | true |
| timestamp_confidence 缺失时 | 不得 PASS |
| date_text 缺失时 | 必须 timestamp_confidence=LOW |
| report 不包含 cookie/token/proxy URL/secret | true |
| observation_status 合法 | true |
| 不引入 Playwright/Selenium | true |

### 7.2 退出码

- 0: ALL CHECKS PASSED
- 非 0: 至少一项检查未通过

## 8. 7 天 observation 成功标准

### 8.1 completed_7d（全部满足）

- 至少 7 个自然日有 observation run 记录
- 每个 observation day 至少 1 次 merck_ir run
- 每次 run `valid_item_count >= 3`
- 每次 run 的 sample items 均不是导航页
- `timestamp_confidence` 可以为 LOW，但必须明确记录
- runtime data 均未进入 git tracking
- failed_queue 或 error_count 无 blocking
- trial_v2 allowlist 未变化
- production_enabled=false

### 8.2 partial_observation（出现任一）

- observation 天数不足 7 天
- 某天缺少 run
- 某次 run `valid_item_count < 3`
- date_text 全部缺失但未记录 timestamp_confidence
- 证据不足

### 8.3 failed（出现任一）

- 连续 2 次抓到导航页
- 连续 2 次 `valid_item_count = 0`
- 出现 login / paywall / captcha / anti-bot 阻断
- runtime data 被 git 跟踪
- 误修改 trial_v2 allowlist
- 误创建 production / permanent TRAE task

## 9. 失败 / 回滚标准

### 9.1 失败处理

一旦 `final_observation_status = failed`：

1. 不再继续 observation run
2. 记录失败原因到 `risk_flags`
3. `recommended_next_action = investigate_blocking_errors`
4. 人工调查阻塞源（login/paywall/captcha/anti-bot）
5. 修复后重新开始 7 天 observation

### 9.2 回滚处理

如果误修改 trial_v2 allowlist 或误创建 production task：

1. 立即停止所有 observation run
2. `git checkout -- <modified files>` 恢复
3. 人工核实 trial_v2 allowlist 仍为 9 源
4. 人工核实 production_enabled = false
5. 记录事故到 notes
6. 修复后重新开始 7 天 observation

## 10. production_enabled

```
production_enabled: false
```

本阶段不得配置 production。低频 observation 仍为 proposal only，runtime data 不提交。

## 11. 当前 observation status（M3C-6C.1 dry-run / run-once 后）

| 字段 | 值 |
|---|---|
| source_id | merck_ir |
| target_days | 7 |
| observed_days | 1 |
| successful_days | 1 |
| partial_days | 0 |
| failed_days | 0 |
| total_runs | 1 |
| min_valid_items_per_run | 15 |
| max_valid_items_per_run | 15 |
| timestamp_confidence_distribution | `{"HIGH": 0, "MEDIUM": 0, "LOW": 15, "NONE": 0}` |
| navigation_regression_count | 0 |
| blocking_error_count | 0 |
| final_observation_status | partial_observation |
| recommended_next_action | continue_observation |
| completed_7d | false |
| missing_to_complete | 6 more days of observation |

## 12. 不创建真实 TRAE scheduled task（harness 阶段）

本阶段（harness 建立）：
- `create_trae_task_now: false`
- `manual_approval_required_before_scheduling: true`
- 不在 TRAE 中创建任何定时任务
- 不修改 TRAE local config
- 不修改 TRAE scheduling 时间
- 不修改 TRAE scheduling 命令

## 12a. Observation Start（2026-07-05，M3C-6C.1 merge 后）

M3C-6C.1 harness 合并到 master（merge commit: 45438b4）后，进入 observation start 阶段：

### 12a.1 Baseline

```
target_days = 7
already_observed_days = 1
remaining_days = 6
expected_final_status_after_completion = completed_7d
```

### 12a.2 本地 TRAE command-only observation task

在本地 TRAE 中创建 command-only observation task（不提交 TRAE local config）：

- **task name:** `foundation_low_frequency_merck_ir_observation_daily`
- **command (command-only):**
  ```bash
  cd "/Users/apple/Documents/一人公司OPC/opc-foundation" && \
  python3 scripts/run_foundation_low_frequency_observation.py --source merck_ir --run-once && \
  python3 scripts/check_foundation_low_frequency_observation.py
  ```
- **frequency:** daily 1 次
- **count:** 6 次（补齐到 7 天）
- **suggested_time:** 10:30 本地时间
- **is_production:** false
- **stop_condition:** 第 6 次运行后人工关闭，或由 M3C-6C.2 close 阶段处理

### 12a.3 边界

- 不修改 trial_v2 allowlist（仍 9 源）
- 不修改 trial_v2 scheduling
- 不配置 production
- 不提交 TRAE local config
- 不提交 data/local/secrets

详细记录见 [M3C-6C.1 Observation Start Report](foundation_m3c_6c1_observation_start_report.md)。

## 13. 边界确认

| 检查项 | 结果 |
|---|---|
| 是否修改 TRAE scheduling | 否 |
| 是否修改 TRAE local config | 否 |
| 是否创建永久自动化任务 | 否（本地 command-only observation task，非永久，6 次后关闭） |
| 是否修改 trial_v2 allowlist | 否 |
| 是否配置 production | 否 |
| 是否提交 data/local/secrets | 否 |
| 是否提交 proxy URL/cookie/token | 否 |
| 是否引入 Playwright/Selenium | 否 |
| 是否恢复已删除 Dashboard 页面 | 否 |
| 是否打 tag | 否 |

## 14. 相关文档

- [M3C-6C.1 Observation Start Report](foundation_m3c_6c1_observation_start_report.md)
- [Low-frequency Observation Harness](foundation_low_frequency_observation_harness.md)
- [M3C-6C.1 Observation Report](foundation_m3c_6c1_merck_ir_low_frequency_observation_report.md)
- [Low-frequency Source Pipeline](foundation_low_frequency_source_pipeline.md)
- [TRAE Low-frequency Task Proposal](foundation_low_frequency_trae_task_proposal.md)
- [TRAE Operations](foundation_trae_operations.md)
