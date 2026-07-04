# OPC Foundation TRAE Execution Layer Architecture

> Phase: M3C-6G (architecture design document)
> Generated: 2026-07-04
> Branch: `feature/m3c-6g-trae-browser-assisted-spike`
> Base commit: `0fd64a4` (master after M3C-6B merge)
> Status: **Architecture document — describes future execution layer design**

---

## 1. Why We Need a TRAE Execution Layer

The OPC Foundation's Python static HTTP pipeline (`python_static_http`,
`rss_or_sitemap`, `public_json_ld_or_metadata`) handles sources that expose
content via server-rendered HTML or public feeds. However, M3C-6B and M3C-6G
demonstrated that this pipeline is **insufficient** for a meaningful subset
of high-value sources:

| Source | Static HTTP | TRAE Browser | Blocker |
|---|---|---|---|
| reuters | HTTP 401 | DataDome challenge page | Anti-bot |
| marketwatch | HTTP 401 | DataDome challenge page | Anti-bot |
| streetinsider | HTTP 403 | Cloudflare + Turnstile captcha | Anti-bot |
| benzinga_analyst_ratings | HTTP 403 | (not tested in 6G) | Cloudflare |
| goldman_sachs_podcasts | JS-rendered | (not tested in 6G) | No static entry points |

A TRAE execution layer — built on TRAE's `agent-browser` skill — can perform
the same "open public page, read visible items, record title / url / date"
operation a human would, **without** introducing Playwright / Selenium as a
repo dependency.

**However, M3C-6G revealed a critical limitation**: commercial anti-bot
services (DataDome, Cloudflare) can fingerprint browser automation tools and
serve challenge pages even to real Chrome instances. The TRAE execution
layer is therefore **not a universal solution** — it works for JS-rendered
sources without anti-bot, but cannot bypass anti-bot defenses (and per
project boundaries, must not attempt to).

---

## 2. Python Static Pipeline: Scope and Limits

### Responsibilities

- httpx / urllib HTTP requests with realistic User-Agent
- RSS / Atom / sitemap parsing
- JSON-LD / OpenGraph / meta tag extraction
- Regular expression / BeautifulSoup HTML parsing
- Scheduled execution via trial_v2 allowlist (9 sources)

### Limits

- Cannot render JavaScript (no JS engine)
- Cannot pass cookie-based sessions (no browser context)
- Cannot bypass 401/403 authentication gates
- Cannot bypass Cloudflare / DataDome anti-bot challenges

### Sources suited for Python scheduled pipeline

All 9 current trial_v2 sources:
- barclays_our_insights, markets_insider, china_fund_news, wind_public,
  goldman_sachs_insights, business_insider, cls_cn, zhitong_caijing, gelonghui

---

## 3. TRAE Browser Pipeline: Scope and Limits

### Responsibilities

- Open public pages with real Chrome (via `agent-browser` skill)
- Wait for network idle / JS rendering
- Extract visible items via accessibility tree snapshot
- Record structured fields only (title / url / date_text)
- One-shot or low-frequency observation

### Limits (revealed by M3C-6G)

- **Cannot bypass anti-bot services**: DataDome and Cloudflare detect browser
  automation and serve challenge pages instead of actual content
- **Cannot solve captchas**: Turnstile / reCAPTCHA / hCaptcha are forbidden
  by project boundaries
- **Not suitable for high-frequency scheduling**: Browser sessions are slow
  and resource-intensive compared to HTTP requests
- **Cannot persist login state**: Per project boundaries, no cookie / session
  storage

### Sources suited for TRAE browser pipeline

- JS-rendered sources without anti-bot (e.g., goldman_sachs_podcasts —
  pending future spike without anti-bot blockers)
- Sources where public content is visible in a normal browser session but
  not in httpx (e.g., User-Agent gated sources — none currently identified)

### Sources NOT suited for TRAE browser pipeline (M3C-6G conclusion)

- reuters, marketwatch: DataDome blocks browser automation
- streetinsider: Cloudflare blocks browser automation
- benzinga_analyst_ratings: Cloudflare blocks (confirmed in M3C-6A)

---

## 4. agent-reach Class Skill: Scope and Limits

### Theoretical responsibilities

- Structured data extraction from JS-heavy pages
- Public feed discovery requiring OAuth
- Headless browser orchestration with anti-detection

### Current status (M3C-6G)

- **Not available** in TRAE skill registry
- Available skills: `TRAE-product-knowledge`, `agent-browser`, `dynamic-ui`,
  `feedback`, `skill-creator`, `web-dev`
- Per M3C-6G boundary: "本阶段不要求强行安装 agent-reach"
- Per M3C-6G boundary: "如果没有，不要强行安装；记录：trae_skill_status = not_available"

### Why not create one

1. Even if agent-reach existed, it would hit the same DataDome / Cloudflare
   anti-bot walls as `agent-browser`
2. Creating a custom skill to bypass anti-bot would violate project boundaries
3. The `skill-creator` skill exists, but using it to create an anti-bot
   bypass tool is forbidden

### Sources suited for agent-reach (theoretical)

- Sources requiring multi-step public navigation (none currently identified
  that aren't already anti-bot blocked)

---

## 5. TRAE Automation vs trial_v2 Allowlist

### Hard rule: Disjoint pipelines

| Pipeline | Allowlist | Frequency | Login | Anti-bot |
|---|---|---|---|---|
| Python trial_v2 | 9 sources | High (2-4x daily) | Never | Never |
| TRAE browser | 0 sources (M3C-6G) | Low / on-demand | Never | Never |
| TRAE automation | 0 sources (M3C-6G) | Manual approval | Never | Never |

### Why TRAE browser candidates do NOT enter trial_v2

1. **Different runtime**: TRAE uses Chrome browser; trial_v2 uses httpx
2. **Different frequency**: TRAE is low-frequency; trial_v2 is high-frequency
3. **Different dependencies**: TRAE needs `agent-browser` runtime; trial_v2
   only needs Python packages in `.venv`
4. **Different failure modes**: TRAE fails on anti-bot; trial_v2 fails on
   HTTP errors / parse errors

A source classified as `trae_browser_assisted_candidate` MUST NOT be added to
the trial_v2 allowlist. The two pipelines are disjoint by design.

### M3C-6G result: No source qualifies for either pipeline

All 3 candidates (reuters, marketwatch, streetinsider) are blocked by
anti-bot services. They cannot enter:
- trial_v2 allowlist (HTTP blocked)
- TRAE browser pipeline (anti-bot blocked)
- TRAE automation (anti-bot blocked)

They move to `cloudflare_or_anti_bot_backlog`.

---

## 6. Risk Avoidance

### 6.1 Login / Paywall / Anti-bot

The TRAE browser observation protocol explicitly checks for and refuses to
bypass these blockers:

| Signal | Detection | Action |
|---|---|---|
| Login required | Page text / iframe mentions "sign in" / "log in" | Mark `login_required=true`; do not proceed |
| Paywall | Page text mentions "subscribe to read" / "premium content" | Mark `paywall_observed=true`; do not proceed |
| Captcha | Turnstile / reCAPTCHA / hCaptcha iframe present | Mark `captcha_or_antibot_observed=true`; do not proceed |
| Cloudflare / botwall | "Checking your browser" / cf-ray / cf-mitigated | Mark `cloudflare_or_botwall_observed=true`; do not proceed |
| DataDome | "DataDome Device Check" iframe / captcha-delivery.com | Mark `captcha_or_antibot_observed=true`; do not proceed |

### 6.2 Browser Dependency Hygiene

The OPC Foundation repo must NOT contain:
- `import playwright` or `from playwright` statements
- `import selenium` or `from selenium` statements
- `requirements.txt` / `pyproject.toml` entries for Playwright / Selenium
- Browser binaries / driver executables
- Screenshot PNG / JPEG files
- Raw HTML dumps (`.html` files in `data/`)
- `agent-browser` install artifacts (installed to `/tmp`, not committed)

The `agent-browser` skill is a **TRAE runtime capability**, not a repo
dependency. It is invoked by TRAE at observation time; the repo only records
the structured result (title / url / date_text / counts).

### 6.3 Evidence Recording Without Raw Artifacts

Every TRAE browser observation produces a `TraeBrowserObservation` record
(defined in `src/opc_foundation/source_inventory/trae_execution_assessment.py`)
with these fields only:

```python
@dataclass
class TraeBrowserObservation:
    public_page_accessible: bool
    login_required: bool
    paywall_observed: bool
    captcha_or_antibot_observed: bool
    cloudflare_or_botwall_observed: bool
    visible_item_count: int
    visible_dated_item_count: int
    sample_items: list[TraeBrowserSampleItem]  # title, url, date_text only
    structured_extraction_possible: bool
    repeatability_observed: bool
    observation_notes: str  # short text, no raw HTML, no cookies, no tokens
```

The `scan_sensitive_keywords()` function enforces this by rejecting any
evidence summary, notes, or sample items containing: `cookie:`, `set-cookie`,
`bearer `, `api_key=`, `apikey:`, `proxy_url=`, `http://127.0.0.1`,
`http://localhost`, `password=`, `secret=`, `token=`, `session_id=`,
`sessionid=`, `jsessionid=`.

---

## 7. Future Manual Approval Gate Design

### 7.1 Why manual approval is required

TRAE automation introduces risks that Python scheduled pipelines do not have:
- Browser sessions can be flagged as bots (DataDome, Cloudflare)
- Browser sessions can accidentally trigger login flows
- Browser sessions can consume more resources
- Browser sessions can be less predictable

Therefore, any source promoted to TRAE automation must pass a **manual
approval gate** before activation.

### 7.2 Gate checklist (future M3C-6H)

For a source to be approved for TRAE automation:

1. ✅ Source must be classified as `trae_browser_assisted_candidate` (not blocked)
2. ✅ `public_page_accessible = true`
3. ✅ `login_required = false`
4. ✅ `paywall_observed = false`
5. ✅ `captcha_or_antibot_observed = false`
6. ✅ `cloudflare_or_botwall_observed = false`
7. ✅ `visible_item_count >= 3`
8. ✅ `visible_dated_item_count >= 2`
9. ✅ `structured_extraction_possible = true`
10. ✅ `repeatability_observed = true`
11. ✅ Manual human review of sample items
12. ✅ `trae_automation_allowed_now = "manual_approval_required"`
13. ✅ User explicit approval

### 7.3 What the gate prevents

- Auto-promoting a source to TRAE automation without human review
- Auto-promoting a blocked source to any pipeline
- Auto-promoting a TRAE candidate to trial_v2 allowlist (disjoint pipelines)

---

## 8. Future Phase Recommendations

| Phase | Scope | Dependency on M3C-6G | Status |
|---|---|---|---|
| M3C-6G (this phase) | TRAE browser spike + architecture | — | **Completed** |
| M3C-6G.1 | TRAE-assisted adapter dry-run | Requires at least 1 source to pass M3C-6G (none did) | **Blocked** — no source qualifies |
| M3C-6E | On-demand source registry | Independent | Available |
| M3C-6F | Proxy retry for `tls_or_proxy_backlog` (merck_ir) | Independent | Available |
| M3C-6H | Automation approval gate | Requires M3C-6G.1 success | **Blocked** — M3C-6G.1 blocked |

### Recommended Next Step

**M3C-6G conclusion**: All 3 candidate sources are blocked by commercial
anti-bot services (DataDome / Cloudflare). No source qualifies for TRAE
browser-assisted automation. The TRAE execution layer design is documented
but has no eligible sources in the current candidate pool.

**Recommendation**: 
1. Update `cloudflare_or_anti_bot_backlog` in source coverage matrix to
   include reuters, marketwatch, streetinsider (joining benzinga_analyst_ratings)
2. Do NOT pursue M3C-6G.1 (no source qualifies)
3. Consider M3C-6E (on-demand registry) for human-assisted research on
   these sources (manual browser visits, not automated)
4. Continue to keep `production_enabled = false`

---

## 9. Boundary Confirmation

| Item | Status |
|---|---|
| 是否修改 TRAE scheduling | No |
| 是否修改 TRAE local config | No |
| 是否修改 trial_v2 allowlist | No (still 9 sources) |
| 是否配置 production | No |
| 是否提交 data/local/secrets | No |
| 是否提交 raw HTML | No |
| 是否提交 screenshot | No |
| 是否提交 cookie/token/proxy | No |
| 是否引入 Playwright/Selenium | No |
| 是否恢复已删除 Dashboard 页面 | No |
| 是否打 tag | No |
| 是否创建永久自动化任务 | No |

---

## References

- [M3C-6G Spike Report](foundation_m3c_6g_trae_browser_assisted_spike_report.md)
- [M3C-6B Preflight Report](foundation_m3c_6b_scheduled_candidate_preflight_report.md)
- [TRAE Browser Execution Design (M3C-6B)](foundation_trae_browser_execution_design.md)
- TRAE assessment model: `src/opc_foundation/source_inventory/trae_execution_assessment.py`
- Execution capability model: `src/opc_foundation/source_inventory/execution_capabilities.py`
- Spike config: `configs/foundation_m3c_6g_trae_browser_assisted_spike.example.yaml`
