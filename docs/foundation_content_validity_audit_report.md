# OPC Foundation M3C-5A5 Content Validity Audit Report

> 版本：2.0
> 生成时间：2026-07-02
> 执行阶段：M3C-5A5
> 配置文件：configs/foundation_content_validity_audit.example.yaml
> 输入 Allowlist：configs/foundation_trial_v2_allowlist.example.yaml
> 输出目录：data/foundation_content_validity/

---

## 1. 执行摘要

| 项目 | 值 |
|---|---|
| 执行时间 | 2026-07-02 |
| 审计模式 | Content Validity Audit（Operational Deep Audit） |
| 操作源数 | 21（operational deep audit） |
| Matrix 源数 | 92（full inventory matrix） |
| content_ready | **9** |
| content_watch | **5**（含 1 个不在 inventory 中的 consolidated 源） |
| content_reject | **2** |
| technical_only | **5** |
| 网络环境 | proxy_enabled=false, proxy_mode=none |

---

## 2. 审计范围

### 2.1 源构成

| 类别 | 数量 | 说明 |
|---|---|---|
| Trial v1 Base | 15 | 当前稳定运行的 trial 源 |
| Trial v2 Additions | 6 | M3C-5A/M3C-5A2/M3C-5A2.1 新增源 |
| Consolidated Candidate | 1 | goldman_sachs_podcasts（合并3个源为1个，**不在 inventory 中**） |
| **Operational Total** | **21** | 审计的 operational source 总数 |
| **Inventory Matrix Total** | **92** | 全量 inventory matrix 覆盖 |

### 2.2 Trial v2 Additions 详情

| source_id | source_name | candidate_type | priority | URL |
|---|---|---|---|---|
| bofa_global_research | BofA Global Research | inventory_backed | P0 | https://www.bankofamerica.com/research |
| texas_instruments_ir | Texas Instruments IR | inventory_backed | P0 | https://investor.ti.com |
| merck_ir | Merck IR | inventory_backed | P0 | https://investors.merck.com |
| benzinga_analyst_ratings | Benzinga Analyst Ratings | inventory_backed | P0 | https://www.benzinga.com/analyst-ratings |
| china_fund_news | 中国基金报 | inventory_backed | P1 | https://www.chnfund.com |
| goldman_sachs_podcasts | Goldman Sachs Podcasts | consolidated | P1 | https://www.goldmansachs.com/insights/podcasts |

### 2.3 Matrix 分布

| 范围 | 数量 | 说明 |
|---|---|---|
| deep_audit | 20 | 21 个 operational 中有 1 个（goldman_sachs_podcasts）不在 inventory 中，故 matrix 中有 20 个 deep_audit |
| matrix_only | 72 | 92 - 20 = 72，尚未分配 deep audit 资源 |
| **Matrix Total** | **92** | 全量 inventory 覆盖 |

---

## 3. 审计方法

### 3.1 内容有效性判定标准

**content_ready（内容就绪）**：
- 页面是目标页面
- 能抽取候选内容
- 候选内容与 source 目标相关
- 有标题 / URL / 时间或可推断时间
- 不是纯导航页、营销页、cookie 页、登录页
- 不需要付费或登录

**content_watch（内容观察）**：
- 页面基本相关
- 能抽到部分候选内容
- 但存在：内容偏少、时间不明确、偶发 empty、重复较多等问题

**content_reject（内容拒绝）**：
- 拿到错误页面（404/403）
- 拿到 cookie/consent/login/blocked 页面
- 页面无有效候选内容
- 候选内容与 source 目标无关
- 全是导航、营销、静态介绍

**technical_only（仅技术）**：
- 技术上可访问
- 但目前只能证明 URL 活着，不能证明有内容价值

### 3.2 审计配置

| 配置项 | 值 |
|---|---|
| max_candidates_per_source | 5 |
| content_ready_min_valid_candidates | 2 |
| content_ready_min_relevant_candidates | 2 |
| content_watch_min_valid_candidates | 1 |
| max_noise_ratio_for_ready | 0.5 |

---

## 4. 审计结果

### 4.1 结果统计

| 状态 | 数量 | 说明 |
|---|---|---|
| content_ready | **9** | 能产出有效候选信息，建议纳入 trial_v2 scheduling |
| content_watch | **5** | 基本可访问但存在内容质量问题，需持续观察 |
| content_reject | **2** | 页面无效或无有效候选内容 |
| technical_only | **5** | 技术访问失败（HTTP 失败/403），需 connector 或网络环境修复 |
| **合计** | **20** | deep_audit 范围内（不含 1 个不在 inventory 中的 consolidated 源） |

> **注意**：goldman_sachs_podcasts（consolidated）在 operational 层面被审计，结果为 content_watch，但该源不在 inventory 中，因此不计入 matrix 的 deep_audit 统计（20 个）。

### 4.2 content_ready 源详情与样例候选

#### 4.2.1 barclays_our_insights（Barclays Our Insights）
- **content_score**: 90
- **http_status**: 200
- **relevant_candidate_count**: 4/5
- **reason**: Content valid and relevant (score: 90)

**样例候选**：

| # | 标题 | URL | content_type | relevance |
|---|---|---|---|---|
| 1 | Setting the record straight on Barclays' links to the defence sector | https://home.barclays/how-Barclays-supports-the-defence-sector/ | unknown | medium |
| 2 | News & Press Releases | https://home.barclays/news/press-releases/ | news | high |
| 3 | Investor News | https://home.barclays/investor-relations/investor-news/ | news | high |
| 4 | Barclays Consumer Spend Index | https://home.barclays/news/spend-reports/ | news | high |
| 5 | Regulatory News | https://home.barclays/investor-relations/investor-news/regulatory-news/ | news | high |

#### 4.2.2 markets_insider（Markets Insider）
- **content_score**: 90
- **http_status**: 200
- **relevant_candidate_count**: 5/5
- **reason**: Content valid and relevant (score: 90)

**样例候选**：

| # | 标题 | URL | content_type | relevance |
|---|---|---|---|---|
| 1 | From the valuation to untested business ideas, here are some concerns investors have ahead of SpaceX's historic offering | https://www.businessinsider.com/spacex-ipo-valuation-risks-what-could-go-wrong-facebook-offering-2026-6 | ir | high |
| 2 | The stock market has clawed back some recent losses, but BofA strategists say technical signals are flashing a bearish warning | https://www.businessinsider.com/stock-market-today-tech-stocks-bearish-warning-bofa-strategist-ndx-2026-6 | market_update | high |
| 3 | Facebook's infamous 2012 IPO offers a preview of what could go wrong for SpaceX | https://markets.businessinsider.com/news | news | high |
| 4 | Top economist Mark Zandi warns the record-high stock market is detached from economic reality | https://markets.businessinsider.com/stocks | market_update | high |
| 5 | Biggest Gainers | https://markets.businessinsider.com/earnings-calendar | ir | high |

#### 4.2.3 wind_public（Wind 万得公开内容）
- **content_score**: 85
- **http_status**: 200
- **relevant_candidate_count**: 3/5
- **noise_flags**: garbled_text
- **reason**: Content valid and relevant (score: 85)

**样例候选**：

| # | 标题 | URL | content_type | relevance |
|---|---|---|---|---|
| 1 | Wind Financial Terminal WFT One-Stop Platform | https://www.wind.com.cn/portal/en/WFT/index.html | unknown | medium |
| 2 | Asset Management Solution | https://www.wind.com.cn/portal/en/AMS/index.html | research | high |
| 3 | Wind ESG | https://www.wind.com.cn/portal/en/ESG/index.html | rating | high |
| 4 | Wind Economic Database | https://www.wind.com.cn/portal/en/EDB/index.html | unknown | medium |
| 5 | Global Enterprise Library | https://www.wind.com.cn/portal/en/GEL/index.html | research | high |

#### 4.2.4 china_fund_news（中国基金报）
- **content_score**: 100
- **http_status**: 200
- **relevant_candidate_count**: 4/5
- **fresh_candidate_count**: 4/5
- **reason**: Content valid and relevant (score: 100)

**样例候选**：

| # | 标题 | URL | published_at | content_type | relevance | freshness |
|---|---|---|---|---|---|---|
| 1 | Invest Insight | https://www.chnfund.com/ins | - | unknown | medium | unknown |
| 2 | 多家券商公布7月金股名单 | https://www.chnfund.com/article/ARb2e2bda8-... | 2026-07-01 | news | high | fresh |
| 3 | 告别"All in AI"，基金公司激辩：下半年风往哪吹 | https://www.chnfund.com/article/AR53c96756-... | 2026-07-01 | news | high | fresh |
| 4 | 48家A股公司公告提示风险，回应六氟化钨、机器人、光模块等热点问题 | https://www.chnfund.com/article/AR87ee4916-... | 2026-07-01 | news | high | fresh |
| 5 | "野生大V"退场、预算重构、自建生态......新规下基金营销重写"游戏规则" | https://www.chnfund.com/article/AR3fb27346-... | 2026-07-01 | news | high | fresh |

### 4.3 content_watch 源详情与问题说明（9 个，inventory 内）

| source_id | source_name | content_score | 问题说明 |
|---|---|---|---|
| goldman_sachs_research | Goldman Sachs Research | 60 | 候选内容全部为导航链接（Asset & Wealth Management、Platform Solutions），无实际研究内容候选，relevant_candidate_count=0 |
| goldman_sachs_reports | Goldman Sachs Reports | 60 | 同上，候选内容全部为导航链接，无研报候选 |
| goldman_sachs_top_of_mind | Goldman Sachs Top of Mind | 60 | 同上，候选内容全部为导航链接，无主题研究候选 |
| goldman_sachs_insights | Goldman Sachs Insights | 60 | 同上，候选内容全部为导航链接 |
| business_insider | Business Insider | 55 | 标题与 URL 不匹配（疑似渲染问题），noise_flags 含 app_download_page，relevant_candidate_count=0 |
| cls_cn | 财联社 | 60 | 候选内容有相关性但 relevant_candidate_count=0，全部为 medium relevance，内容偏短讯 |
| gelonghui | 格隆汇 | 60 | relevant_candidate_count=0，候选包含公众号矩阵、搜索页等导航内容 |
| zhitong_caijing | 智通财经 | 70 | 仅 1 个 relevant candidate，其余为 medium relevance，候选含举报页面等噪音 |
| merck_ir | Merck IR | 70 | 仅 1 个 relevant candidate，其余为 company overview 导航页，非 IR 核心内容 |

#### 4.3.1 不在 inventory 中的 operational consolidated 源

| source_id | source_name | content_score | 问题说明 |
|---|---|---|---|
| goldman_sachs_podcasts | Goldman Sachs Podcasts（consolidated） | 60 | 候选内容全部为导航链接，无播客内容候选。该源为 operational consolidated（合并 goldman_sachs_exchanges, goldman_sachs_the_markets, goldman_sachs_top_of_mind_podcast），**不在 inventory 中**，不计入 matrix deep_audit 统计 |

### 4.4 content_reject 源详情与原因

| source_id | source_name | content_score | 原因 |
|---|---|---|---|
| briefing_com_upgrades | Briefing.com Upgrades | 10 | 页面加载为空（empty_page），无任何候选内容可抽取 |
| wallstreet_cn | 华尔街见闻 | 10 | 页面加载为空（empty_page），无任何候选内容可抽取 |

### 4.5 technical_only 源详情与原因

| source_id | source_name | content_score | 原因 |
|---|---|---|---|
| yahoo_finance | Yahoo Finance | 0 | HTTP 403 Forbidden，页面不可访问 |
| the_fly | The Fly | 0 | HTTP 403 Forbidden，页面不可访问 |
| bofa_global_research | BofA Global Research | 0 | HTTP 请求失败（连接失败），URL 修复后仍无法访问 |
| texas_instruments_ir | Texas Instruments IR | 0 | HTTP 请求失败（连接失败），URL 修复后仍无法访问 |
| benzinga_analyst_ratings | Benzinga Analyst Ratings | 0 | HTTP 403 Forbidden，页面不可访问 |

---

## 5. Scheduling 建议

### 5.1 建议进入 TRAE trial_v2 scheduling（4 个 content_ready）

| source_id | source_name | content_score | 建议动作 | 备注 |
|---|---|---|---|---|
| barclays_our_insights | Barclays Our Insights | 90 | include_in_trial_v2 | 新闻/IR/市场评论内容丰富 |
| markets_insider | Markets Insider | 90 | include_in_trial_v2 | 市场新闻/IR/评级内容丰富 |
| wind_public | Wind 万得公开内容 | 85 | include_in_trial_v2 | 研究/ESG/评级数据，有 garbled_text 标记需关注 |
| china_fund_news | 中国基金报 | 100 | include_in_trial_v2 | 时效性最佳（4/5 fresh），内容相关性高 |

### 5.2 暂缓 - content_watch（9 个 inventory + 1 个 consolidated = 10 个 operational）

| source_id | source_name | content_score | 建议动作 | 备注 |
|---|---|---|---|---|
| goldman_sachs_research | Goldman Sachs Research | 60 | watch | 导航链接无研究内容，需 JS 渲染 |
| goldman_sachs_reports | Goldman Sachs Reports | 60 | watch | 同上 |
| goldman_sachs_top_of_mind | Goldman Sachs Top of Mind | 60 | watch | 同上 |
| goldman_sachs_insights | Goldman Sachs Insights | 60 | watch | 同上 |
| goldman_sachs_podcasts | Goldman Sachs Podcasts | 60 | watch | consolidated 源，不在 inventory 中，导航链接无播客内容 |
| business_insider | Business Insider | 55 | watch | 标题/URL 不匹配，有 app_download_page 噪音 |
| cls_cn | 财联社 | 60 | watch | 短讯为主，relevance 偏低 |
| gelonghui | 格隆汇 | 60 | watch | 导航内容偏多 |
| zhitong_caijing | 智通财经 | 70 | watch | 仅 1 个 relevant，含举报页噪音 |
| merck_ir | Merck IR | 70 | watch | IR 核心内容少，多为公司介绍页 |

### 5.3 不建议纳入 scheduling（7 个 = 2 content_reject + 5 technical_only）

| source_id | source_name | content_score | 原因 | 建议动作 |
|---|---|---|---|---|
| briefing_com_upgrades | Briefing.com Upgrades | 10 | 空页面无内容 | backlog |
| wallstreet_cn | 华尔街见闻 | 10 | 空页面无内容 | backlog |
| yahoo_finance | Yahoo Finance | 0 | HTTP 403 | backlog（需 connector） |
| the_fly | The Fly | 0 | HTTP 403 | backlog（需 connector） |
| bofa_global_research | BofA Global Research | 0 | 连接失败 | backlog（需 connector） |
| texas_instruments_ir | Texas Instruments IR | 0 | 连接失败 | backlog（需 connector） |
| benzinga_analyst_ratings | Benzinga Analyst Ratings | 0 | HTTP 403 | backlog（需 connector） |

### 5.4 后续处理

- **HTTP 403 源**（yahoo_finance, the_fly, benzinga_analyst_ratings）：留待 M3C-5C 处理，需特殊 connector 或代理环境
- **连接失败源**（bofa_global_research, texas_instruments_ir）：需诊断 DNS/网络问题，可能需要代理环境
- **空页面源**（briefing_com_upgrades, wallstreet_cn）：需进一步确认是否为 JS 渲染问题或内容已下线
- **content_watch 中的 Goldman Sachs 系列源**（4 个）：候选内容全为导航链接，极可能需要 JS 渲染，留待 M3C-5B browser-like connector 阶段处理

---

## 6. 审计局限性

### 6.1 网络环境限制

- 本次审计 proxy_enabled=false, proxy_mode=none，在直连网络环境下执行
- 部分 403 和连接失败的源可能是网络环境限制导致，不代表源本身无效
- Goldman Sachs 全站候选均为导航链接，可能与 JS 渲染有关
- 建议在启用代理的环境下重新审计 technical_only 源

### 6.2 审计深度限制

- 仅抽样 5 条候选内容，可能无法代表全量内容质量
- 仅检测页面级噪音，未检测内容级噪音
- 未验证候选内容的实际可访问性
- goldman_sachs_podcasts（consolidated）不在 inventory 中，仅为 operational 层面审计

---

## 7. 后续步骤

### 7.1 M3C-5A6：TRAE trial_v2 scheduling 配置

根据审计结果：
1. 仅将 4 个 content_ready 源纳入 TRAE trial_v2 scheduling
2. 将 9 个 content_watch 源列为观察对象
3. 将 2 个 content_reject + 5 个 technical_only 源列入 backlog

### 7.2 M3C-5A6 详细建议

- **优先配置**：barclays_our_insights, markets_insider, wind_public, china_fund_news
- **观察周期**：content_watch 源建议观察 1-2 周，在 M3C-5B browser-like 阶段重新评估
- **技术攻坚**：technical_only 源中的 403 和连接失败问题需在 M3C-5C 阶段处理
- **空页面源**：briefing_com_upgrades 和 wallstreet_cn 需确认是否为 JS 渲染依赖，如在 browser-like 阶段解决则可重新评估

---

## 8. 边界确认

本审计不修改 trial_v1，不修改 TRAE scheduling，不配置 production。

| 检查项 | 结果 |
|---|---|
| 是否修改当前 15 个 trial v1 | 否 |
| 是否修改 TRAE scheduling | 否 |
| 是否配置 production | 否 |
| 是否调度 92 全量 | 否，只审计 21 个 operational + 92 matrix |
| 是否处理新失败源 | 否，仅记录审计结果 |
| 是否抓 blocked/high-risk | 否 |
| 是否绕登录/付费墙 | 否 |
| 是否下载不明 PDF | 否 |
| 是否提交 data/ | 否 |
| 是否提交 local/secrets | 否 |
| 是否恢复已删除 Dashboard 页面 | 否 |
| 是否引入 Playwright/Selenium | 否 |
| 是否打 tag | 否 |

---

## 9. 相关文件

- 配置文件：`configs/foundation_content_validity_audit.example.yaml`
- Audit 脚本：`scripts/run_foundation_content_validity_audit.ps1`
- Check 脚本：`scripts/check_foundation_content_validity_audit.ps1`
- 审计结果：`data/foundation_content_validity/index/source_content_audit.jsonl`
- Matrix 结果：`data/foundation_content_validity/index/source_content_validity_matrix.jsonl`
- 审计报告：`data/foundation_content_validity/reports/content_validity_audit_2026-07-02.md`
- Trial v2 Allowlist：`configs/foundation_trial_v2_allowlist.example.yaml`
- Trial v2 Candidates：`docs/foundation_trial_v2_candidates.md`

---

## 10. M3C-5A7 Content Watch 源逐个攻坚（第一轮）

> 更新时间：2026-07-02
> 关联报告：`docs/foundation_content_watch_repair_report.md`

### 10.1 修复概要

在 M3C-5A5 审计发现 9 个 content_watch 源后，M3C-5A7 阶段对每个源进行定向修复攻坚，核心策略：

1. **定向源选择器**：在 `extract_candidates_from_html()` 中新增 `_SOURCE_SPECIFIC_SELECTORS` 字典，为每个源定义特定的 CSS 选择器和提取策略
2. **日期提取增强**：新增 `_extract_date_from_text()` 函数，支持英文月份、ISO 格式、中文日期格式

### 10.2 修复结果

| 状态 | 修复前 (M3C-5A5) | 修复后 (M3C-5A7) | 变化 |
|------|--------|--------|------|
| content_ready | 4 | 6 | +2 (goldman_sachs_insights, merck_ir) |
| content_watch | 9 | 7 | -2 |
| content_reject | 2 | 2 | 不变 |
| technical_only | 5 | 6 | +1 (benzinga 从 watch 降级为 technical) |
| **总计** | **20** | **21** | (goldman_sachs_podcasts consolidated 不在 inventory 中) |

### 10.3 升级为 content_ready 的源

| source_id | 修复前分数 | 修复后分数 | 修复方案 |
|---|---|---|---|
| goldman_sachs_insights | 60 | 90 | 使用 `a[href*='/insights/articles/']` 选择器，成功抓到 3 条真实文章 |
| merck_ir | 70 | 90 | 使用 `a[href*='/news/']` 选择器，成功抓到 5 条 IR 新闻 |
| china_fund_news | 100 | 100 | 已 content_ready（M3C-5A5 时即达标），确认维持 |

### 10.4 保持 content_watch 的源（7 个）

| source_id | 分数 | 原因 |
|---|---|---|
| goldman_sachs_reports | 60 | JS 渲染，SSR 不含文章内容 |
| goldman_sachs_top_of_mind | 60 | JS 渲染限制 |
| goldman_sachs_research | 60 | 404 + JS 渲染 |
| goldman_sachs_podcasts | 60 | consolidated 无独立 URL |
| business_insider | 55 | 日期提取失败 + app_download_page noise |
| cls_cn | 60 | 日期提取失败（内容真实） |
| zhitong_caijing | 60 | 日期提取失败（内容真实） |

### 10.5 降级为 technical_only 的源

| source_id | 修复前分数 | 修复后分数 | 原因 |
|---|---|---|---|
| benzinga_analyst_ratings | 0 (原 watch) | 0 (technical) | Cloudflare Bot Protection 返回 403，httpx 无法突破 |

### 10.6 典型发现

1. Goldman Sachs 只有 `/insights` 主页有 SSR 文章内容，子页面全 JS 渲染
2. 中文源（cls_cn、zhitong_caijing）内容真实但日期信息在 JS 渲染区域
3. Benzinga 使用 Cloudflare Bot Protection，httpx 无法突破
4. Business Insider 有真实标题但缺少时间和 app_download noise

### 10.7 对 Section 5 Scheduling 建议的影响

基于 M3C-5A7 修复结果，建议更新 scheduling 评估：

- **新增建议纳入 trial_v2 scheduling**：goldman_sachs_insights（分数 90）、merck_ir（分数 90）
- **content_ready 源从 4 个增至 6 个**：barclays_our_insights, markets_insider, wind_public, china_fund_news, goldman_sachs_insights, merck_ir
- **technical_only 源从 5 个增至 6 个**：benzinga_analyst_ratings 确认为 Cloudflare Bot Protection 阻挡

### 10.8 M3C-5A7 边界确认

| 检查项 | 结果 |
|---|---|
| 是否修改 trial_v1 | 否 |
| 是否修改 TRAE scheduling | 否 |
| 是否配置 production | 否 |
| 是否抓 blocked/high-risk | 否 |
| 是否提交 data/local/secrets | 否 |
| 是否恢复已删除页面 | 否 |
| 是否引入 Playwright/Selenium | 否 |
| 是否打 tag | 否 |

---

## 11. M3C-5A7.1 Content Watch 源第二轮逐源攻坚

> 更新时间：2026-07-02
> 修复范围：business_insider、cls_cn、zhitong_caijing
> 关联阶段：M3C-5A7.1（Content Watch 源第二轮逐源攻坚）
> 关联报告：`docs/foundation_content_watch_repair_report.md`（M3C-5A7.1 章节）

### 11.1 修复概要

M3C-5A7 第一轮后，以下 3 个源仍为 content_watch，第二轮针对性攻坚：

| source_id | 修复前状态 | content_score | 主要问题 |
|---|---|---|---|
| business_insider | content_watch | 55 | article.tout 选择器已失效（JS 渲染），候选与 URL 不匹配 |
| cls_cn | content_watch | 60 | /telegraph 纯 JS 渲染，span.m-r-5 不存在于 SSR |
| zhitong_caijing | content_watch | 70 | 仅 1 个 relevant，日期格式不稳定 |

### 11.2 修复结果

| source_id | 修复前 | 修复后 | content_score | valid | relevant | fresh | content_ready |
|---|---|---|---:|---:|---:|---:|---|
| business_insider | content_watch | **content_ready** | **95** | 5 | 5 | 4 | **YES** |
| cls_cn | content_watch | **content_ready** | **100** | 3 | 3 | 3 | **YES** |
| zhitong_caijing | content_watch | **content_ready** | **100** | 20 | 20 | 18 | **YES** |

### 11.3 更新后统计

| 状态 | M3C-5A5 原始 | M3C-5A7 第一轮 | M3C-5A7.1 第二轮 | 变化 |
|------|--------|--------|--------|------|
| content_ready | 4 | 6 | **9** | +3 (business_insider, cls_cn, zhitong_caijing) |
| content_watch | 9 | 7 | **5** | -2 |
| content_reject | 2 | 2 | 2 | 不变 |
| technical_only | 5 | 6 | 6 | 不变 |

### 11.4 对 Section 5 Scheduling 建议的影响

基于 M3C-5A7.1 修复结果，建议更新 scheduling 评估：

- **新增建议纳入 trial_v2 scheduling（第 2 批）**：business_insider（分数 95）、cls_cn（分数 100）、zhitong_caijing（分数 100）
- **content_ready 源从 6 个增至 9 个**：barclays_our_insights, markets_insider, wind_public, china_fund_news, goldman_sachs_insights, merck_ir, **business_insider, cls_cn, zhitong_caijing**
- **content_watch 源从 7 个减至 5 个**：goldman_sachs_reports, goldman_sachs_top_of_mind, goldman_sachs_research, goldman_sachs_podcasts, gelonghui

### 11.5 新增代码能力

1. **增强 `_infer_published_date`**：支持 BI 的 `/slug-YYYY-M` 和 `/YYYY/M/` URL 日期模式，支持只有年月无日期的情况
2. **增强 `_classify_freshness`**：支持中文日期 "M月D日 HH:MM"、相对时间 "X小时前/X分钟前/昨天"、MM-DD 格式 "07-01"
3. **增强 `_extract_date_from_text`**：支持 "X月X日 HH:MM"、"X小时前"、"X分钟前"、"昨天"、HH:MM
4. **容器级选择器策略**：BI、CLS、ZTC 均采用容器级选择器，一次提取标题+时间+URL+摘要

### 11.6 M3C-5A7.1 边界确认

| 检查项 | 结果 |
|---|---|
| 是否修改 trial_v1 | 否 |
| 是否修改 TRAE scheduling | 否 |
| 是否配置 production | 否 |
| 是否抓 blocked/high-risk | 否 |
| 是否提交 data/local/secrets | 否 |
| 是否恢复已删除页面 | 否 |
| 是否引入 Playwright/Selenium | 否 |
| 是否打 tag | 否 |
