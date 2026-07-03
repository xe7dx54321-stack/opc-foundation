# OPC Foundation M3C-5B1.1 — Next Candidate Preflight Report

> Generated: 2026-07-03 15:32 UTC
> Master commit: `5c2f35f`
> Branch: `feature/m3c-5b1-1-next-candidate-preflight`
> Phase: M3C-5B1.1

---

## Summary

| source_id | source_name | rounds | pass_rounds | latest_status | latest_score | final_decision |
|---|---|---:|---:|---|---:|---|
| gelonghui | 格隆汇 | 3 | 0 | content_ready | 80 | preflight_fail |
| merck_ir | Merck Investor Relations | 3 | 0 | technical_only | 0 | preflight_fail |

## Base 8-Source Allowlist (Unchanged)

- barclays_our_insights
- markets_insider
- china_fund_news
- wind_public
- goldman_sachs_insights
- business_insider
- cls_cn
- zhitong_caijing

## Preflight: 格隆汇 (gelonghui)

**Final decision: preflight_fail**
- Total rounds: 3
- Pass rounds: 0
- Latest status: content_ready
- Latest score: 80
- Consecutive failures: 3
- Failure reasons: dated 0 < 2; dated 0 < 2; dated 0 < 2

### Round Details

| Round | Status | Score | HTTP | Valid | Relevant | Dated | Samples | Pass | Failure Reason |
|---:|---|---:|---:|---:|---:|---:|---:|---|---|
| 1 | content_ready | 80 | 200 | 5 | 5 | 0 | 5 | FAIL | dated 0 < 2 |
| 2 | content_ready | 80 | 200 | 5 | 5 | 0 | 5 | FAIL | dated 0 < 2 |
| 3 | content_ready | 80 | 200 | 5 | 5 | 0 | 5 | FAIL | dated 0 < 2 |

### Real Samples

- **证监会就完善上市公司再融资规则公开征求意见**
  - URL: https://www.gelonghui.com/p/5451415.html
  - Published: 
  - Type: news
  - Relevance: high
  - Freshness: unknown
  - Snippet: 证监会就完善上市公司再融资规则公开征求意见

- **万亿赛道，掀起涨停潮**
  - URL: https://www.gelonghui.com/p/5451237.html
  - Published: 
  - Type: news
  - Relevance: high
  - Freshness: unknown
  - Snippet: 万亿赛道，掀起涨停潮

- **再爆提价！韩国股市大逆转，机构疯狂抄底**
  - URL: https://www.gelonghui.com/p/5446247.html
  - Published: 
  - Type: news
  - Relevance: high
  - Freshness: unknown
  - Snippet: 再爆提价！韩国股市大逆转，机构疯狂抄底

- **三部门：明年起取消节能车、新能源汽车车船税减免**
  - URL: https://www.gelonghui.com/p/5451499.html
  - Published: 
  - Type: news
  - Relevance: high
  - Freshness: unknown
  - Snippet: 三部门：明年起取消节能车、新能源汽车车船税减免

- **下一个三十年的定价权之争！格隆汇年中策略峰会解码**
  - URL: https://www.gelonghui.com/p/5451112.html
  - Published: 
  - Type: news
  - Relevance: high
  - Freshness: unknown
  - Snippet: 下一个三十年的定价权之争！格隆汇年中策略峰会解码

## Preflight: Merck Investor Relations (merck_ir)

**Final decision: preflight_fail**
- Total rounds: 3
- Pass rounds: 0
- Latest status: technical_only
- Latest score: 0
- Consecutive failures: 3
- Failure reasons: HTTP 0; score 0 < 70; valid 0 < 2; relevant 0 < 2; dated 0 < 2; HTTP 0; score 0 < 70; valid 0 < 2; relevant 0 < 2; dated 0 < 2; HTTP 0; score 0 < 70; valid 0 < 2; relevant 0 < 2; dated 0 < 2

### Round Details

| Round | Status | Score | HTTP | Valid | Relevant | Dated | Samples | Pass | Failure Reason |
|---:|---|---:|---:|---:|---:|---:|---:|---|---|
| 1 | technical_only | 0 | 0 | 0 | 0 | 0 | 0 | FAIL | HTTP 0; score 0 < 70; valid 0 < 2; relevant 0 < 2; dated 0 < 2 |
| 2 | technical_only | 0 | 0 | 0 | 0 | 0 | 0 | FAIL | HTTP 0; score 0 < 70; valid 0 < 2; relevant 0 < 2; dated 0 < 2 |
| 3 | technical_only | 0 | 0 | 0 | 0 | 0 | 0 | FAIL | HTTP 0; score 0 < 70; valid 0 < 2; relevant 0 < 2; dated 0 < 2 |

### Real Samples

No valid samples collected.

## Risk Assessment

### gelonghui

**Status: preflight_fail (dated deficiency only)**

gelonghui 内容质量本身很好：3 轮全部 HTTP 200、5 valid、5 relevant、score=80。内容均为港股/A股/宏观财经新闻，高度相关。唯一问题是 **dated_candidate_count = 0**：gelonghui 的 URL 格式为 `gelonghui.com/p/{数字ID}.html`，不包含日期信息，而当前 SSR 首页 HTML 中无显式日期标签被 extract_candidates 捕获。

这是一个已知的日期提取限制，不是内容质量问题。M3C-5B1 repair backlog 中 gelonghui 评分 90 也未依赖 dated 指标。

**风险等级: 低**。内容有效，日期推断需增强。

### merck_ir

**Status: preflight_fail (network failure)**

merck_ir 3 轮全部 HTTP 0（网络不可达）。这与 M3C-5A preflight 中 merck_ir 的 HTTP 403 历史一致——merck.com 域名从中国大陆 macOS 环境直接访问存在网络限制，需要代理或海外网络环境。

M3C-5B1 repair backlog 记录 merck_ir 评分 90 是在有代理环境下获得的。

**风险等级: 中**。内容可能可用但受网络环境约束。

---

## Technical Analysis

### gelonghui dated=0 Root Cause

gelonghui URL 格式 `https://www.gelonghui.com/p/5451415.html` 中不含日期。`_infer_published_date()` 函数无法从 URL 路径或标题中提取日期。但格隆汇文章列表页 SSR 中确实包含时间信息（通常在 HTML 中以相对时间如 "3小时前" 或绝对时间显示），只是当前 `a[href*='/p/']` 选择器只抽取链接元素本身，不包含兄弟时间节点。

**修复方向（未来）**：使用容器级选择器（类似 cls_cn 的 `div.m-b-10` 策略），同时抽取标题和相邻时间元素。

### merck_ir HTTP 0 Root Cause

`www.merck.com/investor-relations/` 从当前 macOS 网络环境不可达。httpx Client 报连接超时/拒绝。这是网络环境问题，不是源本身失效。

**修复方向（未来）**：在有代理环境下重试，或使用 `merck.com` 的其他可达入口（如 SEC EDGAR）。

---

## Boundary Confirmation

| Item | Status |
|---|---|
| Modified trial_v2 allowlist | No |
| Modified TRAE scheduling | No |
| Configured production | No |
| Submitted data/local/secrets | No |
| Introduced Playwright/Selenium | No |
| Restored deleted Dashboard pages | No |
| Created tag | No |

## Conclusion

| Check | gelonghui | merck_ir |
|---|---|---|
| HTTP reachable | Yes (200) | No (HTTP 0, network blocked) |
| content_ready | Yes (80 pts) | N/A |
| valid >= 2 | Yes (5) | N/A |
| relevant >= 2 | Yes (5) | N/A |
| dated >= 2 | **No (0)** | N/A |
| scheduling_allowed_now | false | false |
| Final decision | preflight_fail | preflight_fail |

- gelonghui: 内容满足 content_ready，但 dated 提取需增强后重试
- merck_ir: 需在有代理环境下重试，当前网络不可达
- 两个候选源均不建议在本次进入 8->10 扩容

## Recommendation

1. **不建议进入 M3C-5B1.2**（8->10 扩容评估）
2. gelonghui 需修复日期提取后重新 preflight
3. merck_ir 需在有代理环境下重新 preflight
4. 继续暂缓 production
5. 两个源保持 `next_scheduling_candidate` 状态，不加入 trial_v2 allowlist
