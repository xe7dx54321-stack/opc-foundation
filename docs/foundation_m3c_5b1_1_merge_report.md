# OPC Foundation M3C-5B1.1-merge — Merge Report

> Generated: 2026-07-04T00:01 UTC+8
> Phase: M3C-5B1.1-merge
> Type: Feature branch merge to master

---

## 1. Pre-Merge State

| Item | Value |
|---|---|
| Master path | `/Users/apple/Documents/一人公司OPC/opc-foundation` |
| Master pre-merge commit | `5c2f35f` |
| origin/master pre-merge | `5c2f35f` |
| git status | clean |
| Execution window | 21:30 daily_check completed, >11h until 09:00 |

---

## 2. Merged Branches

| Branch | Commit | Merged | Conflicts |
|---|---|---|---|
| feature/m3c-5b1-1-next-candidate-preflight | `016363a` | Yes | None |
| feature/m3c-5b1-1a-gelonghui-date-repair | `6336a26` | Yes | None |

Merge order: B1.1 first, then B1.1a (B1.1a is based on B1.1).

---

## 3. Post-Merge Smoke

### 3.1 8-Source Trial V2 Allowlist (12/12 PASS)

```
  [PASS] Source count == 8
  [PASS] All content_ready
  [PASS] No gelonghui in allowlist
  [PASS] No merck_ir in allowlist
  [PASS] No blocked sources
  [PASS] production_enabled=false
  [PASS] trae_scheduling_enabled=false
  [PASS] TRAE config exists
  [PASS] All TRAE jobs disabled
  [PASS] Output dir exists
  [PASS] Reports dir exists
  [PASS] failed_queue empty
```

### 3.2 gelonghui Single-Source Preflight Smoke (3/3 PASS)

```
  Round 1/3: PASS (content_ready, score=100, dated=5, valid=5, relevant=5)
  Round 2/3: PASS (content_ready, score=100, dated=5, valid=5, relevant=5)
  Round 3/3: PASS (content_ready, score=100, dated=5, valid=5, relevant=5)
  => preflight_pass (3/3)
```

merck_ir correctly skipped (--source filter).

---

## 4. Allowlist Confirmation

Current 8 sources (unchanged):

1. barclays_our_insights
2. markets_insider
3. china_fund_news
4. wind_public
5. goldman_sachs_insights
6. business_insider
7. cls_cn
8. zhitong_caijing

Exclusion verified:

| Source | In Allowlist | In Candidates |
|---|---|---|
| gelonghui | No | Yes (next_scheduling_candidate) |
| merck_ir | No | Yes (next_scheduling_candidate) |
| goldman_sachs_podcasts | No | No |

---

## 5. Test Results

| Suite | Result |
|---|---|
| tests/source_inventory | 464 passed |
| tests/scripts | 113 passed |
| tests/dashboard | 270 passed |
| **full pytest** | **1820 passed, 0 failed** |

---

## 6. Boundary Confirmation

| Boundary | Status |
|---|---|
| TRAE scheduling modified | No |
| trial_v1 modified | No |
| trial_v2 allowlist modified | No |
| production configured | No |
| data/ submitted | No |
| configs/*.local.yaml submitted | No |
| secrets/cookies/tokens/proxy URL committed | No |
| Playwright/Selenium introduced | No |
| Deleted Dashboard pages restored | No |
| Tag created | No |

---

## 7. Recommendation

gelonghui achieved preflight_pass (3/3, score=100) with container-level date extraction repair. Recommend entering **M3C-5B1.2** for 8 -> 10 expansion readiness assessment, with gelonghui as the sole expansion candidate. merck_ir remains deferred pending proxy environment access.
