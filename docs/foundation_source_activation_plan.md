# OPC Foundation Source Activation Plan

**Version**: 1.1  
**Updated**: 2026-06-25  
**Status**: M3C-1 Ready（上线脚本与 TRAE 调度模板）

---

## 1. 为什么需要从 capability 下钻到 source

### 1.1 背景

Foundation 之前只有 capability 层面的抽象（如 `research.official_public_research`），但缺少具体的信息源清单。一个 capability 可能对应多个信息源（多个投行、多个网站）。

### 1.2 为什么需要 source inventory

| 层面 | 例子 | 粒度 | 用途 |
|------|------|------|------|
| capability | `research.official_public_research` | 功能级别 | 定义能力边界、健康状态、运行手册 |
| source | `goldman_sachs_research` | 网站级别 | 定义具体采集对象、调度频率、优先级 |

### 1.3 好处

1. **调度精确化**：不同 source 可以有不同的调度频率和时间窗口
2. **风险隔离**：一个 source 出问题不影响整个 capability 的健康评估
3. **优先级明确**：S 级源优先保障，blocked 源明确禁止
4. **上线可控**：按批次上线，而不是一次性全部上线
5. **合规清晰**：每个 source 有明确的 legal_confidence 标签

---

## 2. 当前 source inventory 总览

- **source group**: 9 个
- **source 数量**: 87 个
- **默认启用**: 70 个（scheduled 源）
- **默认禁用**: 17 个（search provider + blocked + community）

详见 [Source Inventory Report](foundation_source_inventory_report.md)。

---

## 3. source group 分类

| Group ID | 名称 | 默认优先级 | 默认模式 | 说明 |
|----------|------|-----------|---------|------|
| `official_public_research` | 投行官方公开研究 | S | scheduled | 投行官网公开研究、报告、观点 |
| `official_podcast_transcript` | 投行官方播客/文字稿 | S | scheduled | 投行官方播客节目及文字稿 |
| `bank_conference_transcripts` | 投行会议纪要/公司 IR | S | scheduled | 投行会议纪要、上市公司 IR 页面 |
| `media_research_mentions` | 媒体研报二次引用 | A | scheduled | 主流财经媒体对研报的二次引用 |
| `analyst_actions` | 分析师评级/目标价变动 | A | scheduled | 分析师评级变动、目标价调整 |
| `chinese_rebroadcast` | 中文财经二次传播 | B | scheduled | 中文财经媒体对海外研报的二次传播 |
| `blocked_high_risk_sources` | 高风险禁止源 | blocked | do_not_ingest | 明确禁止接入的高风险渠道 |
| `search_providers` | 搜索补充源 | supplement | on_demand | 搜索 API，按需调用，不自动调度 |
| `community_dev_signals` | 社区/开发者信号 | supplement | dormant | GitHub Issues、HN 等，默认休眠 |

---

## 4. S/A/B/supplement/blocked 定义

| 优先级 | 含义 | 典型场景 | 上线建议 |
|--------|------|---------|---------|
| **S** | 最高优先级，核心数据源 | 投行官方公开研究、核心会议纪要 | 第一批上线 |
| **A** | 高优先级，重要补充源 | 媒体引用、分析师评级、播客 | 第二批上线 |
| **B** | 中优先级，可选补充源 | 中文二次传播、部分公众号 | 第三批上线，需合规确认 |
| **C** | 低优先级，可选 | （当前暂无） | 视情况上线 |
| **supplement** | 补充源，按需使用 | 搜索 provider、社区信号 | 不自动调度，按需调用 |
| **blocked** | 禁止接入，明确不采集 | Telegram 群、网盘、研报下载站 | 永远不接入 |

---

## 5. scheduled/on_demand/dormant/do_not_ingest 定义

| 自动化模式 | 含义 | 调度方式 |
|-----------|------|---------|
| **scheduled** | 定时自动采集 | 按 schedule_profile 自动运行 |
| **on_demand** | 按需触发 | 手动或下游项目调用时触发 |
| **dormant** | 休眠状态 | 默认不运行，需手动激活 |
| **manual_only** | 仅手动 | 完全人工操作 |
| **do_not_ingest** | 禁止接入 | 永远不采集 |

### 5.1 schedule_profile 定义

| 档位 | 含义 | 典型频率 |
|------|------|---------|
| `high_daily` | 高频每日 | 每天 2-4 次 |
| `medium_daily` | 中频每日 | 每天 1-2 次 |
| `low_daily` | 低频每日 | 每天 1 次 或 每周 2-3 次 |
| `weekly` | 每周 | 每周 1 次 |
| `on_demand` | 按需 | 不自动调度 |
| `blocked` | 禁止 | 不采集 |

---

## 6. 第一批上线源

### 6.1 目标

验证基础设施和基本流程，用最可靠的官方源跑通端到端链路。

### 6.2 建议上线源

#### S 级：投行官方公开研究（约 30 个 source）

| 机构 | 主要源 | capability_id | 调度档位 |
|------|--------|---------------|---------|
| Goldman Sachs | Research / Insights / Top of Mind / Greater China | `research.official_public_research` | medium_daily |
| Morgan Stanley | Insights / Research / Thoughts on the Market / China | `research.official_public_research` | medium_daily |
| J.P. Morgan | Research / Global Research Reports / Insights | `research.official_public_research` | medium_daily |
| BofA | Global Research / Market Insights / Must Read | `research.official_public_research` | medium_daily |
| Citi | Research / Institute / GPS / Insights | `research.official_public_research` | medium_daily |
| UBS | Global Research / CIO Insights / IB Insights | `research.official_public_research` | medium_daily |
| Barclays | Research / IB Research / Our Insights | `research.official_public_research` | medium_daily |

#### S 级：投行会议纪要/公司 IR（约 11 个 source）

| 类别 | 主要源 | capability_id | 调度档位 |
|------|--------|---------------|---------|
| 投行会议 | MS TMT / JPM Healthcare / GS Communacopia / UBS Tech / BofA Tech / Barclays Tech / DB Tech / Bernstein SDC | `research.conference_transcript` | low_daily（会议期间高频） |
| 公司 IR | Microsoft / Texas Instruments / Merck | `research.conference_transcript` | low_daily（财报期高频） |

#### S 级：投行官方播客/文字稿（约 6 个 source）

| 机构 | 播客名称 | capability_id | 调度档位 |
|------|---------|---------------|---------|
| Morgan Stanley | Thoughts on the Market | `research.podcast_transcript` | medium_daily |
| Goldman Sachs | Exchanges / The Markets / Top of Mind | `research.podcast_transcript` | medium_daily |
| BofA | Global Research Unlocked | `research.podcast_transcript` | medium_daily |
| UBS | Pod Hub | `research.podcast_transcript` | medium_daily |
| J.P. Morgan | Research Insights | `research.podcast_transcript` | medium_daily |

### 6.3 第一批验收标准

- [ ] 所有 S 级源接入 connector
- [ ] 调度配置完成（TRAE 任务模板）
- [ ] 去重机制验证（SeenStore + Dedupe）
- [ ] 质量门禁验证（QualityGate）
- [ ] Dashboard 健康监控正常展示
- [ ] 连续运行 7 天无重大故障

---

## 7. 第二批上线源

### 7.1 目标

扩大覆盖范围，增加时效性强的媒体和评级源。

### 7.2 建议上线源

#### A 级：媒体研报二次引用（约 5 个 source）

| 媒体 | capability_id | 调度档位 |
|------|---------------|---------|
| Reuters | `research.media_mention` | high_daily |
| MarketWatch | `research.media_mention` | high_daily |
| Yahoo Finance | `research.media_mention` | high_daily |
| Business Insider | `research.media_mention` | high_daily |
| Markets Insider | `research.media_mention` | high_daily |

#### A 级：分析师评级/目标价变动（约 8 个 source）

| 网站 | capability_id | 调度档位 |
|------|---------------|---------|
| Investing.com | `research.analyst_action` | high_daily |
| Benzinga | `research.analyst_action` | high_daily |
| The Fly | `research.analyst_action` | high_daily |
| StreetInsider | `research.analyst_action` | high_daily |
| MarketWatch Upgrades/Downgrades | `research.analyst_action` | medium_daily |
| WSJ Market Data | `research.analyst_action` | medium_daily |
| Briefing.com | `research.analyst_action` | medium_daily |
| TipRanks | `research.analyst_action` | medium_daily |

### 7.3 第二批验收标准

- [ ] 所有 A 级源接入 connector
- [ ] 高频率调度稳定性验证
- [ ] 媒体引用去重效果验证
- [ ] 分析师评级元数据标准化
- [ ] 连续运行 14 天无重大故障

---

## 8. 第三批上线源

### 8.1 目标

补充中文财经传播源，覆盖中文用户关注的信息渠道。

### 8.2 建议上线源

#### B 级：中文财经二次传播（约 17 个 source）

| 类别 | 代表源 | capability_id | 调度档位 | 前置条件 |
|------|--------|---------------|---------|---------|
| 主流财经媒体 | 中国基金报 / 券商中国 / 华尔街见闻 / 财联社 / Wind 公开 / 格隆汇 / 智通财经 | `research.media_mention` | medium_daily | 合规确认 |
| 美股/港股研究社 | 美股研究社 / 港股研究社 | `research.media_mention` | low_daily | 合规确认 |
| 微信公众号 | 高盛中国 / 摩根士丹利中国 / 摩根士丹利基金 / 研报社 / 投研圈 / 见闻 VIP 公开 / 其他二次传播源 | `research.wechat_archive` | medium_daily / low_daily | 合规确认 + 接入方案 |

### 8.3 第三批前置条件

- [ ] 中文来源合规性评估完成
- [ ] 微信公众号接入方案确定
- [ ] 中文内容去重策略验证
- [ ] 敏感内容过滤机制上线

---

## 9. 暂不自动上线源

### 9.1 Search Provider（10 个）

| Provider | 模式 | 说明 |
|----------|------|------|
| Tavily Search | on_demand | 不自动调度，按需调用 |
| Brave Search | on_demand | 不自动调度，按需调用 |
| SerpAPI | on_demand | 不自动调度，按需调用 |
| Bing | on_demand | 不自动调度，按需调用 |
| Google CSE | on_demand | 不自动调度，按需调用 |
| Searx | on_demand | 不自动调度，按需调用 |
| DuckDuckGo | on_demand | 不自动调度，按需调用 |
| Yahoo Search | on_demand | 不自动调度，按需调用 |
| Baidu Search | on_demand | 不自动调度，按需调用 |
| Custom Search | on_demand | 不自动调度，按需调用 |

**使用场景**：
- Demand Radar 按需搜索
- 手动指定查询
- 补充信息验证

### 9.2 Community / Dev 信号（2 个）

| 源 | 模式 | 说明 |
|----|------|------|
| GitHub Issues | dormant | 默认休眠，需指定项目调用 |
| Hacker News | dormant | 默认休眠，需指定项目调用 |

**使用场景**：
- 具体项目的技术信号监控
- Demand Radar 特定领域跟踪
- 手动触发的调研任务

---

## 10. 禁止接入源

以下 5 个源明确禁止接入，**永远不采集**：

| Source ID | 名称 | 原因 |
|-----------|------|------|
| `telegram_groups` | Telegram 群 | 泄露内容高风险 |
| `cloud_drive_share` | 网盘分享 | 泄露研报 PDF 高风险 |
| `pdf_download_sites` | 研报 PDF 下载站 | 非法研报下载站高风险 |
| `unknown_wechat_pdf` | 不明来源公众号 PDF 包 | 涉嫌泄露 |
| `report_download_proxy` | 研报代下载站 | 涉嫌侵权 |

**配置**：
- `automation_mode`: `do_not_ingest`
- `activation_priority`: `blocked`
- `enabled_by_default`: `false`
- `legal_confidence`: `high_risk`

---

## 11. M3C-1 上线脚本与 TRAE 调度模板

### 11.1 M3C-1 完成状态

M3C-1 已完成：上线脚本与 TRAE 调度模板。

详见 [Foundation TRAE Operations](foundation_trae_operations.md)。

### 11.2 新增脚本

| 脚本 | 用途 |
|---|---|
| `scripts/run_research_archive.ps1` | 运行研究归档（覆盖 5 个 source group） |
| `scripts/check_research_archive.ps1` | 检查研究归档产物 |
| `scripts/run_official_filings.ps1` | 运行官方披露归档 |
| `scripts/check_official_filings.ps1` | 检查官方披露归档产物 |
| `scripts/run_manual_url_archive.ps1` | 处理人工 URL 队列 |
| `scripts/check_foundation_control_center.ps1` | Control Center 配置健康检查 |
| `scripts/check_foundation_daily_status.ps1` | 每日状态收口报告 |

### 11.3 TRAE 调度模板

配置文件：`configs/trae_foundation_schedule.example.yaml`

默认启用 7 个定时任务：

| 任务 | 时间 | 覆盖范围 |
|---|---|---|
| 官方公开研究归档 | 07:30 / 13:30 / 20:30 | S 级官方研究 + 播客 + 会议纪要 |
| 媒体引用与分析师动作 | 09:20 / 15:20 / 21:20 | A 级媒体引用 + 分析师动作 |
| 中文财经二次传播 | 08:20 / 12:20 / 18:20 / 22:20 | B 级中文传播源 |
| 官方披露归档 | 08:00 / 12:45 / 17:30 / 22:30 | SEC / CNINFO / HKEX |
| 文档抽取后处理 | 08:40 / 13:05 / 18:00 / 23:00 | 所有已归档文档 |
| Control Center 健康检查 | 09:10 / 18:30 / 23:40 | 配置完整性检查 |
| 每日状态收口 | 23:55 | 生成日报 |

默认禁用：

| 任务 | 原因 |
|---|---|
| 人工 URL 检查 | 以人工触发为主 |

不进入默认定时任务：

| 类别 | 原因 |
|---|---|
| Search Provider | on_demand，按需触发 |
| Community / Dev | on_demand / dormant，先观察 |
| Blocked / High Risk | 禁止接入 |

### 11.4 后续 M3C-2 全信息源基线运行

M3C-2 目标：让所有 scheduled 源稳定运行一周，建立基线数据。

```text
1. 启用第一批 S 级 scheduled 任务
2. 运行 3 天，观察稳定性
3. 启用第二批 A 级 scheduled 任务
4. 运行 2 天，观察稳定性
5. 启用第三批 B 级 scheduled 任务
6. 运行 7 天，建立基线数据
7. 输出基线报告
```

---

## 12. 风险与注意事项

### 12.1 法律合规

- 只采集公开网页和摘要，不抓取付费内容
- 尊重 robots.txt 和网站使用条款
- 不明来源的 PDF 一律不存储
- 中文来源需单独合规评估

### 12.2 技术风险

- 反爬虫机制可能导致 source 失效
- 网站改版需要更新提取规则
- 高频率采集可能触发 IP 封禁
- 需配置合理的 rate limit 和重试策略

### 12.3 数据质量

- 不同 source 的内容格式差异大
- 媒体二次引用可能存在失真
- 分析师评级数据标准化难度高
- 中文内容去重需要额外处理

---

## 13. 变更历史

| Date | Version | Changes |
|------|---------|---------|
| 2026-06-25 | 1 | M3C-0B 初始版本，定义上线计划和三批上线策略 |