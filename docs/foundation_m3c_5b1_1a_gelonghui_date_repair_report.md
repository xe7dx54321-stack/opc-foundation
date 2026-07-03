# OPC Foundation M3C-5B1.1a — gelonghui Date Extraction Repair Report

> Generated: 2026-07-03 15:45 UTC
> Base commit: `016363a` (from feature/m3c-5b1-1-next-candidate-preflight)
> Branch: `feature/m3c-5b1-1a-gelonghui-date-repair`
> Phase: M3C-5B1.1a
> Source: gelonghui only

---

## Summary

| source_id | source_name | rounds | pass_rounds | latest_status | latest_score | final_decision |
|---|---|---:|---:|---|---:|---|
| gelonghui | 格隆汇 | 3 | 3 | content_ready | 100 | preflight_pass |

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

**Final decision: preflight_pass**
- Total rounds: 3
- Pass rounds: 3
- Latest status: content_ready
- Latest score: 100
- Consecutive failures: 0

### Round Details

| Round | Status | Score | HTTP | Valid | Relevant | Dated | Samples | Pass | Failure Reason |
|---:|---|---:|---:|---:|---:|---:|---:|---|---|
| 1 | content_ready | 100 | 200 | 5 | 5 | 5 | 5 | PASS | - |
| 2 | content_ready | 100 | 200 | 5 | 5 | 5 | 5 | PASS | - |
| 3 | content_ready | 100 | 200 | 5 | 5 | 5 | 5 | PASS | - |

### Real Samples

- **AI洪流三部曲：ARR的边界真正决定AI经济影响的，仍然是企业采用速度、模型能力边界、组织流程改造和监管约束**
  - URL: https://www.gelonghui.com/p/5451551
  - Published: 38分钟前
  - Type: news
  - Relevance: high
  - Freshness: fresh
  - Snippet: AI洪流三部曲：ARR的边界真正决定AI经济影响的，仍然是企业采用速度、模型能力边界、组织流程改造和监管约束

- **日元160之后：各方博弈与市场展望高市目前对日元贬值或不够重视**
  - URL: https://www.gelonghui.com/p/5451548
  - Published: 1小时前
  - Type: news
  - Relevance: high
  - Freshness: fresh
  - Snippet: 日元160之后：各方博弈与市场展望高市目前对日元贬值或不够重视

- **公告精选︱江波龙：预计上半年净利润同比增长62204.03%～74393.95%；福赛科技：机器人零部件产品处于早期研发、小批量试制及送样实验阶段立中集团：拟发行可转债募资不超过11.8亿元**
  - URL: https://www.gelonghui.com/p/5451544
  - Published: 1小时前
  - Type: news
  - Relevance: high
  - Freshness: fresh
  - Snippet: 公告精选︱江波龙：预计上半年净利润同比增长62204.03%～74393.95%；福赛科技：机器人零部件产品处于早期研发、小批量试制及送样实验阶段立中集团：拟发行可转债募资不超过11.8亿元

- **促进电影院多样化经营，两部门联合发文！支持通过新建电影院、电影院增厅等形式放映虚拟现实电影**
  - URL: https://www.gelonghui.com/p/5451536
  - Published: 2小时前
  - Type: news
  - Relevance: high
  - Freshness: fresh
  - Snippet: 促进电影院多样化经营，两部门联合发文！支持通过新建电影院、电影院增厅等形式放映虚拟现实电影

- **三部门：明年起取消节能车、新能源汽车车船税减免促进税收公平**
  - URL: https://www.gelonghui.com/p/5451499
  - Published: 3小时前
  - Type: news
  - Relevance: high
  - Freshness: fresh
  - Snippet: 三部门：明年起取消节能车、新能源汽车车船税减免促进税收公平

## Risk Assessment

### gelonghui

No significant risk identified. Source meets content_ready criteria consistently.

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

## Recommendation

gelonghui passes 3/3 rounds with score=100. Recommend entering **M3C-5B1.2** evaluation for 8 -> 10 expansion readiness assessment. gelonghui qualifies as a ready_for_expansion_preflight candidate with scheduling_allowed_now=false.

## Repair Details

### Before (B1.1)
- Selector: `a[href*='/p/']` (element-level)
- dated_candidate_count: 0
- published_at: empty
- content_score: 80

### After (B1.1a)
- Selector: `li.article-li` (container-level)
- Date extraction: `section.source-time` text parsing
- Time formats recognized: `x分钟前`, `x小时前`, `今天 HH:MM`, `昨天 HH:MM`, `MM-DD HH:MM`, `YYYY-MM-DD`
- dated_candidate_count: 5
- published_at: populated (e.g., "38分钟前", "1小时前")
- freshness: fresh
- content_score: 100

### Changes Made
1. `src/opc_foundation/source_inventory/content_validity.py`:
   - gelonghui selector changed from `a[href*='/p/']` to `li.article-li`
   - Added `glh_container` extraction type with container-level date extraction from `section.source-time`
   - Backward-compatible `glh_article` extraction preserved
2. `scripts/run_foundation_trial_v2_next_candidates_preflight.py`:
   - Added `--source` filter parameter to run specific sources only
