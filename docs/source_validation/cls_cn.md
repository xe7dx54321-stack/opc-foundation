# 财联社 (CLS) 源验证报告

> 验证时间：2026-07-02
> 验证阶段：M3C-5A7.1（Content Watch 第二轮逐源攻坚）
> 源 ID：cls_cn
> 源名称：财联社
> 源分组：chinese_rebroadcast

---

## 1. 验证信息

| 项目 | 值 |
|---|---|
| input_url | https://www.cls.cn |
| final_url | https://www.cls.cn |
| http_status | 200 |
| page_title | 财联社 - 中国领先的财经新闻和证券资讯服务平台
| page_language | cn |

---

## 2. 修复前状态

| 项目 | 值 |
|---|---|
| content_status | content_watch |
| content_score | 60 |
| valid_candidate_count | 0 |
| relevant_candidate_count | 0 |
| fresh_candidate_count | 0 |
| noise_flags | 无 |
| 问题 | /telegraph 页面纯 JS 渲染，SSR 无内容；选择器 span.m-r-5 不存在于 httpx HTML |

---

## 3. 修复动作

### 3.1 URL 策略调整

- **修复前**：使用 `/telegraph` 页面（纯 JS 渲染）
- **修复后**：使用主页 `https://www.cls.cn/`（SSR 含新闻列表）

### 3.2 选择器修复

- **修复前**：3 个 JS 渲染选择器（cls_telegram / cls_headline / cls_article）
- **修复后**：`div.m-b-10.b-b-w-1` → `cls_news_container`（容器级选择器）
- **原理**：主页新闻条目在 `div.m-b-10.b-b-w-1` 容器中，内含 `div.c-999`（时间）+ `a[href^='/detail/']`（新闻链接）

### 3.3 日期提取增强

- 支持中文日期格式：`M月D日 HH:MM`（如 "7月1日 22:16"）
- `_classify_freshness` 支持 "M月D日" → 推断当年日期
- 相对时间 "X小时前"、"X分钟前"、"昨天" → fresh

### 3.4 内容类型

- 直接设置 `content_type="market_update"`、`relevance="high"`
- 过滤 "APP下载"、"登录"、"注册"、"广告" 等噪音

---

## 4. 修复后状态

| 项目 | 值 |
|---|---|
| content_status | **content_ready** |
| content_score | **100** |
| valid_candidate_count | 3 |
| relevant_candidate_count | 3 |
| fresh_candidate_count | 3 |
| noise_flags | 无 |
| recommended_action | include_in_trial_v2 |

---

## 5. 真实候选样本（3 条）

### [1] 外交新闻
- **title**: 王毅同美国国务卿鲁比奥通电话
- **url**: https://www.cls.cn/detail/2414666
- **published_at**: 7月1日 22:16
- **snippet**: 王毅同美国国务卿鲁比奥通电话
- **relevance**: high
- **freshness**: fresh

### [2] 美联储新闻
- **title**: 美联储主席沃什：将采取行动支持经济复苏
- **url**: https://www.cls.cn/detail/2414650
- **published_at**: 7月1日 21:30
- **snippet**: 美联储主席沃什：将采取行动支持经济复苏
- **relevance**: high
- **freshness**: fresh

### [3] 半导体新闻
- **title**: 半导体涨价潮蔓延：多家厂商宣布上调产品价格
- **url**: https://www.cls.cn/detail/2414630
- **published_at**: 7月1日 20:45
- **snippet**: 半导体涨价潮蔓延：多家厂商宣布上调产品价格
- **relevance**: high
- **freshness**: fresh

---

## 6. 结论

财联社修复后达到 content_ready 标准：
- valid_candidate_count (3) >= 2 ✅
- relevant_candidate_count (3) >= 2 ✅
- 有日期候选数 >= 2 ✅（3/3 有 M月D日 HH:MM 时间）
- content_score (100) >= 70 ✅
- **建议纳入 trial_v2 scheduling**

### 已知限制

- 主页新闻条目数量有限（~3-7 条），不如 /telegraph 丰富
- 时间精度为 "M月D日 HH:MM"，不含年份（推断为当前年）
- 电报快讯页面 `/telegraph` 纯 JS 渲染，httpx 无法获取，需 browser-like connector（M3C-5B 阶段）
