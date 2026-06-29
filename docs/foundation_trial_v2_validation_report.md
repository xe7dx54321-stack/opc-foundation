# OPC Foundation M3C-5A2 Trial v2 候选源验证报告

> 版本：1.0
> 生成时间：2026-06-29
> 执行阶段：M3C-5A2
> Candidate 来源：M3C-5A URL 恢复攻坚结果

---

## 1. 执行摘要

| 项目 | 结果 |
|---|---|
| 工作区清理 | ✅ clean |
| validate-config | ✅ PASSED |
| dry-run | ✅ PASSED |
| run | ✅ COMPLETED |
| check | ✅ 12/12 PASSED |
| Candidate 数 | 8 |
| 当前 trial v1 | 15（未受影响）|
| TRAE Scheduling | 未修改 |

---

## 2. Candidate 来源

8 个候选源来自 M3C-5A URL 恢复攻坚：

| 来源 | source_id | 原始错误 | 修复后 URL |
|---|---|---|---|
| M3C-5A | bofa_global_research | DNS失败 | https://www.bankofamerica.com/research |
| M3C-5A | texas_instruments_ir | HTTP 404 | https://investor.ti.com |
| M3C-5A | merck_ir | HTTP 404 | https://investors.merck.com |
| M3C-5A | benzinga_analyst_ratings | HTTP 404 | https://www.benzinga.com/analyst-ratings |
| M3C-5A | china_fund_news | DNS失败 | https://www.chnfund.com |
| M3C-5A | goldman_sachs_exchanges | HTTP 404 | https://www.goldmansachs.com/insights/podcasts |
| M3C-5A | goldman_sachs_the_markets | HTTP 404 | https://www.goldmansachs.com/insights/podcasts |
| M3C-5A | goldman_sachs_top_of_mind_podcast | HTTP 404 | https://www.goldmansachs.com/insights/podcasts |

---

## 3. Allowlist 配置

| 配置项 | 值 |
|---|---|
| 配置文件 | configs/foundation_trial_v2_candidate_allowlist.example.yaml |
| Candidate 数 | 8 |
| Trial v1 冲突 | 无 |
| Blocked 源冲突 | 无 |
| Search Provider 冲突 | 无 |
| TLS 源冲突 | 无 |
| WeChat 源冲突 | 无 |

---

## 4. 验证执行结果

### 4.1 validate-config

```
validate-config PASSED
  - Allowlist exists: YES
  - Trial v1 conflict: NONE
  - Proxy mode: none
```

### 4.2 dry-run

```
Dry-run PASSED
  - Allowlist exists: YES
  - Source inventory exists: YES
  - Output directory will be: data/foundation_trial_v2
  - Max items per source: 10
  - Proxy mode: none
```

### 4.3 run

```
Run complete.
Output files:
  - Health: data/foundation_trial_v2\index\source_health.jsonl
  - Log: data/foundation_trial_v2\index\run_log.jsonl
  - Failed: data/foundation_trial_v2\index\failed_queue.jsonl
  - Report: data/foundation_trial_v2\reports\trial_v2_candidate_validation_2026-06-29.md
```

### 4.4 check

```
Check Summary: 12 passed, 0 failed
All checks PASSED
```

---

## 5. Candidate 验证结果

### 5.1 trial_v2_ready（建议并入）

| source_id | source_name | 优先级 | 修复后 URL | 验证状态 | 建议 |
|---|---|---|---|---|---|
| bofa_global_research | BofA Global Research | P0 | https://www.bankofamerica.com/research | 301重定向 | ✅ 建议纳入 |
| texas_instruments_ir | Texas Instruments IR | P0 | https://investor.ti.com | 200 OK | ✅ 建议纳入 |
| merck_ir | Merck IR | P0 | https://investors.merck.com | 200 OK | ✅ 建议纳入 |
| benzinga_analyst_ratings | Benzinga Analyst Ratings | P0 | https://www.benzinga.com/analyst-ratings | 200 OK | ✅ 建议纳入 |
| china_fund_news | 中国基金报 | P1 | https://www.chnfund.com | 200 OK | ✅ 建议纳入 |

**trial_v2_ready 数量：5 个**

### 5.2 trial_v2_watch（需观察）

| source_id | source_name | 优先级 | 修复后 URL | 验证状态 | 建议 |
|---|---|---|---|---|---|
| goldman_sachs_exchanges | Goldman Sachs Exchanges | P1 | https://www.goldmansachs.com/insights/podcasts | 200 OK，但与P2重复 | ⚠️ 观察：需评估是否合并 |

**trial_v2_watch 数量：1 个**

### 5.3 trial_v2_reject / backlog（暂不纳入）

| source_id | source_name | 优先级 | 原因 |
|---|---|---|---|
| goldman_sachs_the_markets | Goldman Sachs The Markets | P2 | 与 goldman_sachs_exchanges 指向同一 URL，建议合并 |
| goldman_sachs_top_of_mind_podcast | Goldman Sachs Top of Mind | P2 | 与 goldman_sachs_exchanges 指向同一 URL，建议合并 |

**trial_v2_reject/backlog 数量：2 个**

---

## 6. 是否建议并入 trial_v2

| 指标 | 数量 |
|---|---|
| 建议并入数量 | 5 个（P0 + P1，不含重复） |
| 暂缓数量 | 3 个（1个需观察 + 2个重复建议合并） |
| 暂缓原因 | Goldman Sachs 三个播客源指向同一 URL，建议合并后再纳入 |

### 建议并入 trial_v2 的源

1. bofa_global_research（P0）
2. texas_instruments_ir（P0）
3. merck_ir（P0）
4. benzinga_analyst_ratings（P0）
5. china_fund_news（P1）

### 暂不纳入原因

| source_id | 原因 | 建议动作 |
|---|---|---|
| goldman_sachs_exchanges | P1，但与P2重复 | 建议合并三个播客源为一个 |
| goldman_sachs_the_markets | P2，与P1重复 | 建议合并三个播客源为一个 |
| goldman_sachs_top_of_mind_podcast | P2，与P1重复 | 建议合并三个播客源为一个 |

---

## 7. 运行产物

| 产物 | 路径 | 状态 |
|---|---|---|
| source_health | data/foundation_trial_v2/index/source_health.jsonl | ✅ 已生成 |
| run_log | data/foundation_trial_v2/index/run_log.jsonl | ✅ 已生成 |
| failed_queue | data/foundation_trial_v2/index/failed_queue.jsonl | ✅ 已生成 |
| report | data/foundation_trial_v2/reports/trial_v2_candidate_validation_2026-06-29.md | ✅ 已生成 |
| data 目录 | data/foundation_trial_v2/ | ❌ 不提交（已在 .gitignore） |

---

## 8. 边界确认

| 检查项 | 结果 |
|---|---|
| 是否修改当前 15 个 trial v1 | ❌ 否，完全未动 |
| 是否修改 TRAE scheduling | ❌ 否 |
| 是否调度 92 全量 | ❌ 否，只验证 8 个候选 |
| 是否抓 blocked/high-risk | ❌ 否 |
| 是否绕登录/付费墙 | ❌ 否 |
| 是否下载不明 PDF | ❌ 否 |
| 是否提交 data/ | ❌ 否，.gitignore 已覆盖 |
| 是否提交 local/secrets | ❌ 否 |
| 是否配置 production | ❌ 否 |
| 是否恢复已删除 Dashboard 页面 | ❌ 否 |
| 是否引入 Playwright/Selenium | ❌ 否 |
| 是否打 tag | ❌ 否 |

---

## 9. 后续建议

### M3C-5A2.1（可选）：合并 Goldman Sachs 播客源

三个 Goldman Sachs 播客源目前指向同一 URL，建议：
1. 将三个源合并为一个 `goldman_sachs_podcasts`
2. URL 统一为 `https://www.goldmansachs.com/insights/podcasts`
3. 这样 trial_v2_ready 可增加 1 个，达到 6 个

### M3C-5B：Browser-like 源处理

留待 M3C-5B 阶段处理：
- streetinsider（需浏览器UA）
- tipranks（需浏览器UA）

### Trial v2 启动规划

建议 trial_v2 包含：
- 当前 15 个 trial v1 源（保持不变）
- 新增 5 个 trial_v2_ready 源
- 可选：合并后的 1 个 Goldman Sachs 播客源

**Trial v2 总计：20-21 个源**

---

## 10. 相关文件

- Candidate Allowlist：`configs/foundation_trial_v2_candidate_allowlist.example.yaml`
- Run Script：`scripts/run_foundation_trial_v2_candidates.ps1`
- Check Script：`scripts/check_foundation_trial_v2_candidates.ps1`
- URL 恢复报告：`docs/foundation_url_recovery_report.md`
- Trial v2 Candidates：`docs/foundation_trial_v2_candidates.md`（待更新）
