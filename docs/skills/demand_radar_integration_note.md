# Demand Radar: OPC Skill Library Integration Note

## Recommended invocation flow

```
D5 demand themes produced
        |
        v
User selects a specific theme
        |
        v
User explicitly invokes: theme-validation
        |
        v (if verdict = pursue_validation)
User explicitly invokes: concierge-mvp
        |
        v (after at least 1 manual delivery)
User explicitly invokes: processize
        |
        v (when ready to find users)
User explicitly invokes: first-customers
        |
        v (when users found, before any build)
User explicitly invokes: pricing-smoke-test
        |
        v (final checkpoint before build decision)
User explicitly invokes: minimalist-review
```

## What Demand Radar should NOT do

```
DO NOT run all 6 skills automatically after run-d5.
DO NOT add skill invocation to any scheduled pipeline.
DO NOT let Foundation skills modify Demand Radar theme data.
DO NOT use skill output as an automatic gate to block themes.
```

## Integration boundary table

| Responsibility | Demand Radar | Foundation Skills |
|---|---|---|
| Collect demand signals | Yes | No |
| Score evidence (TruthScore, FitScore) | Yes | No |
| Group demand themes | Yes | No |
| Run theme-validation | User-triggered only | Provides the method |
| Run concierge-mvp design | User-triggered only | Provides the method |
| Store skill outputs | Yes (in Radar outputs) | No |
| Interpret skill outputs | Yes (Radar decides) | No |

## Pinning the Foundation version

```
# Demand Radar pyproject.toml
opc-foundation @ git+https://github.com/xe7dx54321-stack/opc-foundation@v0.1.3
```

Before upgrading to a new Foundation version, run Demand Radar integration tests.

## D6 recommendation

In Demand Radar D6, the recommended implementation is:

1. After D5 produces themes, user browses the theme list
2. User selects a theme and clicks "Run theme-validation"
3. Radar loads the skill SKILL.md from Foundation, prepares the input from Radar data
4. Radar invokes its own LLM client with the skill prompt
5. Radar saves the validation output to `outputs/skill_results/`
6. User reviews and decides whether to invoke next skill

This keeps Foundation as the skill knowledge base,
and Demand Radar as the invocation controller.