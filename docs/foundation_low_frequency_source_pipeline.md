# Foundation Low-frequency Source Pipeline

## 1. 低频源定义

低频源（low-frequency source）是 OPC Foundation source pipeline 的第二层，与 trial_v2 高频源并行运行。

```
Layer 1: trial_v2_high_frequency (9 sources, daily 3 batches)
Layer 2: low_frequency_sources (merck_ir, weekly/daily low-priority)
Layer 3: on_demand_sources (future, triggered by topic/ticker/keyword)
```

## 2. 适合低频的源类型

- 公司 IR 页面（财报电话会议、投资者事件）
- 更新频率低的新闻源
- 日期提取困难但内容价值高的源
- 需要逐页抓取才能获取日期的源
- 事件型源（非每日更新）

## 3. 不适合低频的源类型

- 每日多次更新的新闻源（应进入 trial_v2）
- 有 login/paywall/captcha/anti-bot 阻断的源
- 无法提取 >= 3 个 valid items 的源
- 通用首页导航页面（无真实内容）

## 4. 与 trial_v2 high-frequency 的区别

| 维度 | trial_v2 high-frequency | low-frequency |
|---|---|---|
| 频率 | 每日 3 批 | 每日 1 次 / 每周 |
| date_text 要求 | 必须 | 可选 |
| dated_item_count | >= 2 | 可为 0 |
| timestamp_confidence | HIGH/MEDIUM | LOW 可接受 |
| discovered_at fallback | 不需要 | 必须 |
| allowlist | trial_v2 allowlist | low_frequency_sources |
| 当前源数 | 9 | 1 (merck_ir) |
| production | false | false |

## 5. 与 on-demand registry 的区别

| 维度 | low-frequency | on-demand |
|---|---|---|
| 触发方式 | 定时（daily/weekly） | 事件触发（ticker/keyword/topic） |
| 数据来源 | 固定 URL | 动态查询 |
| 实现状态 | v1 (merck_ir) | 未实现 |

## 6. 时间戳策略

```
if date_text present:
    timestamp_confidence = MEDIUM
elif discovered_at available:
    timestamp_confidence = LOW
    date_missing_reason = recorded
else:
    timestamp_confidence = NONE
```

- HIGH: 有明确日期且来自结构化数据（JSON-LD / `<time>` 标签）
- MEDIUM: 有日期文本但格式非标准
- LOW: 无日期，使用 discovered_at fallback
- NONE: 无日期且无 discovered_at

## 7. 证据质量策略

- valid_item_count >= 3: 可进入 low-frequency pipeline
- valid_item_count < 3: manual_review_only
- navigation_rejected_count: 必须统计
- sample_items: 最多 5 条，不含敏感数据

## 8. Runtime data 策略

- 所有 runtime data 写入 `data/foundation_low_frequency_sources/`
- 该目录已被 `.gitignore` 忽略
- 不得提交 data/
- 不得提交 raw HTML / screenshot
- 不得提交 proxy URL / cookie / token / secret

## 9. TRAE 任务设计

### 当前阶段：proposal only

```
create_trae_task_now: false
manual_approval_required_before_scheduling: true
```

### 建议的 TRAE 低频任务参数

- **source_id:** merck_ir
- **proposed_frequency:** weekly
- **proposed_command:** `python scripts/run_foundation_low_frequency_sources.py --source merck_ir --run-once`
- **production_enabled:** false
- **不影响现有 4 个 trial_v2 task**

### 后续扩展路径

1. M3C-6C.1: 24h/7d observation（连续观察一周，验证稳定性）
2. 人工批准后创建真实 TRAE scheduled task
3. 逐步纳入更多 L3/L4 低频候选源
4. 评估是否需要 on-demand registry（M3C-6E）

## 10. M3C-6C.1 Observation Harness（2026-07-05 新增）

M3C-6C.1 在 pipeline v1 基础上建立 7 天 observation harness，验证 `merck_ir` 低频 runner 是否可连续稳定运行。

### 10.1 新增能力

- 7 天 observation 状态机：`pending -> active -> completed_7d | partial_observation | failed`
- Daily run 记录：source_id, run_id, run_date, valid_item_count, dated_item_count, missing_date_count, navigation_rejected_count, timestamp_confidence_distribution, sample_items, risk_flags, status
- 7-day summary：observed_days, successful_days, partial_days, failed_days, total_runs, navigation_regression_count, blocking_error_count, final_observation_status
- Navigation regression 检测：连续 2 次 navigation-only run 触发 `failed`
- Blocking error 检测：login_required / paywall_observed / captcha_or_antibot_observed 任一出现即 `failed`
- Runtime data：`data/foundation_low_frequency_observation/`（gitignored）

### 10.2 新增脚本

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

### 10.3 merck_ir observation 当前结果

| 字段 | 值 |
|---|---|
| source_id | merck_ir |
| target_days | 7 |
| observed_days | 1 |
| successful_days | 1 |
| partial_days | 0 |
| failed_days | 0 |
| total_runs | 1 |
| min/max_valid_items_per_run | 15 / 15 |
| timestamp_confidence_distribution | `{"HIGH": 0, "MEDIUM": 0, "LOW": 15, "NONE": 0}` |
| navigation_regression_count | 0 |
| blocking_error_count | 0 |
| final_observation_status | partial_observation |
| recommended_next_action | continue_observation |
| completed_7d | false |
| missing_to_complete | 6 more days of observation |

### 10.4 与 trial_v2 的隔离

- 不修改 trial_v2 allowlist（仍为 9 源）
- 不修改 TRAE scheduling 时间
- 不修改 TRAE scheduling 命令
- 不修改 TRAE local config
- 不创建永久自动化任务
- production_enabled = false

### 10.5 后续 gate

```
Gate 1: M3C-6C pipeline v1 完成（已完成）
Gate 2: M3C-6C.1 7-day observation harness（当前，需连续观察 6 天）
Gate 3: 人工审核 observation 结果（completed_7d 必要条件）
Gate 4: 人工创建 TRAE scheduled task（手动操作）
Gate 5: 纳入更多低频候选源
```

### 10.6 相关文档

- [Low-frequency Observation Harness](foundation_low_frequency_observation_harness.md)
- [M3C-6C.1 Observation Report](foundation_m3c_6c1_merck_ir_low_frequency_observation_report.md)
- [M3C-6C.1 TRAE Observation Proposal](foundation_m3c_6c1_trae_low_frequency_observation_proposal.md)

## 11. 后续扩展路径

### 候选低频源（未来，不本阶段处理）

- jp_morgan_insights
- quanshang_china
- wallstreet_cn
- barclays_research
- citi_research
- ubs_global_research

### 不适合低频的源

- reuters: anti-bot backlog
- marketwatch: anti-bot backlog
- streetinsider: anti-bot backlog
- goldman_sachs_podcasts: browser_like backlog
- benzinga: cloudflare_or_anti_bot_backlog
