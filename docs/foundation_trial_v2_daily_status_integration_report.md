# OPC Foundation Trial V2 Content-Ready Daily Status Integration Report

> 阶段：M3C-5A10-sidecar
> 执行时间：2026-07-02
> 分支：feature/m3c-5a10-sidecar-trial-v2-status
> 目标：Trial V2 Content Ready Daily Status / Control Center 只读接入

---

## 1. Worktree 信息

- **原始 master 路径**：`opc-foundation`（master 分支，HEAD=53bff8d）
- **sidecar worktree 路径**：`opc-foundation-m3c-5a10-sidecar`（feature/m3c-5a10-sidecar-trial-v2-status 分支）
- **原 master 工作目录是否保持不动**：是（通过 git worktree 隔离）

---

## 2. 接入的数据目录

```
data/foundation_trial_v2_content_ready/index/source_health.jsonl
data/foundation_trial_v2_content_ready/index/run_log.jsonl
data/foundation_trial_v2_content_ready/index/failed_queue.jsonl
data/foundation_trial_v2_content_ready/reports/trial_v2_content_ready_validation_latest.md
data/foundation_trial_v2_content_ready/index/preflight_content_ready_audit.jsonl
```

---

## 3. Daily Status 接入

### 3.1 新增 Section

`scripts/generate_daily_status_report.py` 新增 **Foundation Trial V2 Content Ready** section。

### 3.2 展示字段

- source_count
- last_run_at
- latest_run_id
- success_count
- failed_count
- content_ready_count
- content_watch_count
- content_reject_count
- technical_only_count
- failed_queue_count
- production_enabled=false
- observation_status
- wind_public_watch_flag
- wind_public_garbled_text_observed

### 3.3 Fail-Soft 行为

- data 目录不存在：显示"尚未运行"，observation_status=not_started
- source_health 不存在：不报错
- failed_queue 为空：failed_queue_count=0

---

## 4. Control Center 接入

### 4.1 新增只读卡片

`src/opc_foundation/dashboard/app.py` 健康监控页面新增 **Foundation Trial V2 Content Ready** 只读卡片。

展示：
- 8 源 trial_v2
- 最近运行时间
- 成功/失败数
- Failed Queue
- Production=false
- Observation status（颜色编码）
- wind_public watch flag（高亮）

### 4.2 Fail-Soft

- data 不存在：显示"尚未运行 (not_started)"
- 不因缺数据导致 Streamlit 崩溃

---

## 5. Observation Status 判定逻辑

```text
not_started:
  data/foundation_trial_v2_content_ready/ 不存在，或无 run 记录

partial_observation:
  有 run 记录，但不足 morning + afternoon + evening + daily_check

completed_24h:
  检测到同一观察窗口内包含 morning + afternoon + evening + daily_check
```

缺证据时保持 partial_observation，不得伪造 completed_24h。

---

## 6. Wind Public Watch 行为

- wind_public_watch_flag：从 preflight audit 数据和 latest report 中检测
- garbled_text_observed：检测 noise_flags 中是否包含 garbled_text，或 report 中是否出现 garbled/乱码
- 若 valid/relevant candidate < 2，应降级为 content_watch

---

## 7. 边界确认

| 检查项 | 结果 |
|---|---|
| 是否修改 run/check 脚本 | 否 |
| 是否修改 TRAE scheduling | 否 |
| 是否修改 trial_v1 | 否 |
| 是否配置 production | 否 |
| 是否提交 data/local/secrets | 否 |
| 是否影响明天自动任务 | 否（worktree 隔离） |
| 是否恢复已删除 Dashboard 页面 | 否 |
| 是否引入 Playwright/Selenium | 否 |
| 是否打 tag | 否 |

---

## 8. 修改文件清单

- `src/opc_foundation/dashboard/trial_v2_status.py`（新增）
- `scripts/generate_daily_status_report.py`（修改）
- `src/opc_foundation/dashboard/app.py`（修改）
- `docs/foundation_trial_v2_daily_status_integration_report.md`（新增）
- `tests/dashboard/test_trial_v2_content_ready_runtime.py`（新增）
- `tests/scripts/test_daily_status_trial_v2_content_ready.py`（新增）
