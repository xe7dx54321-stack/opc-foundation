# OPC Foundation M3C-4 Report: Trial 运行结果接入 Control Center

> **版本**：1.0
> **执行时间**：2026-06-29
> **状态**：完成

---

## 1. M3C-4 概述

### 目标

将 15 个 trial source 的运行结果从"本地 data 文件"变成"可监控、可汇报、可运维的系统状态"。

### 完成内容

1. 读取 `data/foundation_trial/index/source_health.jsonl`
2. 读取 `data/foundation_trial/index/run_log.jsonl`
3. 读取 `data/foundation_trial/index/failed_queue.jsonl`
4. 在 Control Center 健康监控中展示 trial source 运行摘要
5. 在配置检查中展示 trial allowlist / trial schedule 配置状态
6. 增强 daily status report，加入 trial scheduling 专区
7. 新增 trial operating report（本文档）
8. 新增测试覆盖

---

## 2. Trial Source 当前数量：15

| source_id | source_name | 状态 |
|---|---|---|
| goldman_sachs_research | Goldman Sachs Research | URL 修复（200 OK） |
| goldman_sachs_reports | Goldman Sachs Reports | URL 修复（200 OK） |
| goldman_sachs_top_of_mind | Goldman Sachs Top of Mind | live OK |
| goldman_sachs_insights | Goldman Sachs Insights | live OK |
| barclays_our_insights | Barclays Our Insights | live OK |
| yahoo_finance | Yahoo Finance | live OK |
| business_insider | Business Insider | live OK |
| markets_insider | Markets Insider | live OK |
| the_fly | The Fly | live OK |
| briefing_com_upgrades | Briefing.com Upgrades/Downgrades | live OK |
| wallstreet_cn | 华尔街见闻 | live OK |
| cls_cn | 财联社 | live OK（标记 **transient watch**，偶发 HTTP 418 反爬） |
| wind_public | Wind 万得公开内容 | live OK |
| gelonghui | 格隆汇 | live OK |
| zhitong_caijing | 智通财经 | live OK |

**排除的源**：
- Microsoft IR → url_backlog（HTTP 403 Akamai bot 保护）
- 全部 blocked/search/dormant/problem source → 未纳入 trial

---

## 3. 接入的数据文件

| 文件 | 用途 | fail-soft |
|---|---|---|
| `data/foundation_trial/index/source_health.jsonl` | 每个源的健康状态 | 不存在时返回 unknown |
| `data/foundation_trial/index/run_log.jsonl` | 运行日志 | 不存在时返回空列表 |
| `data/foundation_trial/index/failed_queue.jsonl` | 失败队列 | 不存在时返回空列表 |
| `data/foundation_trial/reports/` | 运行报告 | 不直接读取 |

**注意**：这些 data 文件已加入 `.gitignore`，不提交 Git。

---

## 4. Dashboard 展示位置

### 4.1 健康监控页面

在"状态说明" expander 下方，能力列表表格上方，新增 **Foundation Trial Sources** 摘要卡片：

- Trial 源数
- 成功数（绿色）
- 失败数（红色）
- Transient watch 数（黄色）
- 成功率
- 最近运行时间
- 整体健康状态徽章

**data 不存在时**：显示 info 提示"尚未运行，暂无 trial 数据"

### 4.2 配置检查页面

在"检查分类说明"下方，"能力注册表校验"之前，新增 **Trial 配置与运行状态** section：

- Trial 运行数据是否已生成
- 健康状态、源数、成功/失败/Transient 数
- Transient watch 源列表（如 cls_cn）
- blocked/search/dormant 是否未误纳入确认

**data 不存在时**：显示 info 提示运行命令

### 4.3 能力详情弹窗

未新增内容，复用现有弹窗结构。

---

## 5. Daily Status 新增内容

`scripts/check_foundation_daily_status.ps1` 增强：

新增 **Section 2: Foundation Trial Sources**，包含：

- trial source count
- latest run timestamp
- success / failed / transient count
- skipped (dry_run) count
- empty (candidate_count=0) count
- overall health
- transient watch sources（如 cls_cn HTTP 418）
- Microsoft IR backlog 状态
- blocked/search/dormant 排除确认

新增 **Section 8: Next Steps**：

- Monitor cls_cn transient watch
- If trial stable for 2 weeks, consider M3C-5
- Microsoft IR: explore alternative entry points

---

## 6. Trial 健康状态规则

| 状态 | 条件 |
|---|---|
| **healthy** | 成功率 >= 90%，且无 P0 错误 |
| **degraded** | 存在 transient watch 或成功率 70%-90% |
| **failed** | 最近一次 run 未执行、严重错误、或 success < 70% |
| **unknown** | 尚未生成 trial data（data 文件不存在） |

---

## 7. cls_cn Transient Watch 处理规则

- **现象**：偶发 HTTP 418（I'm a teapot，反爬状态码）
- **处理**：标记为 `transient_watch`，不计入 failed_count
- **影响**：不降低 overall_health 到 failed，但会标记为 degraded
- **后续**：观察 1-2 周，如果持续稳定则移除 transient watch
- **非 P0/P1 blocker**

---

## 8. Microsoft IR Backlog 状态

- **当前状态**：url_backlog，已从 trial allowlist 移除
- **原因**：HTTP 403（Akamai bot 保护）
- **下一步**：探索 SEC EDGAR 或第三方财经平台替代入口
- **不在 trial 范围内**

---

## 9. Blocked / Search / Dormant / Problem Source 排除确认

| 类别 | 是否纳入 trial | 确认 |
|---|---|---|
| blocked | ❌ 否 | 确认 |
| search_providers | ❌ 否 | 确认 |
| dormant | ❌ 否 | 确认 |
| high_risk | ❌ 否 | 确认 |
| TLS/DNS 问题源 | ❌ 否 | 确认 |
| 微信源 | ❌ 否 | 确认 |

---

## 10. 是否具备继续观察 / Production Trial 条件

### 当前评估

| 条件 | 状态 |
|---|---|
| 15 个 trial source 可运行 | ✅ 已通过手动 + TRAE trigger 验证 |
| TRAE command-only 调度稳定 | ✅ 已修复，trigger 正常 |
| Dashboard 可监控 trial 状态 | ✅ M3C-4 已完成 |
| Daily status 包含 trial 专区 | ✅ M3C-4 已完成 |
| cls_cn transient 可控 | ⚠️ 观察中，非 blocker |
| Microsoft IR 有替代方案 | ❌ 待 M3C-5 或后续修复 |
| 2 周稳定运行记录 | ❌ 需要继续观察 |

### 结论

**可以进入继续观察阶段**，但尚未达到 production trial 条件。建议：

1. 继续运行 2 周，观察 cls_cn 稳定性
2. 每日检查 Dashboard trial 摘要
3. 2 周后评估是否进入 M3C-5 production scheduling

---

## 11. 后续 M3C-5 建议

M3C-5 可能方向：

1. **Production Scheduling**：将 15 个 trial source 从 trial-only 转为正式 production 调度
2. **Microsoft IR Fix**：探索 SEC EDGAR 或第三方平台替代方案
3. **扩源评估**：从 92 源中评估第二批可纳入的源（需排除 blocked/high-risk）
4. **Dashboard 增强**：增加 trial 运行趋势图、历史成功率曲线
5. **告警机制**：当 trial 成功率 < 70% 或连续失败时自动告警

---

## 12. 修改文件清单

| 文件 | 修改内容 |
|---|---|
| `src/opc_foundation/dashboard/models.py` | 新增 TrialSourceStatus、TrialRuntimeSummary 数据模型 |
| `src/opc_foundation/dashboard/loaders.py` | 新增 trial runtime loader（load_trial_runtime_data、build_trial_runtime_summary） |
| `src/opc_foundation/dashboard/app.py` | 健康监控页面新增 trial 摘要卡片；配置检查页面新增 trial 状态 section |
| `scripts/check_foundation_daily_status.ps1` | 新增 Foundation Trial Sources 专区和 Next Steps |
| `docs/foundation_trial_operating_report.md` | 新增（本文档） |
| `tests/dashboard/test_trial_runtime_health.py` | 新增测试 |

---

## 13. 重要声明

> **M3C-4 只读取和展示 trial 运行数据，不修改 source inventory，不扩展源。**
>
> 本阶段：
> - 不新增 source
> - 不扩展到 92 全量源
> - 不修 TLS/DNS/404/微信问题源
> - 不调度 Microsoft IR
> - 不抓 blocked/high-risk
> - 不绕登录/付费墙
> - 不下载不明 PDF
> - 不提交 data/
> - 不提交 local config
> - 不恢复已删除 Dashboard 页面
> - 不引入 Playwright/Selenium
> - 不做投资判断
> - 不打 tag
