# Concierge MVP

> **This skill is optional and must be explicitly invoked by a downstream project or user.**
> **Do not run this skill automatically as part of any pipeline.**
>
> 本 skill 是可选决策辅助，必须由下游项目或用户显式调用，不得自动进入任何业务主流程。

## Purpose

Convert a validated demand theme into a manual, code-free service plan
that can be delivered to real users immediately. Validate the value
before building any software.

## When to Use

- After theme-validation returns `pursue_validation`
- When you want to test value delivery before writing any code
- When you have at least 1-2 potential users willing to try the service

## When Not to Use

- Do NOT run before theme-validation
- Do NOT use as a product spec — this is a manual service plan only
- Do NOT build software based solely on this plan without real delivery

## Required Inputs

| Field | Type | Description |
|---|---|---|
| `theme_id` | string | Validated theme identifier |
| `theme_title_zh` | string | Theme title |
| `core_pain_zh` | string | Core pain statement |
| `persona_group` | string | Target persona |
| `evidence_summary` | object | Supporting evidence |

## Optional Inputs

- `user_persona_detail` — detailed persona profile
- `representative_quotes` — key user quotes to ground the design

## Output Format

```json
{
  "theme_id": "...",
  "manual_service_offer": "...",
  "target_user": "...",
  "input_required_from_user": ["..."],
  "human_delivery_steps": ["step 1", "step 2", "..."],
  "expected_delivery_output": "...",
  "time_cost_per_delivery": "...",
  "tools_needed": ["..."],
  "quality_standard": "...",
  "success_criteria": ["..."],
  "what_not_to_build_yet": ["..."]
}
```

## Decision Rules

1. The service must be deliverable by a human without code.
2. Every step must be executable today using existing tools (spreadsheets, docs, Notion, email).
3. `what_not_to_build_yet` must list at least 2 items.
4. If the service cannot be delivered manually, output a warning and stop.
5. Success criteria must be measurable and observable.

## Red Flags

- Delivery plan requires building software first
- Delivery time per unit exceeds what a user would reasonably wait
- No clear, tangible output for the user
- Steps are vague ("do research", "analyze data")

## Example Prompt

```
You are a product validation specialist designing a Concierge MVP.

Input:
{concierge_input_json}

Design a step-by-step manual service plan that delivers real value to the
target user WITHOUT writing any code. Each step must be specific and
executable by a human today.
```

## Example Output Skeleton

```json
{
  "theme_id": "theme__001",
  "manual_service_offer": "为投资分析师提供一份结构化的研究工作流整理报告：给定公司名和研究目标，在 48 小时内交付一份整合了公司基本面、行业背景、竞品简况的 Notion 模板报告。",
  "target_user": "早期阶段投资分析师，需要在 2-3 天内完成标准化公司尽调研究",
  "input_required_from_user": [
    "目标公司名称",
    "研究目的（初步筛选 / 深度尽调 / 竞品分析）",
    "关注的核心指标"
  ],
  "human_delivery_steps": [
    "接收用户输入，确认研究范围",
    "使用公开数据源（SEC filings、公司官网、新闻）整理基本信息",
    "用 Notion 模板填写结构化报告",
    "发送报告给用户，收集反馈"
  ],
  "expected_delivery_output": "一份 Notion 格式的结构化研究报告，包含：公司基本面、行业背景、竞品简况",
  "time_cost_per_delivery": "3-5 小时/份",
  "tools_needed": ["Notion", "公开财务数据源", "Google", "电子邮件"],
  "quality_standard": "用户评分 >= 4/5，愿意为下次使用付费",
  "success_criteria": [
    "用户实际使用了报告",
    "用户表示节省了至少 2 小时研究时间",
    "用户愿意下次继续使用"
  ],
  "what_not_to_build_yet": [
    "自动化数据抓取系统",
    "AI 分析引擎",
    "用户管理平台",
    "报告生成 SaaS"
  ]
}
```