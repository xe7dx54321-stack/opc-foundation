# Foundation Trial v2 候选源清单（M3C-5A）

> 版本：1.0  
> 生成时间：2026-06-29  
> 执行阶段：M3C-5A  
> 当前 trial v1 源数：15  
> M3C-5A 新增 candidate 数：8  
> 累计 candidate 数：8（trial_v2 阶段）  

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
| P1 | goldman_sachs_exchanges | Goldman Sachs Exchanges | https://www.goldmansachs.com/insights/podcasts | 200 OK，播客总览 | 否 | 否 | http_4xx_or_404 |
| P2 | goldman_sachs_the_markets | Goldman Sachs The Markets | https://www.goldmansachs.com/insights/podcasts | 200 OK，播客总览 | 否 | 否 | http_4xx_or_404 |
| P2 | goldman_sachs_top_of_mind_podcast | Goldman Sachs Top of Mind | https://www.goldmansachs.com/insights/podcasts | 200 OK，播客总览 | 否 | 否 | http_4xx_or_404 |

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

### 5.1 建议纳入 trial v2 的源（第一批，5-6个）

优先纳入 P0 + P1，共 5-6 个：
1. `bofa_global_research`
2. `texas_instruments_ir`
3. `merck_ir`
4. `benzinga_analyst_ratings`
5. `china_fund_news`
6. `goldman_sachs_exchanges`（3个播客选1个代表）

### 5.2 暂不纳入的原因

- **Goldman Sachs 三个播客源**：都指向同一个总览页，建议合并后再纳入
- **streetinsider / tipranks**：需 browser-like connector，留待 M3C-5B
- **DNS/URL backlog**：暂无有效替代入口
- **需登录/订阅源**：不绕登录/付费墙，暂不纳入

---

## 6. 相关文件

- URL 恢复报告：`docs/foundation_url_recovery_report.md`
- Source Triage 报告：`docs/foundation_source_triage_report.md`
- Source Activation Plan：`docs/foundation_source_activation_plan.md`
- Trial 运行报告：`docs/foundation_trae_trial_schedule_report.md`
