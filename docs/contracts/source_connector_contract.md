# SourceConnector Contract

## Overview

Every connector in `opc-foundation` must implement the `SourceConnector` protocol:

```python
class SourceConnector(Protocol):
    connector_id: str

    def fetch(
        self,
        query: SourceQuery,
        source: SourceDefinition,
        context: RunContext,
    ) -> FetchResult:
        ...
```

## Rules

1. `fetch()` must never raise an unhandled exception.
2. All errors go into `FetchResult.errors` (list of strings).
3. `max_items` in `SourceQuery` must be respected.
4. Each returned `RawSignal` must have at least one of `source_url` or `source_note`.
5. `raw_text` must not be empty; use title/URL as fallback.
6. `fetched_at` must be set to UTC ISO-8601.
7. Connectors must not store project-specific business logic.
