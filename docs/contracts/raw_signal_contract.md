# RawSignal Contract

## Overview

`RawSignal` is the canonical cross-project signal schema.

## Required Fields

| Field | Type | Description |
|---|---|---|
| signal_id | str | Unique ID (use `new_id()`) |
| source_id | str | Registry source ID |
| source_type | str | e.g. `community_discussion`, `github_issue`, `rss` |
| raw_text | str | Non-empty content body |
| fetched_at | str | UTC ISO-8601 timestamp |

## Validation Rules

- At least one of `source_url` or `source_note` must be non-null.
- `raw_text` must not be empty.
- `metadata` dict is open for project-specific extensions.

## Extension Pattern

Projects should NOT subclass `RawSignal`. Instead, use the `metadata` dict
to carry domain-specific fields, then map to project-specific models downstream.
