# OPC Foundation M3C-5B1.3 — Expand Trial V2 Content-Ready Allowlist to 9 Sources

> Generated: 2026-07-04
> Base branch: feature/m3c-5b1-2-gelonghui-9-source-preflight
> Base commit: 202f73a
> Current branch: feature/m3c-5b1-3-expand-trial-v2-to-9
> Phase: M3C-5B1.3

---

## Summary

| Item | Value |
|---|---|
| Base source count | 8 |
| New source | gelonghui |
| Total source count | 9 |
| production_enabled | false |
| trae_scheduling_enabled | false |
| Full pytest | 1874 passed, 0 failed |

---

## 1. Execution Status

### Pre-Expansion Allowlist (8 Sources)

```text
barclays_our_insights
markets_insider
china_fund_news
wind_public
goldman_sachs_insights
business_insider
cls_cn
zhitong_caijing
```

### Post-Expansion Allowlist (9 Sources)

```text
barclays_our_insights
markets_insider
china_fund_news
wind_public
goldman_sachs_insights
business_insider
cls_cn
zhitong_caijing
gelonghui
```

### Excluded Sources (Not Added)

| Source | Reason |
|---|---|
| merck_ir | next_scheduling_candidate only, not yet approved for trial_v2 |
| goldman_sachs_podcasts | browser_like_candidate, deferred to M3C-5B2 |
| All watch/reject/technical_only sources | policy exclusion |
| All P1/P2/P3 sources | not in current scope |
| 92 full inventory sources | not in current scope |

---

## 2. Verification Results

### 2.1 validate-config

```text
PASS
source_count = 9
expected_source_count = 9
production_enabled = false
gelonghui present = true
merck_ir absent = true
goldman_sachs_podcasts absent = true
all sources content_ready = true
```

### 2.2 preflight

```text
PASS
9/9 sources retained
0 downgraded
gelonghui content_ready = true
gelonghui score = 100 (>= 70)
gelonghui dated_candidate_count = 5 (>= 2)
wind_public retained with garbled_text watch flag
```

### 2.3 dry-run

```text
PASS
dry_run_source_count = 9
dry_run_queue includes gelonghui
dry_run_queue excludes merck_ir
dry_run_queue excludes goldman_sachs_podcasts
production_enabled = false
```

### 2.4 manual run (live)

```text
PASS
run_records_added = 9
```

#### Record Deltas

| Metric | Before | After | Delta |
|---|---|---|---|
| source_health | 0 | 9 | +9 |
| run_log | 0 | 9 | +9 |
| failed_queue | 0 (empty) | 0 (empty) | 0 |

### 2.5 check

```text
PASS
source_count = 9
latest_run_source_count = 9
failed_queue = 0 (empty)
blocked_source_check = pass
production_enabled = false
all sources content_ready = true
```

### 2.6 Daily Status / Control Center

```text
PASS
Daily Status source_count = 9
Control Center tests = 270 passed, 0 failed
wind_public watch flag = visible
 gelonghui visible as trial_v2 content-ready source = true
production_enabled = false
```

---

## 3. Test Results

| Test Suite | Result |
|---|---|
| tests/source_inventory | passed |
| tests/scripts | passed |
| tests/dashboard | 270 passed |
| Full pytest | 1874 passed, 0 failed |

### New Tests Added

- `tests/source_inventory/test_trial_v2_content_ready_9_sources.py` (21 tests)

### Updated Tests

- `tests/source_inventory/test_content_validity_audit.py`
  - `test_allowlist_no_blocked_sources`: removed gelonghui from excluded_ids
  - `test_content_watch_not_in_scheduling`: removed gelonghui from watch_ids
  - `test_allowlist_source_count_is_8` -> `test_allowlist_source_count_is_9`
- `tests/source_inventory/test_next_candidate_preflight.py`
  - `test_allowlist_unchanged` -> `test_allowlist_has_9_sources`
  - `test_allowlist_no_gelonghui` -> `test_allowlist_has_gelonghui`
- `tests/source_inventory/test_9_source_expansion_preflight.py`
  - `test_formal_allowlist_no_gelonghui` (Config) -> `test_formal_allowlist_has_gelonghui`
  - `test_formal_allowlist_unchanged` (Isolation) -> `test_formal_allowlist_has_9_sources`
  - `test_formal_allowlist_no_gelonghui` (Isolation) -> `test_formal_allowlist_has_gelonghui`
- `tests/source_inventory/test_p0_source_repair.py`
  - `test_no_gelonghui_in_trial_v2_allowlist` -> `test_gelonghui_in_trial_v2_allowlist`

---

## 4. Boundary Confirmation

| Item | Status |
|---|---|
| Modified TRAE scheduling time | No |
| Modified TRAE scheduling command | No |
| Modified trial_v1 | No |
| Configured production | No |
| Submitted data/local/secrets | No |
| Introduced Playwright/Selenium | No |
| Restored deleted Dashboard pages | No |
| Created tag | No |
| Committed data/ | No |
| Committed configs/*.local.yaml | No |

---

## 5. Files Modified

| File | Change |
|---|---|
| `configs/foundation_trial_v2_content_ready_allowlist.example.yaml` | expected_source_count 8->9, added gelonghui entry |
| `tests/source_inventory/test_trial_v2_content_ready_9_sources.py` | NEW: 9-source allowlist tests |
| `tests/source_inventory/test_content_validity_audit.py` | Updated 3 tests for 9-source |
| `tests/source_inventory/test_next_candidate_preflight.py` | Updated 2 tests for 9-source |
| `tests/source_inventory/test_9_source_expansion_preflight.py` | Updated 3 tests for 9-source |
| `tests/source_inventory/test_p0_source_repair.py` | Updated 1 test for gelonghui in allowlist |

---

## 6. Next Steps

1. **Enter 9-source 24h observation**
   - Observe 4 automated TRAE job runs:
     - 09:00 morning_run
     - 15:00 afternoon_run
     - 21:00 evening_run
     - 21:30 daily_check
   - Verify each run generates 9 source_health + 9 run_log records
   - Monitor failed_queue remains empty
   - Monitor wind_public garbled_text watch flag

2. **Continue to defer**
   - merck_ir: remain next_scheduling_candidate only
   - goldman_sachs_podcasts: remain browser_like_candidate for M3C-5B2
   - production: remain disabled

3. **Post-observation**
   - If 24h observation passes without issue, trial_v2 9-source configuration is stable
   - Consider M3C-5B2 for browser-like sources or M3C-5C for production scheduling (future phase)
