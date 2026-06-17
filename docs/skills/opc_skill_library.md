# OPC Skill Library

## What is this?

The OPC Skill Library is a collection of optional decision-aid skills stored in
`opc-foundation`. Each skill is a structured method template — not a pipeline stage,
not an automatic process.

> Skills are optional decision aids, not mandatory pipeline stages.
> Skill 是可选决策辅助，不是强制业务流程。

## Skills in this library

| Skill | Stage | Purpose |
|---|---|---|
| `theme-validation` | Post theme grouping | Is this demand theme worth pursuing? |
| `concierge-mvp` | Post validation | What is the code-free manual service version? |
| `processize` | Post concierge delivery | Break delivery into SOP + identify automation |
| `first-customers` | Post validation | Who are the first 3-10 users? How to reach them? |
| `pricing-smoke-test` | Pre pilot | What is the minimal paid validation? |
| `minimalist-review` | Decision checkpoint | Final 8-question minimalist checklist |

## Boundary with Foundation runtime

The Foundation runtime (`src/opc_foundation/`) handles:
- Data acquisition (connectors, search providers)
- Signal normalization and storage
- Deduplication, run context, artifacts

The Skill Library (`.agents/skills/`) handles:
- Decision frameworks (when invoked by user)
- Method templates for validation
- Input/output schemas for judgment tasks

These two layers do NOT mix automatically.

## Boundary with Demand Radar

Demand Radar owns:
- Running acquisition pipelines
- Applying its own scoring (TruthScore, FitScore)
- Deciding which themes to escalate
- Deciding when to invoke skills

Demand Radar does NOT:
- Automatically run skills after every pipeline run
- Let Foundation skills modify Radar data

## Why default_enabled: false?

Skills are not always needed. A skill invoked without relevant inputs is noise.
The user or the downstream project must decide:
- Which theme is worth validating?
- Is there enough evidence to run theme-validation?
- Has the concierge MVP been tried before processize?

## Why requires_user_trigger: true?

Automatic skill execution is dangerous because:
- It consumes LLM tokens on every run regardless of need
- It generates output the user hasn't asked for
- It can create confusion about which step is "official"

## How to add a new skill

1. Create a new subdirectory under `.agents/skills/opc-product-validation/`
2. Add `SKILL.md` with all required sections (see template below)
3. Add `input_schema.example.json` and `output_schema.example.json`
4. Add an entry to `skill_manifest.yaml` with `default_enabled: false` and `requires_user_trigger: true`
5. Run `opc-foundation skills validate` to check everything

## Required sections in every SKILL.md

```
# Skill Name
## Purpose
## When to Use
## When Not to Use
## Required Inputs
## Optional Inputs
## Output Format
## Decision Rules
## Evidence Rules (if applicable)
## Red Flags
## Example Prompt
## Example Output Skeleton
```

Every SKILL.md must also contain this notice:

```
This skill is optional and must be explicitly invoked by a downstream project or user.
Do not run this skill automatically as part of any pipeline.
```

## How to prevent pipeline pollution

1. Never import from `.agents/skills/` in your pipeline runner
2. Never add skill invocation to a scheduled pipeline step
3. Always require explicit user action to invoke a skill
4. Store skill outputs in the project — not in Foundation