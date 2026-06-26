# Foundation Source Inventory Live Smoke 报告

> 版本：1.1  
> 生成时间：2026-06-26T01:28:51Z  
> Source 总数：92  
> 代理启用：False  
> 代理来源：none  
> 网络环境：VPN 开（系统级）

> **重要说明**：
> - 本报告是 live smoke 结果，不等于正式生产稳定运行
> - 本阶段用于确认 92 个源的真实接通能力和后续补齐优先级
> - blocked/high_risk 源按策略未访问
> - on_demand / dormant 源未默认运行
> - search provider 未跑真实搜索，仅做配置检查

## 0. No-Proxy vs VPN/Proxy-Enabled 对比

本阶段执行了两轮 live smoke：

| 指标 | No-Proxy Baseline | VPN/Proxy-Enabled Rerun | 变化 |
|---|---|---|---|
| 执行时间 | 2026-06-26T00:45 | 2026-06-26T01:27 | — |
| Source 总数 | 92 | 92 | 0 |
| 实际访问数（visited=true） | 75 | 75 | 0 |
| blocked 未访问 | 5 | 5 | 0 |
| on_demand 未运行 | 10 | 10 | 0 |
| dormant 未运行 | 2 | 2 | 0 |
| needs_connector | 6 | 6 | 0 |
| live_ok | 1 | 1 | 0 |
| live_ok_candidates_found | 14 | 15 | +1 |
| 可访问小计 | 15 | 16 | +1 |
| http_error | 21 | 20 | -1 |
| failed | 33 | 33 | 0 |
| 失败小计 | 54 | 53 | -1 |
| 接通率（可访问/总数） | 16% | 17% | +1pp |

### 各 Source Group 接通率对比

| Group | 源数 | No-Proxy 成功 | VPN 成功 | 变化 |
|---|---|---|---|---|
| official_public_research | 28 | 5 | 5 | 0 |
| official_podcast_transcript | 7 | 0 | 0 | 0 |
| bank_conference_transcripts | 11 | 1 | 1 | 0 |
| media_research_mentions | 5 | 3 | 3 | 0 |
| analyst_actions | 8 | 2 | 2 | 0 |
| chinese_rebroadcast | 16 | 4 | 5 | +1 |
| blocked_high_risk_sources | 5 | 0 | 0 | 0 |
| search_providers | 10 | 0 | 0 | 0 |
| community_dev_signals | 2 | 0 | 0 | 0 |

### 海外投行源接通情况

| 投行 | 源数 | No-Proxy 成功 | VPN 成功 | VPN 下主要错误 |
|---|---|---|---|---|
| Goldman Sachs（高盛） | 10 | 4 | 4 | 部分子页 404 http_error |
| Morgan Stanley（大摩） | 6 | 0 | 0 | TLS/SSL handshake failure（`UNEXPECTED_EOF_WHILE_READING`） |
| J.P. Morgan（小摩） | 4 | 0 | 0 | TLS/SSL handshake failure（`UNEXPECTED_EOF_WHILE_READING`） |
| BofA（美银） | 4 | 0 | 0 | DNS resolution failure（`getaddrinfo failed`） |
| Citi（花旗） | 4 | 0 | 0 | DNS resolution failure + TLS handshake mixed |
| UBS（瑞银） | 3 | 0 | 0 | TLS/SSL handshake failure（`UNEXPECTED_EOF_WHILE_READING`） |
| Barclays（巴克莱） | 3 | 1 | 1 | 部分子页 404 http_error |
| Deutsche Bank（德银） | 1 | 0 | 0 | TLS/SSL handshake failure |

### 对比结论

no-proxy baseline 后，VPN/proxy-enabled rerun 显示 Goldman Sachs 可正常访问，但 Morgan Stanley / J.P. Morgan / UBS 仍出现 TLS/SSL handshake failure，BofA / Citi 仍出现 DNS resolution failure。因此海外源问题不是单一代理问题，而是按源分化的网络、DNS、TLS、客户端指纹或 URL 配置问题。不能简单归因为 source unavailable。

## 1. 执行信息

- 开始时间：2026-06-26T01:27:23Z
- 结束时间：2026-06-26T01:28:51Z
- 总耗时：88.1 秒
- Source 总数：92
- 代理启用：False
- 代理来源：none

## 2. 总览统计

| 状态 | 数量 | 中文说明 |
|---|---|---|
| live_ok | 1 | 可访问 |
| live_ok_candidates_found | 15 | 已发现候选 |
| needs_connector | 6 | 需要补 connector |
| blocked_by_policy | 5 | 按策略禁止访问 |
| on_demand_not_run | 10 | 按需源未运行 |
| dormant_not_run | 2 | 休眠源未运行 |
| http_error | 20 | HTTP 错误 |
| failed | 33 | 失败 |

### 2.1 关键指标

- 可访问（live_ok 系列）：16
- 按策略禁止访问（blocked_by_policy）：5
- 按需源未运行（on_demand_not_run）：10
- 休眠源未运行（dormant_not_run）：2
- 需要补 connector（needs_connector）：6
- 访问失败（http_error/timeout/failed）：53

## 3. Source Group 总览

| Group | 源数 | 成功 | 失败 | 接通率 |
|---|---|---|---|---|
| official_public_research | 28 | 5 | 23 | 18% |
| official_podcast_transcript | 7 | 0 | 7 | 0% |
| bank_conference_transcripts | 11 | 1 | 10 | 9% |
| media_research_mentions | 5 | 3 | 2 | 60% |
| analyst_actions | 8 | 2 | 6 | 25% |
| chinese_rebroadcast | 16 | 5 | 6 | 31% |
| blocked_high_risk_sources | 5 | 0 | 0 | 0% |
| search_providers | 10 | 0 | 0 | 0% |
| community_dev_signals | 2 | 0 | 0 | 0% |

## 4. 各 Source Group 详细结果

### 4.1 official_public_research

- 源数：28
- 成功：5
- 失败：23

| source_id | source_name | status | 中文 | visited | candidates | 备注 |
|---|---|---|---|---|---|---|
| goldman_sachs_research | Goldman Sachs Research | live_ok_candidates_found | 已发现候选 | ✅ | 6 | title: Goldman Sachs Research | Goldman Sachs |
| goldman_sachs_reports | Goldman Sachs Reports | live_ok_candidates_found | 已发现候选 | ✅ | 6 | title: Reports | Goldman Sachs |
| goldman_sachs_top_of_mind | Goldman Sachs Top of Mind | live_ok_candidates_found | 已发现候选 | ✅ | 6 | title: Top of Mind | Goldman Sachs |
| goldman_sachs_insights | Goldman Sachs Insights | live_ok_candidates_found | 已发现候选 | ✅ | 6 | title: Insights | Goldman Sachs |
| goldman_sachs_greater_china | Goldman Sachs Greater China 我们的观点 | http_error | HTTP 错误 | ✅ | 0 |  |
| morgan_stanley_insights | Morgan Stanley Insights | failed | 失败 | ✅ | 0 | TLS/SSL handshake failure |
| morgan_stanley_research | Morgan Stanley Research | failed | 失败 | ✅ | 0 | TLS/SSL handshake failure |
| morgan_stanley_thoughts_on_market | Morgan Stanley Thoughts on the Market | failed | 失败 | ✅ | 0 |  |
| morgan_stanley_china | Morgan Stanley China | failed | 失败 | ✅ | 0 | TLS/SSL handshake failure |
| morgan_stanley_fund_research | Morgan Stanley 基金研究报告 | failed | 失败 | ✅ | 0 | TLS/SSL handshake failure |
| jp_morgan_research | J.P. Morgan Research | failed | 失败 | ✅ | 0 |  |
| jp_morgan_global_research_reports | J.P. Morgan Global Research Reports | failed | 失败 | ✅ | 0 | TLS/SSL handshake failure |
| jp_morgan_insights | J.P. Morgan Insights | failed | 失败 | ✅ | 0 | TLS/SSL handshake failure |
| jp_morgan_research_insights | J.P. Morgan Research Insights | failed | 失败 | ✅ | 0 | TLS/SSL handshake failure |
| bofa_global_research | BofA Global Research | failed | 失败 | ✅ | 0 | DNS resolution failure |
| bofa_global_research_insights | BofA Global Research and Market Insights | failed | 失败 | ✅ | 0 | TLS/SSL handshake failure |
| bofa_must_read_research | BofA Must Read Research | failed | 失败 | ✅ | 0 | DNS resolution failure |
| bofa_weekly_market_recap | BofA Weekly Market Recap | failed | 失败 | ✅ | 0 | TLS/SSL handshake failure |
| citi_research | Citi Research | failed | 失败 | ✅ | 0 | TLS/SSL handshake failure |
| citi_institute | Citi Institute | failed | 失败 | ✅ | 0 | DNS resolution failure |
| citi_gps | Citi GPS | failed | 失败 | ✅ | 0 | TLS/SSL handshake failure |
| citi_insights | Citi Insights | failed | 失败 | ✅ | 0 |  |
| ubs_global_research | UBS Global Research | failed | 失败 | ✅ | 0 | TLS/SSL handshake failure |
| ubs_cio_insights | UBS CIO Insights | failed | 失败 | ✅ | 0 | TLS/SSL handshake failure |
| ubs_investment_bank_insights | UBS Investment Bank Insights | failed | 失败 | ✅ | 0 | TLS/SSL handshake failure |
| barclays_research | Barclays Research | http_error | HTTP 错误 | ✅ | 0 | 404 |
| barclays_ib_research | Barclays Investment Bank Research | http_error | HTTP 错误 | ✅ | 0 | 404 |
| barclays_our_insights | Barclays Our Insights | live_ok_candidates_found | 已发现候选 | ✅ | 6 | title: UK unlocked: Our insights |

### 4.2 official_podcast_transcript

- 源数：7
- 成功：0
- 失败：7

| source_id | source_name | status | 中文 | visited | candidates | 备注 |
|---|---|---|---|---|---|---|
| bofa_global_research_unlocked | BofA Global Research Unlocked | failed | 失败 | ✅ | 0 | TLS/SSL handshake failure |
| ubs_global_research_pod_hub | UBS Global Research Pod Hub | failed | 失败 | ✅ | 0 | TLS/SSL handshake failure |
| morgan_stanley_thoughts_podcast | Morgan Stanley Thoughts on the Market (Podcast) | failed | 失败 | ✅ | 0 | TLS/SSL handshake failure |
| goldman_sachs_exchanges | Goldman Sachs Exchanges | http_error | HTTP 错误 | ✅ | 0 | 404 |
| goldman_sachs_the_markets | Goldman Sachs The Markets | http_error | HTTP 错误 | ✅ | 0 | 404 |
| goldman_sachs_top_of_mind_podcast | Goldman Sachs Top of Mind (Podcast) | http_error | HTTP 错误 | ✅ | 0 | 404 |
| jp_morgan_research_insights_podcast | J.P. Morgan Research Insights (Podcast) | failed | 失败 | ✅ | 0 | TLS/SSL handshake failure |

### 4.3 bank_conference_transcripts

- 源数：11
- 成功：1
- 失败：10

| source_id | source_name | status | 中文 | visited | candidates | 备注 |
|---|---|---|---|---|---|---|
| morgan_stanley_tmt_conference | Morgan Stanley Technology, Media & Telecom Conference | failed | 失败 | ✅ | 0 | TLS/SSL handshake failure |
| jp_morgan_healthcare_conference | J.P. Morgan Healthcare Conference | failed | 失败 | ✅ | 0 |  |
| goldman_sachs_communacopia | Goldman Sachs Communacopia + Technology Conference | http_error | HTTP 错误 | ✅ | 0 | 404 |
| ubs_global_tech_conference | UBS Global Technology Conference | failed | 失败 | ✅ | 0 |  |
| bofa_global_tech_conference | BofA Global Technology Conference | failed | 失败 | ✅ | 0 | TLS/SSL handshake failure |
| barclays_global_tech_conference | Barclays Global Technology Conference | http_error | HTTP 错误 | ✅ | 0 | 404 |
| deutsche_bank_tech_conference | Deutsche Bank Technology Conference | failed | 失败 | ✅ | 0 | TLS/SSL handshake failure |
| bernstein_strategic_decisions | Bernstein Strategic Decisions Conference | http_error | HTTP 错误 | ✅ | 0 | 404 |
| microsoft_ir | Microsoft Investor Relations | live_ok_candidates_found | 已发现候选 | ✅ | 6 | title: Home page |
| texas_instruments_ir | Texas Instruments Investor Relations | http_error | HTTP 错误 | ✅ | 0 | 404 |
| merck_ir | Merck Investor Relations | http_error | HTTP 错误 | ✅ | 0 | 404 |

### 4.4 media_research_mentions

- 源数：5
- 成功：3
- 失败：2

| source_id | source_name | status | 中文 | visited | candidates | 备注 |
|---|---|---|---|---|---|---|
| reuters | Reuters | http_error | HTTP 错误 | ✅ | 0 | 401 |
| marketwatch | MarketWatch | http_error | HTTP 错误 | ✅ | 0 | 401 |
| yahoo_finance | Yahoo Finance | live_ok_candidates_found | 已发现候选 | ✅ | 6 | title: Yahoo Finance - Stock Market Live, Quotes, Business &amp; Finance News |
| business_insider | Business Insider | live_ok_candidates_found | 已发现候选 | ✅ | 6 | title: Business Insider - Latest News in Tech, Markets, Economy & Innovation |
| markets_insider | Markets Insider | live_ok_candidates_found | 已发现候选 | ✅ | 6 | title: Markets Insider: Stock Market News, Realtime Quotes and Charts |

### 4.5 analyst_actions

- 源数：8
- 成功：2
- 失败：6

| source_id | source_name | status | 中文 | visited | candidates | 备注 |
|---|---|---|---|---|---|---|
| investing_com_analyst_ratings | Investing.com Analyst Ratings | http_error | HTTP 错误 | ✅ | 0 | 403 |
| benzinga_analyst_ratings | Benzinga Analyst Ratings | http_error | HTTP 错误 | ✅ | 0 | 404 |
| marketwatch_upgrades_downgrades | MarketWatch Upgrades/Downgrades | http_error | HTTP 错误 | ✅ | 0 | 401 |
| wsj_upgrades_downgrades | WSJ Market Data Upgrades/Downgrades | http_error | HTTP 错误 | ✅ | 0 | 401 |
| the_fly | The Fly | live_ok_candidates_found | 已发现候选 | ✅ | 6 | title: The Fly | Home |
| streetinsider | StreetInsider | http_error | HTTP 错误 | ✅ | 0 | 403 |
| briefing_com_upgrades | Briefing.com Upgrades/Downgrades | live_ok | 可访问 | ✅ | 0 | title: Briefing.com |
| tipranks | TipRanks | http_error | HTTP 错误 | ✅ | 0 | 403 |

### 4.6 chinese_rebroadcast

- 源数：16
- 成功：5
- 失败：6

| source_id | source_name | status | 中文 | visited | candidates | 备注 |
|---|---|---|---|---|---|---|
| china_fund_news | 中国基金报 | failed | 失败 | ✅ | 0 | DNS resolution failure |
| quanshang_china | 券商中国 | failed | 失败 | ✅ | 0 | timed out |
| wallstreet_cn | 华尔街见闻 | live_ok_candidates_found | 已发现候选 | ✅ | 6 | title: 华尔街见闻 |
| cls_cn | 财联社 | live_ok_candidates_found | 已发现候选 | ✅ | 6 |  |
| wind_public | Wind 万得公开内容 | live_ok_candidates_found | 已发现候选 | ✅ | 6 | title: 万得信息网 |
| gelonghui | 格隆汇 | live_ok_candidates_found | 已发现候选 | ✅ | 6 | title: 格隆汇-财经资讯动态-股市行情 |
| zhitong_caijing | 智通财经 | live_ok_candidates_found | 已发现候选 | ✅ | 6 | title: 智通财经网-连线全球资本市场 |
| us_stock_research | 美股研究社 | failed | 失败 | ✅ | 0 |  |
| hk_stock_research | 港股研究社 | failed | 失败 | ✅ | 0 | DNS resolution failure |
| jiwen_vip_public | 见闻VIP公开文章 | http_error | HTTP 错误 | ✅ | 0 | 404 |
| goldman_sachs_china_wechat | 高盛中国（微信公众号） | needs_connector | 需要补 connector | ❌ | 0 | Unsupported access_mode: manual |
| morgan_stanley_china_wechat | 摩根士丹利中国（微信公众号） | needs_connector | 需要补 connector | ❌ | 0 | Unsupported access_mode: manual |
| morgan_stanley_fund_wechat | 摩根士丹利基金研究报告（微信公众号） | needs_connector | 需要补 connector | ❌ | 0 | Unsupported access_mode: manual |
| yanbaoshe_wechat | 研报社（微信公众号） | needs_connector | 需要补 connector | ❌ | 0 | Unsupported access_mode: manual |
| touyan_circle_wechat | 投研圈类账号（微信公众号） | needs_connector | 需要补 connector | ❌ | 0 | Unsupported access_mode: manual |
| wechat_secondary_broadcast | 部分微信公众号二次传播源 | needs_connector | 需要补 connector | ❌ | 0 | Unsupported access_mode: manual |

### 4.7 blocked_high_risk_sources

- 源数：5
- 成功：0
- 失败：0

| source_id | source_name | status | 中文 | visited | candidates | 备注 |
|---|---|---|---|---|---|---|
| telegram_groups | Telegram群 | blocked_by_policy | 按策略禁止访问 | ❌ | 0 | Blocked by policy: not accessed |
| cloud_drive_share | 网盘分享 | blocked_by_policy | 按策略禁止访问 | ❌ | 0 | Blocked by policy: not accessed |
| pdf_download_sites | 研报PDF下载站 | blocked_by_policy | 按策略禁止访问 | ❌ | 0 | Blocked by policy: not accessed |
| unknown_wechat_pdf | 不明来源公众号PDF包 | blocked_by_policy | 按策略禁止访问 | ❌ | 0 | Blocked by policy: not accessed |
| report_download_proxy | 研报代下载站 | blocked_by_policy | 按策略禁止访问 | ❌ | 0 | Blocked by policy: not accessed |

### 4.8 search_providers

- 源数：10
- 成功：0
- 失败：0

| source_id | source_name | status | 中文 | visited | candidates | 备注 |
|---|---|---|---|---|---|---|
| tavily_search | Tavily Search | on_demand_not_run | 按需源未运行 | ❌ | 0 | Search provider: on-demand only, not run by default |
| brave_search | Brave Search | on_demand_not_run | 按需源未运行 | ❌ | 0 | Search provider: on-demand only, not run by default |
| serpapi | SerpAPI | on_demand_not_run | 按需源未运行 | ❌ | 0 | Search provider: on-demand only, not run by default |
| bing_search | Bing | on_demand_not_run | 按需源未运行 | ❌ | 0 | Search provider: on-demand only, not run by default |
| google_cse | Google CSE | on_demand_not_run | 按需源未运行 | ❌ | 0 | Search provider: on-demand only, not run by default |
| searx | Searx | on_demand_not_run | 按需源未运行 | ❌ | 0 | Search provider: on-demand only, not run by default |
| duckduckgo | DuckDuckGo | on_demand_not_run | 按需源未运行 | ❌ | 0 | Search provider: on-demand only, not run by default |
| yahoo_search | Yahoo Search | on_demand_not_run | 按需源未运行 | ❌ | 0 | Search provider: on-demand only, not run by default |
| baidu_search | Baidu Search | on_demand_not_run | 按需源未运行 | ❌ | 0 | Search provider: on-demand only, not run by default |
| custom_search | Custom Search | on_demand_not_run | 按需源未运行 | ❌ | 0 | Search provider: on-demand only, not run by default |

### 4.9 community_dev_signals

- 源数：2
- 成功：0
- 失败：0

| source_id | source_name | status | 中文 | visited | candidates | 备注 |
|---|---|---|---|---|---|---|
| github_issues | GitHub Issues | dormant_not_run | 休眠源未运行 | ❌ | 0 | Dormant source: not run by default |
| hacker_news | Hacker News | dormant_not_run | 休眠源未运行 | ❌ | 0 | Dormant source: not run by default |

## 5. 海外投行源重新归因

> no-proxy baseline 和 VPN/proxy-enabled rerun 两轮对比后，海外投行源不能简单归因为 "source unavailable"。
> 按错误类型重新归因如下：

| 归因分类 | 涉及源数 | 典型错误 | 说明 |
|---|---|---|---|
| live_ok / candidates_found | 5 | 200 OK | Goldman Sachs 主站 + Barclays Our Insights，可正常访问 |
| tls_handshake_failed | ~20 | `SSL: UNEXPECTED_EOF_WHILE_READING` | Morgan Stanley、J.P. Morgan、UBS、Deutsche Bank 等，TLS 握手阶段被断开，疑似客户端指纹检测 |
| dns_resolution_failed | ~6 | `getaddrinfo failed` | BofA 主域名、Citi 部分子域名、部分中文源，需验证 URL 配置是否正确 |
| http_error (4xx) | ~15 | 401 / 403 / 404 | Reuters、MarketWatch 401 未授权；Investing.com 等 403 拒绝；部分 conference 页面 404 |
| needs_connector | 6 | access_mode=manual | 微信公众号类源，需要专用 connector |
| blocked_by_policy | 5 | 按策略禁止 | 高风险源，不访问 |

### 5.1 各投行详细归因

- **Goldman Sachs（高盛）**：4 个主站源 `live_ok_candidates_found`，可正常访问；部分子页面（Greater China、播客子页、会议子页）404，属 URL 配置问题而非源不可用
- **Morgan Stanley（大摩）**：全部 6 个源 `tls_handshake_failed`，疑似有 TLS 客户端指纹检测 / 反爬虫机制，需 browser-like client
- **J.P. Morgan（小摩）**：全部 4 个源 `tls_handshake_failed`，同上
- **BofA（美银）**：4 个源中，2 个 `dns_resolution_failed`（主域名可能已变更），2 个 `tls_handshake_failed`
- **Citi（花旗）**：4 个源混合了 DNS 失败和 TLS 失败，需先验证 URL 正确性
- **UBS（瑞银）**：全部 3 个源 `tls_handshake_failed`
- **Barclays（巴克莱）**：1 个源正常（Our Insights），2 个源 404（Research / IB Research 子页）
- **Deutsche Bank（德银）**：1 个会议源 `tls_handshake_failed`

## 6. Needs Connector 清单

这些源目前还没有对应的 connector，需要后续开发。

| source_id | source_name | group | access_mode | 备注 |
|---|---|---|---|---|
| goldman_sachs_china_wechat | 高盛中国（微信公众号） | chinese_rebroadcast | manual | Unsupported access_mode: manual |
| morgan_stanley_china_wechat | 摩根士丹利中国（微信公众号） | chinese_rebroadcast | manual | Unsupported access_mode: manual |
| morgan_stanley_fund_wechat | 摩根士丹利基金研究报告（微信公众号） | chinese_rebroadcast | manual | Unsupported access_mode: manual |
| yanbaoshe_wechat | 研报社（微信公众号） | chinese_rebroadcast | manual | Unsupported access_mode: manual |
| touyan_circle_wechat | 投研圈类账号（微信公众号） | chinese_rebroadcast | manual | Unsupported access_mode: manual |
| wechat_secondary_broadcast | 部分微信公众号二次传播源 | chinese_rebroadcast | manual | Unsupported access_mode: manual |

## 7. Parser Mismatch 清单

这些源能访问，但当前解析规则不匹配。

暂无。

## 8. Failed 源清单（按归因分组）

### 8.1 TLS/SSL Handshake Failed（需 browser-like connector）

Morgan Stanley / J.P. Morgan / UBS 等投行站点在 TLS 握手阶段断开连接，疑似检测到非浏览器客户端指纹。当前 urllib 无法绕过，后续可考虑 browser-like connector。

| source_id | source_name | group |
|---|---|---|
| morgan_stanley_insights | Morgan Stanley Insights | official_public_research |
| morgan_stanley_research | Morgan Stanley Research | official_public_research |
| morgan_stanley_china | Morgan Stanley China | official_public_research |
| morgan_stanley_fund_research | Morgan Stanley 基金研究报告 | official_public_research |
| jp_morgan_global_research_reports | J.P. Morgan Global Research Reports | official_public_research |
| jp_morgan_insights | J.P. Morgan Insights | official_public_research |
| jp_morgan_research_insights | J.P. Morgan Research Insights | official_public_research |
| bofa_global_research_insights | BofA Global Research and Market Insights | official_public_research |
| bofa_weekly_market_recap | BofA Weekly Market Recap | official_public_research |
| citi_research | Citi Research | official_public_research |
| citi_gps | Citi GPS | official_public_research |
| ubs_global_research | UBS Global Research | official_public_research |
| ubs_cio_insights | UBS CIO Insights | official_public_research |
| ubs_investment_bank_insights | UBS Investment Bank Insights | official_public_research |
| bofa_global_research_unlocked | BofA Global Research Unlocked | official_podcast_transcript |
| ubs_global_research_pod_hub | UBS Global Research Pod Hub | official_podcast_transcript |
| morgan_stanley_thoughts_podcast | Morgan Stanley Thoughts on the Market (Podcast) | official_podcast_transcript |
| jp_morgan_research_insights_podcast | J.P. Morgan Research Insights (Podcast) | official_podcast_transcript |
| morgan_stanley_tmt_conference | Morgan Stanley Technology, Media & Telecom Conference | bank_conference_transcripts |
| bofa_global_tech_conference | BofA Global Technology Conference | bank_conference_transcripts |
| deutsche_bank_tech_conference | Deutsche Bank Technology Conference | bank_conference_transcripts |

### 8.2 DNS Resolution Failed（需 URL verification）

域名解析失败，可能是 URL 配置错误或域名已变更，需逐一验证。

| source_id | source_name | group |
|---|---|---|
| bofa_global_research | BofA Global Research | official_public_research |
| bofa_must_read_research | BofA Must Read Research | official_public_research |
| citi_institute | Citi Institute | official_public_research |
| china_fund_news | 中国基金报 | chinese_rebroadcast |
| hk_stock_research | 港股研究社 | chinese_rebroadcast |

### 8.3 HTTP Error（4xx）

HTTP 协议层错误，各有不同原因。

| source_id | source_name | group | HTTP 状态码 | 可能原因 |
|---|---|---|---|---|
| goldman_sachs_greater_china | Goldman Sachs Greater China 我们的观点 | official_public_research | 404 | URL 变更或页面下线 |
| barclays_research | Barclays Research | official_public_research | 404 | URL 变更或页面下线 |
| barclays_ib_research | Barclays Investment Bank Research | official_public_research | 404 | URL 变更或页面下线 |
| goldman_sachs_exchanges | Goldman Sachs Exchanges | official_podcast_transcript | 404 | URL 变更或页面下线 |
| goldman_sachs_the_markets | Goldman Sachs The Markets | official_podcast_transcript | 404 | URL 变更或页面下线 |
| goldman_sachs_top_of_mind_podcast | Goldman Sachs Top of Mind (Podcast) | official_podcast_transcript | 404 | URL 变更或页面下线 |
| goldman_sachs_communacopia | Goldman Sachs Communacopia + Technology Conference | bank_conference_transcripts | 404 | 年度会议页面非全年可访问 |
| barclays_global_tech_conference | Barclays Global Technology Conference | bank_conference_transcripts | 404 | 同上 |
| bernstein_strategic_decisions | Bernstein Strategic Decisions Conference | bank_conference_transcripts | 404 | 同上 |
| texas_instruments_ir | Texas Instruments Investor Relations | bank_conference_transcripts | 404 | URL 变更 |
| merck_ir | Merck Investor Relations | bank_conference_transcripts | 404 | URL 变更 |
| reuters | Reuters | media_research_mentions | 401 | 需要登录/认证 |
| marketwatch | MarketWatch | media_research_mentions | 401 | 需要登录/认证 |
| marketwatch_upgrades_downgrades | MarketWatch Upgrades/Downgrades | analyst_actions | 401 | 需要登录/认证 |
| wsj_upgrades_downgrades | WSJ Market Data Upgrades/Downgrades | analyst_actions | 401 | 需要订阅 |
| investing_com_analyst_ratings | Investing.com Analyst Ratings | analyst_actions | 403 | 反爬虫 / 地区限制 |
| streetinsider | StreetInsider | analyst_actions | 403 | 反爬虫 |
| tipranks | TipRanks | analyst_actions | 403 | 反爬虫 |
| benzinga_analyst_ratings | Benzinga Analyst Ratings | analyst_actions | 404 | URL 变更 |
| jiwen_vip_public | 见闻VIP公开文章 | chinese_rebroadcast | 404 | URL 变更 |
| cls_cn | 财联社 | chinese_rebroadcast | 418 | 反爬虫（I'm a teapot） |

## 9. Blocked / High Risk 源确认

以下源按策略禁止访问，确认全部标记为 `blocked_by_policy`，且 `visited=false`。

| source_id | source_name | group | visited | fetched |
|---|---|---|---|---|
| telegram_groups | Telegram群 | blocked_high_risk_sources | false ✅ | false ✅ |
| cloud_drive_share | 网盘分享 | blocked_high_risk_sources | false ✅ | false ✅ |
| pdf_download_sites | 研报PDF下载站 | blocked_high_risk_sources | false ✅ | false ✅ |
| unknown_wechat_pdf | 不明来源公众号PDF包 | blocked_high_risk_sources | false ✅ | false ✅ |
| report_download_proxy | 研报代下载站 | blocked_high_risk_sources | false ✅ | false ✅ |

## 10. On-Demand / Search Provider 源确认

以下源是按需/搜索 provider，确认未默认运行。

| source_id | source_name | group | visited | fetched | 备注 |
|---|---|---|---|---|---|
| tavily_search | Tavily Search | search_providers | false ✅ | false ✅ | Search provider: on-demand only, not run by default |
| brave_search | Brave Search | search_providers | false ✅ | false ✅ | Search provider: on-demand only, not run by default |
| serpapi | SerpAPI | search_providers | false ✅ | false ✅ | Search provider: on-demand only, not run by default |
| bing_search | Bing | search_providers | false ✅ | false ✅ | Search provider: on-demand only, not run by default |
| google_cse | Google CSE | search_providers | false ✅ | false ✅ | Search provider: on-demand only, not run by default |
| searx | Searx | search_providers | false ✅ | false ✅ | Search provider: on-demand only, not run by default |
| duckduckgo | DuckDuckGo | search_providers | false ✅ | false ✅ | Search provider: on-demand only, not run by default |
| yahoo_search | Yahoo Search | search_providers | false ✅ | false ✅ | Search provider: on-demand only, not run by default |
| baidu_search | Baidu Search | search_providers | false ✅ | false ✅ | Search provider: on-demand only, not run by default |
| custom_search | Custom Search | search_providers | false ✅ | false ✅ | Search provider: on-demand only, not run by default |

## 11. 后续建议

### 11.1 可进入 TRAE 试运行的源

状态为 `live_ok_candidates_found` 或 `live_ok` 的 scheduled 源，共 16 个。

**投行官方公开研究（5）：**
- `goldman_sachs_research`（Goldman Sachs Research）— 候选 6 个
- `goldman_sachs_reports`（Goldman Sachs Reports）— 候选 6 个
- `goldman_sachs_top_of_mind`（Goldman Sachs Top of Mind）— 候选 6 个
- `goldman_sachs_insights`（Goldman Sachs Insights）— 候选 6 个
- `barclays_our_insights`（Barclays Our Insights）— 候选 6 个

**投行会议纪要/公司 IR（1）：**
- `microsoft_ir`（Microsoft Investor Relations）— 候选 6 个

**媒体研报二次引用（3）：**
- `yahoo_finance`（Yahoo Finance）— 候选 6 个
- `business_insider`（Business Insider）— 候选 6 个
- `markets_insider`（Markets Insider）— 候选 6 个

**分析师评级/目标价变动（2）：**
- `the_fly`（The Fly）— 候选 6 个
- `briefing_com_upgrades`（Briefing.com Upgrades/Downgrades）

**中文财经二次传播（5）：**
- `wallstreet_cn`（华尔街见闻）— 候选 6 个
- `cls_cn`（财联社）— 候选 6 个
- `wind_public`（Wind 万得公开内容）— 候选 6 个
- `gelonghui`（格隆汇）— 候选 6 个
- `zhitong_caijing`（智通财经）— 候选 6 个

### 11.2 需要 URL Verification 的源

DNS 解析失败、404、URL 疑似变更的源，需人工验证 URL 是否正确，或寻找替代入口。共约 20 个。

**DNS 解析失败（5）：**
- `bofa_global_research`（BofA Global Research）
- `bofa_must_read_research`（BofA Must Read Research）
- `citi_institute`（Citi Institute）
- `china_fund_news`（中国基金报）
- `hk_stock_research`（港股研究社）

**404 / URL 可能变更（~15）：**
- `goldman_sachs_greater_china`、`barclays_research`、`barclays_ib_research`
- Goldman Sachs 播客子页 × 3
- 会议子页 × 6（含 conference 类和 IR 类）
- `benzinga_analyst_ratings`、`jiwen_vip_public`

### 11.3 需要 Browser-Like Connector 的源

TLS/SSL 握手失败的源，疑似有客户端指纹检测，urllib 无法访问，需后续引入 browser-like connector（如 Playwright）后再验证。共约 21 个。

**Morgan Stanley（6）：**
- `morgan_stanley_insights`、`morgan_stanley_research`、`morgan_stanley_thoughts_on_market`
- `morgan_stanley_china`、`morgan_stanley_fund_research`
- `morgan_stanley_thoughts_podcast`

**J.P. Morgan（5）：**
- `jp_morgan_research`、`jp_morgan_global_research_reports`、`jp_morgan_insights`
- `jp_morgan_research_insights`、`jp_morgan_research_insights_podcast`

**UBS（4）：**
- `ubs_global_research`、`ubs_cio_insights`、`ubs_investment_bank_insights`
- `ubs_global_research_pod_hub`

**BofA（部分，3）：**
- `bofa_global_research_insights`、`bofa_weekly_market_recap`、`bofa_global_research_unlocked`

**Citi（部分，2）：**
- `citi_research`、`citi_gps`

**其他（1）：**
- `deutsche_bank_tech_conference`

### 11.4 需要补 Connector 的源

access_mode=manual 或其他非标准模式的源，需开发专用 connector。共 6 个（均为微信公众号）。

- `goldman_sachs_china_wechat`（高盛中国（微信公众号））
- `morgan_stanley_china_wechat`（摩根士丹利中国（微信公众号））
- `morgan_stanley_fund_wechat`（摩根士丹利基金研究报告（微信公众号））
- `yanbaoshe_wechat`（研报社（微信公众号））
- `touyan_circle_wechat`（投研圈类账号（微信公众号））
- `wechat_secondary_broadcast`（部分微信公众号二次传播源）

### 11.5 建议继续 Blocked 的源

- `telegram_groups`（Telegram群）
- `cloud_drive_share`（网盘分享）
- `pdf_download_sites`（研报PDF下载站）
- `unknown_wechat_pdf`（不明来源公众号PDF包）
- `report_download_proxy`（研报代下载站）

## 12. S/A/B/C 优先级接通情况

*待 source inventory 配置中完善 priority 字段后补充。*
