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

## 10. 后续扩展路径

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
