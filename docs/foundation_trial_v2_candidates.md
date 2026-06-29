# Foundation Trial v2 候选源清单（M3C-5A）

> 版本：1.3
> 生成时间：2026-06-29
> 执行阶段：M3C-5A + M3C-5A2 + M3C-5A2.1 + M3C-5A3
> 当前 trial v1 源数：15
> M3C-5A 新增 candidate 数：8
> M3C-5A2 验证结果：5 ready, 1 watch, 2 reject
> M3C-5A2.1 合并结果：3 个 GS podcast → 1 个 consolidated candidate
> M3C-5A3 完整验证：21 源 trial_v2 allowlist 已生成并通过验证
> **累计 trial_v2_ready 数：6**
> **建议 trial_v2 总源数：21（15 trial_v1 + 6 additions）**
> **建议 trial_v2 总新增：6（5 独立 + 1 合并）**  

---

## 1. 概述

本清单列出 M3C-5A URL 攻坚后，可进入 trial v2 试运行的候选源。

**重要说明：**
- 当前 15 个 trial v1 源**不受影响**，继续按原调度运行
- 本清单仅列出 candidate，**尚未进入正式 trial 调度**
- trial v2 启动需等待 M3C-5 全系列完成后统一规划

---

## 2. Trial v2 候选源总览

| 优先级 | source_id | source_name | 修复后URL | 验证状态 | 需代理 | 需特殊connector | 原始分桶 |
|---|---|---|---|---|---|---|---|
| P0 | bofa_global_research | BofA Global Research | https://www.bankofamerica.com/research | 301重定向，可访问 | 否 | 否 | dns_resolution_failed |
| P0 | texas_instruments_ir | Texas Instruments IR | https://investor.ti.com | 200 OK，官方IR | 否 | 否 | http_4xx_or_404 |
| P0 | merck_ir | Merck IR | https://investors.merck.com | 200 OK，官方IR | 否 | 否 | http_4xx_or_404 |
| P0 | benzinga_analyst_ratings | Benzinga Analyst Ratings | https://www.benzinga.com/analyst-ratings | 200 OK | 否 | 否 | http_4xx_or_404 |
| P1 | china_fund_news | 中国基金报 | https://www.chnfund.com | 200 OK，新域名 | 否 | 否 | dns_resolution_failed |
| P1 | **goldman_sachs_podcasts** | **Goldman Sachs Podcasts** | **https://www.goldmansachs.com/insights/podcasts** | **200 OK，播客总览（consolidated）** | **否** | **否** | **http_4xx_or_404** |

> **注意**：M3C-5A2.1 将 3 个 GS podcast 源合并为 1 个 consolidated candidate，避免重复抓取。原始 source 保留在 inventory 中。

---

## 3. 候选源详情

### P0 优先级（4个）- 高置信度，建议优先纳入

#### 3.1.1 bofa_global_research
- **source_name**: BofA Global Research
- **source_group**: official_public_research
- **修复前**: `https://research.bofa.com`（DNS失败）
- **修复后**: `https://www.bankofamerica.com/research`
- **验证状态**: HTTP 301 重定向 → 200 OK
- **相关性**: 高，官方 research 页面，服务于原信息覆盖目标
- **是否需要代理**: 否
- **是否需要特殊 connector**: 否
- **建议频率**: 每天1次

#### 3.1.2 texas_instruments_ir
- **source_name**: Texas Instruments Investor Relations
- **source_group**: bank_conference_transcripts
- **修复前**: `https://www.ti.com/investor`（404）
- **修复后**: `https://investor.ti.com`
- **验证状态**: HTTP 200 OK
- **相关性**: 高，官方 IR 子域名，服务于原信息覆盖目标
- **是否需要代理**: 否
- **是否需要特殊 connector**: 否
- **建议频率**: earnings期间高频，平时周检

#### 3.1.3 merck_ir
- **source_name**: Merck Investor Relations
- **source_group**: bank_conference_transcripts
- **修复前**: `https://www.merck.com/investor`（404）
- **修复后**: `https://investors.merck.com`
- **验证状态**: HTTP 200 OK
- **相关性**: 高，官方 IR 子域名，服务于原信息覆盖目标
- **是否需要代理**: 否
- **是否需要特殊 connector**: 否
- **建议频率**: earnings期间高频，平时周检

#### 3.1.4 benzinga_analyst_ratings
- **source_name**: Benzinga Analyst Ratings
- **source_group**: analyst_actions
- **修复前**: `https://www.benzinga.com/analytics/ratings`（404）
- **修复后**: `https://www.benzinga.com/analyst-ratings`
- **验证状态**: HTTP 200 OK
- **相关性**: 高，路径修正，服务于原信息覆盖目标
- **是否需要代理**: 否
- **是否需要特殊 connector**: 否
- **建议频率**: 每天2-3次

### P1 优先级（2个）- 中高置信度

#### 3.2.1 china_fund_news
- **source_name**: 中国基金报
- **source_group**: chinese_rebroadcast
- **修复前**: `https://www.chinafundnews.com`（DNS失败）
- **修复后**: `https://www.chnfund.com`
- **验证状态**: HTTP 200 OK
- **相关性**: 中高，新域名 chnfund.com，需确认内容一致性
- **是否需要代理**: 否
- **是否需要特殊 connector**: 否
- **建议频率**: 每天1-2次

#### 3.2.2 goldman_sachs_exchanges
- **source_name**: Goldman Sachs Exchanges
- **source_group**: official_podcast_transcript
- **修复前**: `https://www.goldmansachs.com/podcasts/exchanges`（404）
- **修复后**: `https://www.goldmansachs.com/insights/podcasts`
- **验证状态**: HTTP 200 OK
- **相关性**: 中，从单个节目页改为播客总览页，覆盖度降低
- **是否需要代理**: 否
- **是否需要特殊 connector**: 否
- **建议频率**: 每天1次

### P2 优先级（2个）- 需评估是否重复

#### 3.3.1 goldman_sachs_the_markets
- **source_name**: Goldman Sachs The Markets
- **修复后**: 同 goldman_sachs_exchanges，指向同一个播客总览页
- **注意**: 与另外两个 Goldman Sachs 播客源指向同一页面，可能重复
- **建议**: trial v2 前评估是否合并

#### 3.3.2 goldman_sachs_top_of_mind_podcast
- **source_name**: Goldman Sachs Top of Mind (Podcast)
- **修复后**: 同 goldman_sachs_exchanges，指向同一个播客总览页
- **注意**: 与另外两个 Goldman Sachs 播客源指向同一页面，可能重复
- **建议**: trial v2 前评估是否合并

---

## 4. 暂不纳入 Trial v2 的源

### 4.1 Browser-like 候选（2个）
留待 M3C-5B browser-like connector 阶段处理。

| source_id | 原因 |
|---|---|
| streetinsider | 默认UA 403，需浏览器UA |
| tipranks | 默认UA 403，需浏览器UA |

### 4.2 DNS Backlog（4个）
暂无有效替代入口。

| source_id | 原因 |
|---|---|
| bofa_must_read_research | DNS失败，替代路径也404 |
| citi_institute | DNS失败，无有效替代 |
| hk_stock_research | DNS失败，无有效替代 |
| quanshang_china | 超时/DNS失败，需进一步诊断 |

### 4.3 URL Backlog（10个）
暂无有效替代入口。

| source_id | 原因 |
|---|---|
| goldman_sachs_greater_china | 404，无有效替代 |
| barclays_research | 404，与barclays_our_insights重复 |
| barclays_ib_research | 404，与barclays_our_insights重复 |
| goldman_sachs_communacopia | 404，年度会议页 |
| barclays_global_tech_conference | 404，年度会议页 |
| bernstein_strategic_decisions | 404，年度会议页 |
| investing_com_analyst_ratings | 403，反爬严 |
| reuters | 401，需登录 |
| marketwatch | 401，需登录 |
| wsj_upgrades_downgrades | 401/403，需订阅 |

---

## 5. Trial v2 规划建议

### 5.1 建议纳入 trial v2 的源（6个）

优先纳入 P0 + P1，共 6 个（5 个独立 + 1 个合并）：
1. `bofa_global_research`
2. `texas_instruments_ir`
3. `merck_ir`
4. `benzinga_analyst_ratings`
5. `china_fund_news`
6. `goldman_sachs_podcasts`（M3C-5A2.1 合并：3 个播客源 → 1 个 consolidated candidate）

### 5.2 暂不纳入的原因

- **streetinsider / tipranks**：需 browser-like connector，留待 M3C-5B
- **DNS/URL backlog**：暂无有效替代入口
- **需登录/订阅源**：不绕登录/付费墙，暂不纳入

---

## 6. 相关文件

- URL 恢复报告：`docs/foundation_url_recovery_report.md`
- Source Triage 报告：`docs/foundation_source_triage_report.md`
- Source Activation Plan：`docs/foundation_source_activation_plan.md`
- Trial 运行报告：`docs/foundation_trae_trial_schedule_report.md`
- **Trial v2 验证报告**：`docs/foundation_trial_v2_validation_report.md`

---

## 7. M3C-5A2.1 合并结果摘要

> 执行时间：2026-06-29
> 处理范围：3 个 Goldman Sachs podcast 候选源
> 合并类型：Operational consolidation（trial_v2 层面）

### 7.1 合并前后对比

| 状态 | 合并前 | 合并后 | 说明 |
|---|---|---|---|
| trial_v2_ready | 5 | **6** | +1 个 consolidated candidate |
| trial_v2_watch | 1 | 0 | goldman_sachs_exchanges 已合并 |
| trial_v2_reject | 2 | 0 | 已合并为 consolidated candidate |

### 7.2 合并详情

| consolidated candidate | member_source_ids |
|---|---|
| goldman_sachs_podcasts | goldman_sachs_exchanges, goldman_sachs_the_markets, goldman_sachs_top_of_mind_podcast |

### 7.3 trial_v2_ready 最终清单（6个）

| source_id | 优先级 | 建议动作 |
|---|---|---|
| bofa_global_research | P0 | ✅ 建议纳入 |
| texas_instruments_ir | P0 | ✅ 建议纳入 |
| merck_ir | P0 | ✅ 建议纳入 |
| benzinga_analyst_ratings | P0 | ✅ 建议纳入 |
| china_fund_news | P1 | ✅ 建议纳入 |
| **goldman_sachs_podcasts** | P1 | ✅ 建议纳入（consolidated） |

### 7.4 Source Inventory 确认

- **source 总数**：92（保持不变）
- **原始 3 个 GS podcast source**：保留在 inventory 中（不删除）
- **consolidated candidate**：trial_v2 层面的操作，不影响 source inventory

### 7.5 验证边界确认

- ✅ 不修改当前 15 个 trial v1 源
- ✅ 不修改 TRAE scheduling
- ✅ 不调度 92 全量源
- ✅ 不抓 blocked/high-risk 源
- ✅ 不绕登录/付费墙
- ✅ 不提交 data/（.gitignore 已覆盖）
- ✅ 不引入 Playwright/Selenium
- ✅ 不删除 source inventory 记录

### 7.6 后续规划

**建议 trial_v2 包含：**
- 当前 15 个 trial v1 源（保持不变）
- 新增 6 个 trial_v2_ready 源（5 独立 + 1 合并）

**Trial v2 合计：21 个源**

