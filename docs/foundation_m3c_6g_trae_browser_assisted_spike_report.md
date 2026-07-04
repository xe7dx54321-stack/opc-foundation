# OPC Foundation M3C-6G — TRAE Browser-assisted Spike Report

> Phase: M3C-6G
> Generated: 2026-07-04
> Branch: `feature/m3c-6g-trae-browser-assisted-spike`
> Base commit (master after 6B merge): `0fd64a4`
> M3C-6B merge commit: `0fd64a4`
> Status: **Spike completed — all 3 sources blocked by anti-bot services**

---

## Summary

### Execution Baseline

- master path: `/Users/apple/Documents/一人公司OPC/opc-foundation`
- starting master commit: `8fc0ef7`
- M3C-6B merge commit: `0fd64a4`
- 6G branch: `feature/m3c-6g-trae-browser-assisted-spike`
- git status: clean
- trial_v2 source_count: 9 (unchanged)
- production_enabled: false

### M3C-6B Merge Result

- 是否合并: Yes
- merge commit: `0fd64a4` ("merge: scheduled candidate preflight framework")
- full pytest: 2061 passed, 0 failed
- trial_v2 allowlist 是否变化: No (still 9 sources)

### Candidate Sources (M3C-6G)

| source_id | prior_static_result | expected_value |
|---|---|---|
| reuters | http_401 | high |
| marketwatch | http_401 | high |
| streetinsider | http_403 | medium |

### Spike Tooling

- TRAE browser tool used: `agent-browser` (v0.31.1, Chrome 150.0.7871.46)
- Install location: `/tmp/agent-browser-install` (NOT committed to repo)
- agent-reach skill: **not available** in TRAE skill registry
- One-shot automation dry-run: not attempted (sources blocked before dry-run viable)

---

## TRAE Browser Observation Results

> Method: Used `agent-browser` CLI to open each public URL, wait for network idle,
> then inspect page title, body length, anti-bot markers, and visible items.
> **No screenshots saved. No raw HTML saved. No cookies recorded. No login attempted.
> No captcha solved. No Cloudflare bypass.**

### Observation Method Detail

For each source:
1. `agent-browser open <url>` — navigate to public page
2. `agent-browser wait --load networkidle` — wait for page to settle
3. `agent-browser get url` — confirm final URL
4. `agent-browser get title` — check page title
5. `agent-browser eval '...'` — check bodyLen, h1, DataDome/Cloudflare markers
6. `agent-browser snapshot -i` — inspect accessibility tree for visible items
7. `agent-browser get text body` — check actual content (not saved)

### Per-Source Results

| source_id | public_accessible | login_required | paywall | captcha/botwall | visible_items | dated_items | decision |
|---|---|---|---|---|---:|---:|---|
| reuters | true (challenge page loads) | false | false | true (DataDome) | 0 | 0 | captcha_or_antibot_blocked |
| marketwatch | true (challenge page loads) | false | false | true (DataDome) | 0 | 0 | captcha_or_antibot_blocked |
| streetinsider | true (challenge page loads) | false | false | true (Cloudflare + Turnstile) | 0 | 0 | captcha_or_antibot_blocked |

### Detailed Evidence (structured fields only — no raw HTML / cookies)

#### reuters

- URL loaded: `https://www.reuters.com/`
- Page title: `reuters.com` (suspicious — not the real site title)
- Body length: **0** (empty body — no actual news content)
- h1: none
- Anti-bot detected: **DataDome**
  - Iframe "DataDome Device Check" present in accessibility tree
  - `geo.captcha-delivery.com` referenced in page
  - DataDome JavaScript variable present (cookie value NOT recorded)
- Visible news items: 0
- Login prompt: none
- Paywall: none

#### marketwatch

- URL loaded: `https://www.marketwatch.com/`
- Page title: `marketwatch.com` (suspicious — not the real site title)
- Body length: **0** (empty body)
- h1: none
- Anti-bot detected: **DataDome**
  - `datadome=true` confirmed via eval
  - Same DataDome Device Check pattern as reuters
- Visible news items: 0
- Login prompt: none
- Paywall: none

#### streetinsider

- URL loaded: `https://www.streetinsider.com/`
- Page title: `请稍候…` ("Please wait...")
- Body length: **123** (just the challenge page)
- h1: `www.streetinsider.com`
- Anti-bot detected: **Cloudflare security challenge + Turnstile captcha**
  - h2: `正在进行安全验证` ("Security verification in progress")
  - Iframe: `包含 Cloudflare 安全质询的小组件` ("Widget containing Cloudflare security challenge")
  - Checkbox: `请验证您是真人` ("Please verify you are a real person") — Turnstile captcha
  - `cloudflare=true` confirmed via eval
  - Ray ID observed (value NOT recorded — not relevant to decision)
- Visible news items: 0
- Login prompt: none
- Paywall: none

---

## Skill / agent-reach Observation

| source_id | skill_available | structured_output | risk_flags | notes |
|---|---|---|---|---|
| reuters | false | false | not_applicable | agent-reach not in TRAE skill registry |
| marketwatch | false | false | not_applicable | agent-reach not in TRAE skill registry |
| streetinsider | false | false | not_applicable | agent-reach not in TRAE skill registry |

### agent-reach availability

- Checked TRAE skill registry: `agent-reach` is **not available**
- Available skills: `TRAE-product-knowledge`, `agent-browser`, `dynamic-ui`, `feedback`,
  `skill-creator`, `web-dev`
- Per M3C-6G boundary: "本阶段不要求强行安装 agent-reach"
- Per M3C-6G boundary: "如果没有，不要强行安装；记录：trae_skill_status = not_available"
- `trae_skill_status = not_available` for all 3 sources

---

## One-shot Automation Dry-run

| source_id | tested | result | reason |
|---|---|---|---|
| reuters | false | not_attempted | source blocked by DataDome before dry-run viable |
| marketwatch | false | not_attempted | source blocked by DataDome before dry-run viable |
| streetinsider | false | not_attempted | source blocked by Cloudflare before dry-run viable |

### Reason for not executing dry-run

All 3 sources returned `captcha_or_antibot_blocked` in the browser observation
phase. Per M3C-6G boundary:
- `no_captcha_solving: true`
- `no_cloudflare_bypass: true`
- `no_permanent_automation: true`

A one-shot dry-run on a blocked source would either:
1. Fail to extract any items (body empty), OR
2. Require captcha solving / Cloudflare bypass (forbidden)

Therefore the dry-run was not executed. `one_shot_automation_tested = false`.

---

## Sample Items

| source_id | title | url | date_text |
|---|---|---|---|
| reuters | (none — body empty) | — | — |
| marketwatch | (none — body empty) | — | — |
| streetinsider | (none — only challenge page visible) | — | — |

No sample items were recorded because all 3 sources showed 0 visible news items
(their public pages were replaced by anti-bot challenge pages).

---

## Final Decision

| source_id | recommended_execution_mode | trial_v2_allowlist_allowed_now | trae_automation_allowed_now | next_action |
|---|---|---|---|---|
| reuters | captcha_or_antibot_blocked | false | false | move_to_antibot_backlog |
| marketwatch | captcha_or_antibot_blocked | false | false | move_to_antibot_backlog |
| streetinsider | captcha_or_antibot_blocked | false | false | move_to_antibot_backlog |

### Allowlist Categorization

- 可进入 Python trial_v2 preflight 的源: **none**
- 只能进入 TRAE-assisted 的源: **none** (all blocked by anti-bot)
- 应降级 low_frequency 的源: **none**
- 应进入 on_demand 的源: **none**
- 应进入 browser_like / anti-bot backlog 的源: **reuters, marketwatch, streetinsider**
- 需要人工 reaudit 的源: none (decision is conclusive)

### Key Finding

**All 3 candidate sources are protected by commercial anti-bot services:**
- reuters + marketwatch: **DataDome** (French bot detection service)
- streetinsider: **Cloudflare** security challenge + Turnstile captcha

These services specifically detect and block browser automation tools, including
`agent-browser`. Even though `agent-browser` uses a real Chrome browser, the anti-bot
services fingerprint the automation context and serve a challenge page instead of
the actual news content.

**This is not a failure of the TRAE browser tool** — it is a deliberate anti-bot
defense deployed by the publishers. Per M3C-6G boundaries, we do NOT bypass these
defenses.

---

## Boundary Confirmation

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
| 是否引入 Playwright/Selenium | No (agent-browser is a TRAE runtime tool, not a repo dependency) |
| 是否恢复已删除 Dashboard 页面 | No |
| 是否打 tag | No |
| 是否创建永久自动化任务 | No |

---

## Test Results

- tests/source_inventory: **all passed** (including new test_trae_execution_assessment.py)
- tests/scripts: **all passed** (including new test_m3c_6g_trae_browser_assisted_spike.py)
- tests/dashboard: all passed
- full pytest: **all passed, 0 failed**

---

## Recommendation

### Immediate (M3C-6G conclusion)

1. **reuters, marketwatch, streetinsider**: classify as `captcha_or_antibot_blocked`
   in the source coverage layer matrix
2. Move all 3 sources to `cloudflare_or_anti_bot_backlog` (joining benzinga_analyst_ratings)
3. Do NOT add any of these 3 sources to trial_v2 allowlist
4. Do NOT create TRAE automation tasks for these sources
5. Update `configs/foundation_source_coverage_reaudit.example.yaml` in a future phase
   to reflect the anti-bot backlog classification

### Future phases

- **M3C-6E on-demand registry**: These sources may still be valuable for on-demand
  human-assisted research (manual browser visit), but not for automated scheduling
- **M3C-6H automation approval gate**: Not applicable — these sources cannot be
  automated without bypassing anti-bot, which is forbidden
- **Production**: Continue to keep `production_enabled = false`

### What NOT to do

- Do NOT attempt to bypass DataDome or Cloudflare
- Do NOT attempt to solve the Turnstile captcha
- Do NOT use proxy rotation to evade anti-bot fingerprinting
- Do NOT install agent-reach (not available, and would hit the same anti-bot wall)

---

## References

- [TRAE Execution Layer Architecture](foundation_trae_execution_layer_architecture.md)
- [M3C-6B Preflight Report](foundation_m3c_6b_scheduled_candidate_preflight_report.md)
- [M3C-6A Coverage Reaudit](foundation_m3c_6a_source_coverage_reaudit_report.md)
- TRAE assessment model: `src/opc_foundation/source_inventory/trae_execution_assessment.py`
- Spike config: `configs/foundation_m3c_6g_trae_browser_assisted_spike.example.yaml`
