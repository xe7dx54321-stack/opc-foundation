# OPC Foundation Source Inventory Report

**Version**: 1.2  
**Updated**: 2026-06-26  
**Status**: M3C-2A-fix Ready（Source Inventory 92 源口径统一）

---

## 1. Source Inventory 总览

本报告总结 `configs/foundation_source_inventory.example.yaml` 配置文件的内容，用于登记后续准备上线的真实信息源。

**关键点**：
- 本阶段只做配置登记，不真实访问网站，不启动采集
- 按 source group 分类登记所有源
- 每个源标注 capability_id、网站、接入方式、优先级、调度档位
- M3C-0B 已接入 Dashboard 配置检查页，支持自动校验
- 配套上线计划文档：[Source Activation Plan](foundation_source_activation_plan.md)

---

## 2. Source Group 数量

共 **9 个** source group：

| Group ID | Group Name | Default Priority | Default Automation Mode |
|----------|------------|------------------|------------------------|
| official_public_research | 投行官方公开研究 | S | scheduled |
| official_podcast_transcript | 投行官方播客/文字稿 | S | scheduled |
| bank_conference_transcripts | 投行会议纪要/公司IR | S | scheduled |
| media_research_mentions | 媒体研报二次引用 | A | scheduled |
| analyst_actions | 分析师评级/目标价变动 | A | scheduled |
| chinese_rebroadcast | 中文财经二次传播 | B | scheduled |
| blocked_high_risk_sources | 高风险禁止源 | blocked | do_not_ingest |
| search_providers | 搜索补充源 | supplement | on_demand |
| community_dev_signals | 社区/开发者信号 | supplement | dormant |

---

## 3. Source 数量

共 **92 个**信息源（sources）。
> 注：M3C-0A 初始为 87 个源；后续配置扩展后，当前口径为 92 个源。

---

## 4. S/A/B/C/supplement/blocked 数量

| Priority | Count | Description |
|----------|-------|-------------|
| S | 29 | 最高优先级，投行官方研究和会议纪要 |
| A | 26 | 高优先级，投行播客、媒体引用、分析师评级 |
| B | 17 | 中优先级，中文财经二次传播 |
| supplement | 12 | 补充源，搜索 provider 和社区信号 |
| blocked | 5 | 禁止接入源，高风险泄露渠道 |
| C | 0 | 本阶段未配置 C 级源 |

---

## 5. scheduled/on_demand/manual_only/dormant/blocked 数量

| Automation Mode | Count | Description |
|-----------------|-------|-------------|
| scheduled | 70 | 自动定时调度源 |
| on_demand | 10 | 搜索补充源，按需调用 |
| dormant | 2 | 社区/开发者信号，默认休眠 |
| do_not_ingest | 5 | 禁止接入源，明确不采集 |

---

## 6. 第一批建议上线源

### 6.1 投行官方公开研究（S 级，建议首批）

| Source | Institution | Schedule Profile |
|--------|-------------|------------------|
| Goldman Sachs Research | Goldman Sachs | medium_daily |
| Goldman Sachs Insights | Goldman Sachs | medium_daily |
| Goldman Sachs Greater China | Goldman Sachs | medium_daily |
| Morgan Stanley Insights | Morgan Stanley | medium_daily |
| Morgan Stanley Research | Morgan Stanley | medium_daily |
| Morgan Stanley Thoughts on the Market | Morgan Stanley | medium_daily |
| J.P. Morgan Research | J.P. Morgan | medium_daily |
| J.P. Morgan Insights | J.P. Morgan | medium_daily |
| BofA Global Research | Bank of America | medium_daily |
| Citi Research | Citi | medium_daily |
| Citi Insights | Citi | medium_daily |
| UBS Global Research | UBS | medium_daily |
| UBS CIO Insights | UBS | medium_daily |
| Barclays Research | Barclays | medium_daily |

**建议**：第一批上线 14 个投行官方公开研究源，全部 S 级，medium_daily 调度。

### 6.2 投行会议纪要/公司 IR（S 级，建议首批）

| Source | Institution | Schedule Profile |
|--------|-------------|------------------|
| Morgan Stanley TMT Conference | Morgan Stanley | low_daily |
| J.P. Morgan Healthcare Conference | J.P. Morgan | low_daily |
| Goldman Sachs Communacopia | Goldman Sachs | low_daily |
| Microsoft Investor Relations | Microsoft | low_daily |

**建议**：第一批上线 4 个会议纪要/IR 源，S 级，low_daily 调度（会议期间高频）。

### 6.3 媒体研报二次引用（A 级，建议第二批）

| Source | Institution | Schedule Profile |
|--------|-------------|------------------|
| Reuters | Reuters | high_daily |
| MarketWatch | MarketWatch | high_daily |
| Yahoo Finance | Yahoo | high_daily |
| Business Insider | Business Insider | high_daily |

**建议**：第二批上线 4 个主流媒体源，A 级，high_daily 调度。

---

## 7. 暂不自动上线源

### 7.1 中文财经二次传播（B 级，需合规确认）

| Source | Notes |
|--------|-------|
| 华尔街见闻 | VIP 内容需合规确认，不存疑似泄露 PDF |
| 财联社 | 快讯源，需确认采集范围 |
| 微信公众号源 | 需确认具体账号列表 |

**建议**：B 级源需要进一步合规确认后再上线。

### 7.2 搜索补充源（supplement，按需调用）

| Source | Notes |
|--------|-------|
| Tavily Search | 不进入默认 TRAE 高频调度 |
| Brave Search | 不进入默认 TRAE 高频调度 |
| SerpAPI | 不进入默认 TRAE 高频调度 |

**建议**：搜索补充源不自动上线，供 Demand Radar 或指定项目按需调用。

### 7.3 社区/开发者信号（supplement，默认休眠）

| Source | Notes |
|--------|-------|
| GitHub Issues | 默认 dormant，可留给特定项目调用 |
| Hacker News | 默认 dormant，可留给特定项目调用 |

**建议**：社区信号源默认不采集，等待下游项目明确需求后再激活。

---

## 8. 禁止接入源

以下 5 个源明确禁止接入：

| Source ID | Source Name | Reason |
|-----------|-------------|--------|
| telegram_groups | Telegram 群 | 泄露内容高风险 |
| cloud_drive_share | 网盘分享 | 泄露研报 PDF 高风险 |
| pdf_download_sites | 研报 PDF 下载站 | 非法研报下载站高风险 |
| unknown_wechat_pdf | 不明来源公众号 PDF 包 | 涉嫌泄露 |
| report_download_proxy | 研报代下载站 | 涉嫌侵权 |

**配置**：
- `automation_mode`: `do_not_ingest`
- `activation_priority`: `blocked`
- `enabled_by_default`: `false`
- `legal_confidence`: `high_risk`

---

## 9. 后续 M3C-1 如何使用这份清单

### 9.1 M3C-1 任务预览

M3C-1 阶段将基于本清单执行：
1. 为每个 scheduled 源配置具体 connector
2. 配置 TRAE 调度参数（frequency、time_windows）
3. 编写 connector 实现（如已有则复用）
4. 配置 local 配置文件（secrets、具体账号）

### 9.2 使用方式

```yaml
# 示例：M3C-1 配置具体 connector
- source_id: goldman_sachs_research
  connector_type: rss  # 或 web_scraper
  config:
    feed_url: "https://..."
    update_frequency: "medium_daily"
    time_windows:
      - "09:00-10:00"
      - "18:00-19:00"
```

### 9.3 优先级排序

M3C-1 上线顺序建议：
1. **第一批（S 级）**：投行官方公开研究（14 个）+ 会议纪要/IR（4 个）
2. **第二批（A 级）**：媒体研报二次引用（5 个）+ 分析师评级（8 个）+ 播客（6 个）
3. **第三批（B 级）**：中文财经二次传播（17 个），需合规确认
4. **补充**：搜索 provider、社区信号按需配置

---

## 10. 测试覆盖

`tests/dashboard/test_source_inventory.py` 包含 53 个测试：

- 文件存在性测试
- source_groups/sources 非空测试
- source_id 全局唯一测试
- source_group 引用有效性测试
- capability_id 引用有效性测试
- activation_priority 枚举合法性测试
- automation_mode 枚举合法性测试
- schedule_profile 枚举合法性测试
- legal_confidence 枚举合法性测试
- blocked/high_risk 源默认禁用测试
- search provider 默认 not scheduled 测试
- 覆盖 9 个 source group 测试
- 覆盖所有指定投行源测试（GS、MS、JPM、BofA、Citi、UBS、Barclays）
- 覆盖媒体源测试（Reuters、MarketWatch、Yahoo Finance、Business Insider）
- 覆盖分析师评级源测试（Investing.com、Benzinga、The Fly、StreetInsider、Briefing.com、TipRanks）
- 覆盖中文财经源测试（中国基金报、券商中国、华尔街见闻、财联社、格隆汇、智通财经）
- 覆盖搜索 provider 测试（Tavily、Brave、SerpAPI、Bing、Google CSE、Searx、DuckDuckGo、Yahoo Search、Baidu Search、Custom Search）
- 覆盖社区信号源测试（GitHub Issues、Hacker News）
- 不恢复已删除 Dashboard 页面测试

---

## 11. 附录：完整 Source 清单

详见配置文件：`configs/foundation_source_inventory.example.yaml`

---

## 12. 变更历史

| Date | Version | Changes |
|------|---------|---------|
| 2026-06-25 | 1 | M3C-0A 初始版本，登记 87 个信息源，覆盖 9 个 source group |
| 2026-06-26 | 1.2 | M3C-2A-fix 口径统一，更新为 92 个信息源 |