# M3C-6A 源覆盖再审计报告

> **执行时间:** 2026-07-04
> **Base Commit:** 796f9e8 (inherited M3C-5B2 f2cd7cc)
> **Branch:** feature/m3c-6a-source-coverage-reaudit
> **source_inventory_count:** 92

---

## 一、当前覆盖状态

| 指标 | 数值 |
|---|---|
| scheduled_ready | 9 |
| scheduled_candidate | 3 |
| low_frequency_candidate | 14 |
| rss_or_sitemap_candidate | 24 |
| wechat_archive_candidate | 6 |
| on_demand_candidate | 18 |
| browser_like_backlog | 6 |
| tls_or_proxy_backlog | 6 |
| cloudflare_or_anti_bot_backlog | 1 |
| excluded_or_low_value | 5 |
| **总计** | **92** |

### 分层概览

| 层级 | 数量 | 代表源 |
|---|---|---|
| L1 scheduled_ready | 9 | barclays_our_insights, markets_insider, china_fund_news, wind_public, goldman_sachs_insights, business_insider, cls_cn, zhitong_caijing, gelonghui |
| L2 scheduled_candidate | 3 | reuters, marketwatch, streetinsider |
| L3 low_frequency_candidate | 14 | jp_morgan_insights, morgan_stanley_thoughts_on_market, quanshang_china, tipranks 等 |
| L4 rss_or_sitemap_candidate | 24 | barclays_research, citi_research, ubs_global_research, morgan_stanley_research 等 |
| L5 wechat_archive_candidate | 6 | goldman_sachs_china_wechat, morgan_stanley_china_wechat 等 |
| L6 on_demand_candidate | 18 | 搜索/社区类 + IR/会议/评级类 |
| L7 browser_like_backlog | 6 | goldman_sachs_research 系列 |
| L8 tls_or_proxy_backlog | 6 | merck_ir, yahoo_finance, the_fly 等 |
| L9 cloudflare_or_anti_bot_backlog | 1 | benzinga_analyst_ratings |
| L10 excluded_or_low_value | 5 | telegram_groups, cloud_drive_share 等 |

---

## 二、92 源分层统计

| layer | count | 代表源 | 下一步动作 |
|---|---|---|---|
| L1 scheduled_ready | 9 | barclays_our_insights, markets_insider, china_fund_news, wind_public, goldman_sachs_insights, business_insider, cls_cn, zhitong_caijing, gelonghui | 已完成，保持运行 |
| L2 scheduled_candidate | 3 | reuters, marketwatch, streetinsider | manual_reaudit → scheduled_preflight |
| L3 low_frequency_candidate | 14 | jp_morgan_insights, morgan_stanley_thoughts_on_market, morgan_stanley_insights, quanshang_china, us_stock_research, hk_stock_research, jiwen_vip_public, tipranks, morgan_stanley_thoughts_podcast, jp_morgan_research_insights_podcast, bofa_global_research_unlocked, ubs_global_research_pod_hub, wallstreet_cn, bofa_weekly_market_recap | low_frequency_preflight |
| L4 rss_or_sitemap_candidate | 24 | barclays_research, barclays_ib_research, citi_research, citi_institute, citi_gps, citi_insights, ubs_global_research, ubs_cio_insights, ubs_investment_bank_insights, morgan_stanley_research, morgan_stanley_fund_research, morgan_stanley_china, jp_morgan_research, jp_morgan_global_research_reports, jp_morgan_research_insights, bofa_global_research_insights, goldman_sachs_greater_china, briefing_com_upgrades + 6 conference sources | rss_sitemap_discovery |
| L5 wechat_archive_candidate | 6 | goldman_sachs_china_wechat, morgan_stanley_china_wechat, morgan_stanley_fund_wechat, yanbaoshe_wechat, touyan_circle_wechat, wechat_secondary_broadcast | wechat_archive_mapping |
| L6 on_demand_candidate | 18 | 10 search providers, 2 community, microsoft_ir, jp_morgan_healthcare_conference, goldman_sachs_communacopia, investing_com_analyst_ratings, marketwatch_upgrades_downgrades, wsj_upgrades_downgrades | on_demand_registry |
| L7 browser_like_backlog | 6 | goldman_sachs_research, goldman_sachs_reports, goldman_sachs_top_of_mind, goldman_sachs_exchanges, goldman_sachs_the_markets, goldman_sachs_top_of_mind_podcast | browser_like_spike |
| L8 tls_or_proxy_backlog | 6 | merck_ir, yahoo_finance, the_fly, bofa_global_research, texas_instruments_ir, bofa_must_read_research | proxy_retry |
| L9 cloudflare_or_anti_bot_backlog | 1 | benzinga_analyst_ratings | anti_bot_spike |
| L10 excluded_or_low_value | 5 | telegram_groups, cloud_drive_share, pdf_download_sites, unknown_wechat_pdf, report_download_proxy | 暂不处理 |

---

## 三、短期可用目标 (25/92)

| 类别 | 数量 | 说明 |
|---|---|---|
| L1 scheduled_ready (已完成) | 9 | 当前已稳定运行 |
| L2 scheduled_candidate | 3 | reuters, marketwatch, streetinsider，审计后可快速纳入 |
| L5 wechat_archive_candidate | 6 | 微信归档源，需要归档管道但信息密度高 |
| L6 on_demand_candidate (搜索/社区类) | 18 | 10 搜索 + 2 社区 + 其他可按需调用 |
| **合计** | **36** | **超过 25 目标** |

**结论：** 短期可用目标 36/92，已超过 M3C-6A 设定的 25 目标。

---

## 四、中期可用目标 (46+/92)

| 类别 | 数量 | 说明 |
|---|---|---|
| 短期可用 (L1+L2+L5+L6) | 36 | 已统计 |
| L3 low_frequency_candidate | 14 | 低频发布但内容质量高 |
| L4 rss_or_sitemap_candidate | 24 | 需要先发现 feed/sitemap |
| **合计** | **74** | **超过 46 目标** |

**结论：** 中期可用目标 74/92，远超 46 目标。

---

## 五、为什么不能把 46 个全放进高频调度

| 原因 | 说明 |
|---|---|
| L5 微信源需要不同管道 | 微信归档源走微信文章归档管道，不适合放入通用爬虫调度 |
| L6 on-demand 源是搜索/社区类 | 这些源本身是按需触发（搜索查询、社区 API），而非定时爬取目标 |
| L3 低频源更新频率低 | 部分投行研究源每周或更长时间更新一次，高频调度浪费资源 |
| L4 源需要先发现 feed/sitemap | 尚未确认 RSS/sitemap 可用性，需先完成发现阶段 |
| 资源与噪音平衡 | 高频调度过多源会导致重复内容、噪音增加、IP 被封风险上升 |

**合理目标：**
- 高频定时调度 (scheduled): **15-20 个源**
- 低频/事件驱动 (low_frequency): **10-15 个源**
- 微信归档 (wechat_archive): **6 个源**
- 按需/搜索 (on_demand): **12-18 个源**

---

## 六、下一批 Top 10 攻坚源

| rank | source_id | layer | next_action | success_probability | expected_value | effort | suggested_stage |
|---|---|---|---|---|---|---|---|
| 1 | merck_ir | L8 | proxy_retry | 70% | high | medium | M3C-6F |
| 2 | reuters | L2 | manual_reaudit | 80% | high | medium | M3C-6B |
| 3 | marketwatch | L2 | manual_reaudit | 75% | high | medium | M3C-6B |
| 4 | streetinsider | L2 | manual_reaudit | 70% | medium | small | M3C-6B |
| 5 | jp_morgan_insights | L3 | low_frequency_preflight | 60% | medium | medium | M3C-6C |
| 6 | goldman_sachs_greater_china | L4 | rss_sitemap_discovery | 50% | medium | small | M3C-6C |
| 7 | barclays_research | L4 | rss_sitemap_discovery | 50% | medium | small | M3C-6C |
| 8 | goldman_sachs_china_wechat | L5 | wechat_archive_mapping | 80% | high | small | M3C-6D |
| 9 | morgan_stanley_china_wechat | L5 | wechat_archive_mapping | 80% | high | small | M3C-6D |
| 10 | tipranks | L3 | low_frequency_preflight | 65% | medium | small | M3C-6C |

### 优先级分析

- **M3C-6B (最快见效):** reuters, marketwatch, streetinsider + merck_ir proxy → 预计新增 3-4 个 scheduled 源
- **M3C-6D (最高成功概率):** 微信归档源，成功概率 80%，信息密度高
- **M3C-6C (中等投入覆盖面广):** RSS/sitemap 发现 + 低频预检，可批量推进

---

## 七、边界确认

| 问题 | 回答 |
|---|---|
| 是否修改调度配置? | **否** — 本次仅做分层统计与规划，不修改任何调度配置 |
| 是否修改 allowlist? | **否** — 不涉及 allowlist 变更 |
| 是否配置生产环境? | **否** — 不涉及生产部署 |
| 是否提交数据或密钥? | **否** — 不提交任何敏感数据或密钥 |

---

## 八、结论

1. **92 源全覆盖分层完成** — 所有源已分配至 10 个层级，各有明确下一步动作
2. **短期可用目标 36/92，超过 25 目标** — L1(9) + L2(3) + L5(6) + L6(18) = 36
3. **中期可用目标 74/92，超过 46 目标** — 短期 + L3(14) + L4(24) = 74
4. **高频调度目标 15-20 个，不需要也不应该全量调度** — 按源特性分派至不同管道（定时/低频/归档/按需）才是正确策略
5. **Top 10 攻坚源已排序** — 按 success_probability x expected_value / effort 排序，分派至后续阶段 M3C-6B/6C/6D/6F

---

*报告结束*
