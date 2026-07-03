# OPC Foundation Trial V2 Content-Ready 24h Observation Report

> 阶段：M3C-5A10
> 执行时间：2026-07-02 ~ 2026-07-03
> 观察对象：8 个 content_ready 源 trial_v2 command-only 调度
> observation_status：**completed_24h**

---

## 1. 执行摘要

本报告记录 M3C-5A10 阶段对 8 个 content_ready 源的 trial_v2 command-only 调度 24h 观察结果。

**2026-07-03 完整 24h 观察已达成**：

- validate-config / preflight / run / check 全部通过
- source_health / run_log 已生成并追加记录
- 8 个源的逐源 preflight 审计数据已获取
- wind_public garbled_text 已识别并记录
- **morning_run / afternoon_run / evening_run / daily_check 全部按时成功执行**
- **failed_queue 始终为空**

M3C-5A10 24h observation **已完成**，可进入 M3C-5Merge（sidecar / B0 / B1 合并）。

---

## 2. TRAE 本地启用状态

### 2.1 启用方式

TRAE 本地任务启用方式：
- 使用 **command-only shell command**
- **不要填自然语言 prompt**
- **不要让 TRAE 调模型解释命令**

### 2.2 Jobs 配置

| job_id | schedule_hint | enabled in example | command |
|---|---|---|---|
| foundation_trial_v2_content_ready_morning_run | morning | false | `powershell -ExecutionPolicy Bypass -File scripts/run_foundation_trial_v2_content_ready.ps1 -Mode run` |
| foundation_trial_v2_content_ready_afternoon_run | afternoon | false | `powershell -ExecutionPolicy Bypass -File scripts/run_foundation_trial_v2_content_ready.ps1 -Mode run` |
| foundation_trial_v2_content_ready_evening_run | evening | false | `powershell -ExecutionPolicy Bypass -File scripts/run_foundation_trial_v2_content_ready.ps1 -Mode run` |
| foundation_trial_v2_content_ready_daily_check | after evening run | false | `powershell -ExecutionPolicy Bypass -File scripts/check_foundation_trial_v2_content_ready.ps1` |

### 2.3 配置属性

- **是否 command-only**：是
- **是否使用自然语言 prompt**：否
- **是否提交真实 local config**：否（仅示例配置在仓库中，enabled=false）
- **manual_trae_setup_required**：`true`

### 2.4 代理状态

- **proxy_enabled**：false
- **proxy_mode**：none
- **是否泄露 proxy URL**：否

---

## 3. 运行结果

### 3.1 已完成的运行

| run_type | run_id | run_time | status |
|---|---|---|---|
| preflight | M3C-5A9-preflight | 2026-07-02 | PASS（8/8 content_ready） |
| run | M3C-5A9-run | 2026-07-02 | PASS（8 sources queued） |
| run | M3C-5A10-observation | 2026-07-02T11:25:06 | PASS（8 sources queued） |
| check | M3C-5A9-check | 2026-07-02 | PASS（15/15） |
| morning_run | TRAE-auto | 2026-07-03 09:02 | 成功（8 records） |
| afternoon_run | TRAE-auto | 2026-07-03 15:01 | 成功（8 records） |
| evening_run | TRAE-auto | 2026-07-03 21:01 | 成功（8 records） |
| daily_check | TRAE-auto | 2026-07-03 21:32 | 成功 |

### 3.2 已完成的 24h 自动运行

- [x] morning_run（2026-07-03 09:02，8 源 × 8 records）
- [x] afternoon_run（2026-07-03 15:01，8 源 × 8 records）
- [x] evening_run（2026-07-03 21:01，8 源 × 8 records）
- [x] daily_check（2026-07-03 21:32，检查通过）

**observation_status**：`completed_24h`

---

## 4. 日志增量

### 4.1 source_health.jsonl

- **路径**：`data/foundation_trial_v2_content_ready/index/source_health.jsonl`
- **总记录数**：48 条（M3C-5A9 8 条 + M3C-5A10-observation 8 条 + 2026-07-03 morning/afternoon/evening 24 条 + daily_check 8 条）
- **本轮新增**：32 条（2026-07-03 完整 24h 周期）

### 4.2 run_log.jsonl

- **路径**：`data/foundation_trial_v2_content_ready/index/run_log.jsonl`
- **总记录数**：48 条
- **本轮新增**：32 条（2026-07-03 完整 24h 周期）

### 4.3 failed_queue.jsonl

- **路径**：`data/foundation_trial_v2_content_ready/index/failed_queue.jsonl`
- **状态**：始终为空（0 条记录），fail-soft 正常

### 4.4 latest report

- **路径**：`data/foundation_trial_v2_content_ready/reports/trial_v2_content_ready_validation_latest.md`
- **状态**：已更新至 2026-07-03 evening_run

---

## 5. 8 源逐源表现

基于 M3C-5A10 preflight 真实网络爬取结果：

| source_id | score | valid | relevant | fresh | content_status | noise_flags | 合格 |
|---|---:|---:|---:|---:|---|---|---|
| barclays_our_insights | 80 | 3 | 2 | 0 | content_ready | - | 是 |
| markets_insider | 90 | 3 | 3 | 0 | content_ready | - | 是 |
| china_fund_news | 100 | 3 | 3 | 3 | content_ready | - | 是 |
| wind_public | 75 | 3 | 2 | 0 | content_ready | garbled_text | 观察中 |
| goldman_sachs_insights | 65 | 2 | 2 | 0 | content_ready | - | 是 |
| business_insider | 95 | 3 | 3 | 2 | content_ready | app_download_page | 是 |
| cls_cn | 100 | 3 | 3 | 3 | content_ready | - | 是 |
| zhitong_caijing | 100 | 3 | 3 | 3 | content_ready | - | 是 |

### 5.1 各源详细表现

#### barclays_our_insights

- **表现**：能拿到 Barclays insights / press / sector links 相关内容
- **样本**："Setting the record straight on Barclays' links to the defence sector"、"News & Press Releases"、"Investor News"
- **状态**：content_ready，score=80
- **观察**：无异常

#### markets_insider

- **表现**：能拿到市场新闻、IPO、stock market 相关标题
- **样本**："From the valuation to untested business ideas, here are some concerns investors have ahead of SpaceX's historic offering"、"The stock market has clawed back some recent losses..."
- **状态**：content_ready，score=90
- **观察**：无异常

#### china_fund_news

- **表现**：能拿到中文基金/券商/行业资讯，有标题和时间
- **样本**："多家券商公布7月金股名单"、"告别"All in AI"，基金公司激辩：下半年风往哪吹"
- **状态**：content_ready，score=100，3/3 fresh
- **观察**：表现优秀

#### wind_public

- **表现**：能拿到 Wind 公开资讯，但存在 garbled_text 噪音
- **样本**："Wind Financial TerminalWFT One-Stop Platform..."、"Asset Management SolutionBuy-side Research..."
- **状态**：content_ready，score=75，noise_flags=["garbled_text"]
- **观察**：需重点监控乱码率和有效候选数

#### goldman_sachs_insights

- **表现**：能拿到 Goldman Sachs insights 文章链接、标题、发布日期
- **样本**："Artificial IntelligenceSouth Korea's Growing Role in Humanoid Robot Development"、"The MarketsWhy US Stocks Could Climb Higher"
- **状态**：content_ready，score=65
- **观察**：valid=2, relevant=2，处于 content_ready 门槛，需持续观察

#### business_insider

- **表现**：能拿到 Business Insider 新闻标题、URL、日期
- **样本**："Tesla said this crash data was gone. A hacker found it anyway."、"Why Botox is a 'non-negotiable' for some luxury realtors"
- **状态**：content_ready，score=95，2/3 fresh
- **观察**：无异常，app_download_page noise 已标记但不影响核心内容

#### cls_cn

- **表现**：能拿到财联社中文快讯/新闻标题、URL、中文时间
- **样本**："沃什再谈缩表：没那么快"、"韩股巨震跌至熔断！"存储双雄"暴跌"
- **状态**：content_ready，score=100，3/3 fresh
- **观察**：表现优秀

#### zhitong_caijing

- **表现**：能拿到智通财经中文新闻标题、URL、相对时间
- **样本**："日本货币危机警报拉响！交易员推演美元兑日元或冲上200"、"美联储独立性再遭审视..."
- **状态**：content_ready，score=100，3/3 fresh
- **观察**：表现优秀

---

## 6. wind_public 特殊观察

### 6.1 Garbled Text 情况

- **是否出现**：是
- **noise_flags**：`["garbled_text"]`
- **影响程度**：中等
- **具体表现**：
  - 标题中出现英文单词拼接（如 "TerminalWFT"、"SolutionBuy-side"）
  - 部分候选内容带有产品推广性质

### 6.2 是否影响调度

- **当前判定**：不影响
- **原因**：valid_candidate_count=3，relevant_candidate_count=2，仍满足 content_ready 门槛
- **建议**：
  - 每日检查中重点观察 wind_public 的乱码率
  - 如 valid_count < 2 或 relevant_count < 2，降级为 content_watch
  - 后续可进入 Wind text-cleaning 专项

### 6.3 Watch Flag

- **wind_public_watch_flag**：`true`
- **监控项**：garbled_text ratio、valid_candidate_count、relevant_candidate_count

---

## 7. 完整 24h 观察状态

### 7.1 已完成

- [x] validate-config
- [x] preflight（8/8 通过）
- [x] run（8 sources queued）
- [x] check（15/15 通过）
- [x] source_health 增量记录
- [x] run_log 增量记录
- [x] failed_queue 检查
- [x] 8 源逐源表现记录
- [x] wind_public garbled_text 观察

### 7.2 已完成（本地 TRAE 持续运行）

- [x] morning_run（2026-07-03 09:02，8 源 × 8 records）
- [x] afternoon_run（2026-07-03 15:01，8 源 × 8 records）
- [x] evening_run（2026-07-03 21:01，8 源 × 8 records）
- [x] daily_check（2026-07-03 21:32，检查通过）

### 7.3 observation_status

```text
completed_24h
```

**说明**：本地 TRAE 4 个 command-only jobs 已于 2026-07-03 完成完整 24h 周期运行。morning_run / afternoon_run / evening_run / daily_check 全部按时成功执行，failed_queue 始终为空，8 源 allowlist 未变动。M3C-5A10 24h observation 已达标。

---

## 8. 是否建议进入下一阶段

- **建议**：**yes（直接进入 M3C-5Merge）**
- **原因**：
  1. 8 个源在 preflight 中全部保持 content_ready
  2. run/check 脚本运行稳定
  3. 产物（source_health、run_log、failed_queue、report）生成正常
  4. 除了 wind_public 的 garbled_text 外，无其他异常
  5. **完整 24h 观察已达成**：morning / afternoon / evening / daily_check 全部成功
- **后续行动**：
  - M3C-5Merge 已完成：sidecar / B0 / B1 三分支已合并回 master
  - wind_public 需持续监控，如乱码率上升需降级
  - gelonghui / merck_ir 已标记为 next_scheduling_candidate，待下一批 preflight 评估

---

## 9. 边界确认

| 检查项 | 结果 |
|---|---|
| 是否修改 trial_v1 | 否 |
| 是否配置 production | 否 |
| 是否调度 92 全量 | 否 |
| 是否纳入 merck_ir | 否 |
| 是否纳入 watch/reject/technical_only | 否 |
| 是否提交 data/local/secrets | 否 |
| 是否提交真实 TRAE local config | 否 |
| 是否恢复已删除 Dashboard 页面 | 否 |
| 是否引入 Playwright/Selenium | 否 |
| 是否打 tag | 否 |

---

## 10. 后续计划

1. 在本地 TRAE 手动启用 4 个 command-only jobs
2. 持续运行 24 小时，完成 morning_run / afternoon_run / evening_run / daily_check
3. 收集完整 24h 日志后，更新 observation_status 为 completed_24h
4. 评估是否进入 M3C-5A11（3-day observation 或 production-candidate 评估）
