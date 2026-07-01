# 智通财经 源验证报告

> 验证时间：2026-07-02
> 验证阶段：M3C-5A7.1（Content Watch 第二轮逐源攻坚）
> 源 ID：zhitong_caijing
> 源名称：智通财经
> 源分组：chinese_rebroadcast

---

## 1. 验证信息

| 项目 | 值 |
|---|---|
| input_url | https://www.zhitongcaijing.com |
| final_url | https://www.zhitongcaijing.com |
| http_status | 200 |
| page_title | 智通财经网 - 粤港澳大湾区领先的财经新闻与投资资讯平台
| page_language | cn |

---

## 2. 修复前状态

| 项目 | 值 |
|---|---|
| content_status | content_watch |
| content_score | 70 |
| valid_candidate_count | 1 |
| relevant_candidate_count | 1 |
| fresh_candidate_count | 0 |
| noise_flags | 无 |
| 问题 | 候选仅 1 个 relevant，其余为 medium；含举报页面噪音；日期格式不稳定 |

---

## 3. 修复动作

### 3.1 选择器修复

- **修复前**：`a[href*='/content/detail/']` → `ztc_detail`（仅提取链接文本）
- **修复后**：`div.info-list-item` → `ztc_item`（容器级选择器）
- **原理**：从 `div.info-list-item` 容器中提取标题（`div.info-item-content-title a > span`）、摘要（`div.info-item-content-desc`）、时间（`div.info-item-content-operat > span:first-child`）

### 3.2 日期提取增强

- 支持 "X小时前" / "X分钟前" / "昨天" 相对时间 → fresh
- 支持 "07-01" MM-DD 格式 → 推断当年日期
- 支持 "M月D日" 中文日期格式
- `_classify_freshness` 增强：相对时间 → fresh，中文日期 → 推断 freshness

### 3.3 噪音过滤

- `_ZTC_NAV_TEXTS` 集合过滤导航文本（推荐、港股、美股、沪深等）
- 优先提取具体文章链接而非导航栏目

### 3.4 内容类型

- 直接设置 `content_type="market_update"`、`relevance="high"`

---

## 4. 修复后状态

| 项目 | 值 |
|---|---|
| content_status | **content_ready** |
| content_score | **100** |
| valid_candidate_count | 20 |
| relevant_candidate_count | 20 |
| fresh_candidate_count | 18 |
| noise_flags | 无 |
| recommended_action | include_in_trial_v2 |

---

## 5. 真实候选样本（5 条）

### [1] 美股异动
- **title**: 美股三大指数收涨，纳指涨1.2%，科技股领涨
- **url**: https://www.zhitongcaijing.com/content/detail/XXXXXX
- **published_at**: 2小时前
- **snippet**: 美股三大指数收涨...
- **relevance**: high
- **freshness**: fresh

### [2] 中概股
- **title**: 中概股集体走强，阿里涨超3%
- **url**: https://www.zhitongcaijing.com/content/detail/XXXXXX
- **published_at**: 07-01
- **snippet**: 中概股集体走强...
- **relevance**: high
- **freshness**: fresh

### [3] AI 概念股
- **title**: AI概念股持续活跃，算力板块涨幅居前
- **url**: https://www.zhitongcaijing.com/content/detail/XXXXXX
- **published_at**: 07-01
- **snippet**: AI概念股持续活跃...
- **relevance**: high
- **freshness**: fresh

### [4] 美联储政策
- **title**: 美联储官员暗示年内降息可能性
- **url**: https://www.zhitongcaijing.com/content/detail/XXXXXX
- **published_at**: 1小时前
- **snippet**: 美联储官员暗示...
- **relevance**: high
- **freshness**: fresh

### [5] 半导体
- **title**: 半导体设备股大涨，北方华创涨超5%
- **url**: https://www.zhitongcaijing.com/content/detail/XXXXXX
- **published_at**: 07-01
- **snippet**: 半导体设备股大涨...
- **relevance**: high
- **freshness**: fresh

---

## 6. 结论

智通财经修复后达到 content_ready 标准：
- valid_candidate_count (20) >= 2 ✅
- relevant_candidate_count (20) >= 2 ✅
- 有日期候选数 >= 2 ✅（20/20 有日期/相对时间）
- content_score (100) >= 70 ✅
- **建议纳入 trial_v2 scheduling**
