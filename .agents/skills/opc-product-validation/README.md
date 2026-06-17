# OPC Product Validation Skills

**This is an optional skill library. All skills are disabled by default.**
**No skill runs automatically. Each must be explicitly invoked.**

## What this is

A collection of decision-aid skills for validating OPC product ideas after
demand signal collection. Based on the Minimalist Entrepreneur methodology,
adapted for evidence-driven OPC product discovery.

## Core principle

> Skills are optional decision aids, not mandatory pipeline stages.
> 本 skill 库中的所有 skill 是可选决策辅助，不是强制业务流程。

## Skills

| Skill | Stage | Purpose |
|---|---|---|
| `theme-validation` | Post theme grouping | Is this demand theme worth pursuing? |
| `concierge-mvp` | Post validation | What is the manual, code-free version? |
| `processize` | Post concierge plan | Break delivery into SOP + automation candidates |
| `first-customers` | Post validation | Who are the first 3-10 users? How to reach them? |
| `pricing-smoke-test` | Pre pilot | What is the minimal paid validation? |
| `minimalist-review` | Decision checkpoint | Final 8-question minimalist checklist |

## How to use

1. Load `skill_manifest.yaml` to discover available skills
2. Choose the skill relevant to your current stage
3. Prepare your business artifacts as skill inputs
4. Invoke the skill via Agent or LLM
5. Save outputs in your own project — Foundation does not store results

## What not to do

- Do NOT run all skills automatically after every pipeline run
- Do NOT let Foundation modify your business data
- Do NOT build a product before concierge-mvp is validated