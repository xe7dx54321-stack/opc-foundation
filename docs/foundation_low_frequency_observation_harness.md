# Foundation Low-frequency Observation Harness

## 1. 概述

低频源 observation harness 是 M3C-6C.1 引入的连续观察机制，用于验证 `merck_ir` 等 low-frequency candidate 在 7 天观察期内是否稳定可用。该 harness 位于 low-frequency pipeline v1（M3C-6C）与真实 TRAE scheduled task 之间，是后续人工批准创建 TRAE 任务的必要前置 gate。

```
M3C-6C pipeline v1  ->  M3C-6C.1 observation harness  ->  人工批准  ->  TRAE scheduled task
```

## 2. Observation 状态机

```
pending -> active -> completed_7d
                   | partial_observation
                   | failed
```

| 状态 | 含义 | 入口条件 |
|---|---|---|
| `pending` | 未开始观察 | 初始状态，runtime data 不存在或为空 |
| `active` | 观察进行中，但尚未达到 7 天 | 至少 1 次 run，但 `observed_days < 7` |
| `completed_7d` | 7 天观察全部成功 | `observed_days >= 7` 且 `successful_days >= 7`，无 blocking error |
| `partial_observation` | 观察存在但不完整 | `observed_days > 0` 但未达 7 天，或某天缺 run，或某次 run `valid_item_count < 3` |
| `failed` | 观察失败 | 出现 login/paywall/captcha/anti-bot 阻断，或连续 2 次 navigation-only run |

## 3. Daily Run 记录结构

每个 observation run 由 `LowFrequencyObservationRun` 表示，记录以下字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `source_id` | str | 固定为 `merck_ir` |
| `run_id` | str | 唯一 run 标识（基于时间戳） |
| `run_date` | str | YYYY-MM-DD |
| `run_started_at` | str | ISO UTC |
| `run_finished_at` | str | ISO UTC |
| `mode` | str | `dry_run` / `run_once` |
| `valid_item_count` | int | 真实 IR/events/presentations item 数 |
| `dated_item_count` | int | 含 date_text 的 item 数 |
| `missing_date_count` | int | 缺 date_text 的 item 数 |
| `navigation_rejected_count` | int | 被识别为导航页而被拒绝的 item 数 |
| `timestamp_confidence_distribution` | dict | `{"HIGH": n, "MEDIUM": n, "LOW": n, "NONE": n}` |
| `sample_items` | list[dict] | 最多 5 条，含 title/url/date_text/discovered_at/timestamp_confidence |
| `risk_flags` | list[str] | `login_required`/`paywall_observed`/`captcha_or_antibot_observed`/`navigation_only_run` |
| `status` | str | `success`/`partial`/`failed`/`no_run`/`pending` |
| `notes` | str | 人工备注，不含敏感数据 |

## 4. Day Summary 结构

每个观察日由 `LowFrequencyObservationDay` 表示：

| 字段 | 类型 | 说明 |
|---|---|---|
| `date` | str | YYYY-MM-DD |
| `source_id` | str | `merck_ir` |
| `run_count` | int | 当天 run 次数 |
| `best_valid_item_count` | int | 当天最高 valid_item_count |
| `best_dated_item_count` | int | 当天最高 dated_item_count |
| `had_successful_run` | bool | 当天是否有 `valid_item_count >= 3` 的 run |
| `had_navigation_regression` | bool | 当天是否出现 navigation-only run |
| `had_blocking_error` | bool | 当天是否出现 login/paywall/captcha/anti-bot |
| `status` | str | `success`/`partial`/`failed`/`no_run` |

### Day 状态判定

```
if had_blocking_error:        status = "failed"
elif had_successful_run:      status = "success"
else:                         status = "partial"
```

## 5. 7-Day Summary 结构

7 天汇总由 `LowFrequencyObservationSummary` 表示：

| 字段 | 类型 | 说明 |
|---|---|---|
| `source_id` | str | `merck_ir` |
| `target_days` | int | 7 |
| `observed_days` | int | 实际观察天数 |
| `successful_days` | int | status=success 的天数 |
| `partial_days` | int | status=partial 的天数 |
| `failed_days` | int | status=failed 的天数 |
| `total_runs` | int | 总 run 次数 |
| `min_valid_items_per_run` | int | 全部 run 中最低 valid_item_count |
| `max_valid_items_per_run` | int | 全部 run 中最高 valid_item_count |
| `timestamp_confidence_distribution` | dict | 7 天累计 timestamp_confidence 分布 |
| `navigation_regression_count` | int | navigation-only run 次数 |
| `blocking_error_count` | int | blocking error 出现天数 |
| `final_observation_status` | str | `completed_7d`/`partial_observation`/`failed`/`pending`/`active` |
| `recommended_next_action` | str | `propose_trae_low_frequency_task`/`continue_observation`/`investigate_blocking_errors`/`start_observation` |
| `days` | list[LowFrequencyObservationDay] | 每天的 day summary |

## 6. Timestamp Confidence 策略

```
if date_text present:
    timestamp_confidence = MEDIUM
elif discovered_at available:
    timestamp_confidence = LOW   # merck_ir 当前阶段
else:
    timestamp_confidence = NONE
```

| 级别 | 来源 | 当前 merck_ir |
|---|---|---|
| HIGH | 结构化数据（JSON-LD / `<time>` 标签） | 0 |
| MEDIUM | 有日期文本但格式非标准 | 0 |
| LOW | discovered_at fallback | 15（全部 item） |
| NONE | 无任何时间信息 | 0 |

**关键约束**：`date_text` 缺失时必须记录 `timestamp_confidence=LOW`，否则 `validate_observation_run` 返回错误。

## 7. Navigation Regression 检测

当某次 run 满足以下条件时，标记为 `navigation_only_run`：

```
valid_item_count == 0
AND
navigation_rejected_count > 0
```

失败标准（`failed` 状态）：
- 连续 2 次 navigation-only run
- 或 `MAX_CONSECUTIVE_NAVIGATION_ONLY_RUNS = 2`

## 8. Blocking Error 检测

下列 risk_flags 任一出现即视为 blocking error：

| risk_flag | 触发条件 | 后果 |
|---|---|---|
| `login_required` | 检测到登录提示 | `final_observation_status = failed` |
| `paywall_observed` | 检测到付费墙 | `final_observation_status = failed` |
| `captcha_or_antibot_observed` | 检测到验证码/反爬 | `final_observation_status = failed` |

一旦 blocking error 出现，`final_observation_status` 立即转为 `failed`，`recommended_next_action = investigate_blocking_errors`。

## 9. Runtime Data 策略

### 9.1 路径

```
data/foundation_low_frequency_observation/
  ├── runs/
  │   ├── merck_ir_2026-07-05T03:11:22Z.json
  │   ├── merck_ir_2026-07-06T03:12:01Z.json
  │   └── ...
  └── summary/
      └── merck_ir_latest_summary.json
```

### 9.2 gitignore

`.gitignore` 必须包含：

```gitignore
data/foundation_low_frequency_observation/
```

### 9.3 不得提交的内容

- runtime data（任何 JSON / HTML / 截图）
- proxy URL / cookie / token / secret
- raw HTML dump
- browser screenshots
- 真实 TRAE local config

### 9.4 验证方式

```bash
git status --ignored --short data/foundation_low_frequency_observation
# 应显示 !! 前缀，表示被 ignored
```

## 10. 与 Low-frequency Runner 的关系

observation harness 复用 M3C-6C 的 low-frequency runner：

```
scripts/run_foundation_low_frequency_observation.py
  -> 调用 src/opc_foundation/source_inventory/low_frequency_sources.py
  -> 复用 LowFrequencyRunResult（含 valid_item_count, dated_item_count, timestamp_confidence）
  -> 包装为 LowFrequencyObservationRun
  -> 写入 data/foundation_low_frequency_observation/runs/
```

observation harness 在此基础上增加：
- daily status 聚合
- 7-day summary
- navigation regression 检测
- blocking error 检测
- TRAE task proposal gate

## 11. 与 TRAE Task Proposal 的关系

observation harness 是 TRAE low-frequency task proposal 的前置 gate：

```
Gate 1: M3C-6C pipeline v1 完成
Gate 2: M3C-6C.1 7-day observation harness 完成（本阶段）
Gate 3: 人工审核 observation 结果（completed_7d 必要条件）
Gate 4: 人工创建 TRAE scheduled task（手动操作）
Gate 5: 纳入更多低频候选源
```

只有当 `final_observation_status = completed_7d` 时，`recommended_next_action = propose_trae_low_frequency_task` 才允许进入下一阶段。

本阶段（M3C-6C.1）：
- `create_trae_task_now = false`
- `manual_approval_required_before_scheduling = true`
- 不创建真实 TRAE scheduled task

## 12. 后续人工批准 Gate

人工批准创建真实 TRAE low-frequency scheduled task 的条件：

### 12.1 必要条件（全部满足）

- [ ] `final_observation_status = completed_7d`
- [ ] `observed_days >= 7`
- [ ] `successful_days >= 7`
- [ ] `blocking_error_count = 0`
- [ ] `navigation_regression_count = 0`
- [ ] `min_valid_items_per_run >= 3`
- [ ] `timestamp_confidence_distribution.LOW > 0`（merck_ir 当前阶段）
- [ ] runtime data 全部 gitignored
- [ ] trial_v2 allowlist 未变化
- [ ] production_enabled = false

### 12.2 人工审核步骤

1. 用户人工检查 7-day observation summary
2. 用户人工检查 sample items 是否为真实 IR/events/presentations
3. 用户人工确认无 navigation regression
4. 用户人工确认无 blocking error
5. 用户人工在本地 TRAE 创建 scheduled task（command-only）
6. 真实启用只发生在本地，不提交 local config

### 12.3 建议命令（人工批准后）

```bash
# Run observation once
python scripts/run_foundation_low_frequency_observation.py --source merck_ir --run-once

# Summarize
python scripts/run_foundation_low_frequency_observation.py --source merck_ir --summarize

# Check boundary compliance
python scripts/check_foundation_low_frequency_observation.py
```

### 12.4 建议频率

```
初始 observation: 每日 1 次，连续 7 天
正式 low-frequency: weekly 或 daily low-priority，待 7 天结果后决定
```

## 13. 边界确认

| 检查项 | 结果 |
|---|---|
| 是否修改 TRAE scheduling | 否 |
| 是否修改 TRAE local config | 否 |
| 是否创建永久自动化任务 | 否 |
| 是否修改 trial_v2 allowlist | 否 |
| 是否配置 production | 否 |
| 是否提交 data/local/secrets | 否 |
| 是否提交 proxy URL/cookie/token | 否 |
| 是否引入 Playwright/Selenium | 否 |
| 是否恢复已删除 Dashboard 页面 | 否 |
| 是否打 tag | 否 |

## 14. 相关文件

### 14.1 模型

- `src/opc_foundation/source_inventory/low_frequency_observation.py`
  - `LowFrequencyObservationRun`
  - `LowFrequencyObservationDay`
  - `LowFrequencyObservationSummary`
  - `LowFrequencyObservationDecision`
  - `validate_observation_run`
  - `validate_observation_summary`
  - `compute_day_status`
  - `compute_observation_summary`

### 14.2 配置

- `configs/foundation_m3c_6c1_low_frequency_observation.example.yaml`

### 14.3 脚本

- `scripts/run_foundation_low_frequency_observation.py`（dry-run / run-once / summarize）
- `scripts/check_foundation_low_frequency_observation.py`（boundary checker）

### 14.4 测试

- `tests/source_inventory/test_low_frequency_observation.py`（48 tests）
- `tests/scripts/test_foundation_low_frequency_observation.py`（25 tests）

### 14.5 相关文档

- [M3C-6C.1 Observation Report](foundation_m3c_6c1_merck_ir_low_frequency_observation_report.md)
- [TRAE Low-frequency Observation Proposal](foundation_m3c_6c1_trae_low_frequency_observation_proposal.md)
- [Low-frequency Source Pipeline](foundation_low_frequency_source_pipeline.md)
- [TRAE Low-frequency Task Proposal](foundation_low_frequency_trae_task_proposal.md)
