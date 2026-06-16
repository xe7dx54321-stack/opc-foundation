# Connector Reliability Policy

All connectors in `opc-foundation` must satisfy the following invariants.

## Mandatory Rules

1. **No uncaught exceptions** – `fetch()` must never raise. All errors go into `FetchResult.errors`.
2. **Timeout produces errors** – Network timeout must produce a `FetchResult.errors` entry, not an exception.
3. **HTTP 403 / 429 produces warnings** – Rate-limit and access-denied responses must be captured in `FetchResult.warnings` with error_type `rate_limit` or `access_denied`.
4. **Empty result is not failure** – Zero signals with empty errors is a valid outcome.
5. **`max_items` must be respected** – `len(result.raw_signals) <= query.max_items` always.
6. **`source_url` or `source_note` required** – Every `RawSignal` must have at least one set.
7. **`raw_text` must not be empty** – Connectors must use title/URL/notes as fallback.
8. **`fetched_at` must be set** – UTC ISO-8601 string, always populated.
9. **Source-specific IDs in metadata** – Preserve `objectID` (HN), `github_issue_id` (GH), `feed_url` (RSS), `csv_row_index` (Manual URL).
10. **Errors must be actionable** – Error messages should name the source URL, HTTP code, or relevant identifier.

## Retry Policy

- Default `timeout`: 15 seconds per request.
- Default `max_retries`: 2 (with exponential backoff base 1.5s).
- 403 Access Denied: no retry.
- 429 Rate Limit: retry up to `max_retries`.
- Network error / timeout: retry up to `max_retries`.

## Testing

All connectors must pass `tests/test_connector_contracts.py` which verifies the above invariants
using mocked HTTP responses and fixture files in `tests/fixtures/`.