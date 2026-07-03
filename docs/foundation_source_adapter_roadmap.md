# Foundation Source Adapter Roadmap

> Worktree: `feature/m3c-5b0-source-repair-backlog`  
> Purpose: Define repair routes and stage boundaries for the 92-source inventory.

---

## 1. Selector / Date / Noise Light Repair Route

**Scope**: Sources where the page loads successfully but extraction quality is degraded due to DOM noise, incorrect selectors, or missing date normalization.

**Indicators**:
- HTTP 200 OK
- Content is present but buried in navigation boilerplate
- Date extraction returns `null` or inconsistent formats
- Score ~60, primary issue = `noise_filter_issue` or `selector_mismatch`

**Known sources**:
- `gelonghui` — navigation noise too high

**Repair actions**:
1. Refine CSS/XPath selector to target the primary content container.
2. Add date-normalization heuristic (ISO-8601 preferred, fallback to locale parsing).
3. Strip recurring noise patterns (header, footer, ad slots, related-links widgets).
4. Re-run content validity audit and confirm score >= 80.

**Stage assignment**: M3C-5B1

**Boundary**: If the site requires JavaScript to render the content container, escalate to Route 3 (browser-like specialized) instead of patching selectors indefinitely.

---

## 2. RSS / Feed / Sitemap / JSON-LD Alternative Route

**Scope**: Sources where the HTML page is a poor extraction target but the publisher provides a machine-readable alternative.

**Indicators**:
- HTML page is empty, gated, or consolidated
- RSS feed, sitemap, or JSON-LD structured data is available
- Primary issue = `consolidated_modeling_issue` or `empty_page`

**Known sources**:
- `goldman_sachs_podcasts` — consolidated under parent page, no independent URL
- `briefing_com_upgrades` — empty page, may expose RSS
- `wallstreet_cn` — empty page, may expose feed

**Repair actions**:
1. Search for `/rss`, `/feed`, `/sitemap.xml`, or `application/ld+json` on the domain.
2. Verify feed validity (parseable, contains required fields: title, link, pubDate).
3. Map feed items to source schema (canonical URL, title, publish date, content snippet).
4. If feed is valid, add `rss_connector` or `manual_url` pipeline entry.
5. If JSON-LD is present but partial, write a lightweight normalizer.

**Stage assignment**: M3C-5B1

**Boundary**: If no feed exists and the site is JavaScript-dependent, escalate to Route 3. If the site blocks feed readers (403), escalate to Route 4 or 5.

---

## 3. Browser-Like Specialized Route

**Scope**: Sources that require a JavaScript runtime to render meaningful content.

**Indicators**:
- SSR returns minimal or no article body
- Content appears only after client-side hydration
- Score ~60, primary issue = `js_rendering_required`
- Policy flag `no_browser_runtime_in_this_stage = true` defers this to M3C-5B2

**Known sources**:
- `goldman_sachs_research`
- `goldman_sachs_reports`
- `goldman_sachs_top_of_mind`

**Repair actions**:
1. Spike Playwright or Puppeteer extraction with stealth plugins.
2. Measure overhead: cold-start time, memory, concurrency limits.
3. Define a reliability contract (max 30s per page, retry 2x, screenshot on failure).
4. Integrate with existing `url_text_extractor` as a fallback tier (static first, browser second).
5. Cache rendered DOM to avoid re-rendering on duplicate URLs.

**Stage assignment**: M3C-5B2

**Boundary**: If the site adds CAPTCHA or heavy bot detection beyond simple user-agent checks, escalate to Route 5 (Cloudflare/anti-bot). If the failure is TLS/SSL rather than JS, escalate to Route 4.

---

## 4. TLS / SSL Specialized Route

**Scope**: Sources where the connection itself fails due to TLS version mismatch, certificate issues, or aggressive TLS fingerprinting.

**Indicators**:
- `SSLError`, `ConnectionError`, or timeout at handshake
- HTTP 403 despite valid URL and headers
- Score = 0, primary issue = `tls_or_ssl_failure`, `timeout_or_network_unstable`, or `http_403_or_forbidden` where headers do not help

**Known sources**:
- `yahoo_finance` — HTTP 403, suspected TLS fingerprint blocking
- `the_fly` — HTTP 403, aggressive bot detection at TLS layer
- `bofa_global_research` — SSL/connection failure
- `texas_instruments_ir` — timeout/connection failure

**Repair actions**:
1. Spike `requests` with custom `ssl_context` (TLS 1.2 vs 1.3 negotiation).
2. Test with `curl` using different cipher suites and SNI configurations.
3. Evaluate `urllib3` advanced SSL options or `httpx` with custom mounts.
4. If fingerprinting is confirmed, evaluate lightweight fingerprint randomization (ja3).
5. Document the minimal working configuration and wrap it into a reusable `http_utils` helper.

**Stage assignment**: M3C-5C0

**Boundary**: If the site uses Cloudflare or returns a challenge page, escalate to Route 5. If the issue is simply a bad URL, Route 2 (find RSS/feed) is preferred.

---

## 5. Cloudflare / Anti-Bot Handling Boundary

**Scope**: Sources protected by Cloudflare or equivalent anti-bot walls that return challenge pages, CAPTCHAs, or persistent 403s regardless of header/tls tweaks.

**Indicators**:
- Response contains `cf-ray` header or Cloudflare challenge HTML
- Score = 0, primary issue = `cloudflare_or_anti_bot`
- TLS and header tricks do not resolve the block

**Known sources**:
- `benzinga_analyst_ratings` — Cloudflare anti-bot 403

**Repair actions**:
1. **Do not** attempt to bypass CAPTCHA or JS challenge programmatically in M3C-5B0/5B1/5B2.
2. Evaluate ethical alternatives:
   - Official API or partner feed
   - Syndication agreement
   - On-demand search provider (Route 7) as a proxy for discovery
3. If a legitimate bypass exists (e.g., authenticated session with explicit consent), document it in a separate security review.
4. Maintain a dedicated `cloudflare_backlog` category so these sources do not pollute other routes.

**Stage assignment**: M3C-5C0 (backlog maintenance), with resolution deferred until a legal/technical bypass is approved.

**Boundary**: This route is intentionally a hard stop. No automated circumvention tooling is deployed without explicit review.

---

## 6. WeChat Archive Mapping Route

**Scope**: Sources whose primary distribution channel is WeChat Official Accounts rather than traditional web pages.

**Indicators**:
- Content is published as WeChat articles (`mp.weixin.qq.com`)
- No stable public URL outside WeChat ecosystem
- Primary issue = `needs_wechat_archive_mapping`

**Known sources**:
- `goldman_sachs_china_wechat`
- `morgan_stanley_china_wechat`

**Repair actions**:
1. Map the publisher to an entry in `wechat_accounts.example.yaml`.
2. Use the existing `wechat_archive` connector (`feed_client` + `extractor`) to poll the account.
3. Store canonical metadata (title, publish time, content, original URL) in the archive.
4. Deduplicate against web-extracted signals using URL or title hash.
5. If the account is not yet in the feed list, add it and verify with a live smoke run.

**Stage assignment**: M3C-5B1

**Boundary**: If the WeChat account is paywalled or requires subscription verification, escalate to the on-demand search provider (Route 7) for manual URL ingestion.

---

## 7. On-Demand Search Provider Role

**Scope**: Use external search APIs (Brave, Tavily) as a fallback discovery mechanism when direct source access is blocked, degraded, or unknown.

**Role definition**:
- **Not** a replacement for first-party extraction
- **Not** a scheduling source
- **Is** a discovery tool to find alternative URLs, RSS feeds, or recent article links

**Use cases**:
1. `briefing_com_upgrades` — search for "briefing.com upgrades RSS" to locate an official feed.
2. `wallstreet_cn` — search for "wallstreet.cn API" or "wallstreet.cn feed".
3. `merck_ir` — search for "Merck IR press releases RSS" to find an alternative endpoint.
4. `goldman_sachs_china_wechat` — search for recent article titles to confirm account identity.

**Integration**:
- Use existing `search_provider_registry` and `search_runner`.
- Store discovered URLs in `manual_urls.example.csv` for vetting.
- Run a quick URL check (`quick_url_check.ps1`) before promoting to config.

**Stage assignment**: M3C-5B1 (discovery), continuous

**Boundary**: Search results must be vetted for authenticity (domain match, official verification). Do not auto-ingest unverified URLs into production scheduling.

---

## 8. Next Stage Suggestions

### M3C-5B1 — Light Repair & Alternative Route Spike
**Goal**: Resolve the highest-volume, lowest-effort backlog items.

**In scope**:
- Selector/date/noise repairs (Route 1)
- RSS/feed/sitemap/JSON-LD discovery (Route 2)
- WeChat archive mapping (Route 6)
- On-demand search discovery (Route 7)
- Re-audit of `not_audited` sources after network environment changes

**Key sources to resolve**:
- `gelonghui`
- `goldman_sachs_podcasts`
- `briefing_com_upgrades`
- `wallstreet_cn`
- `merck_ir`
- `goldman_sachs_china_wechat`
- `morgan_stanley_china_wechat`
- `citi_research`
- `ubs_insights`

**Exit criteria**:
- All P0 and P1 M3C-5B1 items are either repaired, rerouted, or definitively escalated.
- No new `content_reject` or `content_watch` items remain without a next-stage assignment.

### M3C-5B2 — Browser-Like Runtime Spike
**Goal**: Validate browser-based extraction at scale.

**In scope**:
- Browser-like specialized route (Route 3)
- Playwright/Puppeteer integration with existing `url_text_extractor`
- Overhead measurement and caching strategy

**Key sources to resolve**:
- `goldman_sachs_research`
- `goldman_sachs_reports`
- `goldman_sachs_top_of_mind`

**Exit criteria**:
- Browser extraction achieves score >= 80 on all three Goldman sources.
- Cold-start latency and memory usage are documented and acceptable for batch runs.
- A fallback policy is defined (static first, browser second, fail open).

### M3C-5C0 — TLS/SSL & Anti-Bot Boundary Hardening
**Goal**: Resolve technical barriers and define the anti-bot boundary.

**In scope**:
- TLS/SSL specialized route (Route 4)
- Cloudflare/anti-bot backlog maintenance (Route 5)
- Fingerprint randomization spike (if approved)

**Key sources to resolve**:
- `yahoo_finance`
- `the_fly`
- `bofa_global_research`
- `texas_instruments_ir`
- `benzinga_analyst_ratings` (anti-bot boundary decision)

**Exit criteria**:
- TLS sources achieve stable connection with documented config.
- Anti-bot sources have a clear go/no-go decision documented.
- No source remains in `technical_only` without a defined resolution path.

### M3C-5D0 — Full Matrix Audit & Long Tail
**Goal**: Audit the remaining uncategorized sources and bring the full 92-item inventory under management.

**In scope**:
- Re-audit of deferred `not_audited` sources
- Long-tail investment bank and wire service sources
- Regional media expansion

**Key sources to address**:
- `jp_morgan_research`
- `morgan_stanley_insights`
- `reuters`
- Remaining uncategorized inventory (71 sources)

**Exit criteria**:
- Every source in the 92-item inventory has a category, status, and next stage.
- Scheduling allowlist is expanded only after individual validation.
- The repair backlog config is either empty (all resolved) or intentionally maintained for known boundary cases.

---

*This roadmap is a living document. Update stage assignments as new audit data arrives.*
