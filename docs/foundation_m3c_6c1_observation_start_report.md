# OPC Foundation M3C-6C.1 Observation Start Report

## 1. 执行时间

- **执行时间:** 2026-07-05
- **阶段:** M3C-6C.1 Merge + Merck IR Low-frequency 7-Day Observation Start

## 2. 版本基线

| 项 | 值 |
|---|---|
| master path | `/Users/apple/Documents/一人公司OPC/opc-foundation` |
| starting master commit | a5b7f06（M3C-6C merge 后） |
| 6C.1 branch commit | 8e963c4 |
| 6C.1 merge commit | 45438b4 |
| origin/master latest commit | 45438b4 |
| git status | clean |

## 3. trial_v2 高频源（仍为 9 源）

```
barclays_our_insights
markets_insider
china_fund_news
wind_public
goldman_sachs_insights
business_insider
cls_cn
zhitong_caijing
gelonghui
```

- **trial_v2 source_count:** 9（未变化）
- **production_enabled:** false（未变化）

## 4. Low-frequency Observation Baseline

通过 `python scripts/run_foundation_low_frequency_observation.py --source merck_ir --summarize` 获取的 baseline：

| 字段 | 值 |
|---|---|
| source_id | merck_ir |
| target_days | 7 |
| observed_days | 1 |
| successful_days | 1 |
| partial_days | 0 |
| failed_days | 0 |
| total_runs | 2 |
| min_valid_items_per_run | 0 |
| max_valid_items_per_run | 15 |
| timestamp_confidence_distribution | `{"HIGH": 0, "MEDIUM": 0, "LOW": 30, "NONE": 0}` |
| navigation_regression_count | 0 |
| blocking_error_count | 0 |
| final_observation_status | partial_observation |
| recommended_next_action | continue_observation |
| completed_7d | false |
| missing_to_complete | 6 days |

### Daily Status

| date | status | runs | best_valid | best_dated | nav_regression | blocking_error |
|---|---|---:|---:|---:|---|---|
| 2026-07-05 | success | 1 | 15 | 0 | False | False |

## 5. 观察窗口

```
observation_target_days = 7
already_observed_days = 1
remaining_days = 6
expected_final_status_after_completion = completed_7d
```

注意：观察窗口不是 production SLA，仅用于 harness 验证。

## 6. TRAE Observation Task

### 6.1 是否创建

**是** —— 在本地 TRAE 中创建 command-only observation task。

注意：
- 本任务为 **本地 TRAE 任务**，不提交 TRAE local config 到 Git
- 不在 repo 中创建任何 TRAE 配置文件
- 真实启用只发生在本地

### 6.2 Task 名称

```
foundation_low_frequency_merck_ir_observation_daily
```

### 6.3 Task 命令（command-only）

```bash
cd "/Users/apple/Documents/一人公司OPC/opc-foundation" && \
python3 scripts/run_foundation_low_frequency_observation.py --source merck_ir --run-once && \
python3 scripts/check_foundation_low_frequency_observation.py
```

要求：
- **command-only**（不写自然语言 prompt）
- 不调用模型解释层
- 不改 repo 文件
- 只写 runtime data（gitignored）
- check 必须随 run-once 后执行

### 6.4 Task 频率

```
frequency: daily
count: 6
suggested_time: 10:30 (本地时间)
stop_condition: 第 6 次运行后人工关闭，或由 M3C-6C.2 close 阶段处理
```

如果 TRAE 不支持 count=6，则使用每日 1 次，人工在第 6 次完成后关闭。
如果 TRAE 支持结束日期，则设置到第 6 次运行后的当天结束。

### 6.5 是否 production

```
is_production: false
production_enabled: false
```

### 6.6 是否提交 TRAE local config

**否**。TRAE local config 不提交到 Git。

## 7. 边界确认

| 检查项 | 结果 |
|---|---|
| 是否修改 trial_v2 scheduling | 否 |
| 是否修改 trial_v2 allowlist | 否（仍 9 源） |
| 是否新增 merck_ir 到 high-frequency 9 源 | 否 |
| 是否配置 production | 否 |
| 是否提交 TRAE local config | 否 |
| 是否提交 data/local/secrets | 否 |
| 是否提交 proxy URL/cookie/token | 否 |
| 是否提交 raw HTML/screenshot | 否 |
| 是否引入 Playwright/Selenium | 否 |
| 是否恢复已删除 Dashboard 页面 | 否 |
| 是否打 tag | 否 |

## 8. Runtime Data 状态

```
path: data/foundation_low_frequency_observation/
gitignore: 已包含
git status: !! data/foundation_low_frequency_observation/  (ignored)
```

- runtime data 未被 git 跟踪
- 不会提交到 Git

## 9. 测试结果

| 测试 | 结果 |
|---|---|
| check_foundation_low_frequency_sources | ALL CHECKS PASSED |
| check_foundation_low_frequency_observation | ALL CHECKS PASSED |
| tests/source_inventory | passed |
| tests/scripts | passed |
| tests/dashboard | passed |
| full pytest | 2483 passed, 0 failed |

## 10. 是否修改 trial_v2 / TRAE / production

| 项 | 是否修改 |
|---|---|
| trial_v2 allowlist | 否 |
| trial_v2 scheduling | 否 |
| trial_v2 命令 | 否 |
| TRAE scheduling 时间 | 否 |
| TRAE scheduling 命令 | 否 |
| TRAE local config（提交到 Git） | 否 |
| production_enabled | 否（仍 false） |
| trial_v1 | 否 |

## 11. 下一步 close 标准

第 7 天 observation 完成后，进入 M3C-6C.2 阶段：

```
M3C-6C.2: Merck IR 7-Day Observation Close
```

### 11.1 close 必要条件（completed_7d）

- 至少 7 个自然日有 observation run 记录
- 每个 observation day 至少 1 次 merck_ir run
- 每次 run `valid_item_count >= 3`
- 每次 run 的 sample items 均不是导航页
- `timestamp_confidence` 可以为 LOW，但必须明确记录
- runtime data 均未进入 git tracking
- failed_queue 或 error_count 无 blocking
- trial_v2 allowlist 未变化
- production_enabled=false

### 11.2 每日检查清单

后续每天 TRAE 自动执行后，检查以下内容：

```bash
cd "/Users/apple/Documents/一人公司OPC/opc-foundation"
python3 scripts/run_foundation_low_frequency_observation.py --source merck_ir --summarize
python3 scripts/check_foundation_low_frequency_observation.py
```

每天需要记录：

1. run 是否成功
2. valid_items 是否 >= 3
3. 是否仍是 IR / events / presentations 内容
4. 是否退化成导航页
5. timestamp_confidence 是否 LOW
6. runtime data 是否 gitignored
7. 是否有 blocking error

## 12. 相关文档

- [Low-frequency Observation Harness](foundation_low_frequency_observation_harness.md)
- [M3C-6C.1 Observation Report](foundation_m3c_6c1_merck_ir_low_frequency_observation_report.md)
- [M3C-6C.1 TRAE Observation Proposal](foundation_m3c_6c1_trae_low_frequency_observation_proposal.md)
- [Low-frequency Source Pipeline](foundation_low_frequency_source_pipeline.md)
- [TRAE Low-frequency Task Proposal](foundation_low_frequency_trae_task_proposal.md)
- [TRAE Operations](foundation_trae_operations.md)
