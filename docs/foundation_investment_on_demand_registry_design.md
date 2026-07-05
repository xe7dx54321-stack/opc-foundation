# OPC Foundation M3C-6E Investment On-demand Source Registry 设计

> 阶段：M3C-6E0 Audit → M3C-6E1 Design
> 设计目标：定义投资领域 on-demand 信息源注册表的架构和边界
> 基于审计：th_capital_stock ce83e4d 能力复用评估

---

## 1. M3C-6E 的目标重新定义

### 1.1 我们在做什么

M3C-6E（Investment On-demand Source Registry）是 OPC Foundation 的**第三层源**——按需触发的投资研究信息源层。

三层源架构：

| 层 | 名称 | 触发方式 | 代表源 | 时效性 |
|---|---|---|---|---|
| Layer 1 | High-frequency Trial | 定时调度（每 6h） | trial_v2 9 个源 | 高（6h 内） |
| Layer 2 | Low-frequency Observation | 每日调度 + 7 天观察 | merck_ir | 中（24h 内） |
| Layer 3 | **On-demand Registry** | 事件 / 查询触发 | 投行观点、公司披露、研报搜索 | **按需** |

### 1.2 我们不做什么

- ❌ 不是通用关键词搜索引擎
- ❌ 不做投资评级 / 目标价 / 买卖建议
- ❌ 不输出投资结论
- ❌ 不维护 watchlist 业务含义
- ❌ 不做估值 / 预期差 / 交易信号
- ❌ 不是替代 th_capital_stock 的投研系统

### 1.3 核心价值

> **给下游投资系统提供结构化的、可溯源的、质量可控的一手证据材料，让下游在此基础上做投资判断。**

Foundation 是「证据采集层」，不是「投资决策层」。

---

## 2. 为什么不是普通关键词搜索

普通搜索（Tavily/Bing/Google）的问题：

1. **结果不可控**：质量参差不齐，来源不可信
2. **缺乏结构**：纯文本，无法区分「公司原话」vs「记者解读」vs「分析师观点」
3. **溯源困难**：URL 可能失效，引用难以验证
4. **时间模糊**：发布时间不准确，有时序错乱风险
5. **实体混淆**：同名公司、子公司、关联方难以区分

On-demand Registry 的差异化：

| 特性 | 普通搜索 | On-demand Registry |
|---|---|---|
| 来源质量 | 全网杂糅 | 注册源 + 可信度分级 |
| 输出结构 | 文本片段 | Evidence Packet（结构化字段） |
| 溯源能力 | URL 可能失效 | source_id + text_hash + span_location |
| 时间精度 | 模糊日期 | published_at + observed_at + timestamp_confidence |
| 实体解析 | 关键词匹配 | entity_id + ticker + aliases |
| 证据强度 | 无 | strong_direct / management_commentary / proxy_signal |
| 去重 | 基于 URL | 基于内容指纹 + 语义去重 |

---

## 3. Query Pack 设计

### 3.1 什么是 Query Pack

Query Pack 是 on-demand 查询的标准化输入格式。它不是一个搜索词，而是一个**结构化的研究需求描述**。

```python
@dataclass
class OnDemandQueryPack:
    """Investment on-demand query pack."""
    
    query_id: str
    query_type: str  # company_disclosure / analyst_view / industry_signal / event_reaction
    priority: str  # high / medium / low
    
    # 实体维度
    entities: list[QueryEntity]
    industries: list[str]
    topics: list[str]
    
    # 时间维度
    time_window: TimeWindow
    
    # 源偏好
    preferred_source_types: list[str]  # 空 = 全部
    excluded_sources: list[str]
    min_evidence_strength: str  # 最低证据强度要求
    
    # 研究问题
    research_questions: list[str]
    
    # 触发信息
    trigger_type: str  # event / schedule / manual
    trigger_source: str  # 触发源标识
```

### 3.2 Query Entity

```python
@dataclass
class QueryEntity:
    entity_type: str  # company / bank / industry / product / person
    entity_name: str
    ticker: str | None  # 公司的 ticker（如有）
    aliases: list[str]
    entity_id: str | None  # Foundation 内部实体 ID（解析后填充）
```

### 3.3 Time Window

```python
@dataclass
class TimeWindow:
    start_date: str  # YYYY-MM-DD
    end_date: str  # YYYY-MM-DD
    relative_window: str | None  # e.g., "last_90_days", "last_earnings_call"
```

### 3.4 Query Type 枚举

| query_type | 说明 | 典型源 |
|---|---|---|
| company_disclosure | 公司披露类查询 | 公告、年报、IR 材料、业绩会纪要 |
| analyst_view | 投行/分析师观点类 | 卖方研报、评级变动、目标价调整 |
| industry_signal | 行业信号类 | 行业评论、供应链数据、宏观数据 |
| event_reaction | 事件反应类 | 新闻、公告、市场异动后的信息搜集 |
| transcript_search | 电话会/纪要全文搜索 | earnings call transcript, investor day |

---

## 4. Watchlist / Company / Industry / Bank / Topic 输入

### 4.1 输入层级

下游（th_capital_stock）可以在多个层级触发 on-demand 查询：

```
Watchlist（投资组合）
    └── Company（个股）
        ├── Ticker（交易代码）
        ├── Aliases（别名）
        └── Business Segments（业务线）
    └── Industry（行业）
        ├── Industry Code（行业代码）
        └── Peer Companies（可比公司）
    └── Topic（主题）
        ├── Keywords（关键词）
        └── Related Entities（关联实体）
    └── Bank（投行）
        ├── Analyst Coverage（覆盖分析师）
        └── Research Focus（研究方向）
```

### 4.2 动态 Watchlist 输入模式

Foundation 不维护 watchlist 本身，但支持**基于 watchlist 事件的触发**：

```python
@dataclass
class WatchlistTriggerInput:
    watchlist_id: str  # 下游定义的 watchlist ID
    watchlist_snapshot: list[WatchlistEntry]
    trigger_event: str  # new_entry / rating_change / catalyst_alert
    change_reason: str
```

关键原则：
- **Foundation 不存 watchlist**：只接收查询时刻的快照
- **Foundation 不解释 watchlist**：entry 的业务含义（为什么在 watchlist 里）由下游负责
- **Foundation 只做采集**：根据 watchlist snapshot 生成 evidence packets

---

## 5. Source Routing 设计

### 5.1 Routing 流程

```
Query Pack
    │
    ▼
Entity Expansion（实体扩展）
    │  扩展 ticker 别名、行业关联公司、产品名
    ▼
Source Type Matching（源类型匹配）
    │  根据 query_type + preferred_source_types 筛选
    ▼
Source Quality Filter（质量过滤）
    │  按 source_quality + freshness_status + confidence 过滤
    ▼
Priority Ranking（优先级排序）
    │  高可信度源优先 + 最新鲜优先
    ▼
Execution Plan（执行计划）
    │  并行 / 串行 / 降级策略
    ▼
Evidence Collection（证据采集）
    │
    ▼
Dedup + Merge（去重 + 合并）
    │
    ▼
Evidence Packets（输出）
```

### 5.2 Source Routing Metadata（扩展字段）

在 Foundation 现有 source_inventory 基础上，增加 on-demand 路由所需字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| source_key | string | 唯一标识（沿用现有） |
| source_type | enum | official_filing / company_ir / sellside_research / public_news / transcript / market_data / macro / industry_report |
| entity_scope | enum | company / industry / market / macro / product |
| markets | list[string] | A / H / US / CN / global |
| evidence_strength_max | enum | 该源能提供的最强证据级别 |
| timestamp_confidence_max | enum | 该源时间戳最高置信度 |
| supports_on_demand | boolean | 是否支持按需触发 |
| on_demand_latency_sla | int | 按需查询 SLA（秒） |
| rate_limit_per_hour | int | 每小时限流 |
| cost_per_query | string | free / low / medium / high |
| required_credentials | list[string] | 所需凭证类型（空 = 匿名） |
| fallback_sources | list[string] | 该源不可用时的降级源列表 |

### 5.3 源选择策略

```python
def select_sources(query_pack: OnDemandQueryPack, registry: SourceRegistry) -> list[SourceRoutingPlan]:
    """根据 query pack 选择最佳源组合。"""
    
    candidates = []
    
    # 1. 实体匹配
    for source in registry.active_sources():
        if not entity_matches(source, query_pack.entities):
            continue
        if not industry_matches(source, query_pack.industries):
            continue
        if not source_type_ok(source, query_pack.preferred_source_types):
            continue
        if source.source_quality < min_required_quality:
            continue
        candidates.append(source)
    
    # 2. 优先级排序
    candidates.sort(key=lambda s: (
        -evidence_strength_rank(s.evidence_strength_max),
        -timestamp_confidence_rank(s.timestamp_confidence_max),
        -freshness_rank(s.freshness_status),
        cost_rank(s.cost_per_query),
    ))
    
    # 3. 生成执行计划（含降级路径）
    plan = build_routing_plan(candidates, query_pack.priority)
    return plan
```

---

## 6. 投行观点 Evidence Packet 设计

### 6.1 Base Evidence Packet（Foundation 层）

```python
@dataclass
class EvidencePacket:
    """Foundation-level base evidence packet.
    
    只包含通用证据字段，不包含任何投资判断。
    """
    
    evidence_id: str
    query_id: str  # 来自哪个 query
    source_key: str
    source_type: str
    source_title: str
    source_url: str | None
    source_url_hash: str | None
    
    # 时间维度
    published_at: str | None  # YYYY-MM-DD or ISO datetime
    observed_at: str  # Foundation 抓取时间
    timestamp_confidence: str  # high / medium / low_medium / low
    
    # 内容
    extracted_text: str
    text_hash: str
    quoted_span: str | None  # 直接引文（如有）
    span_location: str | None  # 在原文中的位置
    
    # 质量
    evidence_strength: str
    confidence: str
    limitation: str | None
    cannot_conclude: str | None  # 明确说明不能得出什么结论
    
    # 元数据
    allowed_usage: list[str]
    requires_human_review: bool
    review_status: str
    
    # 溯源
    parent_evidence_id: str | None  # 派生关系
    extraction_method: str  # direct_extract / semantic_extract / summary
```

### 6.2 投行观点扩展（下游层，不由 Foundation 定义）

> ⚠️ 以下字段**不属于 Foundation**，由 th_capital_stock 在下游扩展：
>
> - ticker / company_name / industry
> - analyst_name / bank_name / rating / target_price
> - business_variable / claim_type
> - investment_implication / expectation_change
> - valuation_impact / risk_view

### 6.3 证据强度枚举（复用自 th_capital_stock 设计）

| evidence_strength | 说明 | 典型来源 |
|---|---|---|
| strong_direct_disclosure | 强直接披露 | 法定公告、年报、招股书原文 |
| management_commentary | 管理层评论 | 业绩会纪要、IR 材料、管理层访谈 |
| financial_report_context | 财报语境 | 财务报表附注、MD&A |
| business_context | 业务语境 | 公司官网、业务介绍、行业白皮书 |
| proxy_signal | 代理信号 | 行业数据、供应链数据、上下游信号 |
| risk_or_contradictory_signal | 风险/反向信号 | 负面新闻、监管处罚、诉讼 |
| review_required | 需人工复核 | 低质量源、不确定来源 |

### 6.4 关键设计原则：cannot_conclude 字段

每个 evidence packet **必须**说明「基于这个证据，不能得出什么结论」。

示例：
> **cannot_conclude**: 管理层提到「AI 需求强劲」不构成具体订单确认；公司未披露单一客户供应份额和 ASP 数据；不能直接推断收入增长。

这个字段是防止「证据过度解读」的核心防线，也是 Foundation 不输出投资结论的边界保障。

---

## 7. Foundation 不输出投资结论的边界

### 7.1 硬边界

| Foundation 输出 | ✅ 允许 | ❌ 禁止 |
|---|---|---|
| EvidencePacket | ✅ | |
| SourceObservation | ✅ | |
| OnDemandSearchResult | ✅ | |
| ExtractedDocument | ✅ | |
| SourceHealth | ✅ | |
| TimestampConfidence | ✅ | |
| DedupResult | ✅ | |
| **InvestmentRating** | | ❌ |
| **TargetPrice** | | ❌ |
| **BuySellRecommendation** | | ❌ |
| **ValuationConclusion** | | ❌ |
| **ExpectationChange** | | ❌ |
| **PortfolioDecision** | | ❌ |
| **TradeSignal** | | ❌ |
| **InvestmentThesis** | | ❌ |

### 7.2 灰度地带的处理

| 灰色地带 | Foundation 处理方式 | 下游处理方式 |
|---|---|---|
| 「管理层对需求乐观」 | ✅ 提取原话 + evidence_strength=management_commentary | 下游解读为「预期上修信号」 |
| 「行业需求增长 30%」 | ✅ 提取数据 + source_type=industry_report + confidence=medium | 下游映射到公司收入预测 |
| 「分析师上调目标价」 | ✅ 记录事实：who/when/new_target/old_target | 下游判断是否影响估值 |
| 「股价上涨 5%」 | ✅ 记录市场数据（如有行情源接入） | 下游判断是否为信号 |

**原则**：Foundation 只记录「发生了什么」「谁说的」「什么时候说的」「可信度多高」，不解释「意味着什么」。

---

## 8. 与 th_capital_stock 的接口

### 8.1 接口总览

```
th_capital_stock (下游)
    │
    │  1. Query Pack 请求
    │  (watchlist / entities / research_questions / time_window)
    ▼
OPC Foundation On-demand Layer
    │
    │  2. Source Routing + Evidence Collection
    │
    ▼
    │  3. Evidence Packets 输出
    │  (结构化证据 + 溯源 + 质量分级)
    │
th_capital_stock (下游)
    │
    │  4. 投资解读
    │  (预期变化 / 估值含义 / 风险观点 / 组合决策)
    ▼
Investment Conclusion
```

### 8.2 输入接口：Foundation 接收什么

```python
# 下游 → Foundation
class OnDemandRequest:
    query_pack: OnDemandQueryPack
    callback_url: str | None  # 异步回调（可选）
    result_format: str  # json / markdown / both
    max_packets: int  # 最大证据包数量
```

### 8.3 输出接口：Foundation 返回什么

```python
# Foundation → 下游
class OnDemandResult:
    query_id: str
    status: str  # completed / partial / failed
    packets_found: int
    packets: list[EvidencePacket]
    
    # 元数据
    sources_queried: list[str]
    sources_failed: list[str]
    execution_time_seconds: float
    next_page_token: str | None  # 分页（如有）
```

### 8.4 边界契约

**Foundation 保证：**
- 所有证据包有 source_id + source_url + published_at
- 所有证据包标记 evidence_strength + confidence
- 所有证据包有 cannot_conclude 字段（防止过度解读）
- 不输出任何投资判断

**下游保证：**
- 不在 Foundation 层存储 watchlist / universe / portfolio
- 不在 Foundation 层做估值 / 评级 / 交易决策
- 不在 Foundation 层存储付费数据凭证
- 所有投资结论由下游生成和负责

---

## 9. M3C-6E1 最小施工范围

### 9.1 包含（6 项）

| # | 模块 | 说明 | 预计工作量 |
|---|---|---|---|
| 1 | On-demand Query Pack Schema | 定义查询包数据结构 + 验证 | 2 天 |
| 2 | Source Routing Metadata 扩展 | source_inventory 增加 on-demand 路由字段 | 2 天 |
| 3 | Base Evidence Packet Schema | Foundation 层基础证据包 dataclass + 验证 | 2 天 |
| 4 | Investment Source Taxonomy | 投资领域源分类体系（8 大类） | 1 天 |
| 5 | Dry-run Runner | 查询干跑器：只做路由 + 元数据验证，不真实抓取 | 3 天 |
| 6 | 文档 + 测试 | 设计文档 + 单元测试 + 集成测试 | 2 天 |
| | **总计** | | **12 人天** |

### 9.2 不包含（严格排除）

- ❌ 真实数据抓取（只 dry-run）
- ❌ 投资评级 / 目标价 / 买卖建议
- ❌ 估值模型 / 预期差模型
- ❌ 组合决策 / 交易信号
- ❌ Watchlist 管理
- ❌ 自动报告 agent
- ❌ 生产环境部署
- ❌ TRAE task 配置

### 9.3 成功标准

M3C-6E1 完成标志：

1. ✅ Query Pack 可以被解析和验证
2. ✅ Source Registry 可以按 query pack 做路由选择
3. ✅ Base Evidence Packet 可以被构造和验证
4. ✅ Dry-run 可以输出「如果真实执行会查哪些源、预计返回多少 packets」
5. ✅ 全 pytest 通过
6. ✅ 明确的边界文档证明「不输出投资结论」
7. ✅ 没有任何估值 / 评级 / 交易相关代码进入 Foundation

---

## 10. M3C-6E2 下游接入建议

### 10.1 M3C-6E2 目标

在 th_capital_stock 中接入 Foundation on-demand layer，验证端到端链路。

### 10.2 建议范围

1. **th_capital_stock 侧新增**：
   - Query Pack 生成器（从 watchlist / research question 生成 query pack）
   - Evidence Packet 消费器（接收 Foundation 输出，转为 SMR 内部格式）
   - 投资解释层（在 evidence 基础上生成 expectation_change / valuation_impact）

2. **Foundation 侧增量**：
   - 1-2 个真实源的 on-demand 接入试点（如 SEC 申报、公开 transcript）
   - 异步回调机制
   - 结果分页

3. **不做**：
   - ❌ 全量源接入
   - ❌ 生产环境
   - ❌ 自动交易

### 10.3 成功标准

- th_capital_stock 可以通过 Foundation on-demand API 获取结构化证据
- 证据包可以被下游正确消费和解读
- 边界清晰：Foundation 侧无任何投资判断代码
- 数据回流：evidence → interpretation → thesis 的链路打通（但全在下游）

---

## 11. 风险与缓解

| 风险 | 等级 | 缓解措施 |
|---|---|---|
| 范围蔓延：不自觉加入投资判断逻辑 | 高 | CI 检查 + code review 清单 + 边界测试 |
| 下游依赖过重：Foundation 需要理解太多业务 | 中 | 严格分层；只提供原语，不组装业务 |
| 数据源质量不可控 | 中 | source registry 可信度分级 + evidence_strength 标记 + cannot_conclude 强制字段 |
| 性能问题：on-demand 查询太慢 | 低 | M3C-6E1 只 dry-run，不优化性能 |
| 合规风险：输出投资建议 | 极高 | 硬边界 + 自动化测试 + 人工审计 |

---

## 12. 参考来源

本设计参考了 th_capital_stock 的以下模块（设计复用，非代码迁移）：

- `smr_source_registry.py` — Source Registry 模式
- `smr_evidence_memory_schema.json` — Evidence Packet schema 设计
- `smr_data_health.py` — 健康状态机设计
- `smr_phase182_intelligence_scout_prompt_pack.py` — Query Pack 思路
- `smr_phase92_ticker_entity_resolver.py` — 实体解析设计
- `smr_blocker_source_router.py` — 源路由 + 降级设计
- `source_registry.md` — 40+ 投资源的分类体系

---

## 13. M3C-6E1 实现状态

M3C-6E1 已实现以下内容（dry-run only）：

### 13.1 已实现

| 模块 | 文件 | 状态 |
|---|---|---|
| Query Pack Schema | `src/opc_foundation/source_inventory/investment_on_demand.py` | ✅ |
| Source Routing Metadata | 同上 | ✅ |
| Base Evidence Packet Schema | 同上 | ✅ |
| Investment Source Taxonomy | 同上 | ✅ |
| Dry-run Runner | `scripts/run_investment_on_demand_registry.py` | ✅ |
| Check Script | `scripts/check_investment_on_demand_registry.py` | ✅ |
| Example Config | `configs/foundation_investment_on_demand_registry.example.yaml` | ✅ |
| Tests | `tests/source_inventory/test_investment_on_demand.py` | ✅ |
| Tests | `tests/scripts/test_investment_on_demand_registry.py` | ✅ |

### 13.2 Dry-run 结果

- route_plan_count: 7（9 类源中 7 类 foundation_allowed）
- skipped_route_count: 2（付费研报 + 市场数据）
- evidence_packet_skeleton_count: 7
- real_fetch: false
- production_enabled: false
- forbidden_fields_absent: true

### 13.3 边界验证

- ✅ 9 个禁止投资字段全部不存在
- ✅ 16 个敏感关键词模式全部未检测到
- ✅ runner 脚本无 forbidden network imports
- ✅ runner 脚本无 forbidden network calls
- ✅ 无 Playwright/Selenium
- ✅ 不修改 trial_v2 allowlist
- ✅ 不修改 TRAE scheduling
- ✅ 不修改 merck_ir observation task
- ✅ 不配置 production
