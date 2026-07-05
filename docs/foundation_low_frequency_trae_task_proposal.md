# TRAE Low-frequency Task Proposal

## 1. 为什么需要 low-frequency TRAE task

当前 TRAE 有 4 个 trial_v2 高频任务（每日 3 批，9 源）。但有些源（如 merck_ir）更新频率低、日期提取困难，不适合高频调度，但仍有高内容价值。

低频任务可以：
- 每日或每周观察一次
- 接受 date_text 缺失（使用 discovered_at fallback）
- 不影响现有高频任务
- 为 future on-demand registry 铺路

## 2. 与 trial_v2 每日三批任务的区别

| 维度 | trial_v2 高频任务 | 低频任务 |
|---|---|---|
| 频率 | 每日 3 批 | 每周 1 次 |
| 源数 | 9 | 1 (merck_ir) |
| date_text 要求 | 必须 | 可选 |
| timestamp_confidence | HIGH/MEDIUM | LOW 可接受 |
| allowlist | trial_v2 allowlist | low_frequency_sources |
| production | false | false |

## 3. 初始源

```
source_id: merck_ir
source_layer: low_frequency_candidate
expected_value: high
prior_stage: M3C-6F.1
prior_valid_items: 15
prior_dated_items: 0
```

## 4. 建议频率

```
recommended_initial_frequency: weekly
```

理由：
- IR 事件（财报电话会议、投资者会议）不是每日发生
- dated=0 需要逐页抓取才能解决，目前用 discovered_at fallback
- weekly 足以捕获新事件，不需要 daily

## 5. 建议命令

```bash
python scripts/run_foundation_low_frequency_sources.py --source merck_ir --run-once
```

该命令会：
- 运行 merck_ir 专门 IR 提取
- 将结果包装为 LowFrequencyItem（含 discovered_at / timestamp_confidence）
- 写入 runtime data（gitignored）
- 生成 markdown / JSON summary

## 6. 为什么本阶段不创建真实 TRAE task

1. **M3C-6C 是 pipeline v1**：先建立框架，再创建任务
2. **需要人工批准**：`manual_approval_required_before_scheduling: true`
3. **需要 24h/7d observation**：先验证稳定性
4. **production_enabled = false**：不得配置 production
5. **不影响现有 4 个 trial_v2 task**

## 7. 后续人工批准 gate

```
Gate 1: M3C-6C pipeline v1 完成（已完成，2026-07-05）
Gate 2: M3C-6C.1 7-day observation harness（harness 已完成，连续观察进行中）
       - 当前状态：partial_observation（observed_days=1, successful_days=1）
       - 缺失：6 more days of observation
Gate 3: 人工审核 observation 结果（待 completed_7d 后）
Gate 4: 人工创建 TRAE scheduled task（手动操作）
Gate 5: 纳入更多低频候选源
```

### 7.1 M3C-6C.1 Observation Harness 概述

M3C-6C.1 在 M3C-6C pipeline v1 基础上建立 7 天 observation harness：

- 7 天 observation 状态机：`pending -> active -> completed_7d | partial_observation | failed`
- Daily run 记录 + 7-day summary
- Navigation regression 检测（连续 2 次 navigation-only run 触发 `failed`）
- Blocking error 检测（login/paywall/captcha/anti-bot 任一出现即 `failed`）
- Runtime data：`data/foundation_low_frequency_observation/`（gitignored）

详细说明见：
- [Low-frequency Observation Harness](foundation_low_frequency_observation_harness.md)
- [M3C-6C.1 TRAE Observation Proposal](foundation_m3c_6c1_trae_low_frequency_observation_proposal.md)
- [M3C-6C.1 Observation Report](foundation_m3c_6c1_merck_ir_low_frequency_observation_report.md)

### 7.2 Observation 命令（人工触发）

```bash
# Dry-run（不写 runtime data）
python scripts/run_foundation_low_frequency_observation.py --source merck_ir --dry-run

# Run once（写 runtime data，gitignored）
python scripts/run_foundation_low_frequency_observation.py --source merck_ir --run-once

# Summarize（输出 7-day summary）
python scripts/run_foundation_low_frequency_observation.py --source merck_ir --summarize

# Boundary check
python scripts/check_foundation_low_frequency_observation.py
```

### 7.3 merck_ir observation 当前结果

| 字段 | 值 |
|---|---|
| target_days | 7 |
| observed_days | 1 |
| successful_days | 1 |
| failed_days | 0 |
| final_observation_status | partial_observation |
| recommended_next_action | continue_observation |
| completed_7d | false |
| missing_to_complete | 6 more days of observation |

## 8. production_enabled

```
production_enabled: false
```

本阶段不得配置 production。低频任务仍为 proposal only。

## 9. 不影响现有 4 个 trial_v2 task

- 不修改 trial_v2 allowlist
- 不修改 TRAE scheduling 时间
- 不修改 TRAE scheduling 命令
- 不修改 TRAE local config
- 不创建永久自动化任务

## 10. 边界确认

- 不修改 TRAE scheduling: 是
- 不修改 TRAE local config: 是
- 不创建永久自动化任务: 是
- 不修改 trial_v2 allowlist: 是
- 不配置 production: 是
- 不提交 data/local/secrets: 是
- 不提交 proxy URL/cookie/token: 是
- 不引入 Playwright/Selenium: 是
- 不恢复已删除 Dashboard 页面: 是
- 不打 tag: 是
