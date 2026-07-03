# OPC Foundation M3C-5Merge.1 — Current Master Live Smoke Report

> Generated: 2026-07-03T23:01 UTC+8
> Phase: M3C-5Merge.1
> Type: Post-merge live smoke + stability re-check

---

## 1. Execution Pre-Check

| Item | Value |
|---|---|
| Master path | `/Users/apple/Documents/一人公司OPC/opc-foundation` |
| Master commit | `c41f2bf` |
| origin/master | `c41f2bf` |
| git status | clean (no modified/untracked files) |
| Branch | master |
| Execution window | 21:30 daily_check completed; >11h until next 09:00 morning_run — safe |

All pre-conditions satisfied.

---

## 2. Live Smoke Results

### 2.1 validate-config

```
Allowlist: configs/foundation_trial_v2_content_ready_allowlist.example.yaml
Source count: 8
Production enabled: False
TRAE scheduling enabled: False
All 8 sources are content_ready
Result: PASS
```

### 2.2 preflight

```
Preflight file: data/foundation_trial_v2_content_ready/index/preflight_content_ready_audit.jsonl (8 records)
gelonghui in allowlist: False
merck_ir in allowlist: False
Result: PASS (retained: 8, downgraded: 0, new: [])
```

### 2.3 dry-run

```
Dry run: would process 8 content_ready sources
No actual HTTP requests made in dry-run mode
Result: PASS
```

### 2.4 check (15-item verification)

```
  [PASS] Allowlist exists
  [PASS] Source count == 8 - Got 8
  [PASS] All sources content_ready
  [PASS] No content_watch in allowlist
  [PASS] No content_reject in allowlist
  [PASS] No technical_only in allowlist
  [PASS] production_enabled=false
  [PASS] trae_scheduling_enabled=false
  [PASS] TRAE example config exists
  [PASS] All TRAE jobs enabled=false
  [PASS] Run script exists
  [PASS] Check script exists
  [PASS] Output directory exists
  [PASS] Reports directory exists
  [PASS] No blocked sources in allowlist

check: PASS 15/15, FAIL 0/15
check OVERALL: PASS
```

### 2.5 failed_queue

```
failed_queue: empty
```

### 2.6 Note: PowerShell vs Python

macOS environment — PowerShell (`pwsh`) not available. All 4 modes executed via Python equivalent logic matching the original `run_foundation_trial_v2_content_ready.ps1` and `check_foundation_trial_v2_content_ready.ps1` script logic exactly. No code changes made.

---

## 3. Daily Status / Control Center

### 3.1 Daily Status Report

`python scripts/generate_daily_status_report.py` executed successfully.

Section **Foundation Trial V2 Content Ready** present with:

| Field | Value |
|---|---|
| source_count | 8 |
| production_enabled | False |
| observation_status | partial_observation |
| failed_queue_count | 0 |
| wind_public watch flag | True |
| wind_public garbled_text observed | True |
| Last run | 2026-07-03T21:01:06 (evening_run) |

### 3.2 Dashboard Tests

```
tests/dashboard: 270 passed in 5.06s
```

Key test classes confirmed:
- `test_trial_v2_content_ready_runtime.py`: Trial V2 Content Ready read-only card tests all pass
- `test_trial_runtime_health.py`: Runtime health and fail-soft handling verified
- `test_dashboard_docs.py`: No deleted pages restored

---

## 4. Allowlist Confirmation

### 4.1 Current 8-Source Allowlist

| # | source_id | content_status | priority |
|---|---|---|---|
| 1 | barclays_our_insights | content_ready | P0 |
| 2 | markets_insider | content_ready | P0 |
| 3 | china_fund_news | content_ready | P0 |
| 4 | wind_public | content_ready | P0 |
| 5 | goldman_sachs_insights | content_ready | P1 |
| 6 | business_insider | content_ready | P1 |
| 7 | cls_cn | content_ready | P1 |
| 8 | zhitong_caijing | content_ready | P1 |

### 4.2 Exclusion Verification

| Source | In Allowlist? |
|---|---|
| gelonghui | No |
| merck_ir | No |
| goldman_sachs_podcasts | No |
| Any watch/reject/technical_only | No |

---

## 5. Test Results

| Suite | Result |
|---|---|
| tests/source_inventory | 398 passed |
| tests/scripts | 113 passed |
| tests/dashboard | 270 passed |
| **full pytest** | **1754 passed, 0 failed** |

---

## 6. Boundary Confirmation

| Boundary | Status |
|---|---|
| TRAE scheduling modified? | No |
| trial_v1 modified? | No |
| trial_v2 allowlist modified? | No |
| production configured? | No |
| data/ submitted? | No |
| configs/*.local.yaml submitted? | No |
| secrets/cookies/tokens/proxy URL committed? | No |
| Playwright/Selenium introduced? | No |
| Deleted Dashboard pages restored? | No |
| Tag created? | No |

---

## 7. Commit / Push

| Item | Value |
|---|---|
| New file | `docs/foundation_m3c_5merge_1_live_smoke_report.md` |
| Committed docs | foundation_m3c_5merge_1_live_smoke_report.md |
| origin/master | will be c41f2bf + 1 |
| git status | clean (post-commit) |

---

## 8. Conclusion

All M3C-5Merge.1 live smoke checks passed:

- validate-config: PASS (8 sources, production_enabled=false)
- preflight: PASS (8/8 retained, 0 downgraded, no gelonghui/merck_ir)
- dry-run: PASS (8 sources queued)
- check: PASS (15/15)
- failed_queue: empty
- Daily Status: Foundation Trial V2 Content Ready section present and correct
- Dashboard tests: 270 passed
- full pytest: 1754 passed, 0 failed
- 8-source allowlist unchanged
- TRAE scheduling untouched
- production_enabled=false confirmed
- All boundary constraints respected

### 8.1 Next Step Recommendation

**Enter M3C-5B1.1 preflight** is acceptable. Conditions:

- Master stable at 1754 tests passing
- Trial V2 content-ready sources consistently producing daily health/run_log data (4 runs today)
- wind_public garbled_text under observation but not degrading below content_ready threshold
- gelonghui / merck_ir remain next_scheduling_candidate only (not in allowlist)
- Continue deferring production scheduling
