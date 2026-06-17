# Source Runtime Guide

## Overview

`SourceRuntime` dispatches source fetching based on `SourceDefinitionV2.fetch_method`:

| `fetch_method` | Dispatches to |
|---|---|
| `search_provider` | `SearchProviderRegistry` |
| `url_extraction` | Web extraction adapter |
| `manual` | Web extraction adapter |
| `rss` | Legacy `SourceRegistry` + `RssConnector` |

## Usage

```python
from opc_foundation.sources_v2 import SourceRegistryV2, SourceRuntime
from opc_foundation.search import SearchProviderRegistry
from opc_foundation.web import TrafilaturaExtractor

# Load registry
registry = SourceRegistryV2.from_yaml("config/source_registry_v2.yaml")

# Create runtime
search_reg = SearchProviderRegistry.from_env()
runtime = SourceRuntime(
    search_registry=search_reg,
    web_extractor=TrafilaturaExtractor(),
)

# Run a source
source = registry.get_by_id("tavily_search_discovery")
result = runtime.run_source(source)
print(f"status={result.status}  items={result.items_count}")
```

## SourceRunResult

```python
class SourceRunResult(BaseModel):
    run_id: str
    source_id: str
    source_type: str
    source_category: str
    status: str          # success | partial | blocked | failed
    items_count: int
    errors: list[str]
    warnings: list[str]
    started_at: str
    finished_at: str | None
    artifacts: dict[str, str]
    metrics: dict[str, Any]
```

## Diagnostics

```python
from opc_foundation.sources_v2 import build_diagnostics_report

report = build_diagnostics_report(
    source_id="tavily_search_discovery",
    total_items=42,
    unique_urls=38,
    text_extracted=35,
    run_status="success",
)
```

Downstream projects may backfill yield metrics:
```python
report.downstream_metric_name = "pain_extraction_yield"
report.downstream_yield_rate = 0.43
```
Foundation does not interpret these values.