# Goldman Sachs Podcast 源合并报告（M3C-5A2.1）

> 版本：1.0
> 生成时间：2026-06-29
> 执行阶段：M3C-5A2.1

---

## 1. 处理摘要

| 项目 | 值 |
|---|---|
| 处理时间 | 2026-06-29 |
| 处理范围 | 3 个 Goldman Sachs podcast 候选源 |
| 合并类型 | Operational consolidation（trial_v2 层面） |
| consolidated candidate | goldman_sachs_podcasts |
| 验证结果 | HTTP 200 OK（browser-like UA） |

---

## 2. 合并范围

### 2.1 原始 Source 信息

| source_id | source_name | 原始 URL | URL 状态 | trial_v2 状态 |
|---|---|---|---|---|
| goldman_sachs_exchanges | Goldman Sachs Exchanges | /podcasts/exchanges | 404 | trial_v2_watch |
| goldman_sachs_the_markets | Goldman Sachs The Markets | /podcasts/the-markets | 404 | trial_v2_reject |
| goldman_sachs_top_of_mind_podcast | Goldman Sachs Top of Mind (Podcast) | /podcasts/top-of-mind | 404 | trial_v2_reject |

### 2.2 合并原因

三个 Goldman Sachs podcast 源的独立节目页面均已 404：
- `/podcasts/exchanges` → 404
- `/podcasts/the-markets` → 404
- `/podcasts/top-of-mind` → 404

M3C-5A 修复时将三个源统一指向播客总览页：
- 修复后 URL：`https://www.goldmansachs.com/insights/podcasts`

**问题**：如果将三个源都并入 trial_v2，会造成：
1. 重复抓取同一页面
2. 重复的健康日志
3. 重复的告警
4. 浪费 trial 调度资源

**解决方案**：在 trial_v2 层面合并为一个 consolidated candidate：`goldman_sachs_podcasts`

---

## 3. Source Inventory 保留情况

### 3.1 原始 Source 处理

**重要**：以下 3 个 source 仍保留在 `configs/foundation_source_inventory.example.yaml`：

| source_id | 是否保留 | 说明 |
|---|---|---|
| goldman_sachs_exchanges | ✅ 保留 | 不删除，不修改 source_id |
| goldman_sachs_the_markets | ✅ 保留 | 不删除，不修改 source_id |
| goldman_sachs_top_of_mind_podcast | ✅ 保留 | 不删除，不修改 source_id |

### 3.2 Source Inventory 总数

- **source 总数**：92（保持不变）
- **是否改变**：否
- **原因**：这是 operational consolidation，不删除 source inventory 记录

---

## 4. 合并后的 Consolidated Candidate

### 4.1 goldman_sachs_podcasts

| 属性 | 值 |
|---|---|
| source_id | goldman_sachs_podcasts |
| source_name | Goldman Sachs Podcasts |
| source_group | official_podcast_transcript |
| url | https://www.goldmansachs.com/insights/podcasts |
| candidate_type | consolidated |
| member_source_ids | goldman_sachs_exchanges, goldman_sachs_the_markets, goldman_sachs_top_of_mind_podcast |
| trial_v2_status | trial_v2_ready |
| requires_proxy | false |
| requires_special_connector | false |
| notes | Operational consolidation of three Goldman Sachs podcast sources pointing to the same public podcasts hub. |

### 4.2 验证结果

**URL**：https://www.goldmansachs.com/insights/podcasts

**验证方法**：
```powershell
curl.exe -I -L --max-time 20 -A "Mozilla/5.0 ... Chrome/120 ..." "https://www.goldmansachs.com/insights/podcasts"
```

**验证结果**：
- HTTP Status：200 OK
- Content-Type：text/html; charset=UTF-8
- Last-Modified：Fri, 26 Jun 2026
- Server：WebServer（Goldman Sachs 官方服务器）

**判定**：✅ PASSED - Goldman Sachs 官方播客总览页，公开可访问

---

## 5. Trial v2 结果更新

### 5.1 合并前

| 状态 | 数量 | source_ids |
|---|---|---|
| trial_v2_ready | 5 | bofa_global_research, texas_instruments_ir, merck_ir, benzinga_analyst_ratings, china_fund_news |
| trial_v2_watch | 1 | goldman_sachs_exchanges |
| trial_v2_reject | 2 | goldman_sachs_the_markets, goldman_sachs_top_of_mind_podcast |

### 5.2 合并后

| 状态 | 数量 | source_ids |
|---|---|---|
| trial_v2_ready | 6 | bofa_global_research, texas_instruments_ir, merck_ir, benzinga_analyst_ratings, china_fund_news, goldman_sachs_podcasts |
| trial_v2_watch | 0 | - |
| trial_v2_reject | 0 | - |

### 5.3 Trial v2 建议源数

| 类别 | 数量 | 说明 |
|---|---|---|
| 当前 trial_v1 | 15 | 保持不变 |
| 建议新增 trial_v2 | 6 | 5 个独立 ready + 1 个合并 ready |
| **合计建议 trial sources** | **21** | trial_v1 + trial_v2 |

---

## 6. 边界确认

| 检查项 | 结果 |
|---|---|
| 是否修改当前 15 个 trial v1 | ❌ 否 |
| 是否修改 TRAE scheduling | ❌ 否 |
| 是否处理 92 全量 | ❌ 否，只处理 3 个 Goldman Sachs podcast 源 |
| 是否抓 blocked/high-risk | ❌ 否 |
| 是否绕登录/付费墙 | ❌ 否 |
| 是否下载不明 PDF | ❌ 否 |
| 是否提交 data/ | ❌ 否 |
| 是否提交 local/secrets | ❌ 否 |
| 是否恢复已删除 Dashboard 页面 | ❌ 否 |
| 是否引入 Playwright/Selenium | ❌ 否 |
| 是否打 tag | ❌ 否 |
| 是否删除 source inventory 记录 | ❌ 否，原始 3 个 source 保留 |

---

## 7. 后续建议

### 7.1 Trial v2 启动

建议将以下 6 个源并入 trial_v2：
1. bofa_global_research（P0）
2. texas_instruments_ir（P0）
3. merck_ir（P0）
4. benzinga_analyst_ratings（P0）
5. china_fund_news（P1）
6. goldman_sachs_podcasts（consolidated）

### 7.2 原始 Source 处理

三个原始 source（goldman_sachs_exchanges, goldman_sachs_the_markets, goldman_sachs_top_of_mind_podcast）：
- 建议在未来的 source inventory 清理阶段考虑合并或移除
- 当前阶段保留，不影响 trial_v2 运营

---

## 8. 相关文件

- Source Inventory：`configs/foundation_source_inventory.example.yaml`（未修改）
- Trial v2 Candidates：`docs/foundation_trial_v2_candidates.md`（待更新）
- Trial v2 Allowlist：`configs/foundation_trial_v2_candidate_allowlist.example.yaml`（待更新）
- URL 恢复报告：`docs/foundation_url_recovery_report.md`
- M3C-5A2 验证报告：`docs/foundation_trial_v2_validation_report.md`
