# Downstream Usage Guide: OPC Skill Library

## Overview

Downstream projects (Demand Radar, Content Agent, etc.) use Foundation skills
as optional, explicitly-invoked decision aids.

Foundation does not call skills automatically.
Foundation does not store skill outputs.
The downstream project owns the invocation, the outputs, and the decision.

## Step-by-step usage

### 1. Discover available skills

```python
from opc_foundation.skills import load_skill_manifest, list_skills

manifest = load_skill_manifest(".agents/skills/opc-product-validation/skill_manifest.yaml")
for skill in manifest.skills:
    print(skill.skill_id, "->", skill.stage)
```

Or via CLI:
```bash
opc-foundation skills list
```

### 2. Choose the relevant skill

Match your current pipeline stage to a skill:

| Your stage | Recommended skill |
|---|---|
| Just grouped demand themes | `theme-validation` |
| Theme passed validation | `concierge-mvp` |
| Concierge delivered once | `processize` |
| Concierge ready, need users | `first-customers` |
| First users found | `pricing-smoke-test` |
| Before any build decision | `minimalist-review` |

### 3. Load the skill document

```python
from pathlib import Path

skill_path = Path(".agents/skills/opc-product-validation/theme-validation/SKILL.md")
skill_content = skill_path.read_text(encoding="utf-8")
```

### 4. Prepare your business artifacts as skill input

```python
# Your Demand Radar data -> skill input format
skill_input = {
    "theme_id": theme.theme_id,
    "theme_title_zh": theme.title_zh,
    "core_pain_zh": theme.core_pain_zh,
    "persona_group": theme.persona_group,
    "evidence_summary": {
        "evidence_count": len(theme.evidence),
        "first_hand_evidence_count": theme.first_hand_count,
        "marketing_or_vendor_evidence_count": theme.vendor_count,
    },
    "representative_quotes": theme.representative_quotes[:3],
}
```

### 5. Invoke via LLM (your own LLM client)

```python
from opc_foundation.llm import LLMRequest, LLMMessage, OpenAICompatibleClient, StructuredRunner
import json

client = OpenAICompatibleClient()
runner = StructuredRunner(client)

system_prompt = skill_content  # The SKILL.md content
user_prompt = f"Input:\n{json.dumps(skill_input, ensure_ascii=False, indent=2)}"

request = LLMRequest(
    model="gpt-4o",
    messages=[
        LLMMessage(role="system", content=system_prompt),
        LLMMessage(role="user", content=user_prompt),
    ]
)
result = runner.run_safe(request, YourOutputModel)
```

### 6. Save outputs in your project

```python
# Save in YOUR project's output directory, not in Foundation
import json
output_path = Path("outputs/skill_results") / f"{theme.theme_id}_theme_validation.json"
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(json.dumps(result.parsed.model_dump(), ensure_ascii=False, indent=2))
```

## What Foundation does NOT do

- Does NOT auto-invoke skills on any schedule
- Does NOT store skill outputs anywhere
- Does NOT decide which themes need skills
- Does NOT modify your pipeline data

## Validating skill files exist

```bash
opc-foundation skills validate
```