# OPC Foundation M3C-5Merge Report

**合并时间**: 2026-07-03
**合并前 master commit**: `53bff8d`
**合并后 master commit**: `72d952c`
**执行路径**: `/Users/apple/Documents/一人公司OPC/opc-foundation`

---

## 1. 合并前状态

- **master path**: `/Users/apple/Documents/一人公司OPC/opc-foundation`
- **master pre-merge commit**: `53bff8d`
- **git status**: clean
- **24h observation 是否通过**: 是（2026-07-03 morning/afternoon/evening/daily_check 全部成功）

---

## 2. 合并分支

| 分支 | commit | 是否合并 | 冲突 |
|---|---|---|---|
| feature/m3c-5a10-sidecar-trial-v2-status | def7ae6 | 是 | 无 |
| feature/m3c-5b0-source-repair-backlog | cb8deeb | 是 | 无 |
| feature/m3c-5b1-p0-source-repair | d4f661e | 是 | 无 |

**合并顺序**: sidecar -> B0 -> B1

**合并方式**: `git merge --no-ff`（保留分支历史）

---

## 3. 24h observation 固化

- **observation_status**: `completed_24h`
- **morning_run**: 2026-07-03 09:02，成功，8 源 × 8 records
- **afternoon_run**: 2026-07-03 15:01，成功，8 源 × 8 records
- **evening_run**: 2026-07-03 21:01，成功，8 源 × 8 records
- **daily_check**: 2026-07-03 21:32，成功
- **source_health**: 48 条记录（累计）
- **run_log**: 48 条记录（累计）
- **failed_queue**: 0 条记录（始终为空）

---

## 4. Post-merge smoke test

### 4.1 pytest 全量测试

| 测试套件 | 结果 |
|---|---|
| tests/source_inventory | 366 passed |
| tests/scripts | 113 passed |
| tests/dashboard | 270 passed |
| full pytest | **1754 passed, 0 failed** |

### 4.2 Allowlist 静态检查

- **原 8 源 allowlist 是否不变**: 是
- **gelonghui / merck_ir 是否未加入 allowlist**: 是
- **goldman_sachs_podcasts 是否未加入 allowlist**: 是

当前 allowlist 8 源：
```
barclays_our_insights, markets_insider, china_fund_news, wind_public,
goldman_sachs_insights, business_insider, cls_cn, zhitong_caijing
```

### 4.3 PowerShell 脚本检查（macOS 环境，仅验证文件存在）

- `scripts/run_foundation_trial_v2_content_ready.ps1`: 存在
- `scripts/check_foundation_trial_v2_content_ready.ps1`: 存在
- `scripts/run_foundation_content_validity_audit.ps1`: 存在
- `scripts/check_foundation_content_validity_audit.ps1`: 存在

---

## 5. 合并后新增内容摘要

### sidecar 分支（M3C-5A10-sidecar）
- `src/opc_foundation/dashboard/trial_v2_status.py` — trial_v2 只读状态加载器
- `scripts/generate_daily_status_report.py` — 增加 Foundation Trial V2 Content Ready section
- `src/opc_foundation/dashboard/app.py` — Control Center 增加 trial_v2 状态卡片
- 新增 14 个 dashboard/scripts 测试

### B0 repair backlog（M3C-5B0）
- `configs/foundation_source_repair_backlog.example.yaml` — 28 源修复 backlog 配置
- `src/opc_foundation/source_inventory/repair_backlog.py` — RepairBacklog 数据模型
- `docs/foundation_source_repair_backlog.md` — 修复 backlog 文档
- `docs/foundation_source_adapter_roadmap.md` — 适配器路线图
- 新增 38 个 source_inventory 测试

### B1 P0 source repair（M3C-5B1）
- `src/opc_foundation/source_inventory/content_validity.py` — gelonghui / merck_ir 修复
- `configs/foundation_source_inventory.example.yaml` — merck_ir URL 更新
- `configs/foundation_source_repair_backlog.example.yaml` — P0 修复状态更新
- `docs/source_validation/gelonghui.md` — 格隆汇验证报告
- `docs/source_validation/merck_ir.md` — Merck IR 验证报告
- `docs/source_validation/goldman_sachs_podcasts.md` — GS Podcasts 不可修复说明
- `docs/foundation_p0_source_repair_report.md` — P0 修复总报告
- 新增 32 个 P0 修复边界测试

---

## 6. 边界确认

| 边界项 | 结果 |
|---|---|
| 是否修改 TRAE scheduling | 否 |
| 是否修改 trial_v1 | 否 |
| 是否修改 trial_v2 allowlist | 否（仍为 8 源） |
| 是否配置 production | 否 |
| 是否提交 data/local/secrets | 否 |
| 是否引入 Playwright/Selenium | 否 |
| 是否恢复已删除 Dashboard 页面 | 否 |
| 是否打 tag | 否 |

---

## 7. Commit / Push

- **merge 后 master commit**: `72d952c`
- **docs commit**: 待提交（24h observation 更新 + merge report）
- **origin/master**: 待 push
- **git status**: 有 docs 修改未提交

---

## 8. 下一步建议

- **是否进入 M3C-5B1.1**: 否（当前建议保持稳定，观察已修复源的持续表现）
- **preflight candidates**: gelonghui, merck_ir（已标记为 next_scheduling_candidate）
- **是否暂缓 production**: 是（production_enabled 仍为 false，暂不开启）
- **建议后续动作**:
  1. 持续观察 8 源 trial_v2 自动调度稳定性
  2. 监控 wind_public garbled_text 情况
  3. 待下一批次 preflight 时评估 gelonghui / merck_ir 是否加入 allowlist
  4. M3C-5B2 browser-like spike 待规划（goldman_sachs_podcasts 等 JS 渲染源）
