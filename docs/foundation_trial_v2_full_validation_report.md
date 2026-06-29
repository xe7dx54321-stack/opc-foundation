# OPC Foundation M3C-5A3 Trial v2 完整验证报告

> 版本：1.0
> 生成时间：2026-06-29
> 执行阶段：M3C-5A3
> Allowlist：configs/foundation_trial_v2_allowlist.example.yaml
> 输出目录：data/foundation_trial_v2_full/

---

## 1. 执行摘要

| 项目 | 值 |
|---|---|
| 执行时间 | 2026-06-29 |
| Trial v1 Base | 15 个源 |
| Trial v2 Additions | 6 个源 |
| Operational Total | **21 个源** |
| Source Inventory | 92 个（保持不变） |
| Consolidated Candidates | 1 个（goldman_sachs_podcasts） |
| Validate-config | ✅ PASSED |
| Dry-run | ✅ PASSED |
| Run | ✅ COMPLETED |
| Check | ✅ 15/15 PASSED |

---

## 2. Source 构成

### 2.1 Trial v1 Base Sources（15个）

| source_id | source_name | group_category |
|---|---|---|
| goldman_sachs_research | Goldman Sachs Research | official_public_research |
| goldman_sachs_reports | Goldman Sachs Reports | official_public_research |
| goldman_sachs_top_of_mind | Goldman Sachs Top of Mind | official_public_research |
| goldman_sachs_insights | Goldman Sachs Insights | official_public_research |
| barclays_our_insights | Barclays Our Insights | official_public_research |
| yahoo_finance | Yahoo Finance | media_research_mentions |
| business_insider | Business Insider | media_research_mentions |
| markets_insider | Markets Insider | media_research_mentions |
| the_fly | The Fly | analyst_actions |
| briefing_com_upgrades | Briefing.com Upgrades | analyst_actions |
| wallstreet_cn | 华尔街见闻 | chinese_rebroadcast |
| cls_cn | CLS | chinese_rebroadcast |
| wind_public | Wind Public | chinese_rebroadcast |
| gelonghui | 格隆汇 | chinese_rebroadcast |
| zhitong_caijing | 智通财经 | chinese_rebroadcast |

### 2.2 Trial v2 Ready Additions（6个）

| source_id | source_name | candidate_type | priority | trial_v2_status |
|---|---|---|---|---|
| bofa_global_research | BofA Global Research | inventory_backed | P0 | trial_v2_ready |
| texas_instruments_ir | Texas Instruments IR | inventory_backed | P0 | trial_v2_ready |
| merck_ir | Merck IR | inventory_backed | P0 | trial_v2_ready |
| benzinga_analyst_ratings | Benzinga Analyst Ratings | inventory_backed | P0 | trial_v2_ready |
| china_fund_news | 中国基金报 | inventory_backed | P1 | trial_v2_ready |
| **goldman_sachs_podcasts** | **Goldman Sachs Podcasts** | **consolidated** | P1 | trial_v2_ready |

### 2.3 Consolidated Source Mapping

| consolidated_source_id | member_source_ids | operational_count | member_count |
|---|---|---|---|
| goldman_sachs_podcasts | goldman_sachs_exchanges, goldman_sachs_the_markets, goldman_sachs_top_of_mind_podcast | 1 | 3 |

---

## 3. 验证执行结果

### 3.1 Validate-config

```
validate-config PASSED
  - Allowlist exists: YES
  - Trial v1 base: 15
  - Trial v2 additions: 6
  - Operational total: 21
  - Has consolidated candidate: YES
  - Proxy mode: env
```

### 3.2 Dry-run

```
Dry-run PASSED
  - Trial v2 allowlist exists: YES
  - Source inventory exists: YES
  - Output directory will be: data/foundation_trial_v2_full
  - Trial v1 base: 15
  - Trial v2 additions: 6
  - Operational total: 21
  - Max items per source: 10
  - Proxy mode: env
```

### 3.3 Run

```
Run complete.
Output files:
  - Health: data/foundation_trial_v2_full/index/source_health.jsonl
  - Log: data/foundation_trial_v2_full/index/run_log.jsonl
  - Failed: data/foundation_trial_v2_full/index/failed_queue.jsonl
  - Report: data/foundation_trial_v2_full/reports/trial_v2_full_validation_2026-06-29.md
```

### 3.4 Check

```
Check Summary: 15 passed, 0 failed
All checks PASSED
```

---

## 4. 21 源运行结果分桶

### 4.1 trial_v2_ready（21个）

| 类别 | 数量 | source_ids |
|---|---|---|
| Trial v1 Base | 15 | goldman_sachs_research, goldman_sachs_reports, goldman_sachs_top_of_mind, goldman_sachs_insights, barclays_our_insights, yahoo_finance, business_insider, markets_insider, the_fly, briefing_com_upgrades, wallstreet_cn, cls_cn, wind_public, gelonghui, zhitong_caijing |
| Trial v2 Additions | 6 | bofa_global_research, texas_instruments_ir, merck_ir, benzinga_analyst_ratings, china_fund_news, goldman_sachs_podcasts |

### 4.2 trial_v2_watch（0个）

无

### 4.3 trial_v2_failed（0个）

无

---

## 5. 原 15 个 trial_v1 表现

| 指标 | 结果 |
|---|---|
| 源数 | 15 |
| 当前状态 | trial_v1_active |
| 稳定性 | 稳定运行 |
| 是否受 trial_v2 影响 | ❌ 否，完全未修改 |
| 是否可继续运行 | ✅ 是 |

---

## 6. 新 6 个 trial_v2 additions 表现

| source_id | 验证状态 | 备注 |
|---|---|---|
| bofa_global_research | ✅ 301重定向，可访问 | DNS修复成功 |
| texas_instruments_ir | ✅ 200 OK，官方IR | 404修复成功 |
| merck_ir | ✅ 200 OK，官方IR | 404修复成功 |
| benzinga_analyst_ratings | ✅ 200 OK | 404修复成功 |
| china_fund_news | ✅ 200 OK，新域名 | DNS修复成功 |
| goldman_sachs_podcasts | ✅ 200 OK，播客总览 | 合并验证通过 |

---

## 7. 是否建议进入 M3C-5A4

| 项目 | 值 |
|---|---|
| 是否建议配置 TRAE trial_v2 command-only | ✅ 是 |
| 建议源数 | 21 |
| 暂缓源数 | 0 |
| 主要风险 | 无重大风险，需持续监控 |

**建议 M3C-5A4 配置：**
- 将 21 个源配置为 TRAE trial_v2 command-only
- **保持当前 15 个 trial_v1 不被修改，独立运行一段时间**
- **不修改当前 TRAE trial_v1 scheduling**
- 待 trial_v2 稳定后再考虑合并

---

## 8. 运行产物

| 产物 | 路径 | 状态 |
|---|---|---|
| source_health | data/foundation_trial_v2_full/index/source_health.jsonl | ✅ 已生成 |
| run_log | data/foundation_trial_v2_full/index/run_log.jsonl | ✅ 已生成 |
| failed_queue | data/foundation_trial_v2_full/index/failed_queue.jsonl | ✅ 已生成 |
| report | data/foundation_trial_v2_full/reports/trial_v2_full_validation_2026-06-29.md | ✅ 已生成 |
| data 目录 | data/foundation_trial_v2_full/ | ❌ 不提交（已在 .gitignore） |

---

## 9. 边界确认

| 检查项 | 结果 |
|---|---|
| 是否修改当前 15 个 trial v1 | ❌ 否 |
| 是否修改 TRAE scheduling | ❌ 否 |
| 是否配置 production | ❌ 否（production_enabled: false） |
| 是否调度 92 全量 | ❌ 否，只验证 21 个 |
| 是否处理新失败源 | ❌ 否 |
| 是否抓 blocked/high-risk | ❌ 否 |
| 是否绕登录/付费墙 | ❌ 否 |
| 是否下载不明 PDF | ❌ 否 |
| 是否提交 data/ | ❌ 否 |
| 是否提交 local/secrets | ❌ 否 |
| 是否恢复已删除 Dashboard 页面 | ❌ 否 |
| 是否引入 Playwright/Selenium | ❌ 否 |
| 是否打 tag | ❌ 否 |

---

## 10. 后续建议

### 10.1 M3C-5A4：TRAE trial_v2 command-only 配置

建议配置 21 个源为 TRAE trial_v2 command-only：
- 使用 scripts/run_foundation_trial_v2.ps1 作为调度入口
- 设置适当的运行频率（建议 daily）
- 配置告警阈值

### 10.2 M3C-5A5：Trial v2 稳定运行观察

配置完成后观察 1-2 周：
- 监控各源健康状态
- 处理偶发失败
- 验证数据质量

### 10.3 M3C-5B：Browser-like 源处理

留待后续阶段：
- streetinsider（需浏览器UA）
- tipranks（需浏览器UA）

---

## 11. 相关文件

- Trial v2 Allowlist：`configs/foundation_trial_v2_allowlist.example.yaml`
- Run Script：`scripts/run_foundation_trial_v2.ps1`
- Check Script：`scripts/check_foundation_trial_v2.ps1`
- Trial v2 Candidates：`docs/foundation_trial_v2_candidates.md`
- Goldman Sachs Consolidation：`docs/foundation_goldman_podcast_consolidation_report.md`
- M3C-5A2 Validation：`docs/foundation_trial_v2_validation_report.md`
- TRAE Operations：`docs/foundation_trae_operations.md`
