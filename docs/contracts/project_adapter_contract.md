# Project Adapter Contract

## Principle

> Foundation provides infrastructure. Project owns judgment.
> 公共库提供基础设施，具体项目保留判断力。

## What opc-foundation provides

- `RawSignal` – normalized input signal
- `FetchResult` – connector output
- `SourceDefinition` / `SourceQuery` – source configuration
- `RunContext` / `RunLog` – execution context
- Storage, dedupe, LLM cache, report builder

## What each project must provide

- Domain-specific data models (e.g. `DemandCandidate`, `PainPoint`)
- Scoring rubrics and thresholds
- LLM prompts with business judgment
- Acceptance / rejection criteria
- Output formatting for the end user

## Adapter pattern

```python
# In your project:
from opc_foundation.signals import RawSignal

def to_evidence_item(signal: RawSignal) -> MyEvidenceItem:
    return MyEvidenceItem(
        source=signal.source_id,
        text=signal.raw_text,
        url=signal.source_url,
        # ... project-specific fields
    )
```
