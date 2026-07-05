# OPC Foundation M3C-6E1：Investment On-demand Registry v1 Report

> 阶段：M3C-6E1
> 执行时间：2026-07-05
> 基线：M3C-6E0 合并后 master (bb5619d)

---

## 1. 执行信息

| 项目 | 值 |
|---|---|
| 执行时间 | 2026-07-05 |
| base commit | bb5619d (master, post-6E0 merge) |
| branch | feature/m3c-6e1-investment-on-demand-registry |
| 6E0 merge commit | bb5619d |
| trial_v2 source_count | 9 |
| production_enabled | false |
| merck_ir observation status | running, observed_days = 1 / 7 |

---

## 2. 为什么做 Investment On-demand Registry

OPC Foundation 的三层源架构：

| 层 | 名称 | 触发 | 代表源 |
|---|---|---|---|
| Layer 1 | High-frequency Trial | 每 6h 调度 | trial_v2 9 源 |
| Layer 2 | Low-frequency Observation | 每日 + 7 天观察 | merck_ir |
| Layer 3 | **On-demand Registry** | 事件 / 查询触发 | 投行观点、公司披露、研报 |

M3C-6E1 是 Layer 3 的第一个版本，只做 **dry-run registry**：把投研信息需求结构化为 Query Pack → Source Routing → Evidence Packet Skeleton，但**不真实抓取**。

---

## 3. 为什么不是普通关键词搜索

| 特性 | 普通搜索 | On-demand Registry |
|---|---|---|
| 来源质量 | 全网杂糅 | 注册源 + 可信度分级 |
| 输出结构 | 文本片段 | Evidence Packet（结构化字段） |
| 溯源能力 | URL 可能失效 | source_id + text_hash + span_location |
| 时间精度 | 模糊日期 | published_at + observed_at + timestamp_confidence |
| 实体解析 | 关键词匹配 | entity_id + ticker + aliases |
| 证据强度 | 无 | strong_direct / management_commentary / proxy_signal |
| 去重 | 基于 URL | 基于内容指纹 + 语义去重 |
| 投资判断 | ❌ 无 | ❌ 无（Foundation 不输出投资判断） |

---

## 4. Query Pack Schema

```python
@dataclass
class InvestmentQueryPack:
    request_id: str
    created_at: str
    time_window: TimeWindow
    companies: list[InvestmentEntity]
    industries: list[str]
    topics: list[InvestmentTopic]
    banks: list[str]
    research_questions: list[str]
    preferred_source_types: list[str]
    excluded_source_types: list[str]
    output_mode: str  # evidence_packet_skeleton_only / route_plan_only / full_dry_run
    risk_flags: list[str]
    # 边界标志
    production_enabled: bool = False
    performs_real_fetch: bool = False
    affects_trial_v2_allowlist: bool = False
    affects_trae_scheduling: bool = False
```

Foundation **不拥有 watchlist**，只接收下游传入的快照。Query Pack 是结构化的研究需求描述，不是单一关键词。

---

## 5. Source Routing Metadata

路由流程：
```
Query Pack → Entity Expansion → Source Type Matching → Quality Filter → Priority Ranking → Execution Plan
```

每个路由项包含：
- source_type（9 大类之一）
- foundation_allowed（是否符合 Foundation 边界）
- requires_downstream（是否必须由下游处理）
- expected_access_level（public / entitlement_required / paid_license_required）
- recommended_action（dry_run_route_only / downstream_manual / handled_by_th_capital_stock）

**降级规则**：
- 付费研报 → `foundation_allowed=false`，跳过，建议下游手动接入
- 市场数据 → `foundation_allowed=false`，跳过，由 th_capital_stock 处理

---

## 6. Base Evidence Packet Schema

```python
@dataclass
class BaseEvidencePacket:
    evidence_id: str
    request_id: str
    source_type: str
    source_name: str
    source_url: str
    title: str
    published_at: str
    observed_at: str
    timestamp_confidence: str  # HIGH / MEDIUM / LOW / NONE
    entity_refs: list[str]
    topic_refs: list[str]
    key_claims: list[EvidenceClaimSkeleton]
    evidence_summary: str
    access_level: str
    is_primary_source: bool
    is_media_recap: bool
    confidence: str  # high / medium / low
    evidence_strength: str
    risk_flags: list[str]
    cannot_conclude: str  # 必填（primary source）
    production_enabled: bool = False
    performs_real_fetch: bool = False
```

**禁止字段**（验证器拒绝）：
- rating, target_price, buy_sell_hold, investment_recommendation
- position_size, trade_signal, expected_return, valuation_upside, portfolio_action

---

## 7. Investment Source Taxonomy

| source_type | foundation_allowed | requires_downstream | 风险边界 |
|---|---|---|---|
| official_filing | ✅ | ❌ | 公开披露，可直接采集 |
| company_ir | ✅ | ❌ | 公开 IR 页面，可直接采集 |
| sellside_research_public | ✅ | ❌ | 公开洞察/播客/会议纪要 |
| sellside_research_paid_or_entitled | ❌ | ✅ | 不绕过授权/许可 |
| public_news | ✅ | ❌ | 公开新闻 |
| transcript | ✅ | ❌ | 公开电话会/会议文字稿 |
| market_data | ❌ | ✅ | 行情数据由下游负责 |
| macro | ✅ | ❌ | 宏观数据 |
| industry_report | ✅ | ❌ | 公开行业报告 |

---

## 8. Dry-run Runner 结果

```bash
python scripts/run_investment_on_demand_registry.py --example --dry-run
```

执行结果：
- **route_plan_count**: 7（9 类源中 7 类 foundation_allowed，2 类跳过）
- **evidence_packet_skeleton_count**: 7（每个路由生成 1 个 skeleton）
- **real_fetch**: false
- **production_enabled**: false
- **forbidden_fields_absent**: true

---

## 9. 边界确认

| 检查项 | 状态 |
|---|---|
| 是否修改 th_capital_stock | ❌ 否 |
| 是否真实联网 | ❌ 否 |
| 是否调用搜索 API | ❌ 否 |
| 是否修改 trial_v2 allowlist | ❌ 否 |
| 是否修改 TRAE scheduling | ❌ 否 |
| 是否修改 merck_ir observation task | ❌ 否 |
| 是否配置 production | ❌ 否 |
| 是否提交 data/local/secrets | ❌ 否 |
| 是否迁移投资评级 / 估值 / target price / 交易逻辑 | ❌ 否 |
| 是否包含投资判断字段 | ❌ 否（验证器拒绝） |
| 是否打 tag | ❌ 否 |
| 是否引入 Playwright / Selenium | ❌ 否 |
| 是否恢复 Dashboard 已删除页面 | ❌ 否 |

---

## 10. 测试结果

| 测试 | 结果 |
|---|---|
| check_investment_on_demand_registry | ✅ ALL CHECKS PASSED |
| tests/source_inventory/test_investment_on_demand | ✅ 62 passed |
| tests/scripts/test_investment_on_demand_registry | ✅ 16 passed |
| full pytest | 待全量执行 |

---

## 11. 相关文档

- [Query Pack 文档](./foundation_investment_on_demand_query_pack.md)
- [Source Taxonomy 文档](./foundation_investment_source_taxonomy.md)
- [Base Evidence Packet 文档](./foundation_base_evidence_packet_schema.md)
- [On-demand Registry 设计](./foundation_investment_on_demand_registry_design.md)
