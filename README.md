# OPC Foundation

> **Standardize the pipeline, specialize the judgment.**
> 标准化管道，项目化判断。

`opc-foundation` is a reusable infrastructure library for OPC AI product projects.

**Foundation provides infrastructure. Project owns judgment.**
公共库提供基础设施，具体项目保留判断力。

Current version: **v0.1.3**

---

## What it is

A single installable Python package providing cross-project reusable capabilities:

- **Config** – YAML/JSON loaders, typed config schema
- **Storage** – JSONL and CSV read/write helpers
- **Run** – RunContext, RunLog, Checkpoints, ArtifactManifest
- **Sources** – Source registry, SourceConnector protocol, FetchResult/RawSignal contracts
- **Connectors** – Hacker News, GitHub Issues, RSS, Manual URL batch (all with timeout/retry/backoff)
- **Web** – Trafilatura-based URL text extraction
- **Signals** – RawSignal schema, deduplication, SeenStore (incremental dedupe), QualityGate
- **LLM** – OpenAI-compatible and Anthropic clients, LLMCache (keyed by provider/model/prompt_version/input_hash/config_version/run_scope), StructuredRunner (with JSON repair and retry)
- **Reports** – Markdown builder, table builder

## What it does NOT do

- No business-specific scoring (TruthScore, FitScore, OpportunityScore)
- No domain-specific prompts or rubrics
- No project-specific data models (DemandCandidate, PainPoint, etc.)
- No Reddit / G2 / Capterra / social media connectors
- No scheduling system, no vector database, no UI

---

## Versioning

This library uses [Semantic Versioning](https://semver.org/).

- **v0.1.0** – Initial Phase 0-1 release (all core modules)
- **v0.1.1** – Phase 1.1-1.2: versioning, public API stabilization, connector reliability hardening, SeenStore, ArtifactManifest, StructuredRunner hardening
- **v0.1.2** – Phase 1.3: providers module, search module, sources_v2, web extraction interface
- **v0.1.3** – Phase 1.4: OPC Skill Library, network safety (SSRF protection, URL validation, unified timeout), StructuredRunner retry fix

Projects should **pin** `opc-foundation` at a specific version.
Before upgrading, run your project-level integration tests.

---

## Installation

```bash
git clone https://github.com/xe7dx54321-stack/opc-foundation
cd opc-foundation
pip install -e ".[dev]"
```

Requires Python 3.11+.

---

## Public API

```python
from opc_foundation import __version__

from opc_foundation.config import load_config
from opc_foundation.storage import JsonlStore, CsvStore
from opc_foundation.run import RunContext, RunLog, create_run_id, ArtifactManifestBuilder
from opc_foundation.sources import (
    SourceDefinition, SourceQuery, FetchResult, SourceRegistry,
)
from opc_foundation.sources.connectors import (
    ManualURLConnector, HackerNewsConnector,
    GitHubIssuesConnector, RSSConnector,
)
from opc_foundation.signals import (
    RawSignal, dedupe_raw_signals, DedupeResult, SeenStore,
)
from opc_foundation.web import TrafilaturaExtractor, ExtractedPage
from opc_foundation.llm import (
    LLMRequest, LLMResponse, LLMCache, PromptMetadata, StructuredRunner,
)
from opc_foundation.reports import MarkdownBuilder, ReportSection
```

---

## Quickstart

### Load source registry

```python
from opc_foundation.sources import SourceRegistry

registry = SourceRegistry.from_yaml("config/sources.yaml")
enabled = registry.get_enabled_sources()
print(f"{len(enabled)} enabled sources")
```

### Fetch HN signals

```python
from opc_foundation.sources.connectors import HackerNewsConnector
from opc_foundation.sources import SourceQuery
from opc_foundation.run import RunContext, new_id

ctx = RunContext(project_id="my_project", pipeline_name="acquisition")
source = registry.get_source("hacker_news")
connector = HackerNewsConnector(timeout=15, max_retries=2)
query = SourceQuery(query_id=new_id(), source_id="hacker_news", query="AI tools", max_items=20)
result = connector.fetch(query, source, ctx)
print(f"{len(result.raw_signals)} signals, {len(result.warnings)} warnings")
```

### Write JSONL

```python
from opc_foundation.storage import JsonlStore

JsonlStore.write_records("outputs/signals.jsonl", result.raw_signals)
signals = JsonlStore.load_records("outputs/signals.jsonl", model=RawSignal)
```

### Dedupe RawSignals

```python
from opc_foundation.signals import dedupe_raw_signals

deduped = dedupe_raw_signals(signals, by="both")
print(f"{deduped.duplicate_count} duplicates removed")
```

### Incremental dedupe with SeenStore

```python
from opc_foundation.signals import SeenStore

store = SeenStore(".seen/signals.jsonl")
new_signals, already_seen = store.filter_new(result.raw_signals, run_id=ctx.run_id)
print(f"{len(new_signals)} new, {len(already_seen)} already seen")
```

### Track artifacts with ArtifactManifest

```python
from opc_foundation.run import ArtifactManifestBuilder

builder = ArtifactManifestBuilder(run_id=ctx.run_id, pipeline_name="acquisition")
builder.add_artifact("raw_signals", "outputs/signals.jsonl", artifact_type="jsonl", count=len(new_signals))
builder.add_artifact("report", "outputs/report.md", artifact_type="markdown")
builder.write("outputs/manifest.json")
```

### Build markdown report

```python
from opc_foundation.reports import MarkdownBuilder

md = MarkdownBuilder()
md.heading(1, "Acquisition Report")
md.bullet_list([f"{s.title or s.source_url}" for s in new_signals[:5]])
md.write_report("outputs/report.md")
```

### Use LLM with cache

```python
from opc_foundation.llm import LLMCache, LLMRequest, LLMMessage, OpenAICompatibleClient, StructuredRunner

cache = LLMCache(".llm_cache")
client = OpenAICompatibleClient()
runner = StructuredRunner(client)

request = LLMRequest(
    model="gpt-4o",
    messages=[LLMMessage(role="user", content="Summarize: " + signals[0].raw_text)],
)
result = runner.run_safe(request, MyOutputModel)
if result.success:
    print(result.parsed)
```

---

## Connector reliability

All connectors support:
- `timeout` (default 15s)
- `max_retries` (default 2, with exponential backoff)
- 403/429 captured in `FetchResult.warnings` as `rate_limit` / `access_denied`
- Network failures captured in `FetchResult.errors` — never raise

See `docs/contracts/connector_reliability_policy.md`.

---

## Defining a source registry

```yaml
sources:
  - source_id: hacker_news
    source_name: Hacker News
    source_type: community_discussion
    connector: hacker_news
    enabled: true
    trust_weight: 0.85
    default_queries:
      - AI startup tracking
```

---

## Using the CLI

```bash
opc-foundation version
opc-foundation validate-source-registry --path examples/source_registry.example.yaml
opc-foundation fetch-source hacker_news --query "AI tools" --max-items 10
opc-foundation extract-url https://example.com/article
opc-foundation dedupe-signals inputs.jsonl outputs.jsonl --by url
opc-foundation seen-store-stats .seen/signals.jsonl
```

---

## Integrating into a project

```python
from opc_foundation.signals import RawSignal

def to_my_evidence(signal: RawSignal) -> MyEvidenceItem:
    return MyEvidenceItem(
        source=signal.source_id,
        text=signal.raw_text,
        url=signal.source_url,
        # ... add your project fields
    )
```

See `docs/integration/demand_radar_integration_guide.md`.

---

## How Demand Radar uses it

1. Import acquisition connectors from `opc_foundation.sources.connectors`
2. Use `JsonlStore` for raw signal persistence
3. Use `SeenStore` for incremental dedupe across runs
4. Use `LLMCache` with `prompt_version` + `run_scope` to prevent stale-cache cross-contamination
5. Use `ArtifactManifestBuilder` to record every output file
6. **Keep** all TruthScore / FitScore / EvidenceRubric / DemandCandidate in Demand Radar

---

## Core contracts

- `RawSignal` – `docs/contracts/raw_signal_contract.md`
- `SourceConnector` – `docs/contracts/source_connector_contract.md`
- `ProjectAdapter` – `docs/contracts/project_adapter_contract.md`
- `Connector Reliability` – `docs/contracts/connector_reliability_policy.md`

---

## License

Internal OPC use. Not published to PyPI.