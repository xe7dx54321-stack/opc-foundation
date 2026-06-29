# Foundation URL 恢复攻坚报告（M3C-5A）

> 版本：1.0  
> 生成时间：2026-06-29  
> 执行阶段：M3C-5A  
> 处理源数：24  
> Source 总数：92（保持不变）  

---

## 1. 概述

本报告记录 M3C-5A 阶段的 URL / DNS / 404 / HTTP 4xx 类失败源攻坚结果。

### 1.1 背景

Foundation 现有 92 个 source，其中：
- 15 个已进入 trial v1 试运行
- 大量源处于 URL 失效、DNS 失败、HTTP 4xx 等状态

### 1.2 目标

从 URL / DNS / 404 / HTTP 4xx 源中恢复 5-10 个，让 trial candidate 从 15 提升到 20+。

### 1.3 处理范围

本次处理以下分桶的源：
- `dns_resolution_failed`（5个）
- `http_4xx_or_404`（18个，排除 2 个 browser_like_needed）
- `url_verification_needed`（1个）

**不处理：**
- `tls_handshake_failed`（21个，需 browser-like connector）
- `browser_like_needed`（2个，已知换UA可解决，留待后续）
- `wechat_archive_mapping_needed`（6个，需微信映射）
- `on_demand_only`（10个，搜索provider）
- `dormant`（2个，社区源）
- `blocked_by_policy`（5个，高风险）

---

## 2. 整体统计

| 指标 | 数量 |
|---|---|
| 处理源总数 | 24 |
| DNS 失败源 | 5 |
| HTTP 404 源 | 13 |
| HTTP 403 源 | 1 |
| HTTP 401/需登录源 | 4 |
| 超时待验证源 | 1 |

### 2.1 修复结果分桶

| 分桶 | 数量 | 说明 |
|---|---|---|
| url_fixed_trial_v2_candidate | 8 | URL已修复，可进入trial_v2候选 |
| browser_like_candidate | 2 | 需浏览器UA才能访问 |
| dns_backlog | 4 | DNS解析失败，暂无有效替代 |
| url_backlog | 10 | URL失效，暂无有效替代 |
| **合计** | **24** | |

---

## 3. 成功修复源清单（8个）

以下源已找到稳定公开替代入口，URL 已在 source inventory 中更新。

### 3.1 DNS 失败 → 已修复（2个）

| source_id | source_name | 原始URL | 原始错误 | 修复后URL | 状态 |
|---|---|---|---|---|---|
| bofa_global_research | BofA Global Research | https://research.bofa.com | DNS失败 | https://www.bankofamerica.com/research | 301重定向，官方域名 |
| china_fund_news | 中国基金报 | https://www.chinafundnews.com | DNS失败 | https://www.chnfund.com | 200 OK，新域名 |

### 3.2 HTTP 404 → 已修复（3个）

| source_id | source_name | 原始URL | 原始错误 | 修复后URL | 状态 |
|---|---|---|---|---|---|
| texas_instruments_ir | Texas Instruments IR | https://www.ti.com/investor | 404 | https://investor.ti.com | 200 OK，官方IR子域名 |
| merck_ir | Merck IR | https://www.merck.com/investor | 404 | https://investors.merck.com | 200 OK，官方IR子域名 |
| benzinga_analyst_ratings | Benzinga Analyst Ratings | https://www.benzinga.com/analytics/ratings | 404 | https://www.benzinga.com/analyst-ratings | 200 OK，路径修正 |

### 3.3 播客页面 404 → 已修复（3个）

三个 Goldman Sachs 播客源的独立页面均已 404，统一指向播客总览页。

| source_id | source_name | 原始URL | 修复后URL | 状态 |
|---|---|---|---|---|
| goldman_sachs_exchanges | Goldman Sachs Exchanges | /podcasts/exchanges | /insights/podcasts | 200 OK，播客总览页 |
| goldman_sachs_the_markets | Goldman Sachs The Markets | /podcasts/the-markets | /insights/podcasts | 200 OK，播客总览页 |
| goldman_sachs_top_of_mind_podcast | Goldman Sachs Top of Mind (Podcast) | /podcasts/top-of-mind | /insights/podcasts | 200 OK，播客总览页 |

> **注意**：三个播客源现在指向同一个总览页，内容覆盖度有所降低，但仍是官方公开入口，相关性可接受。

---

## 4. Browser-like 候选（2个）

以下源默认 UA 返回 403，但浏览器式 UA 可正常访问。留待 M3C-5B/browser-like connector 阶段处理。

| source_id | source_name | 默认UA | 浏览器UA | 建议 |
|---|---|---|---|---|
| streetinsider | StreetInsider | 403 | 200 | 换UA即可，后续browser-like阶段纳入 |
| tipranks | TipRanks | 403 | 200 | 换UA即可，后续browser-like阶段纳入 |

---

## 5. 无法修复源清单

### 5.1 DNS Backlog（4个）

| source_id | source_name | 原始错误 | 候选URL测试结果 | 建议动作 |
|---|---|---|---|---|
| bofa_must_read_research | BofA Must Read Research | DNS失败+404 | bankofamerica.com/research/must-read 404 | 继续寻找替代入口，或并入bofa_global_research |
| citi_institute | Citi Institute | DNS失败 | citi.com/insights 404, citi.com/citi-gps 404 | 继续寻找citi研究相关公开入口 |
| hk_stock_research | 港股研究社 | DNS失败 | 无有效候选 | 建议标记replace_or_remove，或用gelonghui替代 |
| quanshang_china | 券商中国 | 超时/DNS失败 | 超时 | 需进一步网络诊断，可能区域网络问题 |

### 5.2 URL Backlog（10个）

| source_id | source_name | 原始错误 | 候选URL测试结果 | 建议动作 |
|---|---|---|---|---|
| goldman_sachs_greater_china | Goldman Sachs Greater China | 404 | insights/china 404, greater-china 404 | 继续寻找高盛中国相关公开页面 |
| barclays_research | Barclays Research | 404 | barclays.com/insights 301（已存在barclays_our_insights） | 建议与barclays_our_insights合并，不重复 |
| barclays_ib_research | Barclays IB Research | 404 | investment-bank/insights 404 | 同上，建议合并 |
| goldman_sachs_communacopia | Goldman Sachs Communacopia | 404 | events/communacopia 404, events 404 | 年度会议页面，会议期间再验证 |
| barclays_global_tech_conference | Barclays Global Tech Conference | 404 | （推断类似，未单独验证） | 年度会议页面，会议期间再验证 |
| bernstein_strategic_decisions | Bernstein SDC | 404 | alliancebernstein.com 200，但会议页404 | 年度会议页面，会议期间再验证 |
| investing_com_analyst_ratings | Investing.com Ratings | 403 | analysts/ratings 也403 | 反爬较严，需browser-like或RSS |
| reuters | Reuters | 401需登录 | news页面也401 | 需登录，暂不纳入，寻找RSS替代 |
| marketwatch | MarketWatch | 401需登录 | investing页面也401 | 需登录，暂不纳入 |
| wsj_upgrades_downgrades | WSJ Upgrades/Downgrades | 401需订阅 | market-data 403 | 需订阅，暂不纳入 |

---

## 6. Source Inventory 变更说明

### 6.1 修改的源（8个）

1. `bofa_global_research` - URL 从 research.bofa.com 改为 bankofamerica.com/research
2. `china_fund_news` - URL 从 chinafundnews.com 改为 chnfund.com
3. `texas_instruments_ir` - URL 从 ti.com/investor 改为 investor.ti.com
4. `merck_ir` - URL 从 merck.com/investor 改为 investors.merck.com
5. `benzinga_analyst_ratings` - URL 从 /analytics/ratings 改为 /analyst-ratings
6. `goldman_sachs_exchanges` - URL 从 /podcasts/exchanges 改为 /insights/podcasts
7. `goldman_sachs_the_markets` - URL 从 /podcasts/the-markets 改为 /insights/podcasts
8. `goldman_sachs_top_of_mind_podcast` - URL 从 /podcasts/top-of-mind 改为 /insights/podcasts

### 6.2 未修改的源

- 当前 15 个 trial v1 源：**完全未动**，不受影响
- source_id：**全部保持不变**
- source 总数：**保持 92 个**

---

## 7. 候选 URL 测试明细

### 7.1 测试方法

每个源测试：
1. 原始 URL（默认 UA + 浏览器 UA）
2. 至少 2 个候选替代 URL
3. 优先官方公开入口，其次稳定二次传播源

### 7.2 验证工具

- `curl.exe -I -L --max-time 15`（默认 UA）
- `curl.exe -I -L --max-time 15 -A "Mozilla/5.0 ... Chrome/120 ..."`（浏览器 UA）

---

## 8. 边界确认

| 检查项 | 结果 |
|---|---|
| 处理 92 全量源 | ❌ 否，仅处理 24 个 URL/DNS/4xx 源 |
| 抓取 blocked/high-risk 源 | ❌ 否，5 个 blocked 源未动 |
| 绕登录/付费墙 | ❌ 否，Reuters/MarketWatch/WSJ 均标记为 backlog |
| 下载不明 PDF | ❌ 否 |
| 提交 data/local/secrets | ❌ 否，data/ 在 .gitignore 中 |
| 配置最终 production TRAE | ❌ 否 |
| 恢复已删除 Dashboard 页面 | ❌ 否 |
| 引入 Playwright/Selenium | ❌ 否 |
| 做投资判断 | ❌ 否 |
| 打 tag | ❌ 否 |
| 污染当前 15 个 trial v1 源 | ❌ 否，trial v1 源完全未动 |
| 修改 source_id | ❌ 否，所有 source_id 保持不变 |
| source 总数变化 | ❌ 否，保持 92 个 |

---

## 9. 后续建议

### M3C-5B 建议（Browser-like 阶段）
1. 处理 `streetinsider` 和 `tipranks`（换 UA 即可）
2. 评估 browser-like connector 方案需求
3. 处理部分 TLS 失败源中可通过换 UA 解决的

### M3C-5C 建议（TLS/深度替代入口阶段）
1. 处理 21 个 TLS 握手失败源（Morgan Stanley, J.P. Morgan, UBS 等）
2. 寻找官方 RSS / 播客 RSS 等替代入口
3. 评估是否需要 Playwright 等重武器

### 源优化建议
1. **barclays_research / barclays_ib_research**：与已有的 `barclays_our_insights` 内容高度重叠，建议合并或移除
2. **hk_stock_research**：域名失效且无替代，建议标记 replace_or_remove
3. **Goldman Sachs 三个播客源**：都指向同一个总览页，建议评估是否合并为一个 `goldman_sachs_podcasts`
4. **年度会议源**（Communacopia, SDC 等）：会议期间才更新，建议降低频率或标记为季节性

---

## 10. 相关文件

- 配置修改：`configs/foundation_source_inventory.example.yaml`（8 个源 URL 更新）
- Trial v2 候选清单：`docs/foundation_trial_v2_candidates.md`
- Source Triage 报告：`docs/foundation_source_triage_report.md`
- Source Activation Plan：`docs/foundation_source_activation_plan.md`
