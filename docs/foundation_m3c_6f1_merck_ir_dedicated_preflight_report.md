# OPC Foundation M3C-6F.1 Merck IR Dedicated Extraction Preflight Report

## 1. 执行前状态

- **master path:** `/Users/apple/Documents/一人公司OPC/opc-foundation`
- **starting master commit:** a444afe (after 6F merge)
- **6F merge commit:** a444afe
- **6F.1 branch:** feature/m3c-6f1-merck-ir-dedicated-preflight
- **git status:** clean
- **trial_v2 source_count:** 9
- **production_enabled:** false

## 2. 为什么只处理 merck_ir

M3C-6F 三个候选源的结果：
- **merck_ir:** HTTP 200 但通用首页抓取只拿到导航链接 → manual_review_only（需要专门提取路径）
- **the_fly:** timeout → tls_or_proxy_backlog（需代理环境重试）
- **yahoo_finance:** HTTP 200 但检测到 login/paywall 风险 → login_or_paywall_blocked

merck_ir 是本批唯一有明确恢复可能的高价值源：
- M3C-5B1 曾达到 content_ready（score 90, 5 valid, 3 relevant）
- 问题不是 HTTP 不通，而是 M3C-6F 用了通用首页抓取，抓错了入口
- 有 M3C-5B1 验证过的专门选择器（`a[href*='/news/']`, `a[href*='/events/']`, `a[href*='/presentations/']`）

## 3. M3C-6F 中 merck_ir 的问题

M3C-6F 的 proxy retry 脚本使用通用首页 anchor 提取，结果：
- valid_items=20（全是导航链接：Who we are, What we do, Sustainability）
- dated_items=0
- 决策：manual_review_only

根因：脚本抓取了 `https://www.merck.com/investor-relations/` 首页的所有 `<a>` 标签，没有按 IR 路径过滤。

## 4. 本阶段使用入口

### 尝试的入口类型

| 入口类型 | URL | 说明 |
|---|---|---|
| investor_news | https://www.merck.com/investor-relations/ | IR 首页，发现 IR 链接 |
| events_presentations | https://www.mck.com/events/ | 事件和演示文稿页面 |
| press_releases | 从 IR 页面发现 | 新闻稿链接 |
| rss_atom | 从 HTML `<link>` 标签发现 | RSS/Atom feed |
| sitemap_investor_urls | https://www.merck.com/sitemap.xml | sitemap 中的 IR 相关 URL |
| json_ld_metadata | 从 HTML `<script type="application/ld+json">` 提取 | JSON-LD 结构化数据 |

### 是否仍抓到导航页

**否。** 本阶段使用 M3C-5B1 验证过的路径模式（`/news/`, `/events/`, `/presentations/`）过滤，并扩展了噪音过滤模式（Skip to content, Areas of innovation, See full agenda 等共 20 个 pattern）。提取到的全是真实 IR 内容。

## 5. Merck IR Dedicated Preflight 结果

| 入口指标 | 值 |
|---|---|
| entry_url | https://www.merck.com/investor-relations/ |
| entry_type | investor_news |
| http_status | 200 |
| content_type | text/html; charset=UTF-8 |
| candidate_url_count | 92 |
| valid_item_count | 15 |
| dated_item_count | 0 |
| rejected_navigation_count | 0 |
| rss_or_feed_found | false |
| sitemap_investor_url_count | 4 |
| json_ld_item_count | 1 |
| login_required | false |
| paywall_observed | false |
| captcha_or_antibot_observed | false |

## 6. 样本 items

| title | url | date_text | entry_type |
|---|---|---|---|
| Q3 2026 Earnings Call | https://www.merck.com/events/q3-2026-earnings-call/ | - | events_presentations |
| Q2 2026 Earnings Call | https://www.merck.com/events/q2-2026-earnings-call/ | - | events_presentations |
| 47th Annual Goldman Sachs Global Healthcare Conference | https://www.merck.com/events/47th-annual-goldman-sachs-global-healthcare-conference/ | - | events_presentations |
| Jefferies Global Healthcare Conference | https://www.merck.com/events/jefferies-global-healthcare-conference/ | - | events_presentations |
| Q1 2026 Earnings Call | https://www.merck.com/events/q1-2026-earnings-call/ | - | events_presentations |

## 7. 最终决策

- **recommended_execution_mode:** low_frequency_candidate
- **trial_v2_allowlist_allowed_now:** False
- **next_action:** evaluate_low_frequency_schedule
- **是否建议进入 scheduled_candidate round 2:** 否（dated_item_count=0 < 2）
- **是否建议进入 low_frequency:** 是（有真实 IR 内容，但无法从列表页 HTML 提取日期）
- **是否仍 manual_review_only:** 否（已从 manual_review_only 提升为 low_frequency_candidate）

### 决策依据

1. **HTTP 200** ✅ 站点可达
2. **无 login/paywall/captcha** ✅ 无阻断
3. **valid_item_count=15** ✅ >= 3，远超阈值
4. **dated_item_count=0** ❌ < 2，无法从列表页 HTML 提取日期
5. **样本全是真实 IR 内容** ✅ 财报电话会议、医疗健康会议
6. **不满足 scheduled_candidate_round_2 条件**（dated 不足）
7. **适合 low_frequency**（IR 事件更新频率低，适合每日或每周检查）

### 日期提取问题分析

Merck 事件列表页的日期信息可能：
1. 通过 JavaScript 动态渲染（不在 SSR HTML 中）
2. 在单独的事件详情页中（需逐页抓取）
3. 在非标准日期格式中（当前 regex 未覆盖）

M3C-5B1 曾达到 3 个 dated items，说明存在可提取日期的路径，可能需要逐个访问事件详情页。

## 8. 测试结果

- **tests/source_inventory:** 66 passed (model tests)
- **tests/scripts:** 32 passed (config + script boundary tests)
- **tests/dashboard:** all passed
- **full pytest:** (待运行)

## 9. 边界确认

- **是否修改 TRAE scheduling:** 否
- **是否修改 TRAE local config:** 否
- **是否修改 trial_v2 allowlist:** 否
- **是否配置 production:** 否
- **是否提交 data/local/secrets:** 否
- **是否提交 proxy URL:** 否
- **是否提交 cookie/token:** 否
- **是否提交 raw HTML:** 否
- **是否提交 screenshot:** 否
- **是否引入 Playwright/Selenium:** 否
- **是否恢复已删除 Dashboard 页面:** 否
- **是否打 tag:** 否

## 10. 技术资产

### 新增文件

- `configs/foundation_m3c_6f1_merck_ir_dedicated_preflight.example.yaml` - 6F.1 配置
- `src/opc_foundation/source_inventory/merck_ir_dedicated_preflight.py` - 数据模型
- `scripts/run_m3c_6f1_merck_ir_dedicated_preflight.py` - 执行脚本
- `tests/source_inventory/test_merck_ir_dedicated_preflight.py` - 模型测试
- `tests/scripts/test_m3c_6f1_merck_ir_dedicated_preflight.py` - 脚本/配置测试
- `docs/foundation_m3c_6f1_merck_ir_dedicated_preflight_report.md` - 本报告

### 核心改进

1. **专门 IR 路径过滤:** 只提取 `/news/`, `/events/`, `/presentations/` 路径的链接
2. **扩展噪音过滤:** 从 M3C-5B1 的 13 个 pattern 扩展到 20 个（含 Skip to content, Areas of innovation 等）
3. **精确 blocker 检测:** 使用更具体的 login/paywall/captcha hint，避免 false positive
4. **多入口发现:** IR 首页 + 新闻页 + 事件页 + sitemap + RSS + JSON-LD
5. **日期提取增强:** 从 `<time>` 标签、标题文本、URL 路径、邻近 HTML 多处尝试

## 11. 下一步建议

1. **merck_ir:** 进入 low_frequency_candidate，评估低频调度配置
2. **日期提取改进:** 可考虑逐个访问事件详情页提取日期，或使用 content_validity.py 中 M3C-5B1 的选择器
3. **不建议本阶段直接新增 merck_ir 到 trial_v2 allowlist**
4. **继续暂缓 the_fly**（需代理环境）
5. **继续排除 yahoo_finance**（login/paywall 待确认）
6. **继续暂缓 production 配置**
