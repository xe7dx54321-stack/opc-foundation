# OPC Foundation M3C-6F Proxy Retry Batch Report

- **Generated at:** 2026-07-04T16:56:17.399745+00:00
- **Branch:** feature/m3c-6f-proxy-retry-batch
- **Base commit:** 3162faa
- **Trial v2 source count:** 9
- **Proxy env configured:** False

## Scope

- **Candidate count:** 1
- **Candidate sources:** merck_ir

## Summary Table

| source_id | direct_status | proxy_status | http_status | error_type | valid_items | dated_items | decision |
|---|---|---|---|---|---:|---:|---|
| merck_ir | success | not_tested | 200 | none | 20 | 0 | manual_review_only |

## Sample Items

### merck_ir

| title | url | date_text |
|---|---|---|
| Who we are | https://www.merck.com/company-overview/ |  |
| What we do | https://www.merck.com/what-we-do/ |  |
| Sustainability | https://www.merck.com/company-overview/sustainability/ |  |

## Decisions

| source_id | recommended_execution_mode | trial_v2_allowlist_allowed_now | low_frequency_allowed_now | on_demand_allowed_now | next_action |
|---|---|---|---|---|---|
| merck_ir | manual_review_only | False | False | False | manual_content_extraction_review |

## Boundary Compliance

- Does NOT modify trial_v2 allowlist: yes
- Does NOT modify TRAE scheduling: yes
- Does NOT configure production: yes
- Does NOT commit data/local/secrets: yes
- Does NOT commit proxy URL: yes
- Does NOT commit cookie/token: yes
- Does NOT commit raw HTML: yes
- Does NOT commit screenshot: yes
- Does NOT introduce Playwright/Selenium: yes
- Does NOT restore deleted Dashboard pages: yes
- Does NOT create tag: yes
