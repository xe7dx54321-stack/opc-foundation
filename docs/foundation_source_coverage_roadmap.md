# M3C-6A Source Coverage Roadmap

> **日期:** 2026-07-04
> **Base Commit:** 796f9e8 (inherited M3C-5B2 f2cd7cc)

---

## 一、覆盖系统四层目标

| 层级 | 名称 | 当前 | 目标 | 说明 |
|---|---|---|---|---|
| 第一层 | 高频定时调度 (scheduled_ready) | 9 | 15-20 | 已有 9 个稳定运行源，目标扩展至 15-20 |
| 第二层 | 低频/事件驱动 (low_frequency + rss/sitemap) | 0 | 10-15 | 投行研究源、低频更新源 |
| 第三层 | 微信归档 (wechat_archive) | 0 | 6 | 微信公众号文章归档管道 |
| 第四层 | 按需/搜索 (on_demand) | 0 | 12 | 搜索引擎、社区平台、事件触发查询 |

---

## 二、覆盖率曲线

| 阶段 | scheduled | low_freq | wechat | on_demand | 总可用 | 覆盖率 |
|---|---|---|---|---|---|---|
| 当前 (M3C-6A) | 9 | 0 | 0 | 18 | 27 | 29% |
| M3C-6B 之后 | 12-15 | 0 | 0 | 18 | 30-33 | 33-36% |
| M3C-6C 之后 | 12-15 | 8-12 | 0 | 18 | 38-45 | 41-49% |
| M3C-6D 之后 | 12-15 | 8-12 | 4-6 | 18 | 42-51 | 46-55% |
| M3C-6F 之后 | 15-20 | 8-12 | 4-6 | 18 | 45-56 | 49-61% |

### 覆盖率说明

- **总可用** = scheduled + low_freq + wechat + on_demand（不重复计数）
- **覆盖率** = 总可用 / 92 源总数
- 当前 18 个 on_demand 源（搜索/社区类）已可按需调用，但尚未正式注册到覆盖系统中
- M3C-6B 后 reuters, marketwatch, streetinsider 预计 2-3 个通过审计进入 scheduled
- M3C-6C 后投行研究源通过 RSS/sitemap 发现预计 8-12 个进入 low_freq
- M3C-6D 后微信归档源预计 4-6 个进入 wechat 层
- M3C-6F 后 proxy retry 预计 3-5 个额外源进入 scheduled

---

## 三、后续阶段路线图

### M3C-6B: scheduled_candidate 预检 + proxy 试探

**目标:** 将 reuters, marketwatch, streetinsider 纳入定时调度，同时试探 merck_ir proxy 可行性

| 任务 | 源 | 动作 | 预期产出 |
|---|---|---|---|
| Reuters 审计 | reuters | manual_reaudit → scheduled_preflight | 确认可调度性，评估更新频率与内容质量 |
| MarketWatch 审计 | marketwatch | manual_reaudit → scheduled_preflight | 同上 |
| StreetInsider 审计 | streetinsider | manual_reaudit → scheduled_preflight | 同上 |
| Merck IR Proxy 试探 | merck_ir | proxy_retry → 成功则加入 scheduled | TLS/proxy 障碍测试 |

**预计新增:** 3-6 个 scheduled 源

---

### M3C-6C: 低频 / RSS / sitemap 发现

**目标:** 批量发现投行研究源的 RSS/sitemap，建立低频调度管道

| 任务 | 源类别 | 动作 | 预期产出 |
|---|---|---|---|
| RSS/sitemap 发现 | 24 个 L4 源 | rss_sitemap_discovery → 筛选可订阅源 | 确认哪些源有可用 feed |
| 低频预检 | 14 个 L3 源 | low_frequency_preflight → 评估可调度性 | 确认更新频率与内容质量 |
| 低频调度配置 | 通过预检的源 | 创建 low_frequency schedule | 纳入低频调度管道 |

**预计新增:** 8-12 个 low_freq 源

---

### M3C-6D: 微信归档映射

**目标:** 建立 6 个微信源的归档管道

| 任务 | 源 | 动作 | 预期产出 |
|---|---|---|---|
| 微信归档映射 | goldman_sachs_china_wechat | wechat_archive_mapping | 确认归档可用性 |
| 微信归档映射 | morgan_stanley_china_wechat | wechat_archive_mapping | 确认归档可用性 |
| 微信归档映射 | morgan_stanley_fund_wechat | wechat_archive_mapping | 确认可用性 |
| 微信归档映射 | yanbaoshe_wechat | wechat_archive_mapping | 确认可用性 |
| 微信归档映射 | touyan_circle_wechat | wechat_archive_mapping | 确认可用性 |
| 微信归档映射 | wechat_secondary_broadcast | wechat_archive_mapping | 确认可用性 |

**预计新增:** 4-6 个 wechat 源（成功概率 80%）

---

### M3C-6E: on-demand 源注册

**目标:** 将 18 个按需源正式注册到覆盖系统

| 任务 | 源类别 | 动作 | 预期产出 |
|---|---|---|---|
| 搜索引擎注册 | 10 search providers | on_demand_registry | 搜索查询管道配置 |
| 社区平台注册 | 2 community | on_demand_registry | 社区查询管道配置 |
| 事件/IR 注册 | microsoft_ir, conferences | on_demand_registry | 事件触发管道配置 |
| 评级/升级注册 | investing_com, marketwatch_ud, wsj_ud | on_demand_registry | 评级查询管道配置 |

**预计新增:** 12-18 个 on_demand 源（功能已有，主要是正式注册）

---

### M3C-6F: proxy retry 批量处理

**目标:** 解决 L8 层 6 个源的 TLS/proxy 障碍

| 任务 | 源 | 动作 | 预期产出 |
|---|---|---|---|
| Merck IR | merck_ir | proxy_retry | M3C-6B 试探结果，正式纳入 |
| Yahoo Finance | yahoo_finance | proxy_retry | 评估 TLS 指纹兼容性 |
| The Fly | the_fly | proxy_retry | 评估反爬机制 |
| BofA Global Research | bofa_global_research | proxy_retry | 评估 TLS 障碍 |
| Texas Instruments IR | texas_instruments_ir | proxy_retry | 评估 IR 页面可达性 |
| BofA Must Read | bofa_must_read_research | proxy_retry | 评估研究页面可达性 |

**预计新增:** 3-5 个 scheduled 源

---

### M3C-6G: browser-like 可行性探索

**目标:** 评估 Goldman Sachs 系列 6 个源是否需要浏览器模拟管道

| 任务 | 源 | 动作 | 预期产出 |
|---|---|---|---|
| GS Research | goldman_sachs_research | browser_like_spike | 评估 JS 渲染需求 |
| GS Reports | goldman_sachs_reports | browser_like_spike | 同上 |
| GS Top of Mind | goldman_sachs_top_of_mind | browser_like_spike | 同上 |
| GS Exchanges | goldman_sachs_exchanges | browser_like_spike | 同上 |
| GS The Markets | goldman_sachs_the_markets | browser_like_spike | 同上 |
| GS Top of Mind Podcast | goldman_sachs_top_of_mind_podcast | browser_like_spike | 同上 |

**预计新增:** 0-6 个源（取决于可行性探索结果）

---

## 四、定时调度目标

### 核心原则

> **不要把 46 个全放进高频调度**

### 原因分析

| 风险 | 说明 |
|---|---|
| 资源浪费 | 部分源每周或更久更新一次，高频爬取无意义 |
| 噪音增加 | 低质量源的重复内容会稀释信号质量 |
| 封禁风险 | 过多请求频率导致 IP 被目标站封禁 |
| 管道不匹配 | 微信源、搜索源需要各自的专用管道 |

### 合理分配

| 管道类型 | 目标数量 | 适用源特征 |
|---|---|---|
| scheduled (高频定时) | **15-20** | 更新频率 >= 日更，内容稳定，可直接爬取 |
| low_frequency (低频/事件) | **10-15** | 更新频率 <= 周更，通过 RSS/sitemap 订阅 |
| wechat_archive (微信归档) | **6** | 微信公众号文章，走微信归档管道 |
| on_demand (按需/搜索) | **12-18** | 搜索引擎、社区平台，按需触发 |

### 各管道源分配规划

**scheduled (目标 15-20):**
- 当前已有: barclays_our_insights, markets_insider, china_fund_news, wind_public, goldman_sachs_insights, business_insider, cls_cn, zhitong_caijing, gelonghui (9)
- M3C-6B 预计新增: reuters, marketwatch, streetinsider, merck_ir (3-4)
- M3C-6F 预计新增: yahoo_finance, the_fly, bofa_must_read_research (0-3)
- 预计最终: 12-19

**low_frequency (目标 10-15):**
- M3C-6C 预计新增: jp_morgan_insights, morgan_stanley_thoughts_on_market, quanshang_china, us_stock_research, hk_stock_research, jiwen_vip_public, tipranks, wallstreet_cn, bofa_weekly_market_recap + RSS 发现源 (8-12)

**wechat_archive (目标 6):**
- M3C-6D 预计新增: goldman_sachs_china_wechat, morgan_stanley_china_wechat, morgan_stanley_fund_wechat, yanbaoshe_wechat, touyan_circle_wechat, wechat_secondary_broadcast (4-6)

**on_demand (目标 12-18):**
- M3C-6E 正式注册: 10 search providers, 2 community, microsoft_ir, conferences, rating sources (12-18)

---

## 五、总结

| 阶段 | 核心产出 | 覆盖率提升 |
|---|---|---|
| M3C-6A (当前) | 92 源全覆盖分层，路线图制定 | 29% (27/92) |
| M3C-6B | scheduled +3-6 | 33-36% |
| M3C-6C | low_freq +8-12 | 41-49% |
| M3C-6D | wechat +4-6 | 46-55% |
| M3C-6E | on_demand 正式注册 | 不变（已有功能） |
| M3C-6F | proxy_retry +3-5 | 49-61% |
| M3C-6G | browser-like 可行性探索 | 视结果而定 |

**核心观点:** 覆盖系统不需要也绝不应该追求全量高频调度。按源特性分派至合适的管道（定时/低频/归档/按需），在 49-61% 的总覆盖率下即可覆盖绝大多数高价值信息流。

---

*路线图结束*

---

## 附录 A：M3C-6F 更新（2026-07-04）

**阶段:** M3C-6F — Proxy Retry Batch  
**结论:** 无新增 scheduled_candidate，无新增 low_frequency

| source_id | prior_status | M3C-6F 结果 | 去向 | 说明 |
|---|---|---|---|---|
| merck_ir | content_ready_then_network_unreachable | manual_review_only | 需要专门提取路径重做 preflight | Direct 可达但首页通用抓取只能拿到导航链接，不是新闻/事件条目；历史上 M3C-5B1 曾达 content_ready（score 90），应使用专门提取路径 |
| the_fly | tls_or_proxy_backlog | timeout | 继续 tls_or_proxy_backlog | Direct 模式超时，当前网络环境不可达；待代理环境重试 |
| yahoo_finance | tls_or_proxy_backlog | login_or_paywall_blocked | 待人工确认 | Direct 可达但检测到 login/paywall 提示，且通用首页抓取内容质量低；需人工确认阻断程度及 RSS/API 替代入口 |

**覆盖率影响:** 无变化（scheduled 仍为 9）

**核心教训:**
1. 通用首页锚点提取不等于内容就绪，需专门的新闻/事件提取路径
2. merck_ir 历史上曾通过专门提取路径达到 content_ready，应复用而非从零开始
3. the_fly 需代理环境进一步验证
4. yahoo_finance 需人工确认 login/paywall 实际阻断程度

---

## 附录 B：M3C-6F.1 更新（2026-07-05）

**阶段:** M3C-6F.1 — Merck IR Dedicated Extraction Preflight
**结论:** merck_ir 从 manual_review_only 提升为 low_frequency_candidate

| source_id | M3C-6F 结果 | M3C-6F.1 结果 | 去向 | 说明 |
|---|---|---|---|---|
| merck_ir | manual_review_only | low_frequency_candidate | 评估低频调度 | 使用专门 IR 路径过滤后提取到 15 个真实 IR items（财报电话会议、医疗健康会议），无 login/paywall/captcha 阻断，但无法从列表页 HTML 提取日期（dated=0） |

**覆盖率影响:** low_freq 候选 +1（merck_ir），scheduled 仍为 9

**关键改进:**
1. 使用 M3C-5B1 验证过的 IR 路径模式（/news/, /events/, /presentations/）替代通用首页抓取
2. 扩展噪音过滤从 13 到 20 个 pattern
3. 精确化 login/paywall/captcha 检测，避免 false positive
4. 多入口发现：IR 首页 + 新闻页 + 事件页 + sitemap + RSS + JSON-LD

---

## 附录 C：M3C-6C 更新（2026-07-05）

**阶段:** M3C-6C — Low-frequency Source Pipeline
**结论:** 建立 low-frequency pipeline v1，merck_ir 作为第一个样板源

### 新增 source layer

```
Layer 1: trial_v2_high_frequency (9 sources, daily 3 batches) — 不变
Layer 2: low_frequency_sources (merck_ir, weekly) — 新增
Layer 3: on_demand_sources — 未实现
```

### merck_ir 低频 pipeline 结果

| 指标 | 值 |
|---|---|
| valid_item_count | 15 |
| dated_item_count | 0 |
| missing_date_count | 15 |
| timestamp_confidence | LOW |
| recommended_frequency | weekly |
| low_frequency_allowed_now | true |
| trial_v2_allowlist_allowed_now | false |

### 覆盖率影响

- scheduled (high-frequency): 9 — 不变
- low_frequency: 1 (merck_ir) — 新增
- TRAE task: proposal only, not created

### 核心能力

1. **discovered_at fallback:** date_text 缺失时使用 discovered_at 作为时间戳
2. **timestamp_confidence:** LOW/MEDIUM/HIGH/NONE 四级置信度
3. **dry-run / run-once:** 两种运行模式
4. **check script:** 自动验证配置和 runtime data 合规性
5. **TRAE task proposal:** 只生成文档，不创建真实任务
