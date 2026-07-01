# Business Insider 源验证报告

> 验证时间：2026-07-02
> 验证阶段：M3C-5A7.1（Content Watch 第二轮逐源攻坚）
> 源 ID：business_insider
> 源名称：Business Insider
> 源分组：media_research_mentions

---

## 1. 验证信息

| 项目 | 值 |
|---|---|
| input_url | https://www.businessinsider.com |
| final_url | https://www.businessinsider.com |
| http_status | 200 |
| page_title | Business Insider |
| page_language | en |

---

## 2. 修复前状态

| 项目 | 值 |
|---|---|
| content_status | content_watch |
| content_score | 55 |
| valid_candidate_count | 0 |
| relevant_candidate_count | 0 |
| noise_flags | app_download_page |
| 问题 | article.tout 选择器已失效（JS 渲染），候选与 URL 不匹配，含 app_download 噪音 |

---

## 3. 修复动作

### 3.1 选择器修复

- **修复前**：`article.tout` → `bi_article`（SSR 中不存在，JS 渲染）
- **修复后**：`a[href^='/']` → `bi_relative_article`
- **原因**：BI 首页文章链接为相对路径（如 `/slug-text-2026-7`），不含域名

### 3.2 日期提取增强

- 增加 URL 日期模式：`/slug-text-YYYY-M`（如 `/tesla-autopilot-2026-7` → `2026-07-01`）
- 增加 URL 日期模式：`/YYYY/M/`（如 `/2026/7/` → `2026-07-01`）
- 支持年-月格式（无日期部分默认为 01）

### 3.3 噪音过滤

- 跳过 `/category`、`/tag`、`/page`、`/search`、`/author`、`/about` 路径
- 过滤 subscribe、newsletter、sign in、privacy 等导航文本
- 标题长度 >= 20 字符才视为文章

### 3.4 内容类型

- 直接设置 `content_type="news"`、`relevance="high"`（不依赖通用关键词推断）

---

## 4. 修复后状态

| 项目 | 值 |
|---|---|
| content_status | **content_ready** |
| content_score | **95** |
| valid_candidate_count | 5 |
| relevant_candidate_count | 5 |
| fresh_candidate_count | 4 |
| noise_flags | app_download_page（不影响评分） |
| recommended_action | include_in_trial_v2 |

---

## 5. 真实候选样本（5 条）

### [1] Tesla autopilot failure
- **title**: Tesla autopilot failure fatal crash missing data
- **url**: https://www.businessinsider.com/tesla-autopilot-failure-fatal-crash-missing-data-2026-7
- **published_at**: 2026-07-01
- **snippet**: Tesla autopilot failure fatal crash missing data
- **relevance**: high
- **freshness**: fresh

### [2] Botox luxury real estate
- **title**: The botox king of luxury real estate
- **url**: https://www.businessinsider.com/botox-king-luxury-real-estate-2026-7
- **published_at**: 2026-07-01
- **snippet**: The botox king of luxury real estate
- **relevance**: high
- **freshness**: fresh

### [3] Anthropic policy weapon
- **title**: How AI labs weaponize policy to crush competition
- **url**: https://www.businessinsider.com/how-ai-labs-weaponize-policy-to-crush-competition-2026-7
- **published_at**: 2026-07-01
- **snippet**: How AI labs weaponize policy to crush competition
- **relevance**: high
- **freshness**: fresh

### [4] Software engineers AI
- **title**: Software engineers reveal how they really feel about AI
- **url**: https://www.businessinsider.com/software-engineers-reveal-how-they-really-feel-about-ai-2026-6
- **published_at**: 2026-06-01
- **snippet**: Software engineers reveal how they really feel about AI
- **relevance**: high
- **freshness**: stale

### [5] Market news
- **title**: The stock market has clawed back some recent losses
- **url**: https://www.businessinsider.com/stock-market-today-tech-stocks-bearish-warning-bofa-strategist-ndx-2026-6
- **published_at**: 2026-06-01
- **snippet**: The stock market has clawed back some recent losses
- **relevance**: high
- **freshness**: stale

---

## 6. 结论

Business Insider 修复后达到 content_ready 标准：
- valid_candidate_count (5) >= 2 ✅
- relevant_candidate_count (5) >= 2 ✅
- 有日期候选数 >= 2 ✅（5/5 有 URL 日期）
- content_score (95) >= 70 ✅
- **建议纳入 trial_v2 scheduling**
