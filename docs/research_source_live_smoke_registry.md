# Research Source Foundation Live Smoke Registry

> 更新时间：2026-06-23
> 当前最新相关 commit：32e5bab
> 状态：非微信自动源主线已完成 Live Smoke 1-6

---

## 1. 总览

本文件记录 Research Source Foundation 在真实公开源上的 live smoke 验证结果。
每类 source_type 都已用 2-3 个真实公开、无需登录、无需 cookie、无需付费 API 的源做小规模验证。

| Source Type | Live Smoke | Result | Production Readiness | Notes |
|---|---|---|---|---|
| official_public_research | Live Smoke 1 | 部分成功 | ready with caveats | 静态 HTML 成功，JS 渲染 fail-soft |
| podcast_transcript | Live Smoke 2 | 部分成功 | ready with caveats | IMF Podcasts 完全成功，Fed/BIS JS 渲染 fail-soft |
| conference_transcript | Live Smoke 3 | 部分成功 | ready with caveats | BIS Events 部分成功，PDF 只 metadata |
| analyst_action | Live Smoke 4 | 部分成功 | ready with caveats | Stock Analysis/MarketBeat 成功，WSJ JS 反爬 fail-soft |
| media_mention | Live Smoke 5 | 部分成功 | ready with caveats | CNBC 成功，Reuters JS 反爬 fail-soft |
| rss_feed | Live Smoke 6 | 部分成功 | ready | Federal Reserve RSS 完全成功，ECB/IMF 空 feed 可诊断 |
| manual_url | skipped by decision | N/A | optional fallback | 人工兜底入口，不属于自动主线 |
| wechat_archive | pending | N/A | separate track | 后续单独处理，优先高信噪比账号 |

---

## 2. 已完成 Live Smoke 的 Source Types

### 2.1 official_public_research

#### Sources Tested

| Source | Result | Status | Notes |
|---|---|---|---|
| ECB Research | 5/5 saved, extraction_quality high | healthy | 静态公开页面完全成功 |
| Federal Reserve Research | 1 saved / 2 partial / 1 failed | degraded | 部分链接指向社交媒体或正文为空 |
| BIS Public Documents | JS rendered empty page | failed | fail-soft connector_error |

#### Conclusion

official_public_research 基本攻下。适合静态官方研究页；JS 渲染页面不硬攻。

### 2.2 podcast_transcript

| Source | Result | Status | Notes |
|---|---|---|---|
| IMF Podcasts | 5/5 saved, extraction_quality high | healthy | episode title/url/published_at/summary/body 全部可提取 |
| Federal Reserve Podcasts | empty / likely JS-rendered | failed | fail-soft connector_error |
| BIS Podcasts | empty / likely JS-rendered | failed | fail-soft connector_error |

#### Conclusion

podcast_transcript 基本攻下。适合页面内有 episode list 和 transcript/body 的官方 podcast 页面；不下载音频、不转写。

### 2.3 conference_transcript

| Source | Result | Status | Notes |
|---|---|---|---|
| BIS Events | 2 saved / 3 partial PDF links | degraded | HTML 可抽取，PDF 只 metadata/partial |
| IMF Events | 5/5 duplicate | healthy | 去重机制正常 |
| Federal Reserve Events | Flickr HTTP 429 | failed | fail-soft 正常 |

#### Conclusion

conference_transcript 基本攻下。适合公开 IR/event HTML；PDF 不下载、不 OCR；限流/社交跳转 fail-soft。

### 2.4 analyst_action

| Source | Result | Status | Notes |
|---|---|---|---|
| Stock Analysis AAPL Analyst Ratings | 1 saved, high extraction | healthy | table 型 rating/target/broker/analyst/action_type 可提取 |
| MarketBeat AAPL Analyst Ratings | 1 saved | healthy | news list 型页面可归档 |
| WSJ AAPL Analyst Ratings | empty JS/anti-bot page | failed | fail-soft connector_error |

#### Conclusion

analyst_action 基本攻下。rating/price_target/ticker 只作为 raw metadata，不做投资判断。

### 2.5 media_mention

| Source | Result | Status | Notes |
|---|---|---|---|
| CNBC Market News | 2 saved, medium/high extraction | healthy | cards 型页面可解析，识别 JPMorgan mention |
| Yahoo Finance Market News | 2 saved / 1 failed | degraded | news list 型页面部分成功 |
| Reuters Markets News | empty JS/anti-bot page | failed | fail-soft connector_error |

#### Conclusion

media_mention 基本攻下。媒体提及只作为 raw metadata，不转成投资判断。

### 2.6 rss_feed

| Source | Result | Status | Notes |
|---|---|---|---|
| Federal Reserve Press Releases RSS | 5/5 saved, high extraction | healthy | RSS item + detail page 全链路成功 |
| ECB Press Releases RSS | empty feed content | failed | fail-soft connector_error |
| IMF News RSS | 0 items | degraded | empty_source |

#### Conclusion

rss_feed 基本攻下。真实 RSS XML feed 可完整解析；空 feed 和 0-item feed 可诊断。

---

## 3. 未单独 Live Smoke 的 Source Types

### manual_url

manual_url 是人工指定 URL 的兜底入口，不属于自动采集主线。当前可跳过。

适用场景：
- 临时发现一篇公开文章
- 自动 connector 抓不到列表页，但单篇详情页可访问
- 人工补充 evidence

### wechat_archive

wechat_archive 暂缓，后续单独处理。微信源应优先筛选高信噪比账号，避免大面积接入券商官方噪音源。

---

## 4. Source Pattern 分类

### Recommended for production trial

| Pattern | Examples from Live Smoke | Reason |
|---|---|---|
| static official HTML pages | ECB Research, IMF Podcasts, BIS FAQ | 稳定、公开、正文可抽取 |
| valid RSS XML feed | Federal Reserve RSS | feed item 和 detail body 可完整归档 |
| simple analyst rating table | Stock Analysis | metadata 清晰 |
| media cards/list pages | CNBC, Yahoo Finance partial | 可发现候选和正文 |

### Use with caution

| Pattern | Examples | Risk |
|---|---|---|
| mixed outbound/social links | Federal Reserve Research / Events | 容易 partial/failed |
| PDF-heavy event pages | BIS Events | 只能 metadata/partial |
| empty feeds | ECB RSS, IMF RSS | 需 source health 监控 |

### Not suitable without future capability

| Pattern | Examples | Reason |
|---|---|---|
| JS-rendered pages | BIS pages, Fed/BIS Podcasts | 当前无浏览器自动化 |
| anti-bot pages | WSJ, Reuters | 不绕过、不使用浏览器 |
| rate-limited social pages | Flickr 429 | 不适合 foundation 自动抓 |
| paywalled content | N/A | 不绕过 paywall |
| audio-only pages | N/A | 不下载、不转写 |

---

## 5. Production Readiness

结论：非微信自动源主线已达到 production trial ready。

含义：
- 不是所有网页都能抓
- 但每类 source_type 都已在真实公开源上验证
- 成功、部分成功、失败三种情况都能被 source_health / failed_queue / report 正确表达
- 不会因为单个 source 失败拖垮全局 run

---

## 6. Boundary

- 不做 JS 渲染
- 不做反爬对抗
- 不保存 cookie/token/API key
- 不绕过 paywall
- 不下载 PDF
- 不 OCR
- 不下载音频
- 不转写音频
- 不做投资判断
- 不接 th_capital_stock

---

## 7. Next Step

建议进入：
- WeChat high-signal source selection
- WeChat archive live smoke
- 下游 documents.jsonl 消费契约审查
