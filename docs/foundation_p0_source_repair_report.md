# Foundation P0 Source Repair Report

**M3C-5B1 执行时间**: 2026-07-03
**Worktree 路径**: `/Users/apple/Documents/一人公司OPC/opc-foundation-m3c-5b1-p0-repair`
**Branch**: `feature/m3c-5b1-p0-source-repair`
**Base Branch**: `feature/m3c-5b0-source-repair-backlog`
**Commit Hash**: `c54173a`

---

## 1. Worktree / Branch

- **原始 master 路径**: `/Users/apple/Documents/一人公司OPC/opc-foundation`
- **B1 worktree 路径**: `/Users/apple/Documents/一人公司OPC/opc-foundation-m3c-5b1-p0-repair`
- **Branch**: `feature/m3c-5b1-p0-source-repair`
- **Base Branch**: `feature/m3c-5b0-source-repair-backlog`
- **是否影响 TRAE 原工作目录**: 否（master 保持 53bff8d，clean）

---

## 2. 修改文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/opc_foundation/source_inventory/content_validity.py` | 修改 | gelonghui selector + noise filter + relevance fix; merck_ir noise filter |
| `configs/foundation_source_inventory.example.yaml` | 修改 | merck_ir URL 更新为 `www.merck.com/investor-relations/` |
| `configs/foundation_source_repair_backlog.example.yaml` | 修改 | 新增 `p0_repaired_ready` / `browser_like_backlog` 分类，更新 3 个 P0 源状态 |
| `docs/foundation_source_repair_backlog.md` | 修改 | 新增 P0 repaired ready 章节，调整计数 |
| `docs/foundation_source_adapter_roadmap.md` | 修改 | Route 1/2/3 更新 M3C-5B1 结果 |
| `tests/source_inventory/test_source_repair_backlog.py` | 修改 | 补充 `repaired` / `next_scheduling_candidate` 合法值 |
| `docs/source_validation/gelonghui.md` | 新增 | 格隆汇真实验证报告 |
| `docs/source_validation/goldman_sachs_podcasts.md` | 新增 | GS Podcasts 不可修复说明 |
| `docs/source_validation/merck_ir.md` | 新增 | Merck IR 真实验证报告 |
| `tests/source_inventory/test_p0_source_repair.py` | 新增 | 32 个 P0 修复边界测试 |

---

## 3. 逐源修复结果

| source_id | 修复前 | 修复后 | content_score | 是否 content_ready | 真实样本数 | 下一步 |
|-----------|--------|--------|--------------:|-------------------:|----------:|--------|
| gelonghui | content_watch (noise_filter_issue) | content_ready | 90 | 是 | 5 | next_scheduling_candidate |
| merck_ir | technical_only (http_403_or_forbidden) | content_ready | 90 | 是 | 5 | next_scheduling_candidate |
| goldman_sachs_podcasts | content_watch (consolidated_modeling_issue) | browser_like_candidate | 60 | 否 | 5 (nav noise) | M3C-5B2 browser-like spike |

---

## 4. 真实样本摘要

### gelonghui

```text
[1] 暴跌7.5%！特斯拉Q2交付大捷，市场为何不买账？ | https://www.gelonghui.com/p/5436380.html | rel=high
[2] AI芯片泡沫，真要破了吗？ | https://www.gelonghui.com/p/5432471.html | rel=high
[3] 德国大刀阔斧改革！提高退休年龄、对高收入者加税 | https://www.gelonghui.com/p/5435047.html | rel=high
[4] 李迅雷：判断泡沫破灭看这三个信号 | https://www.gelonghui.com/p/5434198.html | rel=high
[5] 但斌最新演讲：不要错失一个伟大的时代 | https://www.gelonghui.com/p/5433960.html | rel=high
```

- 全部 5 条为 `/p/` 文章链接，标题完整
- 已过滤：登录、注册、App 下载、广告、导航、搜索、隐私政策、免责声明等噪音
- 显式设置 `content_type=news` / `relevance=high`（绕过英文-only 分类器）

### merck_ir

```text
[1] Merck to Hold Second-Quarter 2026 Sales and Earnings Conference Call | https://www.merck.com/news/merck-to-hold-second-quarter-2026 | rel=high
[2] Merck Announces New Agreement with ADAP Crisis Task Force to Increase Access to HIV Medicines | https://www.merck.com/news/merck-announces-new-agreement-wit | rel=high
[3] FDA Approves KEYTRUDA® (pembrolizumab) ... | https://www.merck.com/news/fda-approves-keytruda-pembrolizum | rel=high
[4] 47th Annual Goldman Sachs Global Healthcare Conference | https://www.merck.com/events/47th-annual-goldman-sachs-globa | rel=medium
[5] Jefferies Global Healthcare Conference | https://www.merck.com/events/jefferies-global-healthcare-con | rel=medium
```

- 3 条 high relevance（新闻稿），2 条 medium（投资者会议）
- 已过滤："See full agenda", "Icons /", "MicrophoneWebcast" 等导航噪音
- URL 保持 source_id=merck_ir 不变

### goldman_sachs_podcasts

```text
[1] ASSET & WEALTH MANAGEMENT | https://www.goldmansachs.com/what-we-do/investment-banking | rel=medium
[2] ASSET & WEALTH MANAGEMENT | https://www.goldmansachs.com/what-we-do/ficc-and-equities | rel=medium
[3] ASSET & WEALTH MANAGEMENT | https://marquee.gs.com/welcome/ | rel=medium
[4] ASSET & WEALTH MANAGEMENT | https://www.goldmansachs.com/what-we-do/transaction-banking | rel=medium
[5] PLATFORM SOLUTIONS | https://www.gsiam.com/ | rel=medium
```

- 全部为业务板块导航卡片，无 SSR episode 内容
- 无发现 RSS / Atom / JSON-LD podcast feed
- 结论：本轮无法修复，需浏览器渲染（M3C-5B2）

---

## 5. 新 content validity 统计

| 分类 | 数量 | 说明 |
|------|------|------|
| content_ready (trial_v2 scheduled) | 8 | 原有 8 源，未变动 |
| p0_repaired_ready | 2 | gelonghui, merck_ir（下一轮 scheduling candidate） |
| content_watch | 4 | GS research/reports/top_of_mind/podcasts |
| content_reject | 2 | briefing_com_upgrades, wallstreet_cn |
| technical_only | 5 | yahoo_finance, the_fly, benzinga, bofa, ti_ir |
| browser_like_backlog | 1 | goldman_sachs_podcasts |
| matrix_uncategorized | 71 | 未审计 |
| **总计** | **92** | — |

---

## 6. Scheduling 建议

- **新增 next_scheduling_candidate**: gelonghui, merck_ir
- **是否修改 trial_v2 allowlist**: 否
- **是否建议进入下一批 preflight**: 是（gelonghui、merck_ir 可作为下一批 trial_v2 候选）
- **暂缓源及原因**:
  - goldman_sachs_podcasts: 需浏览器渲染，归入 M3C-5B2
  - GS research/reports/top_of_mind: 同为 JS 渲染，归入 M3C-5B2

---

## 7. 测试结果

| 测试套件 | 结果 |
|----------|------|
| tests/source_inventory | 全部通过（含 32 个新增 P0 测试） |
| tests/scripts | 全部通过 |
| tests/dashboard | 全部通过 |
| full pytest | **1735 passed, 0 failed** |

---

## 8. 边界确认

| 边界项 | 结果 |
|--------|------|
| 是否实际修改 master | 否 |
| 是否修改 TRAE scheduling | 否 |
| 是否修改 trial_v1 | 否 |
| 是否修改 trial_v2 allowlist | 否（8 源未变） |
| 是否配置 production | 否 |
| 是否提交 data/local/secrets | 否 |
| 是否引入 Playwright/Selenium | 否 |
| 是否打 tag | 否 |
| 是否恢复总览/运行日志/失败队列/文档入口 | 否 |

---

## 9. Commit 信息

- **Branch commit hash**: `c54173a`
- **Push branch**: `feature/m3c-5b1-p0-source-repair`
- **git status**: clean
- **是否 merge master**: 否

---

## 10. 是否建议等待 24h 自动运行汇报后再 merge

- **建议**: yes
- **原因**:
  1. 当前 master 的 8 源 trial_v2 仍在 24h 观察周期内（M3C-5A10）。
  2. B1 分支只修 P0 源，未影响 trial_v2 allowlist 或 TRAE 调度，技术上与 master 无冲突。
  3. 但为保持阶段清晰，建议待 M3C-5A10 的 24h 完整运行日志确认 8 源稳定后，再将 B1 分支合并回 master。
  4. B1 分支中的 2 个 content_ready 源（gelonghui、merck_ir）已标记为 `next_scheduling_candidate`，可在下一轮 preflight 中直接评估。
