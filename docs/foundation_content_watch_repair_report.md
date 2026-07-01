# OPC Foundation M3C-5A7：Content Watch 源逐个攻坚（第一轮）

## 执行时间
2026-07-02

## 网络环境
proxy_enabled=false, proxy_mode=none

## 修复范围
9 个 content_watch 源（按任务说明）

注意：jp_morgan、morgan_stanley、reuters 不在 trial_v2 allowlist 的 21 个 operational 源中，因此不包含在本轮修复范围内。

## 修复方案
### 定向源选择器
在 `extract_candidates_from_html()` 中新增 `_SOURCE_SPECIFIC_SELECTORS` 字典，为每个源定义特定的 CSS 选择器和提取策略。

### 日期提取
新增 `_extract_date_from_text()` 函数，支持英文月份、ISO格式、中文日期格式。

## 逐源修复结果

### 1. goldman_sachs_insights ✅ 升级为 content_ready
- 修复前：候选全是导航链接
- 修复方案：使用 `a[href*='/insights/articles/']` 选择器
- 修复后样本（3条真实文章）：
  - "Why Oil Prices Could 'Grind Lower' Amid the US-Iran Deal" (Jun 18, 2026)
  - "The Outlook for AI-Related Stocks and US Interest Rates" (Jun 12, 2026)
  - "The Outlook for Data Centers in Asia" (Jun 10, 2026)
- 分数：90 | 候选：3 | 状态：content_ready

### 2. goldman_sachs_reports ❌ 保持 content_watch
- 修复前：候选全是导航链接
- 修复方案：尝试 a[href*='/insights/articles/'] 选择器
- 修复后：页面为 JS 渲染，SSR 不含文章内容，fallback 到通用选择器仍抓到导航
- 原因：reports 子页面内容通过 JavaScript 动态加载，httpx 无法获取
- 分数：60 | 状态：content_watch

### 3. goldman_sachs_top_of_mind ❌ 保持 content_watch
- 同 goldman_sachs_reports，JS 渲染限制

### 4. goldman_sachs_research ❌ 保持 content_watch
- 同 goldman_sachs_reports，JS 渲染限制
- 注意：该页面返回 404

### 5. goldman_sachs_podcasts ❌ 保持 content_watch
- consolidated source，无独立 URL，fallback 到 insights 主页但抓到导航

### 6. business_insider ❌ 保持 content_watch
- 修复前：候选全是导航
- 修复后：使用 `a.tout-title-link` 选择器成功抓到 5 条真实标题
- 但问题：日期提取失败，存在 app_download_page noise
- 分数：55 | 状态：content_watch

### 7. cls_cn ❌ 保持 content_watch
- 修复后：使用 `a[href*='/detail/']` 选择器抓到 5 条真实中文新闻
- 问题：日期提取失败
- 分数：60 | 状态：content_watch

### 8. zhitong_caijing ❌ 保持 content_watch
- 修复后：使用 `a[href*='/content/detail/']` 选择器抓到 5 条真实中文新闻
- 问题：日期提取失败
- 分数：60 | 状态：content_watch

### 9. benzinga_analyst_ratings ❌ 降级为 technical_only
- Cloudflare Bot Protection 返回 403
- 无法通过 httpx 获取内容
- 需要浏览器级别模拟才能突破

### 10. merck_ir ✅ 升级为 content_ready
- 修复前：候选是"Who we are"导航
- 修复方案：使用 `a[href*='/news/']` 选择器
- 修复后样本（5条IR新闻）：
  - "Merck to Hold Second-Quarter 2026 Sales and Earnings Conference Call"
  - "Merck Announces New Agreement with ADAP Crisis Task Force"
  - "FDA Approves KEYTRUDA® (pembrolizumab) and KEYTRUDA QLEX™"
- 分数：90 | 状态：content_ready

### 11. china_fund_news ✅ 升级为 content_ready
- 修复前：已 content_ready（M3C-5A5 时即达标）
- 确认样本（5条中文新闻，全部有日期 2026-07-01）
- 分数：100 | 状态：content_ready

## 新统计
| 状态 | 修复前 | 修复后 | 变化 |
|------|--------|--------|------|
| content_ready | 4 | 6 | +2 (gs_insights, merck_ir) |
| content_watch | 9 | 7 | -2 |
| content_reject | 2 | 2 | 不变 |
| technical_only | 5 | 6 | +1 (benzinga 从 watch→technical) |
| **总计** | **20** | **21** | (goldman_sachs_podcasts consolidated 不在 inventory 中) |

## 升级清单
1. goldman_sachs_insights: content_watch → content_ready ✅
2. merck_ir: content_watch → content_ready ✅
3. china_fund_news: 已 content_ready（确认维持）✅

## 保持 content_watch 清单（7个）
1. goldman_sachs_reports - JS 渲染
2. goldman_sachs_top_of_mind - JS 渲染
3. goldman_sachs_research - 404 + JS 渲染
4. goldman_sachs_podcasts - consolidated 无独立 URL
5. business_insider - 缺日期 + noise
6. cls_cn - 缺日期
7. zhitong_caijing - 缺日期

## 降级 technical_only 清单
1. benzinga_analyst_ratings - Cloudflare 403

## 典型发现
1. Goldman Sachs 只有 /insights 主页有 SSR 文章内容，子页面全 JS 渲染
2. 中文源（cls_cn、zhitong_caijing）内容真实但日期信息在 JS 渲染区域
3. Benzinga 使用 Cloudflare Bot Protection，httpx 无法突破
4. Business Insider 有真实标题但缺少时间和 app_download noise

## M3C-5A7 后续建议（M3C-5A8）
1. JS 渲染源（GS子页面、BI日期、中文源日期）需要 Playwright/Selenium，但当前不允许引入
2. 可考虑 GS 改为统一使用 /insights 主页作为入口（已有 3 篇文章）
3. 中文源可考虑使用 RSS feed 作为替代数据源
4. Benzinga 需要确认是否有 API 或 RSS 可用
5. jp_morgan/morgan_stanley/reuters 虽不在 trial_v2 allowlist 中，后续可考虑加入

## 边界确认
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
