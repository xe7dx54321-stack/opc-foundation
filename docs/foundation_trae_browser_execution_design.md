# OPC Foundation TRAE Browser Execution Layer Design

> Phase: M3C-6B (design only — no production configuration)
> Generated: 2026-07-04
> Branch: `feature/m3c-6b-scheduled-candidate-preflight`
> Base commit: `8fc0ef7`
> Status: **Design document — not for production use**

---

## 1. Why We Need a TRAE Execution Layer

The OPC Foundation's Python static HTTP pipeline (`python_static_http`,
`rss_or_sitemap`, `public_json_ld_or_metadata`) handles sources that expose
content via server-rendered HTML or public feeds. The M3C-6B preflight
demonstrated that this pipeline is **insufficient** for a meaningful subset
of high-value sources:

| Source | Static HTTP Result | Implication |
|---|---|---|
| reuters | HTTP 401 | Auth gate or anti-bot; static pipeline blocked |
| marketwatch | HTTP 401 | Same pattern as reuters (Dow Jones / News Corp) |
| streetinsider | HTTP 403 | Likely Cloudflare / anti-bot challenge |

These sources are publicly readable in a normal browser session but reject
non-browser HTTP clients. A TRAE execution layer — built on TRAE's
`agent-browser` skill — can perform the same "open public page, read visible
items, record title / url / date" operation a human would, **without**
introducing Playwright / Selenium as a repo dependency.

The key insight: **TRAE itself is the execution layer.** The OPC Foundation
codebase does not need to ship browser automation; it only needs to define
the contract for what TRAE should observe and how to record the result.

---

## 2. Boundary: Python Static Pipeline vs TRAE Browser Pipeline

| Aspect | Python Static Pipeline | TRAE Browser Pipeline |
|---|---|---|
| Runtime | httpx + regex / bs4 in `.venv` | TRAE `agent-browser` skill (built-in) |
| Repo dependency | httpx, PyYAML, feedparser | None — TRAE provides browser tooling |
| Frequency | Scheduled (high / low) | On-demand or low-frequency only |
| Login / paywall bypass | Never | Never |
| Cookie / token storage | Never | Never |
| Output | JSONL in `data/` | Summary in `docs/` (no raw HTML) |
| Promotes to trial_v2 allowlist | Yes (when pass_static / pass_feed) | **No** — TRAE-assisted sources stay out of trial_v2 |
| Promotes to TRAE automation | N/A | Yes, with manual approval |

**Hard rule**: A source classified as `trae_browser_assisted_candidate` or
`trae_skill_assisted_candidate` MUST NOT be added to the trial_v2 allowlist.
The two pipelines are disjoint by design.

---

## 3. Source-to-Mode Mapping (Recommendation)

Based on M3C-6B preflight + M3C-6A coverage reaudit, the following mapping
is recommended:

### 3.1 Sources suited for Python scheduled pipeline (trial_v2)

These already pass `scheduled_preflight_pass_static` or `_feed` and are
in the current 9-source allowlist:

- barclays_our_insights
- markets_insider
- china_fund_news
- wind_public
- goldman_sachs_insights
- business_insider
- cls_cn
- zhitong_caijing
- gelonghui

### 3.2 Sources suited for TRAE browser-assisted observation

Static HTTP fails (401/403/JS-rendered) but the public page is viewable
in a browser without login. Candidates (pending M3C-6G spike):

- reuters (HTTP 401 — likely User-Agent gate)
- marketwatch (HTTP 401 — likely User-Agent gate)
- goldman_sachs_podcasts (JS-rendered, no static entry points — M3C-5B2)

### 3.3 Sources suited for agent-reach class skills

Not currently available in TRAE environment. If/when an `agent-reach` or
similar skill is installed, it could handle:

- Sources requiring structured-data extraction from JS-heavy pages
- Sources where the public feed requires OAuth discovery

**M3C-6B verdict**: `trae_skill_status = not_available`. No skill artifacts
to commit; no production dependency.

### 3.4 Sources suited for on-demand search

Content value is high but update frequency is irregular or topic-driven:

- marketwatch_upgrades_downgrades (already classified as `on_demand_candidate`)
- Sources best triggered by ticker / keyword / event

### 3.5 Sources that should stay in backlog

- streetinsider: HTTP 403, likely Cloudflare → `cloudflare_or_anti_bot_backlog`
  (pending M3C-6G confirmation)
- benzinga_analyst_ratings: confirmed Cloudflare (M3C-6A) →
  `cloudflare_or_anti_bot_backlog`
- merck_ir: TLS / proxy issue → `tls_or_proxy_backlog` (M3C-6F)

---

## 4. Automation Task Design

When a source is approved for TRAE browser-assisted observation
(manual approval required), the following task shape is used:

### 4.1 One-Shot Observation Task (M3C-6G spike style)

```text
Task: TRAE browser observation for <source_id>
Trigger: manual (via Schedule tool with action: "trigger")
Boundary:
  - Open public page only (no login)
  - No cookie / token usage
  - No paywall bypass
  - No captcha bypass
  - No raw HTML saved to repo
  - No screenshot saved to repo
Output (recorded in docs/ only):
  - public_page_accessible: bool
  - login_required: bool
  - paywall_observed: bool
  - captcha_or_antibot_observed: bool
  - visible_item_count: int
  - visible_dated_item_count: int
  - sample_items: list[SampleItem] (max 5, title/url/date_text only)
  - automation_suitability: suitable_for_scheduled | suitable_for_low_frequency | suitable_for_on_demand | not_suitable
  - notes: short text summary
Decision:
  - If public_page_accessible AND NOT login_required AND NOT paywall_observed
    AND NOT captcha_or_antibot_observed AND visible_item_count >= 3
    -> classify as trae_browser_assisted_candidate
  - If captcha_or_antibot_observed -> cloudflare_or_anti_bot_backlog
  - Else -> manual_reaudit_needed
```

### 4.2 Low-Frequency Recurring Observation (future, post-M3C-6G)

If a source proves stable under TRAE browser observation, a low-frequency
recurring task (e.g., daily or every 6 hours) can be created via the
`Schedule` tool. Constraints:

- `cron_expression` must respect the "no more than once every 10 minutes" rule
- `message` must include: source_id, public_url, boundary rules, output
  destination (docs/ only), and the "no login / no paywall / no bypass"
  mandate
- `enabled` defaults to false in example configs; real scheduling requires
  manual local setup

### 4.3 What MUST NOT Be Automated

- Login flows
- Paywall bypass
- Captcha solving
- Cookie persistence
- Raw HTML archiving in repo
- Screenshot storage in repo

---

## 5. Risk Avoidance

### 5.1 Login / Paywall / Anti-Bot

The TRAE browser observation protocol explicitly checks for and refuses to
bypass these blockers:

| Signal | Detection | Action |
|---|---|---|
| Login required | Page text contains "sign in" / "log in" / "subscribe to continue" | Mark `login_required=true`; do not proceed |
| Paywall | Page text contains "subscribe to read" / "premium content" | Mark `paywall_observed=true`; do not proceed |
| Captcha / anti-bot | Page text contains "captcha" / "checking your browser" / "cf-ray" | Mark `captcha_or_antibot_observed=true`; do not proceed |

### 5.2 Browser Dependency Hygiene

The OPC Foundation repo must NOT contain:

- `import playwright` or `from playwright` statements
- `import selenium` or `from selenium` statements
- `requirements.txt` / `pyproject.toml` entries for Playwright / Selenium
- Browser binaries / driver executables
- Screenshot PNG / JPEG files
- Raw HTML dumps (`.html` files in `data/`)

The `agent-browser` skill is a **TRAE runtime capability**, not a repo
dependency. It is invoked by TRAE at observation time; the repo only
records the structured result (title / url / date_text / counts).

### 5.3 Evidence Recording Without Raw Artifacts

Every TRAE browser observation produces a `TraeBrowserAssessment` record
(defined in `src/opc_foundation/source_inventory/execution_capabilities.py`)
with these fields only:

```python
@dataclass
class TraeBrowserAssessment:
    public_page_accessible: bool
    login_required: bool
    paywall_observed: bool
    captcha_or_antibot_observed: bool
    visible_item_count: int
    visible_dated_item_count: int
    sample_items: list[SampleItem]  # title, url, date_text only
    automation_suitability: str
    notes: str  # short text, no raw HTML, no cookies, no tokens
```

The `scan_sensitive_keywords()` function in `execution_capabilities.py`
enforces this by rejecting any evidence summary or notes containing:
`cookie:`, `set-cookie`, `bearer `, `api_key=`, `apikey:`, `proxy_url=`,
`http://127.0.0.1`, `http://localhost`, `password=`, `secret=`, `token=`.

---

## 6. Future Phase Recommendations

| Phase | Scope | Dependency on M3C-6B |
|---|---|---|
| M3C-6B (this phase) | Static preflight + TRAE capability design | — |
| M3C-6C | Feed / sitemap deep discovery for sources that returned 401/403 but may have public RSS endpoints not yet probed | Builds on M3C-6B feed_count=0 results |
| M3C-6E | On-demand source registry (ticker / keyword triggered) | Builds on M3C-6B `on_demand_candidate` classification |
| M3C-6F | Proxy retry for `tls_or_proxy_backlog` sources (e.g., merck_ir) | Independent of M3C-6B |
| M3C-6G | TRAE browser-assisted spike — invoke `agent-browser` once per source for reuters / marketwatch / goldman_sachs_podcasts | Directly consumes M3C-6B design |

### Recommended Next Step

**M3C-6G** is the natural successor: it takes the TRAE browser execution
design defined here and performs the first real `agent-browser` observation
on the 3 M3C-6B candidates. Until M3C-6G is approved, the 3 candidates
remain in `manual_reaudit_needed` and MUST NOT enter trial_v2 allowlist
or TRAE production scheduling.

---

## 7. Boundary Confirmation

| Item | Status |
|---|---|
| Modified TRAE scheduling | No |
| Modified TRAE local config | No |
| Modified trial_v2 allowlist | No |
| Configured production | No |
| Submitted data/local/secrets | No |
| Introduced Playwright/Selenium into repo | No |
| Submitted raw HTML / screenshot / cookies | No |
| Restored deleted Dashboard pages | No |
| Created tag | No |
| Created permanent TRAE automation task | No |

---

## References

- [M3C-6B Preflight Report](foundation_m3c_6b_scheduled_candidate_preflight_report.md)
- [M3C-6A Coverage Reaudit Report](foundation_m3c_6a_source_coverage_reaudit_report.md)
- [M3C-5B2 Goldman Podcasts Feed Spike](foundation_m3c_5b2_goldman_podcasts_feed_spike_report.md)
- Source execution capability model: `src/opc_foundation/source_inventory/execution_capabilities.py`
- Preflight config: `configs/foundation_m3c_6b_scheduled_candidate_preflight.example.yaml`
- Preflight script: `scripts/run_m3c_6b_scheduled_candidate_preflight.py`
