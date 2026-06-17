# Processize Before Productize

> **This skill is optional and must be explicitly invoked by a downstream project or user.**
> **Do not run this skill automatically as part of any pipeline.**
>
> 本 skill 是可选决策辅助，必须由下游项目或用户显式调用，不得自动进入任何业务主流程。

## Purpose

Break a concierge MVP manual delivery plan into a repeatable SOP,
identify future automation candidates, and clarify which steps require
a human in the loop.

## When to Use

- After delivering the concierge MVP at least once successfully
- When you want to make the manual service more consistent and scalable
- Before deciding which parts to automate first

## When Not to Use

- Do NOT run before at least one real manual delivery
- Do NOT use to generate a product feature list prematurely
- Do NOT skip this step and go directly to building software

## Required Inputs

| Field | Type | Description |
|---|---|---|
| `theme_id` | string | Theme identifier |
| `manual_service_offer` | string | The concierge MVP offer |
| `human_delivery_steps` | list[string] | Steps from concierge plan |
| `tools_needed` | list[string] | Tools used in delivery |

## Optional Inputs

- `delivery_notes` — notes from actual delivery runs
- `failure_points_observed` — things that went wrong

## Output Format

```json
{
  "theme_id": "...",
  "step_by_step_sop": [
    {"step": 1, "action": "...", "type": "human | automatable", "input": "...", "output": "...", "quality_check": "..."}
  ],
  "human_steps": ["..."],
  "automation_candidates": [
    {"step_id": 1, "action": "...", "automation_approach": "...", "priority": "high | medium | low"}
  ],
  "inputs": ["..."],
  "outputs": ["..."],
  "quality_checks": ["..."],
  "failure_points": ["..."],
  "next_process_iteration": "..."
}
```

## Decision Rules

1. Every SOP step must come from an actual human delivery step — no invented steps.
2. Automation candidates must come from existing human steps only.
3. Steps that require judgment, context, or relationship should stay human.
4. Steps that are purely mechanical and repeatable are automation candidates.
5. `failure_points` must be honest — do not omit known problems.

## Red Flags

- SOP steps are too vague to execute ("do research")
- All steps are marked as automatable prematurely
- No quality check defined
- Failure points are omitted

## Example Prompt

```
You are a process design specialist applying the Processize skill.

Input:
{processize_input_json}

Break the manual delivery into a step-by-step SOP. For each step, classify
it as human or automatable. Do not invent steps. Only use the actual
delivery steps provided.
```

## Example Output Skeleton

```json
{
  "theme_id": "theme__001",
  "step_by_step_sop": [
    {"step": 1, "action": "接收用户输入，确认研究范围", "type": "human",
     "input": "用户邮件/表单", "output": "确认清单", "quality_check": "所有字段已填写"},
    {"step": 2, "action": "抓取公司基本面数据", "type": "automatable",
     "input": "公司名称", "output": "结构化数据JSON", "quality_check": "数据不为空，来源可靠"}
  ],
  "human_steps": ["接收用户输入，确认研究范围", "撰写研究结论和建议"],
  "automation_candidates": [
    {"step_id": 2, "action": "抓取公司基本面数据", "automation_approach": "搜索API + 结构化提取", "priority": "high"}
  ],
  "inputs": ["公司名称", "研究目的"],
  "outputs": ["结构化研究报告"],
  "quality_checks": ["报告模板所有字段已填写", "用户确认内容可用"],
  "failure_points": ["数据来源质量不稳定", "用户需求不清晰导致返工"],
  "next_process_iteration": "下次交付时，先用标准化问卷收集用户需求，减少来回确认"
}
```