# Foundation Source Repair Backlog Report

> Worktree: `feature/m3c-5b0-source-repair-backlog`  
> Scope: 92 source inventory items  
> Active trial v2 content-ready: 8 sources  
> Production enabled: **false**  
> Affects trial v2 scheduling: **false**

---

## 1. Policy Guardrails

The following policy flags are locked for this stage:

| Policy Flag | Value | Meaning |
|-------------|-------|---------|
| `do_not_modify_trial_v1` | `true` | Trial v1 source set must remain unchanged. |
| `do_not_modify_trial_v2_allowlist` | `true` | Trial v2 allowlist must remain unchanged. |
| `no_browser_runtime_in_this_stage` | `true` | Browser-like runtime (Playwright/Puppeteer) is out of scope for M3C-5B0. |
| `no_source_repair_in_this_stage` | `true` | Active source code repair is deferred; this backlog is for routing only. |

**Consequence**: No non-ready source may enter scheduling in M3C-5B0. Only the 8 `scheduled_observation` sources are permitted in trial v2 scheduling.

---

## 2. scheduled_observation — Active Trial v2 Content-Ready (8 sources)

These 8 sources are the only ones with `scheduling_allowed: true`.

| # | Source ID | Status | Action |
|---|-----------|--------|--------|
| 1 | `barclays_our_insights` | trial_v2_content_ready | Continue 24h observation |
| 2 | `markets_insider` | trial_v2_content_ready | Continue 24h observation |
| 3 | `china_fund_news` | trial_v2_content_ready | Continue 24h observation |
| 4 | `wind_public` | trial_v2_content_ready | Continue 24h observation |
| 5 | `goldman_sachs_insights` | trial_v2_content_ready | Continue 24h observation |
| 6 | `business_insider` | trial_v2_content_ready | Continue 24h observation |
| 7 | `cls_cn` | trial_v2_content_ready | Continue 24h observation |
| 8 | `zhitong_caijing` | trial_v2_content_ready | Continue 24h observation |

---

## 3. p0_repaired_ready — M3C-5B1 Round 1 Repaired (2 sources)

Sources successfully repaired during M3C-5B1 P0 round 1 and verified as `content_ready` via real network crawl. They are **NOT** added to the current trial v2 allowlist; marked as `next_scheduling_candidate` for future batches.

| Source ID | Score | Primary Issue | Recommended Action | Priority | Next Stage |
|-----------|-------|---------------|--------------------|----------|------------|
| `gelonghui` | 90 | Repaired | next_scheduling_candidate | P0 | — |
| `merck_ir` | 90 | Repaired | next_scheduling_candidate | P0 | — |

### Per-Source Details

- **gelonghui**: Selector fixed (`a[href*='/p/']`), aggressive noise filter added, explicit `content_type=news`/`relevance=high` set for Chinese titles. Verified: 5 valid, 5 relevant, score=90. Not in trial_v2 allowlist.
- **merck_ir**: URL updated to `www.merck.com/investor-relations/`, noise filter added for navigation elements. Verified: 5 valid, 3 relevant, score=90. Not in trial_v2 allowlist.

---

## 4. content_watch — Degraded Content (4 sources)

These sources return partial or degraded content. They must **NOT** enter scheduling until repaired or rerouted.

| Source ID | Score | Primary Issue | Recommended Action | Priority | Next Stage |
|-----------|-------|---------------|--------------------|----------|------------|
| `goldman_sachs_research` | 60 | JS rendering + 404 | Move to browser-like spike | P1 | M3C-5B2 |
| `goldman_sachs_reports` | 60 | JS rendering, SSR lacks article content | Move to browser-like spike | P1 | M3C-5B2 |
| `goldman_sachs_top_of_mind` | 60 | JS rendering limitation | Move to browser-like spike | P1 | M3C-5B2 |
| `goldman_sachs_podcasts` | 60 | JS rendering required (hub page, no SSR episodes) | Move to browser-like spike | P0 | M3C-5B2 |

### Per-Source Details

- **goldman_sachs_research**: Direct fetch yields 404; content is present only after JavaScript rendering. Static extraction is insufficient. Route to browser-like specialized spike in M3C-5B2.
- **goldman_sachs_reports**: Server-side render does not include article body. Full content loaded dynamically. Route to browser-like specialized spike in M3C-5B2.
- **goldman_sachs_top_of_mind**: Same JS rendering limitation as above. Route to browser-like specialized spike in M3C-5B2.
- **goldman_sachs_podcasts**: Hub page has no SSR episode list; no RSS/Atom/JSON-LD feed found. Requires browser-like extraction (M3C-5B2). Moved from M3C-5B1 after real crawl confirmed JS-only content.
- **M3C-5B2 Update (2026-07-04)**: Feed/metadata spike completed. Attempted RSS/Atom (all 404), sitemap.xml (1 podcast URL, no episodes), series pages (all 404), JSON-LD/OpenGraph (hub page only, no episode metadata). No stable non-browser entry found. Final decision: `browser_like_backlog`. Continue to defer browser-like extraction.

---

## 4. content_reject — Empty Page (2 sources)

These sources return empty pages and must **NOT** enter scheduling until an official alternative URL or feed is located.

| Source ID | Score | Primary Issue | Recommended Action | Priority | Next Stage |
|-----------|-------|---------------|--------------------|----------|------------|
| `briefing_com_upgrades` | 10 | Empty page | Find official alternative URL | P2 | M3C-5B1 |
| `wallstreet_cn` | 10 | Empty page | Find official alternative URL | P2 | M3C-5B1 |

### Per-Source Details

- **briefing_com_upgrades**: Returns empty page. Likely caused by URL migration or paywall redirect. Search for official alternative endpoint or RSS feed.
- **wallstreet_cn**: Returns empty page. Verify whether the site has an official API, feed, or updated public endpoint.

---

## 5. technical_only — Technical Barriers (5 sources)

These sources are blocked by HTTP 403, TLS/SSL failure, timeout, or Cloudflare anti-bot. They must **NOT** enter scheduling until the relevant specialized route is ready.

| Source ID | Score | Primary Issue | Recommended Action | Priority | Next Stage |
|-----------|-------|---------------|--------------------|----------|------------|
| `yahoo_finance` | 0 | HTTP 403 Forbidden | Move to TLS/SSL spike | P2 | M3C-5C0 |
| `the_fly` | 0 | HTTP 403 Forbidden | Move to TLS/SSL spike | P2 | M3C-5C0 |
| `benzinga_analyst_ratings` | 0 | Cloudflare anti-bot 403 | Move to Cloudflare backlog | P2 | M3C-5C0 |
| `bofa_global_research` | 0 | TLS/SSL connection failure | Move to TLS/SSL spike | P2 | M3C-5C0 |
| `texas_instruments_ir` | 0 | Timeout / connection failure | Move to TLS/SSL spike | P1 | M3C-5C0 |

### Per-Source Details

- **yahoo_finance**: HTTP 403. Suspected TLS fingerprint or user-agent blocking. Route to TLS/SSL specialized spike in M3C-5C0.
- **the_fly**: HTTP 403. Aggressive bot detection at the TLS layer. Route to TLS/SSL specialized spike in M3C-5C0.
- **benzinga_analyst_ratings**: Cloudflare anti-bot 403. This is a boundary case; route to dedicated Cloudflare/anti-bot handling backlog in M3C-5C0.
- **bofa_global_research**: SSL/connection failure. Requires TLS version negotiation or updated certificate bundle. Route to TLS/SSL specialized spike in M3C-5C0.
- **texas_instruments_ir**: Timeout/connection failure. Network path or TLS handshake instability suspected. Route to TLS/SSL specialized spike in M3C-5C0 (P1 because IR content is high value).

---

## 6. 92 Matrix Uncategorized — High-Level View

The full inventory contains 92 sources. After accounting for the 8 scheduled observation, 2 p0_repaired_ready, 4 content_watch, 2 content_reject, and 5 technical_only sources, **71 sources remain uncategorized** in the detailed backlog.

These 71 sources span:

- Major investment banks (Citi, UBS, J.P. Morgan, Morgan Stanley)
- Global wire services (Reuters, Bloomberg public pages)
- Regional Chinese financial media
- Corporate IR pages
- WeChat-native publisher accounts

### Representative Key Sources from the 71

The following representative sources are explicitly tracked in the backlog config to guide later triage:

| Source ID | Status | Primary Issue | Recommended Action | Priority | Next Stage |
|-----------|--------|---------------|--------------------|----------|------------|
| `citi_research` | not_audited | Not audited | Re-audit after network change | P2 | M3C-5B1 |
| `ubs_insights` | not_audited | Not audited | Re-audit after network change | P2 | M3C-5B1 |
| `jp_morgan_research` | not_audited | Not audited | Re-audit after network change | P3 | M3C-5D0 |
| `morgan_stanley_insights` | not_audited | Not audited | Re-audit after network change | P3 | M3C-5D0 |
| `goldman_sachs_china_wechat` | not_audited | Needs WeChat archive mapping | Map to WeChat archive | P1 | M3C-5B1 |
| `morgan_stanley_china_wechat` | not_audited | Needs WeChat archive mapping | Map to WeChat archive | P1 | M3C-5B1 |
| `reuters` | not_audited | Not audited | Re-audit after network change | P3 | M3C-5D0 |

The remaining uncategorized sources will be triaged in M3C-5B1, M3C-5C0, or M3C-5D0 depending on network environment changes and audit capacity.

---

## 7. Scheduling Blocklist

The following sources **must NOT enter scheduling** in M3C-5B0:

- All `p0_repaired_ready` sources (2) — repaired but awaiting future batch
- All `content_watch` sources (4)
- All `content_reject` sources (2)
- All `technical_only` sources (5)
- All `matrix_uncategorized` sources (71 represented; full 92 minus 8 observation)

In other words, every source except the 8 `scheduled_observation` items is blocked from scheduling.

---

## 8. Default Ops Removal Recommendations

The following sources should be **removed from default operational runs** (e.g., live smoke, daily archive) because they are known to fail and consume runtime resources without yielding valid content:

| Source ID | Reason |
|-----------|--------|
| `goldman_sachs_research` | JS rendering required; static fetch fails |
| `goldman_sachs_reports` | SSR lacks content; static fetch fails |
| `goldman_sachs_top_of_mind` | JS rendering required; static fetch fails |
| `goldman_sachs_podcasts` | JS rendering required; hub page has no SSR episodes |
| `briefing_com_upgrades` | Empty page; no content to extract |
| `wallstreet_cn` | Empty page; no content to extract |
| `yahoo_finance` | HTTP 403; static fetch blocked |
| `the_fly` | HTTP 403; static fetch blocked |
| `benzinga_analyst_ratings` | Cloudflare anti-bot; static fetch blocked |
| `bofa_global_research` | TLS/SSL failure; connection cannot complete |
| `texas_instruments_ir` | Timeout; connection unstable |

Removing these from default ops prevents noise in run logs, reduces wasted compute, and keeps failure rates meaningful.

---

## 9. Summary Table

| Category | Count | Scheduling Allowed | Action Theme |
|----------|-------|--------------------|--------------|
| scheduled_observation | 8 | Yes | Continue observation |
| p0_repaired_ready | 2 | No | Repaired; next_scheduling_candidate |
| content_watch | 4 | No | Repair or reroute |
| content_reject | 2 | No | Find alternative URL/feed |
| technical_only | 5 | No | Specialized route (TLS/SSL/anti-bot) |
| matrix_uncategorized | 71 | No | Audit and triage |
| **Total** | **92** | **8 only** | — |

---

*Generated for stage M3C-5B1. No browser runtime, no proxy URLs, no secrets.*
