# OPC Foundation Trial V2 Content-Ready Scheduling Report

> 版本：1.0
> 执行时间：2026-07-02
> 执行阶段：M3C-5A8
> 输入依据：M3C-5A5/M3C-5A7/M3C-5A7.1 内容有效性审计

---

## 1. 概要

| 项目 | 值 |
|---|---|
| 初始 content_ready 源数 | 9 |
| preflight 后保留源数 | **8** |
| preflight 降级源数 | 1（merck_ir） |
| 网络环境 | proxy_enabled=false, proxy_mode=none |

---

## 2. Preflight 真实验证结果

| source_id | content_status | preflight_score | valid | relevant | fresh | noise_flags | 保留 |
|---|---|---:|---:|---:|---:|---|---|
| barclays_our_insights | content_ready | 80 | 3 | 2 | 0 | - | YES |
| markets_insider | content_ready | 90 | 3 | 3 | 0 | - | YES |
| china_fund_news | content_ready | 100 | 3 | 3 | 3 | - | YES |
| wind_public | content_ready | 75 | 3 | 2 | 0 | garbled_text | YES |
| goldman_sachs_insights | content_ready | 65 | 2 | 2 | 0 | - | YES |
| business_insider | content_ready | 95 | 3 | 3 | 2 | app_download_page | YES |
| cls_cn | content_ready | 100 | 3 | 3 | 3 | - | YES |
| zhitong_caijing | content_ready | 100 | 3 | 3 | 3 | - | YES |

### 2.1 降级源

| source_id | 降级前 | 降级后 | 原因 |
|---|---|---|---|
| merck_ir | content_ready | technical_only | HTTP 403 Forbidden（investors.merck.com 拒绝访问） |

---

## 3. 真实样本摘要

### barclays_our_insights
- Setting the record straight on Barclays' links to the defence sector
- News & Press Releases
- Barclays Consumer Spend Index

### markets_insider
- SpaceX IPO valuation risks
- Stock market bearish warning from BofA strategists
- Facebook's infamous 2012 IPO

### china_fund_news
- 多家券商公布7月金股名单（fresh）
- 告别"All in AI"，基金公司激辩下半年（fresh）
- 48家A股公司公告提示风险（fresh）

### cls_cn
- 王毅同美国国务卿鲁比奥通电话（fresh）
- 美联储主席沃什发言（fresh）
- 半导体涨价潮蔓延（fresh）

### zhitong_caijing
- 美股三大指数收涨（fresh）
- 中概股集体走强（fresh）
- AI概念股持续活跃（fresh）

---

## 4. 被排除源

### content_watch（4 个，不纳入）
- goldman_sachs_research（JS 渲染，无研究内容）
- goldman_sachs_reports（JS 渲染）
- goldman_sachs_top_of_mind（JS 渲染）
- goldman_sachs_podcasts（JS 渲染，consolidated）

> 注：gelonghui 在 M3C-5B1.3 中已修复并纳入 trial_v2 allowlist（9 源），不再属于排除源。

### content_reject（2 个，不纳入）
- briefing_com_upgrades（空页面）
- wallstreet_cn（空页面）

### technical_only（6 个，不纳入）
- yahoo_finance（403）
- the_fly（403）
- bofa_global_research（SSL 错误）
- texas_instruments_ir（超时）
- benzinga_analyst_ratings（403）
- merck_ir（preflight 降级：403）

---

## 5. Allowlist 路径

`configs/foundation_trial_v2_content_ready_allowlist.example.yaml`

### 5.1 M3C-5A8 初始 allowlist（8 源）

- barclays_our_insights (P0)
- markets_insider (P0)
- china_fund_news (P0)
- wind_public (P0)
- goldman_sachs_insights (P1)
- business_insider (P1)
- cls_cn (P1)
- zhitong_caijing (P1)

### 5.2 M3C-5B1.3 扩容后 allowlist（9 源）

在上述 8 源基础上新增：

- gelonghui (P0)

扩容验证：
- validate-config：PASS
- preflight：PASS 9/9
- dry-run：PASS source_count=9
- manual run：PASS +9 source_health / +9 run_log
- check：PASS

---

## 6. TRAE command-only 示例配置

- **路径**：`configs/trae_foundation_trial_v2_content_ready.example.yaml`
- **enabled**：全部 false
- **production_enabled**：false
- **command_only**：true
- **是否包含自然语言 prompt**：否

---

## 7. 执行结果

| 步骤 | 结果 |
|---|---|
| validate-config | PASS |
| preflight | 8/9 retained, 1 downgraded (merck_ir) |
| dry-run | PASS |
| run | PASS（8 sources queued） |
| check | PASS |

---

## 8. Scheduling 建议

### 8.1 是否建议进入 M3C-5A9

YES，建议进入 M3C-5A9。

### 8.2 建议调度源数

8 个 content_ready 源。

### 8.3 暂缓源数

1 个（merck_ir），暂缓原因：HTTP 403 需特殊 connector。

### 8.4 其他暂缓源

- goldman_sachs 系列（4 个）：JS 渲染，需 browser-like connector
- gelonghui：导航噪音多，需进一步修复
- 其他 technical_only / reject：网络问题或空页面

---

## 9. 差异说明

任务预期列表中包含以下源，但实际不在 content_ready 中：

| 预期源 | 实际状态 | 原因 |
|---|---|---|
| yahoo_finance | technical_only | HTTP 403，不是 content_ready |
| marketwatch | 不在 21 operational 中 | 未被纳入 trial_v2 allowlist |
| business_insider_markets | 不存在 | 该 ID 不在 source inventory 中 |
| cninfo_announcement | 不在 21 operational 中 | 未被纳入 trial_v2 allowlist |

以实际审计结果为准。

---

## 10. 边界确认

- 是否修改 trial_v1：否
- 是否修改真实 TRAE scheduling：否
- 是否配置 production：否
- 是否纳入 content_watch：否
- 是否纳入 content_reject：否
- 是否纳入 technical_only：否
- 是否调度 92 全量：否
- 是否提交 data/local/secrets：否

---

## 11. M3C-5A9：Trial V2 Command-Only 调度启用

> 执行时间：2026-07-02
> 阶段：M3C-5A9
> 目标：启用 8 个 content_ready 源 TRAE trial_v2 command-only 调度

### 11.1 调度源清单

| source_id | source_name | content_score | priority | audit_phase |
|---|---|---:|---|---|
| barclays_our_insights | Barclays Our Insights | 90 | P0 | M3C-5A5 |
| markets_insider | Markets Insider | 90 | P0 | M3C-5A5 |
| china_fund_news | 中国基金报 | 100 | P0 | M3C-5A5 |
| wind_public | Wind 万得公开内容 | 85 | P0 | M3C-5A5 |
| goldman_sachs_insights | Goldman Sachs Insights | 90 | P1 | M3C-5A7 |
| business_insider | Business Insider | 95 | P1 | M3C-5A7.1 |
| cls_cn | 财联社 | 100 | P1 | M3C-5A7.1 |
| zhitong_caijing | 智通财经 | 100 | P1 | M3C-5A7.1 |

- source_count：**8**
- 是否包含 merck_ir：**否**（M3C-5A8 preflight 降级为 technical_only）
- 是否包含 watch/reject/technical_only：**否**

### 11.2 未纳入源及原因

| source_id | 状态 | 原因 |
|---|---|---|
| merck_ir | technical_only | HTTP 403 Forbidden，需特殊 connector |
| yahoo_finance | technical_only | HTTP 403 |
| the_fly | technical_only | HTTP 403 |
| benzinga_analyst_ratings | technical_only | HTTP 403 / Cloudflare |
| bofa_global_research | technical_only | SSL 错误 |
| texas_instruments_ir | technical_only | 超时 |
| briefing_com_upgrades | content_reject | 空页面 |
| wallstreet_cn | content_reject | 空页面 |
| goldman_sachs_research | content_watch | JS 渲染，无 SSR 内容 |
| goldman_sachs_reports | content_watch | JS 渲染 |
| goldman_sachs_top_of_mind | content_watch | JS 渲染 |
| goldman_sachs_podcasts | content_watch | JS 渲染，consolidated |
| gelonghui | content_watch | 导航噪音多 |

### 11.3 TRAE Command-Only 配置

- **config path**：`configs/trae_foundation_trial_v2_content_ready.example.yaml`
- **jobs**：4 个
  - `foundation_trial_v2_content_ready_morning_run`
  - `foundation_trial_v2_content_ready_afternoon_run`
  - `foundation_trial_v2_content_ready_evening_run`
  - `foundation_trial_v2_content_ready_daily_check`
- **enabled in example**：全部 `false`
- **production_enabled**：`false`
- **command_only**：`true`
- **是否包含自然语言 prompt**：否
- **是否包含 proxy URL**：否

### 11.4 手动执行结果

| 步骤 | 结果 |
|---|---|
| validate-config | PASS（source_count=8，全部 content_ready，无 blocked 源） |
| preflight | 8/8 通过，全部 content_ready |
| run | PASS（8 sources queued） |
| check | PASS（15/15 项通过） |

Preflight 详细结果：

| source_id | score | valid | relevant | status |
|---|---|---:|---:|---|
| barclays_our_insights | 80 | 3 | 2 | content_ready |
| markets_insider | 90 | 3 | 3 | content_ready |
| china_fund_news | 100 | 3 | 3 | content_ready |
| wind_public | 75 | 3 | 2 | content_ready |
| goldman_sachs_insights | 65 | 2 | 2 | content_ready |
| business_insider | 95 | 3 | 3 | content_ready |
| cls_cn | 100 | 3 | 3 | content_ready |
| zhitong_caijing | 100 | 3 | 3 | content_ready |

### 11.5 TRAE Manual Trigger 结果

- **manual_trae_setup_required**：`true`
- **原因**：TRAE 本地任务无法由代码直接配置，需在本地 TRAE 界面手动创建 command-only job
- **推荐命令**：
  ```powershell
  powershell -ExecutionPolicy Bypass -File scripts/run_foundation_trial_v2_content_ready.ps1 -Mode run
  ```
- **检查命令**：
  ```powershell
  powershell -ExecutionPolicy Bypass -File scripts/check_foundation_trial_v2_content_ready.ps1
  ```
- **morning_run trigger**：待本地 TRAE 手动启用（示例配置 enabled=false）
- **daily_check trigger**：待本地 TRAE 手动启用（示例配置 enabled=false）
- **source_health 是否新增**：是（run 后生成 8 条记录）
- **run_log 是否新增**：是（run 后生成 8 条记录）
- **failed_queue**：已创建（当前为空，fail-soft）
- **latest report**：`data/foundation_trial_v2_content_ready/reports/trial_v2_content_ready_validation_latest.md`

### 11.6 Wind Public Garbled Text 观察提示

`wind_public` 在 preflight 中 score=75，存在 `garbled_text` 噪音风险。每日检查中需重点观察：
- 乱码率是否上升
- 有效候选数是否低于 2
- 如出现持续乱码，需降级为 content_watch 并暂停调度

### 11.7 运行产物

| 产物 | 路径 | 状态 |
|---|---|---|
| source_health | `data/foundation_trial_v2_content_ready/index/source_health.jsonl` | 8 条记录 |
| run_log | `data/foundation_trial_v2_content_ready/index/run_log.jsonl` | 8 条记录 |
| failed_queue | `data/foundation_trial_v2_content_ready/index/failed_queue.jsonl` | 已创建（空） |
| preflight | `data/foundation_trial_v2_content_ready/index/preflight_content_ready_audit.jsonl` | 8 条记录 |
| report | `data/foundation_trial_v2_content_ready/reports/trial_v2_content_ready_validation_*.md` | 已生成 |

**data 是否提交**：否（已加入 .gitignore）

### 11.8 边界确认（M3C-5A9）

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

## 12. M3C-5A10：24h 观察期

> 执行时间：2026-07-02
> 阶段：M3C-5A10
> 目标：验证 8 个 content_ready 源在 TRAE 本地 command-only 调度下的稳定性

### 12.1 观察状态

- **observation_status**：`partial_observation`
- **原因**：单次会话内完成了脚本验证、preflight 审计、产物生成和 check 检查。完整 24h 观察（morning_run + afternoon_run + evening_run + daily_check）需本地 TRAE 持续运行后补齐。

### 12.2 已完成的验证

- [x] validate-config PASS
- [x] preflight PASS（8/8 content_ready）
- [x] run PASS（8 sources queued）
- [x] check PASS（15/15）
- [x] source_health 增量记录（16 条总记录）
- [x] run_log 增量记录（16 条总记录）
- [x] failed_queue 已创建（空，fail-soft）
- [x] 8 源逐源表现已记录
- [x] wind_public garbled_text 已识别

### 12.3 待完成的 24h 观察

- [ ] morning_run（独立 24h 周期内自动执行）
- [ ] afternoon_run（独立 24h 周期内自动执行）
- [ ] evening_run（独立 24h 周期内自动执行）
- [ ] daily_check（独立 24h 周期内自动执行）

### 12.4 8 源逐源表现摘要

| source_id | score | valid | relevant | fresh | 合格 | watch_flag |
|---|---:|---:|---:|---:|---|---|
| barclays_our_insights | 80 | 3 | 2 | 0 | 是 | - |
| markets_insider | 90 | 3 | 3 | 0 | 是 | - |
| china_fund_news | 100 | 3 | 3 | 3 | 是 | - |
| wind_public | 75 | 3 | 2 | 0 | 观察中 | garbled_text |
| goldman_sachs_insights | 65 | 2 | 2 | 0 | 是 | - |
| business_insider | 95 | 3 | 3 | 2 | 是 | - |
| cls_cn | 100 | 3 | 3 | 3 | 是 | - |
| zhitong_caijing | 100 | 3 | 3 | 3 | 是 | - |

### 12.5 Wind Public 观察

- **garbled_text 是否出现**：是
- **影响**：中等，valid=3, relevant=2，仍满足 content_ready 门槛
- **建议**：每日检查中重点监控，如乱码率上升或 valid/relevant < 2，降级为 content_watch

### 12.6 是否建议进入 M3C-5A11

- **建议**：yes（附带条件）
- **原因**：8 源全部 content_ready，脚本稳定，产物正常
- **附加条件**：需在本地 TRAE 完成完整 24h 观察后再评估是否进入 3-day observation 或 production-candidate

### 12.7 24h Observation Report

- **报告路径**：`docs/foundation_trial_v2_24h_observation_report.md`
- **内容**：TRAE 启用状态、运行结果、日志增量、逐源表现、wind_public 观察、边界确认

### 12.8 边界确认（M3C-5A10）

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
