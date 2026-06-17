# Pricing Smoke Test

> **This skill is optional and must be explicitly invoked by a downstream project or user.**
> **Do not run this skill automatically as part of any pipeline.**
>
> 本 skill 是可选决策辅助，必须由下游项目或用户显式调用，不得自动进入任何业务主流程。

## Purpose

Design the minimal paid validation for a concierge MVP. Distinguish
strong signals (willingness to pay / commit) from weak ones
(likes, saves, verbal interest).

## When to Use

- After at least one successful concierge delivery
- Before building any pricing infrastructure
- When you want to test if users will actually pay

## When Not to Use

- Do NOT run before any concierge delivery
- Do NOT use as a substitute for real delivery
- Do NOT confuse interest signals with payment signals

## Required Inputs

| Field | Type | Description |
|---|---|---|
| `theme_id` | string | Theme identifier |
| `manual_service_offer` | string | What the concierge service delivers |
| `target_user` | string | Who it is for |
| `value_proposition` | string | Why users should pay |

## Optional Inputs

- `delivery_notes` — what worked / what users valued
- `time_cost_per_delivery` — your cost to deliver

## Output Format

```json
{
  "theme_id": "...",
  "unit_of_value": "...",
  "pricing_hypotheses": [
    {"hypothesis": "...", "price_point": "...", "rationale": "..."}
  ],
  "one_time_offer": "...",
  "monthly_offer": "...",
  "pilot_offer": "...",
  "smoke_test_offer": "...",
  "payment_signal_criteria": {"strong": ["..."], "weak": ["..."], "not_valid": ["..."]},
  "objection_questions": ["..."],
  "what_counts_as_validation": "...",
  "what_does_not_count_as_validation": "..."
}
```

## Decision Rules

1. Strong signals: user pays, user schedules delivery, user refers others, user provides real data.
2. Weak signals: user says "sounds interesting", user likes/saves post, user agrees in interview.
3. NOT valid: hypothetical willingness ("I would pay"), anonymous form submissions, survey responses.
4. Pilot offer must be lower risk for the user than the full offer.
5. At least 2 of 3 first paid users is the minimum validation threshold.

## Evidence Rules

- Validated: money collected or formal commitment with deposit
- Partial: written commitment with specific date and scope
- Weak: verbal interest without follow-through

## Red Flags

- Only measuring verbal interest as validation
- Price has no connection to value delivered
- Pilot offer is too cheap to signal real intent
- No clear definition of "what counts as validated"

## Example Prompt

```
You are a pricing strategist applying the Pricing Smoke Test skill.

Input:
{pricing_input_json}

Design the minimal paid validation. Clearly define what counts as
strong vs weak vs invalid signals. Do not overestimate verbal interest.
```

## Example Output Skeleton

```json
{
  "theme_id": "theme__001",
  "unit_of_value": "一份结构化公司研究报告",
  "pricing_hypotheses": [
    {"hypothesis": "用户愿意为节省2-3小时研究时间付费", "price_point": "¥299/份", "rationale": "对标一次初级分析师的时间成本"},
    {"hypothesis": "月度订阅模式可行", "price_point": "¥999/月（4份/月）", "rationale": "满足月度研究需求"}
  ],
  "one_time_offer": "¥299 一份结构化研究报告，48小时交付",
  "monthly_offer": "¥999/月，每月最多4份",
  "pilot_offer": "¥99 首次试用，满意再续",
  "smoke_test_offer": "前3名用户，首份报告¥99，如满意请转介绍1位同行",
  "payment_signal_criteria": {
    "strong": ["完成支付", "预约了具体交付时间", "提供了真实公司研究需求", "主动转介绍同行"],
    "weak": ["说'听起来不错'", "收藏了介绍帖子", "访谈中表示有兴趣"],
    "not_valid": ["问卷里说愿意付", "假设性回答（'如果价格合适我会考虑'）"]
  },
  "objection_questions": [
    "你觉得什么样的报告质量值得这个价格？",
    "你现在是怎么解决这个问题的？花了多少时间或成本？"
  ],
  "what_counts_as_validation": "3个用户中至少2个完成付费并接受交付",
  "what_does_not_count_as_validation": "收到口头认可但没有完成付款的情况"
}
```