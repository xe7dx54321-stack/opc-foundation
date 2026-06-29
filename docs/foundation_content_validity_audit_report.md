# OPC Foundation M3C-5A4 Content Validity Audit Report

> 版本：1.0
> 生成时间：2026-06-29
> 执行阶段：M3C-5A4
> 配置文件：configs/foundation_content_validity_audit.example.yaml
> 输入 Allowlist：configs/foundation_trial_v2_allowlist.example.yaml
> 输出目录：data/foundation_content_validity/

---

## 1. 执行摘要

| 项目 | 值 |
|---|---|
| 执行时间 | 2026-06-29 |
| 审计模式 | Content Validity Audit |
| 操作源数 | 21 |
| content_ready | 待统计 |
| content_watch | 待统计 |
| content_reject | 待统计 |
| technical_only | 待统计 |
| 代理模式 | env |
| Proxy Enabled | YES |

---

## 2. 审计范围

### 2.1 源构成

| 类别 | 数量 | 说明 |
|---|---|---|
| Trial v1 Base | 15 | 当前稳定运行的 trial 源 |
| Trial v2 Additions | 6 | M3C-5A/M3C-5A2/M3C-5A2.1 新增源 |
| Consolidated Candidate | 1 | goldman_sachs_podcasts（合并3个源为1个） |
| **Operational Total** | **21** | 审计的 operational source 总数 |

### 2.2 Trial v2 Additions 详情

| source_id | source_name | candidate_type | priority | URL |
|---|---|---|---|---|
| bofa_global_research | BofA Global Research | inventory_backed | P0 | https://www.bankofamerica.com/research |
| texas_instruments_ir | Texas Instruments IR | inventory_backed | P0 | https://investor.ti.com |
| merck_ir | Merck IR | inventory_backed | P0 | https://investors.merck.com |
| benzinga_analyst_ratings | Benzinga Analyst Ratings | inventory_backed | P0 | https://www.benzinga.com/analyst-ratings |
| china_fund_news | 中国基金报 | inventory_backed | P1 | https://www.chnfund.com |
| goldman_sachs_podcasts | Goldman Sachs Podcasts | consolidated | P1 | https://www.goldmansachs.com/insights/podcasts |

---

## 3. 审计方法

### 3.1 内容有效性判定标准

**content_ready（内容就绪）**：
- 页面是目标页面
- 能抽取候选内容
- 候选内容与 source 目标相关
- 有标题 / URL / 时间或可推断时间
- 不是纯导航页、营销页、cookie 页、登录页
- 不需要付费或登录

**content_watch（内容观察）**：
- 页面基本相关
- 能抽到部分候选内容
- 但存在：内容偏少、时间不明确、偶发 empty、重复较多等问题

**content_reject（内容拒绝）**：
- 拿到错误页面（404/403）
- 拿到 cookie/consent/login/blocked 页面
- 页面无有效候选内容
- 候选内容与 source 目标无关
- 全是导航、营销、静态介绍

**technical_only（仅技术）**：
- 技术上可访问
- 但目前只能证明 URL 活着，不能证明有内容价值

### 3.2 审计配置

| 配置项 | 值 |
|---|---|
| max_candidates_per_source | 5 |
| content_ready_min_valid_candidates | 2 |
| content_ready_min_relevant_candidates | 2 |
| content_watch_min_valid_candidates | 1 |
| max_noise_ratio_for_ready | 0.5 |

---

## 4. 审计结果

### 4.1 结果统计

> 注：实际审计结果需从 data/foundation_content_validity/index/source_content_audit.jsonl 获取

| 状态 | 数量 | 说明 |
|---|---|---|
| content_ready | 待更新 | 能产出有效候选信息 |
| content_watch | 待更新 | 基本可访问但有问题 |
| content_reject | 待更新 | 页面无效或噪音 |
| technical_only | 待更新 | 技术可访问但无内容 |

### 4.2 典型发现

**技术可访问但有问题的源**：
- 部分源返回 SSL/TLS handshake 错误（网络环境问题）
- 部分源 timeout（网络环境问题）
- 部分源返回 404/403（URL 可能已变更）

**内容质量问题的源**：
- 部分源页面为纯导航页，无实际内容模块
- 部分源需要登录或付费
- 部分源内容严重过旧

---

## 5. Scheduling 建议

### 5.1 建议进入 TRAE trial_v2 scheduling

| source_id | 优先级 | 建议动作 | 备注 |
|---|---|---|---|
| 待更新 | 待更新 | 待更新 | 需从审计结果更新 |

### 5.2 暂缓进入 scheduling

| source_id | 原因 | 建议动作 |
|---|---|---|
| 待更新 | 待更新 | 待更新 |

### 5.3 后续处理

- **TLS/SSL 问题**：留待 M3C-5C 处理（需要特殊 connector）
- **需要登录的源**：不绕登录，暂不纳入
- **需要付费的源**：不绕付费墙，暂不纳入
- **Browser-like 源**：留待 M3C-5B 处理

---

## 6. 审计局限性

### 6.1 网络环境限制

- 部分源在当前网络环境下无法访问（SSL handshake failed / timeout）
- 这是环境问题，不代表源本身无效
- 建议在稳定网络环境下重新审计

### 6.2 审计深度限制

- 仅抽样 5 条候选内容，可能无法代表全量内容质量
- 仅检测页面级噪音，未检测内容级噪音
- 未验证候选内容的实际可访问性

---

## 7. 后续步骤

### 7.1 M3C-5A5：更新审计结果

完成审计后：
1. 更新 source_content_audit.jsonl
2. 统计 content_ready/content_watch/content_reject/technical_only 数量
3. 更新本报告的结果统计部分

### 7.2 M3C-5A6：TRAE trial_v2 配置

根据审计结果：
1. 仅将 content_ready 源纳入 TRAE trial_v2 scheduling
2. 将 content_watch 源列为观察对象
3. 将 content_reject/technical_only 源列入 backlog

---

## 8. 边界确认

| 检查项 | 结果 |
|---|---|
| 是否修改当前 15 个 trial v1 | ❌ 否，不修改 |
| 是否修改 TRAE scheduling | ❌ 否，不修改 |
| 是否配置 production | ❌ 否 |
| 是否调度 92 全量 | ❌ 否，只审计 21 个 |
| 是否处理新失败源 | ❌ 否，仅记录审计结果 |
| 是否抓 blocked/high-risk | ❌ 否 |
| 是否绕登录/付费墙 | ❌ 否 |
| 是否下载不明 PDF | ❌ 否 |
| 是否提交 data/ | ❌ 否 |
| 是否提交 local/secrets | ❌ 否 |
| 是否恢复已删除 Dashboard 页面 | ❌ 否 |
| 是否引入 Playwright/Selenium | ❌ 否 |
| 是否打 tag | ❌ 否 |

---

## 9. 相关文件

- 配置文件：`configs/foundation_content_validity_audit.example.yaml`
- Audit 脚本：`scripts/run_foundation_content_validity_audit.ps1`
- Check 脚本：`scripts/check_foundation_content_validity_audit.ps1`
- 审计结果：`data/foundation_content_validity/index/source_content_audit.jsonl`
- 审计报告：`data/foundation_content_validity/reports/content_validity_audit_2026-06-29.md`
- Trial v2 Allowlist：`configs/foundation_trial_v2_allowlist.example.yaml`
- Trial v2 Candidates：`docs/foundation_trial_v2_candidates.md`
