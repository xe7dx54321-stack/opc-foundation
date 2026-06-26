# Foundation TRAE Trial Run

> 版本：2.0
> 创建时间：2026-06-26
> 更新时间：2026-06-26
> 状态：**M3C-3 Trial Scheduling 已接入**

## 1. 概述

本文档记录 M3C-2D 阶段的目标、配置和使用方法。

**核心目标**：将 M3C-2D-URLFix 后的 15 个 trial ready 源纳入 TRAE Trial Scheduling，形成最小真实运营闭环。

> **重要说明**：M3C-2D / M3C-3 是 trial-only（试运行），不代表最终 production TRAE 接管。

---

## 2. Trial Source 范围

以 `docs/foundation_trae_trial_sources.md` 和 `configs/foundation_trial_source_allowlist.example.yaml` 为准。

**候选源数量：15 个**（原 16 个，移出 Microsoft IR：HTTP 403 Akamai bot 保护）

| 类别 | 数量 | 代表源 |
|---|---|---|
| 投行官方公开研究 | 4 | Goldman Sachs × 4, Barclays |
| 媒体研报二次引用 | 3 | Yahoo Finance, Business Insider, Markets Insider |
| 分析师评级/目标价变动 | 2 | The Fly, Briefing.com |
| 中文财经二次传播 | 5 | 华尔街见闻, 财联社, 万得, 格隆汇, 智通财经 |

**注**：Microsoft IR 已移出（HTTP 403 Akamai bot 保护），进入 url_backlog。

---

## 3. 明确排除的源

Trial 范围**不得包含**以下源：

| 类别 | 数量 | 原因 |
|---|---|---|
| blocked/high-risk | 5 | 策略禁止 |
| search provider | 10 | 仅按需使用 |
| dormant | 2 | 社区源，休眠 |
| TLS 握手失败 | 21 | 需替代入口/browser-like connector |
| DNS 失败 | 5 | 需验证替代域名 |
| HTTP 4xx/404 | 20 | 需修正 URL |
| 微信待映射 | 6 | 需 wechat_archive connector |
| 超时待验证 | 1 | 需进一步确认 |

---

## 4. 配置文件

### 4.1 Trial Source Allowlist

**文件**：`configs/foundation_trial_source_allowlist.example.yaml`

记录 15 个 trial source_id 和被明确排除的 source_id（含 Microsoft IR 进入 url_backlog）。

### 4.2 Trial Sources Config

**文件**：`configs/trae_foundation_trial_sources.example.yaml`

完整的 trial-only research 配置，包含 15 个 trial sources 的 feed_url、source_type 等信息。

---

## 5. 运行脚本

### 5.1 运行脚本

**文件**：`scripts/run_foundation_trial_sources.ps1`

```powershell
# 验证配置
powershell -ExecutionPolicy Bypass -File scripts/run_foundation_trial_sources.ps1 -Mode validate-config

# Dry-run（不访问网络）
powershell -ExecutionPolicy Bypass -File scripts/run_foundation_trial_sources.ps1 -Mode dry-run

# 真实运行
powershell -ExecutionPolicy Bypass -File scripts/run_foundation_trial_sources.ps1 -Mode run

# 如需代理
powershell -ExecutionPolicy Bypass -File scripts/run_foundation_trial_sources.ps1 -Mode run -Proxy "http://127.0.0.1:7890"
```

### 5.2 检查脚本

**文件**：`scripts/check_foundation_trial_sources.ps1`

```powershell
powershell -ExecutionPolicy Bypass -File scripts/check_foundation_trial_sources.ps1
```

### 5.3 CLI 命令

```powershell
# 验证配置
python -m opc_foundation.source_inventory.cli trial-validate

# Dry-run
python -m opc_foundation.source_inventory.cli trial-run --dry-run

# 真实运行
python -m opc_foundation.source_inventory.cli trial-run

# 生成报告
python -m opc_foundation.source_inventory.cli trial-report
```

---

## 6. 输出目录

Trial 运行产物写入：

```
data/foundation_trial/
  index/
    source_health.jsonl      # 各源运行状态
    run_log.jsonl             # 运行日志
    run_summary.json          # 汇总
    failed_queue.jsonl        # 失败队列
  reports/
    trial_run_YYYY-MM-DD.md   # 运行报告
```

> **注意**：`data/` 目录不提交 Git。

---

## 7. 报告

Trial 运行报告写入：

- `data/foundation_trial/reports/trial_run_YYYY-MM-DD.md`
- `docs/foundation_trial_run_report.md`

报告包含：
- 执行时间、source 总数、运行结果
- 每个 source 的状态（success / empty / failed）
- Failed queue 明细
- 后续建议

---

## 8. 代理配置

如需代理：

```powershell
# 方式 1：CLI 参数
python -m opc_foundation.source_inventory.cli trial-run --proxy "http://127.0.0.1:7890"

# 方式 2：PowerShell 脚本参数
powershell -ExecutionPolicy Bypass -File scripts/run_foundation_trial_sources.ps1 -Mode run -Proxy "http://127.0.0.1:7890"

# 方式 3：环境变量
$env:HTTPS_PROXY = "http://127.0.0.1:7890"
python -m opc_foundation.source_inventory.cli trial-run
```

报告里只记录 `proxy_enabled=true/false` 和 `proxy_mode=cli/env/none`，不输出完整代理地址。

---

## 9. 后续阶段建议

| 阶段 | 内容 |
|---|---|
| M3C-2D-URLFix | ✅ 已完成（GS 2 源 URL 修复，MS IR 移出） |
| M3C-3 | ✅ **已接入 TRAE Trial Scheduling**（15 个源） |
| M3C-2D-MSIR-Fix | Microsoft IR url_backlog，探索替代入口（SEC EDGAR 等） |
| M3C-4 | 基于 trial 结果，配置正式 TRAE production 调度 |

---

## 10. 边界规则

- 不纳入 92 个全量源
- 不调度 blocked/high-risk 源
- 不调度 search provider 默认
- 不配置最终 production TRAE 任务
- 不提交 data/
- 不恢复已删除 Dashboard 页面

## 11. M3C-3: TRAE Trial Scheduling 接入

M3C-3 已完成。详细报告见 `docs/foundation_trae_trial_schedule_report.md`。

### 接入的 Trial Jobs（6 个 Windows Task Scheduler jobs）

| job | 调度时间 | 命令 |
|---|---|---|
| `OPC_Foundation_Trial_Morning_Run` | 08:10 daily | `run_foundation_trial_sources.ps1 -Mode run` |
| `OPC_Foundation_Trial_Morning_Check` | 08:25 daily | `check_foundation_trial_sources.ps1` |
| `OPC_Foundation_Trial_Afternoon_Run` | 13:10 daily | `run_foundation_trial_sources.ps1 -Mode run` |
| `OPC_Foundation_Trial_Evening_Run` | 20:10 daily | `run_foundation_trial_sources.ps1 -Mode run` |
| `OPC_Foundation_Trial_Evening_Check` | 20:25 daily | `check_foundation_trial_sources.ps1` |
| `OPC_Foundation_Trial_Daily_Status` | 23:50 daily | `run_foundation_trial_sources.ps1 -Mode dry-run` |

### Setup/Cleanup 脚本

```powershell
# 预览（不实际创建）
powershell -ExecutionPolicy Bypass -File scripts/setup_foundation_trial_schedule.ps1 -Mode dry-run

# 创建 jobs
powershell -ExecutionPolicy Bypass -File scripts/setup_foundation_trial_schedule.ps1 -Mode setup

# 列出当前 jobs
powershell -ExecutionPolicy Bypass -File scripts/setup_foundation_trial_schedule.ps1 -Mode list

# 暂停 jobs
powershell -ExecutionPolicy Bypass -File scripts/remove_foundation_trial_schedule.ps1 -Action disable

# 删除 jobs
powershell -ExecutionPolicy Bypass -File scripts/remove_foundation_trial_schedule.ps1 -Action delete
```

### Rollback

暂停/删除 trial jobs 不影响：
- source inventory（92 源不受影响）
- production research archive
- blocked 源策略
- Dashboard
