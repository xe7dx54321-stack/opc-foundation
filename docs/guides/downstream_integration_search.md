# Downstream Integration: Search Provider

## Principle

> Foundation provides infrastructure. Project owns judgment.

Foundation handles: how to search, how to normalize results, which provider to use.
Downstream projects handle: what is a good signal, domain relevance, pain extraction, scoring.

## Quick Start

```python
from opc_foundation.search import SearchProviderRegistry, SearchQuery
from opc_foundation.providers.env_loader import load_env_file

load_env_file(".env")

# Build registry from env
registry = SearchProviderRegistry.from_env()

# Get preferred provider (tavily > brave > ...)
client = registry.get_preferred_provider()
if client is None:
    raise RuntimeError("No search provider configured")

# Search
result = client.search(SearchQuery(
    query="investment research workflow spreadsheet pain",
    max_results=10,
))

print(f"Provider: {result.provider}")
for r in result.results:
    print(f"  [{r.rank}] {r.title}")
    print(f"       {r.url}")
```

## With normalization

```python
from opc_foundation.search import normalize_results

normalized = normalize_results(result.results, filter_example_domains=True, deduplicate_urls=True)
```

## Downstream boundary

After getting `SearchResult` objects, your project applies its own logic:

```python
# This code lives in YOUR project, NOT in Foundation
from my_project.domain import is_domain_relevant, extract_pain_signals

relevant = [r for r in normalized if is_domain_relevant(r.url, r.snippet)]
signals = extract_pain_signals(relevant)
```

Foundation does NOT:
- Judge business relevance
- Extract pain points
- Apply TruthScore / FitScore
- Make investment decisions

## SourceRegistryV2 integration

```python
from opc_foundation.sources_v2 import SourceRegistryV2, SourceRuntime

registry = SourceRegistryV2.from_yaml("config/sources_v2.yaml")
runtime = SourceRuntime(search_registry=SearchProviderRegistry.from_env())

for source in registry.get_enabled():
    if source.fetch_method == "search_provider":
        result = runtime.run_source(source)
        # hand result.items_count etc. to your own pipeline
```

## Version pinning

Pin Foundation at a specific version before deploying:
```
opc-foundation @ git+https://github.com/xe7dx54321-stack/opc-foundation@v0.1.2
```