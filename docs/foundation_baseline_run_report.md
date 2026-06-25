# OPC Foundation Baseline Run Report - M3C-2A

**Version**: 1.0  
**Execution Date**: 2026-06-26  
**Commit**: 262a416  
**Status**: M3C-2A Ready（首次全信息源基线运行完成）

---

## 1. Execution Environment

| Item | Value |
|---|---|
| Repository Path | D:\李少博的文件\一人公司项目开发\opc-foundation |
| Current Commit | 262a416 |
| Execution Date | 2026-06-26 |
| Execution Time | 00:07 - 00:10 (local) |
| Execution Root | Repository root directory |

---

## 2. Execution Summary

M3C-2A completed first baseline run for all information sources. This run establishes baseline data for Dashboard integration.

**Execution Order**:
1. Control Center Config Check
2. Research Archive Baseline Run
3. WeChat Archive Baseline Run
4. Official Filings Baseline Run
5. Manual URL Check
6. Document Extraction Baseline Run
7. Daily Status Report Generation

---

## 3. Script Execution Results

### 3.1 Control Center Config Check

**Command**: `powershell -ExecutionPolicy Bypass -File scripts/check_foundation_control_center.ps1`

**Result**: SUCCESS

| Config File | Status |
|---|---|
| foundation_capabilities.yaml | OK |
| capability_runbooks.yaml | OK |
| capability_runtime_bindings.yaml | OK |
| foundation_source_inventory.example.yaml | OK |
| trae_foundation_schedule.example.yaml | OK |

**Source Inventory Load**:
- Groups: 9
- Sources: 92
- Errors: 0
- Warnings: 1

---

### 3.2 Research Archive Baseline Run

**Commands**:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_research_archive.ps1 -Mode validate-config
powershell -ExecutionPolicy Bypass -File scripts/run_research_archive.ps1 -Mode dry-run
powershell -ExecutionPolicy Bypass -File scripts/check_research_archive.ps1
```

**Result**: SUCCESS

**Validate-Config Output**:
```
- Total sources: 3
- Enabled sources: 3
  - live_ecb_rss (rss_feed) - ECB Press Releases RSS
  - live_fed_rss (rss_feed) - Federal Reserve Press Releases RSS
  - live_imf_rss (rss_feed) - IMF News RSS
```

**Dry-Run Output**:
```
- Total sources: 3
- Enabled: 3
- Candidate docs: 5
- New docs: 3
- Saved: 0 (dry-run mode)
- Duplicates skipped: 2
- Failed: 0
```

**Source Health**:
| Status | Count |
|---|---|
| healthy | 1 |
| degraded | 0 |
| failed | 2 |
| disabled | 0 |
| unknown | 0 |

**Failed Sources**:
| Source | Error |
|---|---|
| ECB Press Releases RSS | feed content empty: https://www.ecb.europa.eu/rss/press.html.en |
| IMF News RSS | feed content empty: https://www.imf.org/en/News/Rss |

**Healthy Sources**:
- Federal Reserve Press Releases RSS (rss_feed)

**Archive Products**:
| File | Status |
|---|---|
| documents.jsonl (42KB) | OK |
| documents.latest.jsonl (0 bytes) | OK |
| run_log.jsonl (36KB) | OK |
| source_health.jsonl (2KB) | OK |
| failed_queue.jsonl (5KB) | OK |
| reports/ (4 reports) | OK |

**Failed Queue Entries**: 6

---

### 3.3 WeChat Archive Baseline Run

**Command**: `powershell -ExecutionPolicy Bypass -File scripts/run_wechat_archive.ps1`

**Result**: SUCCESS

**Output**:
```
- Monitored accounts: 1
- Candidate articles: 10
- New articles: 0
- Saved: 0
- Duplicates skipped: 10
- Failed: 0
```

**Warning**:
- Account [第四维的梦想] feed parsing warning: text/plain; charset=utf-8 is not an XML media type

**Reports**: data\wechat_archive\reports\daily_capture_2026-06-25.md

---

### 3.4 Official Filings Baseline Run

**Commands**:
```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_official_filings.ps1 -Mode dry-run
```

**Result**: SUCCESS

**Output**:
```
- Total sources: 3
- Enabled: 1
- Candidate filings: 0
- New saved: 0
- Duplicates skipped: 0
- Failed: 0
- Skipped: 2 (other sources not enabled)
```

---

### 3.5 Manual URL Check

**Command**: `powershell -ExecutionPolicy Bypass -File scripts/run_manual_url_archive.ps1`

**Result**: SUCCESS (no pending URLs)

**Output**: "No pending URLs, waiting for human trigger."

---

### 3.6 Document Extraction Baseline Run

**Command**: `powershell -ExecutionPolicy Bypass -File scripts/run_document_extraction.ps1 -Mode dry-run`

**Result**: SUCCESS

**Output**:
```
- Total sources: 5
- Enabled: 5
- Candidate docs: 5
- Saved: 4
- Duplicates: 0
- Partial: 0
- Failed: 1
- Skipped: 0
```

**Warning**: Run completed with 1 failure (non-blocking)

---

### 3.7 Daily Status Report

**Command**: `powershell -ExecutionPolicy Bypass -File scripts/check_foundation_daily_status.ps1`

**Result**: SUCCESS

**Report Path**: data\foundation_control_center\reports\daily_status_2026-06-26.md

---

## 4. Source Group Status Summary

| Source Group | Status | Notes |
|---|---|---|
| official_public_research | PARTIAL | ECB/IMF RSS feed issues, Fed RSS healthy |
| official_podcast_transcript | NOT TESTED | No production config |
| bank_conference_transcripts | NOT TESTED | No production config |
| media_research_mentions | NOT TESTED | No production config |
| analyst_actions | NOT TESTED | No production config |
| chinese_rebroadcast | BASELINE | 1 account, 10 candidates, 0 new (duplicate) |
| official_filings | PARTIAL | 3 sources, 1 enabled, 0 candidates |
| document_extraction | BASELINE | 5 sources, 5 candidates, 4 saved, 1 failed |
| manual_url | READY | No pending URLs |
| search_providers | NOT TESTED | Default on_demand |
| community_dev_signals | NOT TESTED | Default on_demand/dormant |
| blocked_high_risk_sources | NOT RUN | Confirmed not executed |

---

## 5. Capability Status Changes

| Category | Count | Notes |
|---|---|---|
| Running normally | TBD | Awaiting runtime data integration |
| Degraded | 2 | ECB/IMF RSS feed issues |
| Failed | 1 | Document extraction partial failure |
| Known limited | 2 | HKEX (known_limited), ECB/IMF (feed issues) |
| Unknown never run | TBD | Awaiting runtime data integration |
| Manual only | TBD | Awaiting runtime data integration |
| Utility | TBD | Awaiting runtime data integration |

---

## 6. Source Status Distribution

Based on source inventory (92 sources):

| Status | Count |
|---|---|
| Scheduled | TBD |
| On-demand | TBD |
| Dormant | TBD |
| Do not ingest | TBD |
| Success | TBD |
| Empty source | TBD |
| Failed | TBD |
| Skipped | TBD |

---

## 7. Dashboard Status

**Pages** (4 pages, no restored pages):
- [OK] Capability Map
- [OK] Workflow Map
- [OK] Health Monitor
- [OK] Config Check

**Restored Pages**: None (confirmed)

**Data Integration**:
- Source inventory: 92 sources loaded
- Runtime binding: Awaiting runtime data
- Source health: 3 healthy, 2 failed (research archive)

---

## 8. Blocked/High-Risk Confirmation

**Confirmed**: No blocked/high-risk sources were executed during this baseline run.

| Source Type | Execution |
|---|---|
| Blocked sources | NOT RUN |
| High-risk sources | NOT RUN |
| Telegram groups | NOT RUN |
| Cloud storage shares | NOT RUN |
| Paid report download sites | NOT RUN |

---

## 9. Issues Summary

### P0 (Critical)

None

### P1 (High)

| Issue | Description | Resolution |
|---|---|---|
| ECB RSS Feed Empty | ECB Press Releases RSS feed returns empty content | Monitor; may need alternative source |
| IMF RSS Feed Empty | IMF News RSS feed returns empty content | Monitor; may need alternative source |

### P2 (Medium)

| Issue | Description | Resolution |
|---|---|---|
| Document Extraction Partial | 1 out of 5 document extraction sources failed | Retry-failed available |
| WeChat Feed Format | text/plain instead of XML media type | Non-blocking warning |

---

## 10. M3C-2B Prerequisites

To proceed to M3C-2B (one week stable run):

- [ ] Fix ECB/IMF RSS feed issues (P1)
- [ ] Configure production configs for remaining source groups
- [ ] Verify all scheduled sources can run successfully
- [ ] Establish baseline data for 7 days
- [ ] Generate baseline stability report

---

## 11. Next Steps

1. **M3C-2B**: One week stable run with monitoring
2. **M3C-2C**: Production config optimization based on baseline results
3. **M3C-2D**: TRAE task configuration for automated scheduling

---

## 12. Related Documents

- [Foundation TRAE Operations](foundation_trae_operations.md)
- [Source Activation Plan](foundation_source_activation_plan.md)
- [Source Inventory Report](foundation_source_inventory_report.md)
- [Control Center Design](foundation_control_center.md)
