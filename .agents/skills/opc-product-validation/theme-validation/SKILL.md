# Theme Validation

> **This skill is optional and must be explicitly invoked by a downstream project or user.**
> **Do not run this skill automatically as part of any pipeline.**
>
> 本 skill 是可选决策辅助，必须由下游项目或用户显式调用，不得自动进入任何业务主流程。

## Purpose

Evaluate whether a demand theme has sufficient first-hand evidence to justify further
validation effort. Output a verdict and identify evidence gaps.

## When to Use

- After demand signal collection and theme grouping
- Before committing time to concierge MVP design
- When a theme has mixed or weak evidence and needs structured evaluation

## When Not to Use

- Do NOT run on every theme automatically after each pipeline run
- Do NOT use as a scoring gate that blocks all themes uniformly
- Do NOT substitute for actual user interviews

## Required Inputs

| Field | Type | Description |
|---|---|---|
| `theme_id` | string | Unique theme identifier |
| `theme_title_zh` | string | Theme title in Chinese |
| `core_pain_zh` | string | Core pain description |
| `persona_group` | string | Target persona |
| `evidence_summary` | object | Counts: total, first-hand, marketing/vendor |
| `representative_quotes` | list[string] | Direct quotes from evidence |

## Optional Inputs

- `source_quality_summary` — breakdown by source type
- `human_review_summary` — notes from manual review
- `representative_source_urls` — URLs of key evidence

## Output Format

```json
{
  "theme_id": "...",
  "validation_verdict": "pursue_validation | needs_more_evidence | watch | reject",
  "verdict_reason_zh": "...",
  "evidence_strength": "strong | moderate | weak | insufficient",
  "commercial_potential": "high | medium | low | unclear",
  "first_hand_evidence_gap": true,
  "evidence_gaps": ["..."],
  "recommended_next_step": "...",
  "do_not_do": ["..."]
}
```

## Decision Rules

1. All judgments must be grounded in the provided evidence — no fabrication.
2. If first_hand_evidence_count < 2, always flag `first_hand_evidence_gap = true`.
3. Content marketing pages / vendor blogs / job postings are low-quality evidence only.
4. Reddit posts / community discussions / user workarounds are higher-quality evidence.
5. A theme can only receive `pursue_validation` if there are first-hand pain signals.
6. Never recommend "build a product" as a next step.
7. Next steps must be: validate / gather more evidence / interview users / manual service / watch / reject.

## Evidence Rules

- Strong: 3+ first-hand user quotes showing pain + workaround behavior
- Moderate: 1-2 first-hand signals + community discussion
- Weak: only vendor content or job postings
- Insufficient: no direct user evidence

## Red Flags

- All evidence comes from vendor blogs or company websites
- Pain is described only in abstract / generic terms (no specific workflow)
- No workaround behavior found
- Only one source domain
- Quote looks like marketing copy, not user frustration

## Example Prompt

```
You are a product validation analyst using the OPC Theme Validation skill.

Input:
{theme_input_json}

Using the Decision Rules and Evidence Rules above, produce a structured
validation assessment. Do not fabricate evidence. If evidence is insufficient,
say so clearly.
```

## Example Output Skeleton

```json
{
  "theme_id": "theme__001",
  "validation_verdict": "needs_more_evidence",
  "verdict_reason_zh": "当前证据以资讯类内容为主，缺少用户第一手痛点描述和变通方案记录。",
  "evidence_strength": "weak",
  "commercial_potential": "unclear",
  "first_hand_evidence_gap": true,
  "evidence_gaps": [
    "缺少真实用户描述自己工作流的第一手内容",
    "没有发现 workaround 行为记录"
  ],
  "recommended_next_step": "在 Reddit / 相关社区寻找真实用户的工作流描述，或直接访谈 2-3 名目标用户",
  "do_not_do": ["不要在证据不足时直接开发产品", "不要把厂商博客当作主要证据"]
}
```