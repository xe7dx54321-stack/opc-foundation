# Minimalist Review

> **This skill is optional and must be explicitly invoked by a downstream project or user.**
> **Do not run this skill automatically as part of any pipeline.**
>
> 本 skill 是可选决策辅助，必须由下游项目或用户显式调用，不得自动进入任何业务主流程。

## Purpose

Run a structured 8-question minimalist startup checklist before committing
to building any product. Forces explicit, evidence-based answers to the
most critical early-stage questions.

## When to Use

- Before any product development decision
- After theme-validation and concierge-mvp are complete
- As a final review checkpoint before moving to pilot or build phase

## When Not to Use

- Do NOT use as a replacement for theme-validation or concierge-mvp
- Do NOT run automatically at the end of any pipeline
- Do NOT use it to rubber-stamp a decision already made

## Required Inputs

| Field | Type | Description |
|---|---|---|
| `theme_id` | string | Theme identifier |
| `theme_title_zh` | string | Theme title |
| `core_pain_zh` | string | Core pain statement |
| `evidence_summary` | object | Evidence counts and quality |
| `validation_verdict` | string | Output from theme-validation |

## Optional Inputs

- `concierge_mvp_plan` — output from concierge-mvp skill
- `first_customer_plan` — output from first-customers skill
- `pricing_smoke_test` — output from pricing-smoke-test skill
- `human_review_summary` — notes from manual review

## Output Format

```json
{
  "theme_id": "...",
  "checklist": {
    "has_clear_user": {"answer": "yes | no | unclear", "evidence": "..."},
    "has_real_pain": {"answer": "yes | no | unclear", "evidence": "..."},
    "has_first_hand_evidence": {"answer": "yes | no | unclear", "evidence": "..."},
    "has_workaround_behavior": {"answer": "yes | no | unclear", "evidence": "..."},
    "has_manual_delivery_plan": {"answer": "yes | no | unclear", "evidence": "..."},
    "has_reachable_first_users": {"answer": "yes | no | unclear", "evidence": "..."},
    "has_payment_validation_path": {"answer": "yes | no | unclear", "evidence": "..."},
    "no_premature_productization_risk": {"answer": "yes | no | unclear", "evidence": "..."}
  },
  "final_verdict": "pursue_concierge | needs_more_evidence | watch | reject",
  "reason": "...",
  "red_flags": ["..."],
  "evidence_gaps": ["..."],
  "next_smallest_step": "...",
  "do_not_build_list": ["..."]
}
```

## Decision Rules

The 8 mandatory checklist questions:

1. **Has clear user?** — Can you name a specific type of person who has this pain?
2. **Has real pain?** — Is the pain specific, observable, and causing workflow friction?
3. **Has first-hand evidence?** — Are there direct quotes from real users (not vendor content)?
4. **Has workaround behavior?** — Are users doing something inefficient to cope with the pain?
5. **Has manual delivery plan?** — Can you deliver value to one user manually right now?
6. **Has reachable first users?** — Can you identify 3-5 specific people to reach out to?
7. **Has payment validation path?** — Is there a clear way to test willingness to pay?
8. **No premature productization risk?** — Are you NOT about to build before validating?

Verdict logic:
- All 8 = yes → `pursue_concierge`
- 5-7 = yes → `needs_more_evidence` (specify gaps)
- 3-4 = yes → `watch`
- < 3 = yes → `reject`

## Red Flags

- Building before any manual delivery
- No first-hand user evidence
- Jumping from theme to product without concierge step
- Assuming pain without direct user confirmation
- Counting vendor blogs as user evidence

## Example Prompt

```
You are a minimalist startup reviewer applying the Minimalist Review skill.

Input:
{minimalist_review_input_json}

Answer each of the 8 checklist questions with evidence from the input.
Do not assume or fabricate. If evidence is missing, answer "unclear" and
specify the gap. Then produce a final verdict.
```

## Example Output Skeleton

```json
{
  "theme_id": "theme__001",
  "checklist": {
    "has_clear_user": {"answer": "yes", "evidence": "目标用户为初级投资分析师，有具体工作场景描述"},
    "has_real_pain": {"answer": "yes", "evidence": "用户描述研究流程碎片化，需要在多工具间手动整合"},
    "has_first_hand_evidence": {"answer": "unclear", "evidence": "仅1条第一手社区帖子，其余为资讯内容"},
    "has_workaround_behavior": {"answer": "no", "evidence": "未找到用户描述自己变通方案的记录"},
    "has_manual_delivery_plan": {"answer": "yes", "evidence": "已设计48小时人工研究报告交付方案"},
    "has_reachable_first_users": {"answer": "yes", "evidence": "已识别LinkedIn群组和微信VC社群为触达渠道"},
    "has_payment_validation_path": {"answer": "yes", "evidence": "已设计¥99试用定价和付费验证标准"},
    "no_premature_productization_risk": {"answer": "yes", "evidence": "当前计划为人工交付，未开始软件开发"}
  },
  "final_verdict": "needs_more_evidence",
  "reason": "第一手证据不足，且未发现用户变通行为记录，建议先补充社区访谈再推进",
  "red_flags": ["第一手证据数量偏少"],
  "evidence_gaps": ["缺少用户描述自己工作流变通方案的记录"],
  "next_smallest_step": "在Reddit r/ValueInvesting 或相关微信群找2-3名投资分析师进行15分钟访谈",
  "do_not_build_list": ["研究报告生成自动化", "数据抓取系统", "用户管理平台"]
}
```