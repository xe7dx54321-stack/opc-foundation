# OPC Foundation M3C-Cleanup — 合并分支与清理 Worktree 报告

**执行时间**: 2026-07-04
**master 起始 commit**: `c6bc2c0`
**master 最终 commit**: `fe9c316`
**执行路径**: `/Users/apple/Documents/一人公司OPC/opc-foundation`

---

## 1. 执行前状态

- **master path**: `/Users/apple/Documents/一人公司OPC/opc-foundation`
- **starting master commit**: `c6bc2c0`
- **origin/master**: `c6bc2c0`
- **git status**: clean
- **9 源 observation 是否已完成**: 是（2026-07-04 全天 4 批次成功）

---

## 2. M3C-5B1.4 收口

- **observation_status**: `completed_24h`
- **morning_run**: 2026-07-04 09:03:24, source_count=9, success
- **afternoon_run**: 2026-07-04 15:03:13, source_count=9, success
- **evening_run**: 2026-07-04 21:03:15, source_count=9, success
- **daily_check**: 2026-07-04 21:32:13, success
- **failed_queue**: 0
- **gelonghui coverage**: 3/3 batches（morning/afternoon/evening）
- **当日 source_health 增量**: +27（3 批次 × 9 源）
- **累计 source_health**: 75 条

---

## 3. 合并分支

| 分支 | commit | 是否合并 | 冲突 |
|---|---|---|---|
| feature/m3c-5b2-goldman-podcasts-feed-spike | f2cd7cc | 是 | 无 |
| feature/m3c-6a-source-coverage-reaudit | afe0b8d | 是 | 无 |

### 3.1 B2 合并内容

- `docs/foundation_m3c_5b2_goldman_podcasts_feed_spike_report.md` — Goldman Podcasts feed 探测报告
- `scripts/discover_goldman_sachs_podcasts_feed.py` — 静态入口探测脚本
- `tests/source_inventory/test_goldman_podcasts_feed_discovery.py` — 459 个测试
- 更新 `docs/foundation_source_adapter_roadmap.md` 和 `foundation_source_repair_backlog.md`

**结论**: Goldman podcasts 静态 feed / sitemap / JSON-LD / OG 均不可行，进入 `browser_like_backlog`。

### 3.2 6A 合并内容

- `configs/foundation_source_coverage_reaudit.example.yaml` — 92 源 coverage 配置
- `docs/foundation_m3c_6a_source_coverage_reaudit_report.md` — Coverage reaudit 报告
- `docs/foundation_source_coverage_roadmap.md` — Coverage 路线图
- `src/opc_foundation/source_inventory/coverage_reaudit.py` — Coverage reaudit 模块
- `tests/source_inventory/test_source_coverage_reaudit.py` — 553 个测试

**结论**: 92 源分层 coverage roadmap 已完成。

---

## 4. 合并后状态

- **current master commit**: `fe9c316`
- **origin/master**: `fe9c316`
- **trial_v2 source_count**: 9
- **current 9 sources**:
  - barclays_our_insights
  - markets_insider
  - china_fund_news
  - wind_public
  - goldman_sachs_insights
  - business_insider
  - cls_cn  
  - zhitong_caijing
  - gelonghui
- **goldman_sachs_podcasts 状态**: browser_like_backlog（B2 结论）
- **coverage short_term count**: 36（6A 统计）
- **coverage mid_term count**: 74（6A 统计）

---

## 5. 测试结果

| 测试套件 | 结果 |
|---|---|
| tests/source_inventory | 590 passed |
| tests/scripts | 113 passed |
| tests/dashboard | 270 passed |
| full pytest | **1937 passed, 9 failed** |

**注意**: 9 个失败全部位于 `tests/test_url_text_extractor.py`，失败原因为 `example.com` 解析到被阻止的 IP（`198.18.0.22`），属于测试环境网络限制，与本次 merge 无关。

---

## 6. Worktree 清理

### 6.1 清理前 worktree 列表

| worktree path | branch | status | merged? | action |
|---|---|---|---|---|
| `/Users/apple/Documents/一人公司OPC/opc-foundation` | master | clean | — | **保留（主仓库）** |
| `/Users/apple/Documents/一人公司OPC/opc-foundation-m3c-5a10-sidecar` | feature/m3c-5a10-sidecar-trial-v2-status | clean | 是 | 待删除 |
| `/Users/apple/Documents/一人公司OPC/opc-foundation-m3c-5b0-repair-backlog` | feature/m3c-5b0-source-repair-backlog | clean | 是 | 待删除 |
| `/Users/apple/Documents/一人公司OPC/opc-foundation-m3c-5b1-1a-gelonghui-date` | feature/m3c-5b1-1a-gelonghui-date-repair | clean | 是 | 待删除 |
| `/Users/apple/Documents/一人公司OPC/opc-foundation-m3c-5b1-3-expand-9` | feature/m3c-5b1-3-expand-trial-v2-to-9 | clean | 是 | 待删除 |
| `/Users/apple/Documents/一人公司OPC/opc-foundation-m3c-5b1-p0-repair` | feature/m3c-5b1-p0-source-repair | clean | 是 | 待删除 |
| `/Users/apple/Documents/一人公司OPC/opc-foundation-m3c-5b2-gs-podcasts` | feature/m3c-5b2-goldman-podcasts-feed-spike | clean | 是 | 待删除 |
| `/Users/apple/Documents/一人公司OPC/opc-foundation-m3c-6a-coverage` | feature/m3c-6a-source-coverage-reaudit | clean | 是 | 待删除 |

### 6.2 清理后 worktree 列表

| worktree path | branch | status | action |
|---|---|---|---|
| `/Users/apple/Documents/一人公司OPC/opc-foundation` | master | clean | **保留（主仓库）** |

其余 7 个历史 worktree 已全部通过 `git worktree remove` 安全删除，并执行 `git worktree prune` 清理。

---

## 7. 本地分支清理

### 7.1 清理前已合并分支

- `feature/m3c-5a10-sidecar-trial-v2-status`
- `feature/m3c-5b0-source-repair-backlog`
- `feature/m3c-5b1-1-next-candidate-preflight`
- `feature/m3c-5b1-1a-gelonghui-date-repair`
- `feature/m3c-5b1-2-gelonghui-9-source-preflight`
- `feature/m3c-5b1-3-expand-trial-v2-to-9`
- `feature/m3c-5b1-p0-source-repair`

### 7.2 保留分支

- `master` — 主分支
- 远程分支保留（origin/*）

---

## 8. 边界确认

| 检查项 | 结果 |
|---|---|
| 是否修改 TRAE scheduling | 否 |
| 是否修改 TRAE local config | 否 |
| 是否修改 trial_v2 allowlist | 否（仍为 9 源） |
| 是否配置 production | 否 |
| 是否提交 data/local/secrets | 否 |
| 是否引入 Playwright/Selenium | 否 |
| 是否恢复已删除 Dashboard 页面 | 否 |
| 是否打 tag | 否 |

---

## 9. 下一步建议

- **是否进入 M3C-6B**: 是（6A coverage roadmap 已完成，可进入 6B 批量修复）
- **M3C-6B 候选**: 36 个 short_term usable 源中筛选高价值候选
- **是否继续暂缓 merck_ir**: 是（当前 allowlist 9 源稳定，merck_ir 保持 next_scheduling_candidate）
- **是否继续暂缓 production**: 是（production_enabled 仍为 false）
