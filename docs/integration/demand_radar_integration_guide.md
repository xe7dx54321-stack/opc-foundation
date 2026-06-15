# Demand Radar Integration Guide

This guide shows how Demand Radar uses `opc-foundation` for its acquisition pipeline.

## Installation

```bash
pip install -e path/to/opc-foundation
# or after publishing:
pip install opc-foundation
```

## Import pattern

```python
from opc_foundation.sources import SourceRegistry, SourceQuery
from opc_foundation.sources.connectors import HackerNewsConnector, GitHubIssuesConnector
from opc_foundation.storage import JsonlStore
from opc_foundation.signals import RawSignal, dedupe_raw_signals
from opc_foundation.run import RunContext, RunLog, new_run_id
from opc_foundation.reports import MarkdownBuilder
```

## Typical acquisition pipeline

```python
# 1. Load source registry
registry = SourceRegistry.from_yaml("config/source_registry.yaml")

# 2. Create run context
ctx = RunContext(
    project_id="demand_radar",
    pipeline_name="acquisition_v1",
)
run_log = RunLog(ctx.run_id)

# 3. Fetch from each source
all_signals: list[RawSignal] = []
for source in registry.get_enabled_sources():
    connector = get_connector(source.connector)  # your mapping
    for query_str in source.default_queries:
        query = SourceQuery(
            query_id=new_id(),
            source_id=source.source_id,
            query=query_str,
            max_items=50,
        )
        result = connector.fetch(query, source, ctx)
        all_signals.extend(result.raw_signals)

# 4. Dedupe
deduped = dedupe_raw_signals(all_signals, by="both")

# 5. Save raw signals
JsonlStore.write_records("outputs/raw_signals.jsonl", deduped.unique_signals)

# 6. --- Project-specific: Demand Radar judgment layer ---
# Import your OWN modules here:
from demand_radar.scoring import TruthScorer
from demand_radar.models import DemandCandidate
# ... apply domain scoring
```

## What Demand Radar keeps (do NOT move to foundation)

| Module | Stays in Demand Radar |
|---|---|
| `TruthScore` | Yes |
| `FitScore` | Yes |
| `EvidenceRubric` | Yes |
| `PainPoint` | Yes |
| `DemandCandidate` | Yes |
| `OpportunityScore` | Yes |
| Domain-specific prompts | Yes |
| Acceptance thresholds | Yes |

## Replace local modules

| Old Demand Radar module | Replace with |
|---|---|
| `src/demand_radar/storage/jsonl_writer.py` | `opc_foundation.storage.JsonlStore` |
| `src/demand_radar/acquisition/hn_fetcher.py` | `opc_foundation.sources.connectors.HackerNewsConnector` |
| `src/demand_radar/acquisition/github_fetcher.py` | `opc_foundation.sources.connectors.GitHubIssuesConnector` |
| `src/demand_radar/acquisition/rss_fetcher.py` | `opc_foundation.sources.connectors.RssConnector` |
| Custom URL extractor | `opc_foundation.web.TrafilaturaExtractor` |
| LLM cache | `opc_foundation.llm.LLMCache` |
| Run logging | `opc_foundation.run.RunLog` |

## Next steps

1. Add `opc-foundation` to Demand Radar `pyproject.toml` dependencies.
2. Replace acquisition modules with foundation connectors.
3. Keep all scoring / rubric / judgment modules in Demand Radar.
4. Use `RawSignal.metadata` to carry any HN/GitHub-specific fields you need downstream.
