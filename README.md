# OPC Foundation

> **Standardize the pipeline, specialize the judgment.**
> 标准化管道，项目化判断。

`opc-foundation` is a reusable infrastructure library for OPC AI product projects.

**Foundation provides infrastructure. Project owns judgment.**
公共库提供基础设施，具体项目保留判断力。

---

## What it is

A single installable Python package that provides cross-project reusable capabilities:

- **Config** – YAML/JSON loaders, typed config schema
- **Storage** – JSONL and CSV read/write helpers
- **Run** – RunContext, RunLog, Checkpoints, ID generator, time utils
- **Sources** – Source registry, SourceConnector protocol, FetchResult/RawSignal contracts
- **Connectors** – Hacker News, GitHub Issues, RSS, Manual URL batch
- **Web** – Trafilatura-based URL text extraction
- **Signals** – RawSignal schema, deduplication, quality gate
- **LLM** – OpenAI-compatible and Anthropic client wrappers, cache, prompt metadata
- **Reports** – Markdown builder, table builder

## What it does NOT do

- No business-specific scoring (TruthScore, FitScore, OpportunityScore)
- No domain-specific prompts or rubrics
- No project-specific data models (DemandCandidate, PainPoint, etc.)
- No Reddit / G2 / Capterra / social media connectors
- No scheduling system
- No vector database / embedding / MinHash
- No UI

---

## Products using opc-foundation

```
Demand Radar       需求雷达
Content Agent      内容生产系统
Stock Research Agent  投研系统
WorldCup Strategy Agent  策略系统
```

---

## Installation

```bash
# development install
git clone https://github.com/xe7dx54321-stack/opc-foundation
cd opc-foundation
pip install -e ".[dev]"
```

Requires Python 3.11+.

---

## Defining a source registry

Create a YAML file (see `examples/source_registry.example.yaml`):

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

  - source_id: rss_ai
    source_name: AI Research RSS
    source_type: rss
    connector: rss
    enabled: true
    base_url: https://your-feed-url.com/rss
    trust_weight: 0.60
```

---

## Running a connector

```python
from opc_foundation.sources import SourceRegistry, SourceQuery
from opc_foundation.sources.connectors import HackerNewsConnector
from opc_foundation.run import RunContext, new_id

registry = SourceRegistry.from_yaml("config/sources.yaml")
source = registry.get_source("hacker_news")

connector = HackerNewsConnector()
ctx = RunContext(project_id="my_project", pipeline_name="acquisition")

query = SourceQuery(query_id=new_id(), source_id="hacker_news", query="AI tools", max_items=20)
result = connector.fetch(query, source, ctx)

print(f"{len(result.raw_signals)} signals fetched")
```

---

## Using the CLI

```bash
# Validate source registry
opc-foundation validate-source-registry --path examples/source_registry.example.yaml

# Fetch from a single source
opc-foundation fetch-source hacker_news --query "AI tools" --max-items 10

# Extract text from a URL
opc-foundation extract-url https://example.com/article

# Deduplicate a JSONL file
opc-foundation dedupe-signals inputs.jsonl outputs.jsonl --by url
```

---

## Integrating into a project

```python
from opc_foundation.signals import RawSignal

# Map to your project-specific model:
def to_my_evidence(signal: RawSignal) -> MyEvidenceItem:
    return MyEvidenceItem(
        source=signal.source_id,
        text=signal.raw_text,
        url=signal.source_url,
        # ... add your project fields
    )
```

See `docs/integration/demand_radar_integration_guide.md` for the full Demand Radar walkthrough.

---

## How Demand Radar uses it

1. Import acquisition connectors from `opc_foundation.sources.connectors`
2. Use `JsonlStore` for raw signal persistence
3. Use `LLMCache` with `prompt_version` + `run_scope` to avoid stale cache
4. Use `RunLog` for step-level logging
5. **Keep** all TruthScore / FitScore / EvidenceRubric / DemandCandidate in Demand Radar

---

## Core contracts

- `RawSignal` – `docs/contracts/raw_signal_contract.md`
- `SourceConnector` – `docs/contracts/source_connector_contract.md`
- `ProjectAdapter` – `docs/contracts/project_adapter_contract.md`

---

## License

Internal OPC use. Not published to PyPI.
