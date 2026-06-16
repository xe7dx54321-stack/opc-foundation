# Demand Radar Integration Guide

This guide shows how Demand Radar uses `opc-foundation` for its acquisition pipeline.

## Version pinning

**Demand Radar should pin `opc-foundation` at a specific version.**

```
# In Demand Radar pyproject.toml or requirements.txt:
opc-foundation @ git+https://github.com/xe7dx54321-stack/opc-foundation@v0.1.1
```

Before upgrading to a new Foundation version (e.g. v0.1.2), run the Demand Radar
integration test suite first to ensure no regressions.

## Installation

```bash
pip install -e path/to/opc-foundation
```

## Import pattern

```python
from opc_foundation import __version__
from opc_foundation.sources import SourceRegistry, SourceQuery
from opc_foundation.sources.connectors import HackerNewsConnector, GitHubIssuesConnector
from opc_foundation.storage import JsonlStore
from opc_foundation.signals import RawSignal, dedupe_raw_signals, SeenStore
from opc_foundation.run import RunContext, RunLog, new_run_id, ArtifactManifestBuilder
from opc_foundation.reports import MarkdownBuilder
```

## Typical acquisition pipeline

```python
# 1. Load source registry
registry = SourceRegistry.from_yaml("config/source_registry.yaml")

# 2. Create run context
ctx = RunContext(
    project_id="demand_radar",
    pipeline_name="acquisition_v2",
)
run_log = RunLog(ctx.run_id)
manifest = ArtifactManifestBuilder(ctx.run_id, "acquisition_v2", "demand_radar")

# 3. Load seen store for incremental dedupe
seen_store = SeenStore(".seen/signals.jsonl")

# 4. Fetch from each source
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

# 5. Dedupe + incremental filter
deduped = dedupe_raw_signals(all_signals, by="both")
new_signals, already_seen = seen_store.filter_new(deduped.unique_signals, run_id=ctx.run_id)

# 6. Save raw signals
JsonlStore.write_records("outputs/raw_signals.jsonl", new_signals)
manifest.add_artifact("raw_signals", "outputs/raw_signals.jsonl",
                      artifact_type="jsonl", count=len(new_signals))

# 7. --- Demand Radar judgment layer (stays in Demand Radar) ---
from demand_radar.scoring import TruthScorer
from demand_radar.models import DemandCandidate
# ... apply domain scoring

# 8. Write manifest
manifest.write("outputs/manifest.json")
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
| LLM cache | `opc_foundation.llm.LLMCache` (use `prompt_version` + `run_scope`) |
| Run logging | `opc_foundation.run.RunLog` |
| Incremental dedupe | `opc_foundation.signals.SeenStore` |
| Artifact tracking | `opc_foundation.run.ArtifactManifestBuilder` |

## LLM cache migration note

The new `LLMCache` key includes `prompt_version`, `run_scope`, and `config_version`.
This prevents the stale-cache problem where new data reuses old judgments.

Always set:
```python
cache.set(
    provider="openai",
    model="gpt-4o",
    prompt_version="demand_v3",      # bump when prompt changes
    input_hash=cache.make_input_hash(text),
    value=result,
    config_version="cfg_v1",         # bump when config changes
    run_scope=ctx.run_id,            # isolates per-run cache
)
```

## Next steps

1. Add `opc-foundation` to Demand Radar `pyproject.toml`.
2. Replace acquisition modules one by one, test each replacement.
3. Keep all scoring / rubric / judgment modules in Demand Radar.
4. Use `RawSignal.metadata` for source-specific fields (HN points, GH labels, etc.).
5. After stable MVP-A, consider Foundation Phase 1.3 or Phase 2 (new connectors).