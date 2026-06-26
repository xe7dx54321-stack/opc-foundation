# TRAE 试运行候选源清单

> 版本：1.0  
> 生成时间：2026-06-26  
> 候选源数：16  
> 依据：M3C-2B Live Smoke + Triage 分桶

## 1. 概述

本清单列出可进入 TRAE 试运行的候选信息源。入选标准：

1. Live smoke 状态为 `live_ok` 或 `live_ok_candidates_found`
2. `access_mode` 为 `public_web` 或 `company_ir`（非 manual / 非 search_provider）
3. 非 blocked / 非 on-demand / 非 dormant
4. 不需要特殊 connector（如 wechat_archive）

---

## 2. 候选源清单（16 个）

### 2.1 投行官方公开研究（5 个）

| source_id | source_name | access_mode | recommended_frequency | 最近状态 | 代理需求 | 特殊 connector | 风险备注 |
|---|---|---|---|---|---|---|---|
| goldman_sachs_research | Goldman Sachs Research | public_web | 每天 1-2 次 | live_ok_candidates_found | 不需要 | 无 | 官方公开页面，合规度高 |
| goldman_sachs_reports | Goldman Sachs Reports | public_web | 每天 1-2 次 | live_ok_candidates_found | 不需要 | 无 | 官方公开页面 |
| goldman_sachs_top_of_mind | Goldman Sachs Top of Mind | public_web | 每周 1-2 次 | live_ok_candidates_found | 不需要 | 无 | 专题报告，更新频率低 |
| goldman_sachs_insights | Goldman Sachs Insights | public_web | 每天 1 次 | live_ok_candidates_found | 不需要 | 无 | 综合 insight 总览页 |
| barclays_our_insights | Barclays Our Insights | public_web | 每天 1 次 | live_ok_candidates_found | 不需要 | 无 | 注意 301 重定向到 home.barclays |

### 2.2 投行会议纪要 / 公司 IR（1 个）

| source_id | source_name | access_mode | recommended_frequency | 最近状态 | 代理需求 | 特殊 connector | 风险备注 |
|---|---|---|---|---|---|---|---|
| microsoft_ir | Microsoft Investor Relations | company_ir | 每周 1 次 | live_ok_candidates_found | 不需要 | 无 | IR 页面，季报期间更新多 |

### 2.3 媒体研报二次引用（3 个）

| source_id | source_name | access_mode | recommended_frequency | 最近状态 | 代理需求 | 特殊 connector | 风险备注 |
|---|---|---|---|---|---|---|---|
| yahoo_finance | Yahoo Finance | public_web | 每天 2-3 次 | live_ok_candidates_found | 不需要 | 无 | 主流财经媒体，数据量大 |
| business_insider | Business Insider | public_web | 每天 2 次 | live_ok_candidates_found | 不需要 | 无 | 商业新闻类，注意噪音多 |
| markets_insider | Markets Insider | public_web | 每天 2 次 | live_ok_candidates_found | 不需要 | 无 | Business Insider 旗下市场频道 |

### 2.4 分析师评级 / 目标价变动（2 个）

| source_id | source_name | access_mode | recommended_frequency | 最近状态 | 代理需求 | 特殊 connector | 风险备注 |
|---|---|---|---|---|---|---|---|
| the_fly | The Fly | public_web | 每天 3-4 次 | live_ok_candidates_found | 不需要 | 无 | 快讯类，更新频繁 |
| briefing_com_upgrades | Briefing.com Upgrades/Downgrades | public_web | 每天 1 次 | live_ok | 不需要 | 无 | 仅登记 metadata，不做投资判断 |

### 2.5 中文财经二次传播（5 个）

| source_id | source_name | access_mode | recommended_frequency | 最近状态 | 代理需求 | 特殊 connector | 风险备注 |
|---|---|---|---|---|---|---|---|
| wallstreet_cn | 华尔街见闻 | public_web | 每天 2-3 次 | live_ok_candidates_found | 不需要 | 无 | 中文主流财经媒体 |
| cls_cn | 财联社 | public_web | 每天 3-4 次 | live_ok_candidates_found | 不需要 | 无 | 电报式快讯，速度快 |
| wind_public | Wind 万得公开内容 | public_web | 每天 1 次 | live_ok_candidates_found | 不需要 | 无 | 万得公开页面，内容有限 |
| gelonghui | 格隆汇 | public_web | 每天 2 次 | live_ok_candidates_found | 不需要 | 无 | 出海/港股方向 |
| zhitong_caijing | 智通财经 | public_web | 每天 2 次 | live_ok_candidates_found | 不需要 | 无 | 港股方向 |

---

## 3. 试运行建议节奏

### 第一阶段（先上 5 个核心源验证管道
建议先上以下 5 个，验证采集管道和数据质量：

1. `goldman_sachs_insights（高盛官方，质量高）
2. `yahoo_finance`（媒体源，数据量大）
3. `the_fly`（快讯源，验证实时性）
4. `wallstreet_cn`（中文源，验证中文解析）
5. `microsoft_ir`（IR 源，验证结构化提取）

### 第二阶段（再上 11 个）
管道稳定后，逐步加入剩余 11 个源。

---

## 4. 不纳入试运行的源及原因

| 分类 | 数量 | 原因 |
|---|---|---|
| TLS 握手失败 | 21 | Morgan Stanley / J.P. Morgan / UBS 等，需 browser-like connector 或替代入口 |
| HTTP 4xx（404/403/401） | 20 | URL 失效 / 反爬 / 需要登录，待解决后再评估 |
| DNS 解析失败 | 5 | 域名失效，需寻找替代入口 |
| 微信公众号 | 6 | 需要 wechat_archive connector 映射 |
| Search Provider | 10 | 仅按需使用，不进入默认定时 |
| Dormant | 2 | 社区源，当前休眠 |
| Blocked | 5 | 高风险，禁止接入 |
| 超时待验证 | 1 | 需进一步确认 |

**不纳入合计：76 个

---

## 5. 试运行注意事项

1. **仅做元数据**：试运行阶段仅提取标题、链接、发布时间等元数据，不下载全文
2. **频率保守**：初始频率从每天 1 次开始，稳定后再调高
3. **失败告警**：配置失败率告警，连续失败 3 次自动暂停
4. **去重**：多个源可能引用同一篇研报，需要去重逻辑
5. **合规**：所有源均为公开网页，遵守 robots.txt 友好抓取
6. **不做投资判断**：仅采集和整理公开信息，不做任何投资建议
