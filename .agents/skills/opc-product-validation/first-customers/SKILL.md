# First Customers

> **This skill is optional and must be explicitly invoked by a downstream project or user.**
> **Do not run this skill automatically as part of any pipeline.**
>
> 本 skill 是可选决策辅助，必须由下游项目或用户显式调用，不得自动进入任何业务主流程。

## Purpose

Identify and plan outreach to the first 3-10 potential users for a
concierge MVP. Start with the people closest to you, then expand.

## When to Use

- After concierge-mvp plan is ready
- Before building anything or running any marketing
- When you need to find real people to test the manual service with

## When Not to Use

- Do NOT use as a mass marketing plan
- Do NOT run before knowing what you are offering (no concierge plan = no outreach)
- Do NOT assume users will come to you without outreach

## Required Inputs

| Field | Type | Description |
|---|---|---|
| `theme_id` | string | Theme identifier |
| `manual_service_offer` | string | The concierge MVP offer |
| `target_user` | string | Who the service is for |
| `persona_group` | string | Target persona group |

## Optional Inputs

- `evidence_summary` — which communities they appeared in
- `representative_quotes` — what they said about the pain
- `known_contacts` — any existing contacts in this space

## Output Format

```json
{
  "theme_id": "...",
  "target_customer_segments": ["..."],
  "where_to_find_them": ["..."],
  "community_or_channel_list": ["..."],
  "warm_outreach_angles": ["..."],
  "cold_outreach_messages": ["..."],
  "interview_questions": ["..."],
  "offer_message": "...",
  "disqualification_criteria": ["..."]
}
```

## Decision Rules

1. Start with the 1-2 degrees of separation from your own network.
2. Identify 2-3 specific communities or channels where these people gather.
3. Write at least one warm and one cold outreach message — both specific, not generic.
4. Interview questions must probe actual pain, not validate your solution.
5. Disqualification criteria: be explicit about who is NOT your target user.
6. Do not plan large-scale marketing — goal is 3-10 real conversations.

## Red Flags

- Outreach message is generic ("Do you have pain with research?")
- No specific communities identified
- Offer is unclear or too complex for first message
- No disqualification criteria

## Example Prompt

```
You are a customer development specialist applying the First Customers skill.

Input:
{first_customers_input_json}

Design a specific outreach plan to find the first 3-10 potential users.
Messages must be personal and specific. Interview questions must probe
real pain, not validate a solution.
```

## Example Output Skeleton

```json
{
  "theme_id": "theme__001",
  "target_customer_segments": ["初级投资分析师（1-3年经验）", "小型VC研究团队成员"],
  "where_to_find_them": [
    "LinkedIn 投资分析相关群组",
    "微信/Slack VC 从业者社群",
    "Reddit r/investing, r/FinancialCareers"
  ],
  "community_or_channel_list": ["r/ValueInvesting", "CFA考生群", "国内VC从业者微信群"],
  "warm_outreach_angles": [
    "你之前做过相关领域研究 — 请教你做公司尽调时最痛的环节是什么？",
    "我注意到你在 XX 社区提到了研究工作流的问题 — 我正在研究这个，能否聊15分钟？"
  ],
  "cold_outreach_messages": [
    "Hi，我是李少博。我在研究投资分析师的工作流程痛点。你有没有遇到过整理研究资料特别费时间的情况？能否聊15分钟分享一下？"
  ],
  "interview_questions": [
    "你最近一次做公司研究时，从开始到产出报告大概花了多少时间？",
    "哪个环节最让你头疼？为什么？",
    "你现在怎么解决这个问题的？用什么工具或方法？",
    "如果这个问题消失了，你的工作会有什么变化？"
  ],
  "offer_message": "我可以帮你在48小时内整理一份结构化的公司研究报告（Notion格式），你只需要告诉我目标公司名和研究目的。第一份免费，如果有用再谈后续合作。",
  "disqualification_criteria": [
    "不做个股研究的人（如指数投资者）",
    "已经有完整研究团队的大型机构",
    "没有实际痛点、只是好奇的人"
  ]
}
```