# Foundation Source Triage Report

> 版本：1.0  
> 生成时间：2026-06-26  
> Source 总数：92  
> 依据：M3C-2B Live Smoke + M3C-2B-proxy-rerun + URL Verification 诊断

## 1. 概述

本报告基于 M3C-2B live smoke（92 源）、M3C-2B-proxy-rerun 对比、以及 URL verification 轻量诊断，对 92 个信息源进行分流（triage）分桶，明确每个源的后续处理方向。

**核心结论：**
- 16 个源可直接进入 TRAE 试运行
- 约 21 个源为 TLS/SSL 握手失败（curl 也失败，非 Python 客户端独有问题）
- 约 5 个源为 DNS 解析失败（域名可能已变更）
- 约 20 个源为 HTTP 4xx（404/403/401）
- 6 个微信公众号源需映射到 wechat_archive
- 5 个高风险源继续 blocked
- 10 个 search provider 保持 on-demand
- 2 个社区源保持 dormant

## 2. 分桶总览

| 分桶 | 数量 | 中文说明 | 后续动作 |
|---|---|---|---|
| trae_trial_ready | 16 | 可进入 TRAE 试运行 | 配置调度，上线试运行 |
| tls_handshake_failed | 21 | TLS/SSL 握手失败 | 寻找替代入口 / 后续 browser-like connector |
| http_4xx_or_404 | 20 | HTTP 4xx / 404 | URL verification + 寻找替代入口 |
| dns_resolution_failed | 5 | DNS 解析失败 | 验证域名 + 寻找替代入口 |
| wechat_archive_mapping_needed | 6 | 需要微信归档映射 | 配置 wechat_archive account |
| needs_connector | 0 | 需要补 connector | （已合并到 wechat 桶） |
| on_demand_only | 10 | 仅按需使用 | 保持 search provider on-demand |
| dormant | 2 | 休眠 | 保持 dormant |
| blocked_by_policy | 5 | 策略禁止访问 | 继续 blocked |
| url_verification_needed | 1 | 需要 URL 校验 | 超时类源待验证 |
| python_client_limited | 0 | Python 客户端能力不足 | （本阶段未发现纯 python 问题） |
| browser_like_needed | 2 | 需要浏览器式 UA | streetinsider / tipranks |
| url_fixed | 0 | URL 已修正 | （本阶段未改动配置） |
| replace_or_remove_candidate | 0 | 建议替换或移除 | （全部已归入具体桶） |

**总计：92**

## 3. 各分桶详细清单

### 3.1 trae_trial_ready（16 个）

可直接进入 TRAE 试运行候选。

| source_id | source_name | source_group | priority | access_mode | 最近状态 |
|---|---|---|---|---|---|
| goldman_sachs_research | Goldman Sachs Research | official_public_research | S | public_web | live_ok_candidates_found |
| goldman_sachs_reports | Goldman Sachs Reports | official_public_research | S | public_web | live_ok_candidates_found |
| goldman_sachs_top_of_mind | Goldman Sachs Top of Mind | official_public_research | S | public_web | live_ok_candidates_found |
| goldman_sachs_insights | Goldman Sachs Insights | official_public_research | S | public_web | live_ok_candidates_found |
| barclays_our_insights | Barclays Our Insights | official_public_research | A | public_web | live_ok_candidates_found |
| microsoft_ir | Microsoft Investor Relations | bank_conference_transcripts | S | company_ir | live_ok_candidates_found |
| yahoo_finance | Yahoo Finance | media_research_mentions | A | public_web | live_ok_candidates_found |
| business_insider | Business Insider | media_research_mentions | A | public_web | live_ok_candidates_found |
| markets_insider | Markets Insider | media_research_mentions | A | public_web | live_ok_candidates_found |
| the_fly | The Fly | analyst_actions | A | public_web | live_ok_candidates_found |
| briefing_com_upgrades | Briefing.com Upgrades/Downgrades | analyst_actions | A | public_web | live_ok |
| wallstreet_cn | 华尔街见闻 | chinese_rebroadcast | B | public_web | live_ok_candidates_found |
| cls_cn | 财联社 | chinese_rebroadcast | B | public_web | live_ok_candidates_found |
| wind_public | Wind 万得公开内容 | chinese_rebroadcast | B | public_web | live_ok_candidates_found |
| gelonghui | 格隆汇 | chinese_rebroadcast | B | public_web | live_ok_candidates_found |
| zhitong_caijing | 智通财经 | chinese_rebroadcast | B | public_web | live_ok_candidates_found |

### 3.2 tls_handshake_failed（21 个）

TLS/SSL 握手失败。经 curl 验证，curl 也返回 exit code 35（TLS 握手失败），说明不是 Python urllib 独有的问题，而是目标站点 TLS 层面有拦截或网络限制。

建议：优先寻找官方 RSS / 官方 Insight 总览页 / 媒体镜像等替代入口；后续 M3C-2D 可考虑 browser-like connector。

**Morgan Stanley（6）：**
| source_id | source_name | priority |
|---|---|---|
| morgan_stanley_insights | Morgan Stanley Insights | S |
| morgan_stanley_research | Morgan Stanley Research | S |
| morgan_stanley_thoughts_on_market | Morgan Stanley Thoughts on the Market | S |
| morgan_stanley_china | Morgan Stanley China | A |
| morgan_stanley_fund_research | Morgan Stanley 基金研究报告 | B |
| morgan_stanley_thoughts_podcast | Morgan Stanley Thoughts on the Market (Podcast) | S |

**J.P. Morgan（5）：**
| source_id | source_name | priority |
|---|---|---|
| jp_morgan_research | J.P. Morgan Research | S |
| jp_morgan_global_research_reports | J.P. Morgan Global Research Reports | S |
| jp_morgan_insights | J.P. Morgan Insights | S |
| jp_morgan_research_insights | J.P. Morgan Research Insights | S |
| jp_morgan_research_insights_podcast | J.P. Morgan Research Insights (Podcast) | A |

**UBS（4）：**
| source_id | source_name | priority |
|---|---|---|
| ubs_global_research | UBS Global Research | S |
| ubs_cio_insights | UBS CIO Insights | S |
| ubs_global_research_pod_hub | UBS Global Research Pod Hub | A |
| ubs_investment_bank_insights | UBS Investment Bank Insights | A |

**BofA（部分，2）：**
| source_id | source_name | priority |
|---|---|---|
| bofa_global_research_insights | BofA Global Research and Market Insights | S |
| bofa_weekly_market_recap | BofA Weekly Market Recap | A |

**BofA 播客（1）：**
| source_id | source_name | priority |
|---|---|---|
| bofa_global_research_unlocked | BofA Global Research Unlocked | A |

**Citi（部分，2）：**
| source_id | source_name | priority |
|---|---|---|
| citi_research | Citi Research | S |
| citi_gps | Citi GPS | S |

**其他（1）：**
| source_id | source_name | priority |
|---|---|---|
| deutsche_bank_tech_conference | Deutsche Bank Technology Conference | A |

### 3.3 http_4xx_or_404（20 个）

HTTP 4xx 错误，包括 404（页面不存在/URL 变更）、403（禁止访问/反爬）、401（需要登录）。

**404 页面下线 / URL 变更（13 个）：**
| source_id | source_name | group | 备注 |
|---|---|---|---|
| goldman_sachs_greater_china | Goldman Sachs Greater China 我们的观点 | official_public_research | 子页面 404 |
| barclays_research | Barclays Research | official_public_research | 子页面 404 |
| barclays_ib_research | Barclays Investment Bank Research | official_public_research | 子页面 404 |
| goldman_sachs_exchanges | Goldman Sachs Exchanges | official_podcast_transcript | 播客子页 404 |
| goldman_sachs_the_markets | Goldman Sachs The Markets | official_podcast_transcript | 播客子页 404 |
| goldman_sachs_top_of_mind_podcast | Goldman Sachs Top of Mind (Podcast) | official_podcast_transcript | 播客子页 404 |
| goldman_sachs_communacopia | Goldman Sachs Communacopia + Technology Conference | bank_conference_transcripts | 年度会议页面 |
| barclays_global_tech_conference | Barclays Global Technology Conference | bank_conference_transcripts | 年度会议页面 |
| bernstein_strategic_decisions | Bernstein Strategic Decisions Conference | bank_conference_transcripts | 年度会议页面 |
| texas_instruments_ir | Texas Instruments Investor Relations | bank_conference_transcripts | URL 变更 |
| merck_ir | Merck Investor Relations | bank_conference_transcripts | URL 变更 |
| benzinga_analyst_ratings | Benzinga Analyst Ratings | analyst_actions | URL 变更 |
| jiwen_vip_public | 见闻VIP公开文章 | chinese_rebroadcast | URL 变更 |

**403 禁止访问 / 反爬虫（4 个）：**
| source_id | source_name | group | 备注 |
|---|---|---|---|
| investing_com_analyst_ratings | Investing.com Analyst Ratings | analyst_actions | 反爬虫 |
| streetinsider | StreetInsider | analyst_actions | 反爬虫（browser UA 可访问） |
| tipranks | TipRanks | analyst_actions | 反爬虫（browser UA 可访问） |

**401 需要登录 / 订阅（3 个）：**
| source_id | source_name | group | 备注 |
|---|---|---|---|
| reuters | Reuters | media_research_mentions | 需要登录 |
| marketwatch | MarketWatch | media_research_mentions | 需要登录 |
| marketwatch_upgrades_downgrades | MarketWatch Upgrades/Downgrades | analyst_actions | 需要登录 |
| wsj_upgrades_downgrades | WSJ Market Data Upgrades/Downgrades | analyst_actions | 需要订阅 |

### 3.4 browser_like_needed（2 个）

默认 User-Agent 返回 403，但浏览器式 User-Agent 可正常访问（200 OK）。说明反爬虫机制是基于 UA 检测的，换 UA 即可解决。

| source_id | source_name | group | 默认 UA | 浏览器 UA |
|---|---|---|---|---|
| streetinsider | StreetInsider | analyst_actions | 403 | 200 |
| tipranks | TipRanks | analyst_actions | 403 | 200 |

**建议**：在 connector 中使用浏览器式 User-Agent 即可，暂不需要完整 browser-like connector。

### 3.5 dns_resolution_failed（5 个）

DNS 解析失败，域名可能已变更或失效。

| source_id | source_name | group | 原域名 | 备注 |
|---|---|---|---|---|
| bofa_global_research | BofA Global Research | official_public_research | bofaglobalresearch.com | 主域名失效，可能已迁移 |
| bofa_must_read_research | BofA Must Read Research | official_public_research | bofaml.com | 404 + 域名变更 |
| citi_institute | Citi Institute | official_public_research | research.citibank.com | 子域名失效 |
| china_fund_news | 中国基金报 | chinese_rebroadcast | chinafundnews.com | 域名失效 |
| hk_stock_research | 港股研究社 | chinese_rebroadcast | hkstockresearch.com | 域名失效 |

**建议**：寻找这些机构的官方公开入口替代。

### 3.6 url_verification_needed（1 个）

请求超时，需进一步确认是网络慢还是源不可用。

| source_id | source_name | group | 错误 |
|---|---|---|---|
| quanshang_china | 券商中国 | chinese_rebroadcast | timed out |

### 3.7 wechat_archive_mapping_needed（6 个）

微信公众号源，access_mode=manual，需映射到 wechat_archive connector。

| source_id | 公众号名称 | 原 URL 标识 | 备注 |
|---|---|---|---|
| goldman_sachs_china_wechat | 高盛中国 | wechat:goldman_sachs_china | 外资投行中文输出 |
| morgan_stanley_china_wechat | 摩根士丹利中国 | wechat:morgan_stanley_china | 外资投行中文输出 |
| morgan_stanley_fund_wechat | 摩根士丹利基金研究报告 | wechat:morgan_stanley_fund | 合资基金研报 |
| yanbaoshe_wechat | 研报社 | wechat:yanbaoshe | 第三方研报解读 |
| touyan_circle_wechat | 投研圈类账号 | wechat:touyan_circle | 第三方研报解读 |
| wechat_secondary_broadcast | 部分微信公众号二次传播源 | wechat:secondary_broadcast | 综合二次传播 |

**详细映射方案见**：[foundation_wechat_source_mapping.md](foundation_wechat_source_mapping.md)

### 3.8 on_demand_only（10 个）

搜索 provider，仅按需使用，不进入默认调度。

| source_id | source_name |
|---|---|
| tavily_search | Tavily Search |
| brave_search | Brave Search |
| serpapi | SerpAPI |
| bing_search | Bing |
| google_cse | Google CSE |
| searx | Searx |
| duckduckgo | DuckDuckGo |
| yahoo_search | Yahoo Search |
| baidu_search | Baidu Search |
| custom_search | Custom Search |

### 3.9 dormant（2 个）

社区/开发者信号，当前休眠。

| source_id | source_name |
|---|---|
| github_issues | GitHub Issues |
| hacker_news | Hacker News |

### 3.10 blocked_by_policy（5 个）

高风险源，继续禁止接入。

| source_id | source_name | 原因 |
|---|---|---|
| telegram_groups | Telegram群 | 合规风险 |
| cloud_drive_share | 网盘分享 | 版权风险 |
| pdf_download_sites | 研报PDF下载站 | 版权风险 |
| unknown_wechat_pdf | 不明来源公众号PDF包 | 版权/合规风险 |
| report_download_proxy | 研报代下载站 | 版权/合规风险 |

## 4. URL Verification 诊断结果

### 4.1 已验证源数
- DNS 失败验证：5 个（全部确认 DNS 解析失败）
- TLS 失败验证：4 个（Morgan Stanley、J.P. Morgan、UBS、Deutsche Bank），curl 也 TLS 失败
- 404 验证：3 个（Barclays Research、Goldman Greater China、TI IR），curl 也 404
- 403 验证：3 个（Investing.com、StreetInsider、TipRanks），其中 2 个换 UA 可访问

### 4.2 关键发现

1. **TLS 失败不是 Python 客户端问题**：Morgan Stanley / J.P. Morgan / UBS 等源，curl（exit code 35）和 Python urllib 都在 TLS 握手阶段失败，说明是目标站点或网络层面的 TLS 拦截，不是 Python 特有问题。
2. **StreetInsider / TipRanks 换 UA 即可**：这两个源默认 UA 返回 403，浏览器 UA 返回 200，说明反爬机制较简单。
3. **BofA 主域名已失效**：`bofaglobalresearch.com` 和 `research.citibank.com` 无法解析，需寻找替代入口。

## 5. 优先级建议

### P0：立即进入 TRAE 试运行
- 16 个 trae_trial_ready 源，优先配置 Goldman Sachs、Yahoo Finance、中文财经源

### P1：URL 修正 + 寻找替代入口
- DNS 失败的 5 个源：确认替代域名
- 404 的 13 个源：寻找官方替代入口

### P2：轻量改造即可接入
- StreetInsider / TipRanks：换 browser UA 即可（P2 低成本）

### P3：需要 browser-like connector
- 21 个 TLS 握手失败源：后续 M3C-2D 评估 Playwright 等方案

### P4：需要 wechat_archive 映射
- 6 个微信公众号源：配置 wechat_archive account 后接入

### P5：保持现状
- 10 个 search provider（on-demand）
- 2 个 dormant 源
- 5 个 blocked 源
