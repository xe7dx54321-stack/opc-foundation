# Source Validation Report: merck_ir

## Source Info
- **source_id**: merck_ir
- **source_name**: Merck Investor Relations
- **source_group**: bank_conference_transcripts

## Pre-Repair Status
- **content_status**: content_watch / technical drift
- **reason**: Original inventory URL `https://investors.merck.com` was unstable; some navigation noise was leaking into candidates

## Repair Actions
1. **Inventory URL fix**: Updated source inventory URL from `https://investors.merck.com` to `https://www.merck.com/investor-relations/`
   - Rationale: The old subdomain has been migrated to the corporate-site investor-relations path; the new URL is the canonical stable endpoint
2. **Noise filtering**: Added robust noise filtering for all Merck extraction types (`merck_news`, `merck_events`, `merck_presentation`)
   - Blocked exact-match navigation strings (MERCK_NOISE): 13 patterns including "News releases", "Events & presentations", "Investors overview", etc.
   - Blocked substring patterns: "Icons /", "See full agenda", "MicrophoneWebcast"
   - Minimum title length raised from 5 to 10 characters for events/presentations
   - Unified the three separate extraction blocks into one consolidated branch

## Network Validation Results

| Field | Value |
|-------|-------|
| input_url | https://investors.merck.com |
| final_url | https://www.merck.com/investor-relations/ |
| http_status | 200 |
| content_score | 90 |
| content_status | content_ready |
| valid_candidate_count | 5 |
| relevant_candidate_count | 3 |

## Real Candidate Samples

| # | Title | URL | Date |
|---|-------|-----|------|
| 1 | Merck to Hold Second-Quarter 2026 Sales and Earnings Confere | https://www.merck.com/news/merck-to-hold-second-quarter-2026 | - |
| 2 | Merck Announces New Agreement with ADAP Crisis Task Force to | https://www.merck.com/news/merck-announces-new-agreement-wit | - |
| 3 | FDA Approves KEYTRUDA® (pembrolizumab) and KEYTRUDA QLEX™ (p | https://www.merck.com/news/fda-approves-keytruda-pembrolizum | - |
| 4 | 47th Annual Goldman Sachs Global Healthcare Conference | https://www.merck.com/events/47th-annual-goldman-sachs-globa | - |
| 5 | Jefferies Global Healthcare Conference | https://www.merck.com/events/jefferies-global-healthcare-con | - |

## Assessment
- The URL update and noise filtering successfully restored Merck IR to `content_ready`.
- 5 valid candidates extracted, 3 of which are classified as relevant.
- Candidates include genuine news releases (`/news/`) and investor conference entries (`/events/`), matching the expected `research.conference_transcript` capability.
- Score 90 is well above the `content_ready` threshold.
