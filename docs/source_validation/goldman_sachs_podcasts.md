# Source Validation Report: goldman_sachs_podcasts

## Source Info
- **source_id**: goldman_sachs_podcasts
- **source_name**: Goldman Sachs Podcasts
- **source_group**: official_podcast_transcript
- **candidate_type**: consolidated

## Pre-Repair Status
- **content_status**: content_watch
- **reason**: Insufficient valid candidates (score: 60)
- **recommended_action**: watch

## Network Validation Results

| Field | Value |
|-------|-------|
| input_url | https://www.goldmansachs.com/insights/podcasts |
| final_url | https://www.goldmansachs.com/insights/podcasts |
| http_status | 200 |
| content_score | 60 |
| content_status | content_watch |
| valid_candidate_count | 5 |
| relevant_candidate_count | 0 |

## Real Candidate Samples

| # | Title | URL | Date |
|---|-------|-----|------|
| 1 | ASSET & WEALTH MANAGEMENT | https://www.goldmansachs.com/what-we-do/investment-banking | - |
| 2 | ASSET & WEALTH MANAGEMENT | https://www.goldmansachs.com/what-we-do/ficc-and-equities | - |
| 3 | ASSET & WEALTH MANAGEMENT | https://marquee.gs.com/welcome/ | - |
| 4 | ASSET & WEALTH MANAGEMENT | https://www.goldmansachs.com/what-we-do/transaction-banking | - |
| 5 | PLATFORM SOLUTIONS | https://www.gsiam.com/ | - |

## Why It Cannot Be Fixed in This Round

1. **Hub page architecture**: The Goldman Sachs podcast landing page (`/insights/podcasts`) is a consolidated hub page. It does not list individual podcast episodes in SSR HTML; instead it presents high-level business divisions and navigation cards.
2. **No SSR episode list**: Real network crawl shows that the podcast episode links are rendered client-side (JavaScript). The SSR HTML only contains generic navigation links ("ASSET & WEALTH MANAGEMENT", "PLATFORM SOLUTIONS", etc.), not actual podcast episodes.
3. **No RSS feed**: There is no discoverable RSS feed URL in the SSR HTML or in the page source that would allow direct ingestion of episodes without browser-like rendering.
4. **Selector limitation**: The current selector (`a.gs-card`, `gs_card`) matches navigation cards, not episodes. Changing the CSS selector alone cannot fix the issue because the desired content simply does not exist in the SSR response.

## Recommended Next Action

**Move to browser-like spike**
- This source requires a headless-browser or JavaScript-rendered crawl to extract actual podcast episodes.
- A spike should evaluate:
  1. Whether the podcast hub page renders episode links after JS execution
  2. Whether there is a hidden JSON API or RSS endpoint
  3. Whether individual member sources (`goldman_sachs_exchanges`, `goldman_sachs_the_markets`, `goldman_sachs_top_of_mind_podcast`) have dedicated episode list pages with SSR content
- Until browser-like extraction is available, this consolidated source should remain in `content_watch`.
