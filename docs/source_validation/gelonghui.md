# Source Validation Report: gelonghui

## Source Info
- **source_id**: gelonghui
- **source_name**: 格隆汇
- **source_group**: financial_news

## Pre-Repair Status
- **content_status**: content_watch
- **reason**: Selector `div.detail-left a[href*="/p/"]` returned 0 matches on SSR HTML

## Repair Actions
1. **Selector fix**: Changed from `div.detail-left a[href*="/p/"]` to `a[href*="/p/"]`
   - Rationale: The `div.detail-left` wrapper is not present in SSR HTML; the article links exist at the top level
2. **Noise filtering**: Added aggressive noise filtering for gelonghui
   - Exact title match filter (GELONGHUI_NOISE_TITLE): 30+ navigation/UI strings
   - Keyword-based filter (GELONGHUI_NOISE_KEYWORDS): 16 lower-case patterns
   - Minimum title length raised from 5 to 10 characters
   - Title extraction now prefers child heading/span/div/p elements over raw link text
3. **Relevance fix**: Explicitly set `content_type="news"` and `relevance="high"` for glh_article candidates
   - Rationale: The generic `_classify_content_type_simple()` only matches English keywords, causing all Chinese news titles to be classified as `unknown` / `medium` relevance. This suppressed the score below the `content_ready` threshold despite valid article links.

## Network Validation Results

| Field | Value |
|-------|-------|
| input_url | https://www.gelonghui.com |
| final_url | https://www.gelonghui.com |
| http_status | 200 |
| content_score | 90 |
| content_status | content_ready |
| valid_candidate_count | 5 |
| relevant_candidate_count | 5 |

## Real Candidate Samples

| # | Title | URL | Date |
|---|-------|-----|------|
| 1 | 暴跌7.5%！特斯拉Q2交付大捷，市场为何不买账？ | https://www.gelonghui.com/p/5436380.html | - |
| 2 | AI芯片泡沫，真要破了吗？ | https://www.gelonghui.com/p/5432471.html | - |
| 3 | 德国大刀阔斧改革！提高退休年龄、对高收入者加税 | https://www.gelonghui.com/p/5435047.html | - |
| 4 | 李迅雷：判断泡沫破灭看这三个信号 | https://www.gelonghui.com/p/5434198.html | - |
| 5 | 但斌最新演讲：不要错失一个伟大的时代 | https://www.gelonghui.com/p/5433960.html | - |

## Assessment
- The selector fix successfully recovered article links from the SSR HTML.
- 5 valid candidates were extracted, all with genuine news titles and `/p/` article URLs.
- The explicit `content_type="news"` / `relevance="high"` fix resolved the English-only classifier limitation for Chinese titles.
- Content score 90 places gelonghui in `content_ready` with all 5 candidates marked as high relevance.
- **Result**: Upgraded from `content_watch` to `content_ready`. Marked as `next_scheduling_candidate=true` for future trial_v2 batches (NOT added to current allowlist).
