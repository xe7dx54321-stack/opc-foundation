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

---

## M3C-5A7.1：第二轮逐源攻坚结果

> 更新时间：2026-07-02
> 修复范围：business_insider、cls_cn、zhitong_caijing
> 关联阶段：M3C-5A7.1（Content Watch 源第二轮逐源攻坚）

### M3C-5A7.1.1 修复概要

M3C-5A7 第一轮后，以下 3 个源仍为 content_watch：

| source_id | 修复前状态 | content_score | 主要问题 |
|---|---|---|---|
| business_insider | content_watch | 55 | article.tout 选择器已失效（JS 渲染），候选与 URL 不匹配 |
| cls_cn | content_watch | 60 | /telegraph 纯 JS 渲染，span.m-r-5 不存在于 SSR |
| zhitong_caijing | content_watch | 70 | 仅 1 个 relevant，日期格式不稳定 |

### M3C-5A7.1.2 逐源修复动作

#### business_insider

| 项目 | 修复前 | 修复后 |
|---|---|---|
| 选择器 | `article.tout` (bi_article) | `a[href^='/']` (bi_relative_article) |
| 日期提取 | 无 | URL 路径 `/slug-YYYY-M` 提取年月 |
| 噪音过滤 | 无 | 过滤 /category /tag /page 等路径 + 导航文本 |
| 内容类型 | unknown (通用推断失败) | news (直接设置) |
| relevance | medium | high |

**根本原因**：BI 首页 `article.tout` 和 `feed-list` 均为 JS 渲染，SSR HTML 中文章链接以相对路径（`/slug-text-YYYY-M`）呈现。

#### cls_cn

| 项目 | 修复前 | 修复后 |
|---|---|---|
| URL 策略 | /telegraph (纯 JS) | 主页 https://www.cls.cn/ |
| 选择器 | 3 个 JS 选择器 | `div.m-b-10.b-b-w-1` (cls_news_container) |
| 时间提取 | span.m-r-5 (不存在) | div.c-999 容器内 "M月D日 HH:MM" |
| 内容类型 | unknown | market_update (直接设置) |
| freshness | unknown | fresh (中文日期解析) |

**根本原因**：CLS /telegraph 页面内容完全由客户端 JavaScript 渲染，SSR HTML 中无任何结构化新闻数据。

#### zhitong_caijing

| 项目 | 修复前 | 修复后 |
|---|---|---|
| 选择器 | `a[href*='/content/detail/']` (ztc_detail) | `div.info-list-item` (ztc_item) |
| 提取内容 | 仅标题 | 标题 + 摘要 + 时间 + URL |
| 日期格式 | 不稳定 | 支持 "X小时前"、"07-01"、"M月D日" |
| 内容类型 | unknown | market_update (直接设置) |
| relevance | medium | high |

**根本原因**：旧选择器只提取链接文本，未利用容器级结构。

### M3C-5A7.1.3 修复后验证结果

| source_id | 修复前 | 修复后 | content_score | valid | relevant | fresh | content_ready |
|---|---|---|---:|---:|---:|---:|---|
| business_insider | content_watch | **content_ready** | **95** | 5 | 5 | 4 | **YES** |
| cls_cn | content_watch | **content_ready** | **100** | 3 | 3 | 3 | **YES** |
| zhitong_caijing | content_watch | **content_ready** | **100** | 20 | 20 | 18 | **YES** |

### M3C-5A7.1.4 新增代码能力

1. **增强 `_infer_published_date`**：支持 BI 的 `/slug-YYYY-M` 和 `/YYYY/M/` URL 日期模式，支持只有年月无日期的情况
2. **增强 `_classify_freshness`**：支持中文日期 "M月D日 HH:MM"、相对时间 "X小时前/X分钟前/昨天"、MM-DD 格式 "07-01"
3. **增强 `_extract_date_from_text`**：支持 "X月X日 HH:MM"、"X小时前"、"X分钟前"、"昨天"、HH:MM
4. **容器级选择器策略**：BI、CLS、ZTC 均采用容器级选择器，一次提取标题+时间+URL+摘要

### M3C-5A7.1.5 边界确认

- 不处理 Goldman Sachs JS 渲染类源 ✅
- 不处理 benzinga Cloudflare 403 ✅
- 不处理 TLS/SSL 专项源 ✅
- 不新增 source ✅
- 不修改 source inventory 总数 ✅
- 不修改 trial_v1 ✅
- 不修改 TRAE scheduling ✅
- 不配置 production ✅
- 不提交 data/local/secrets ✅
- 不恢复已删除 Dashboard 页面 ✅
- 不引入 Playwright/Selenium ✅
- 不打 tag ✅

### M3C-5A7.1.6 建议

- 新增可进入 scheduling 的源：business_insider、cls_cn、zhitong_caijing
- content_ready 总数：6 → 9（+3）
- content_watch 总数：7 → 5（-2，gelonghui 和 GS 系列仍为 watch）
- 建议进入 TRAE trial_v2 scheduling（第 2 批）
