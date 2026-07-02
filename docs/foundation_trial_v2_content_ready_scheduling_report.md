# OPC Foundation Trial V2 Content-Ready Scheduling Report

> 版本：1.0
> 执行时间：2026-07-02
> 执行阶段：M3C-5A8
> 输入依据：M3C-5A5/M3C-5A7/M3C-5A7.1 内容有效性审计

---

## 1. 概要

| 项目 | 值 |
|---|---|
| 初始 content_ready 源数 | 9 |
| preflight 后保留源数 | **8** |
| preflight 降级源数 | 1（merck_ir） |
| 网络环境 | proxy_enabled=false, proxy_mode=none |

---

## 2. Preflight 真实验证结果

| source_id | content_status | preflight_score | valid | relevant | fresh | noise_flags | 保留 |
|---|---|---:|---:|---:|---:|---|---|
| barclays_our_insights | content_ready | 80 | 3 | 2 | 0 | - | YES |
| markets_insider | content_ready | 90 | 3 | 3 | 0 | - | YES |
| china_fund_news | content_ready | 100 | 3 | 3 | 3 | - | YES |
| wind_public | content_ready | 75 | 3 | 2 | 0 | garbled_text | YES |
| goldman_sachs_insights | content_ready | 65 | 2 | 2 | 0 | - | YES |
| business_insider | content_ready | 95 | 3 | 3 | 2 | app_download_page | YES |
| cls_cn | content_ready | 100 | 3 | 3 | 3 | - | YES |
| zhitong_caijing | content_ready | 100 | 3 | 3 | 3 | - | YES |

### 2.1 降级源

| source_id | 降级前 | 降级后 | 原因 |
|---|---|---|---|
| merck_ir | content_ready | technical_only | HTTP 403 Forbidden（investors.merck.com 拒绝访问） |

---

## 3. 真实样本摘要

### barclays_our_insights
- Setting the record straight on Barclays' links to the defence sector
- News & Press Releases
- Barclays Consumer Spend Index

### markets_insider
- SpaceX IPO valuation risks
- Stock market bearish warning from BofA strategists
- Facebook's infamous 2012 IPO

### china_fund_news
- 多家券商公布7月金股名单（fresh）
- 告别"All in AI"，基金公司激辩下半年（fresh）
- 48家A股公司公告提示风险（fresh）

### cls_cn
- 王毅同美国国务卿鲁比奥通电话（fresh）
- 美联储主席沃什发言（fresh）
- 半导体涨价潮蔓延（fresh）

### zhitong_caijing
- 美股三大指数收涨（fresh）
- 中概股集体走强（fresh）
- AI概念股持续活跃（fresh）

---

## 4. 被排除源

### content_watch（5 个，不纳入）
- goldman_sachs_research（JS 渲染，无研究内容）
- goldman_sachs_reports（JS 渲染）
- goldman_sachs_top_of_mind（JS 渲染）
- gelonghui（导航噪音多）
- goldman_sachs_podcasts（JS 渲染，consolidated）

### content_reject（2 个，不纳入）
- briefing_com_upgrades（空页面）
- wallstreet_cn（空页面）

### technical_only（6 个，不纳入）
- yahoo_finance（403）
- the_fly（403）
- bofa_global_research（SSL 错误）
- texas_instruments_ir（超时）
- benzinga_analyst_ratings（403）
- merck_ir（preflight 降级：403）

---

## 5. Allowlist 路径

`configs/foundation_trial_v2_content_ready_allowlist.example.yaml`

8 个源：
- barclays_our_insights (P0)
- markets_insider (P0)
- china_fund_news (P0)
- wind_public (P0)
- goldman_sachs_insights (P1)
- business_insider (P1)
- cls_cn (P1)
- zhitong_caijing (P1)

---

## 6. TRAE command-only 示例配置

- **路径**：`configs/trae_foundation_trial_v2_content_ready.example.yaml`
- **enabled**：全部 false
- **production_enabled**：false
- **command_only**：true
- **是否包含自然语言 prompt**：否

---

## 7. 执行结果

| 步骤 | 结果 |
|---|---|
| validate-config | PASS |
| preflight | 8/9 retained, 1 downgraded (merck_ir) |
| dry-run | PASS |
| run | PASS（8 sources queued） |
| check | PASS |

---

## 8. Scheduling 建议

### 8.1 是否建议进入 M3C-5A9

YES，建议进入 M3C-5A9。

### 8.2 建议调度源数

8 个 content_ready 源。

### 8.3 暂缓源数

1 个（merck_ir），暂缓原因：HTTP 403 需特殊 connector。

### 8.4 其他暂缓源

- goldman_sachs 系列（4 个）：JS 渲染，需 browser-like connector
- gelonghui：导航噪音多，需进一步修复
- 其他 technical_only / reject：网络问题或空页面

---

## 9. 差异说明

任务预期列表中包含以下源，但实际不在 content_ready 中：

| 预期源 | 实际状态 | 原因 |
|---|---|---|
| yahoo_finance | technical_only | HTTP 403，不是 content_ready |
| marketwatch | 不在 21 operational 中 | 未被纳入 trial_v2 allowlist |
| business_insider_markets | 不存在 | 该 ID 不在 source inventory 中 |
| cninfo_announcement | 不在 21 operational 中 | 未被纳入 trial_v2 allowlist |

以实际审计结果为准。

---

## 10. 边界确认

- 是否修改 trial_v1：否
- 是否修改真实 TRAE scheduling：否
- 是否配置 production：否
- 是否纳入 content_watch：否
- 是否纳入 content_reject：否
- 是否纳入 technical_only：否
- 是否调度 92 全量：否
- 是否提交 data/local/secrets：否
