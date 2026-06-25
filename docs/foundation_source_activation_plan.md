# OPC Foundation Source Activation Plan

**Version**: 1  
**Updated**: 2026-06-25  
**Status**: M3C-0B Ready（Source Inventory 接入配置检查与上线计划）

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

## 11. 后续 M3C-1 如何生成 TRAE 调度模板

### 11.1 M3C-1 目标

基于 source inventory 配置，生成 TRAE 调度任务模板，实现真正的自动化采集。

### 11.2 关键步骤

```text
1. 为每个 scheduled 源选择/实现 connector
   - RSS 源 → RSSConnector
   - 网页源 → WebScraperConnector
   - API 源 → APIConnector
   - 播客源 → PodcastConnector

2. 配置 connector 参数
   - URL / feed URL
   - 认证方式（如果需要）
   - 抓取范围（列表页/详情页）
   - 提取规则（标题/正文/日期/作者）

3. 配置调度参数
   - schedule_profile → 具体 cron 表达式
   - recommended_time_windows → 具体时间窗口
   - 超时 / 重试 / 退避策略

4. 配置质量门禁
   - 去重策略（URL + 内容哈希）
   - 质量评分规则
   - 失败队列处理

5. 生成 TRAE 任务 YAML
   - 每个 source 一个任务
   - 按 priority 和 schedule_profile 分组
   - 依赖关系定义
```

### 11.3 输出产物

```text
configs/trae_tasks/
  ├── s级_投行公开研究.yaml
  ├── s级_会议纪要.yaml
  ├── a级_媒体引用.yaml
  ├── a级_分析师评级.yaml
  └── b级_中文传播.yaml
```

### 11.4 上线顺序

```text
M3C-1 Phase 1: S 级投行公开研究（约 30 个）
M3C-1 Phase 2: S 级会议纪要 + 播客（约 17 个）
M3C-1 Phase 3: A 级媒体引用 + 分析师评级（约 13 个）
M3C-1 Phase 4: B 级中文传播（约 17 个，需合规确认）
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