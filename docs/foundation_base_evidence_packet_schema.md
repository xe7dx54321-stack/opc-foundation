# Base Evidence Packet Schema

> 阶段：M3C-6E1
> 模块：`src/opc_foundation/source_inventory/investment_on_demand.py`

---

## 1. EvidencePacket 基础字段

Foundation 层的 Base Evidence Packet 只包含通用证据字段，不包含任何投资判断。

```python
@dataclass
class BaseEvidencePacket:
    # 标识
    evidence_id: str
    request_id: str

    # 来源
    source_type: str          # 9 大类之一
    source_name: str
    source_url: str
    title: str

    # 时间
    published_at: str         # YYYY-MM-DD or ISO datetime
    observed_at: str          # Foundation 抓取时间
    timestamp_confidence: str # HIGH / MEDIUM / LOW / NONE

    # 实体关联
    entity_refs: list[str]    # 关联实体名称
    topic_refs: list[str]     # 关联主题/行业

    # 内容
    key_claims: list[EvidenceClaimSkeleton]
    evidence_summary: str

    # 质量
    access_level: str         # public / registration_required / entitlement_required / paid_license_required
    is_primary_source: bool   # 是否一手来源
    is_media_recap: bool      # 是否媒体转述
    confidence: str           # high / medium / low
    evidence_strength: str    # 7 级证据强度

    # 风险
    risk_flags: list[str]
    cannot_conclude: str      # 必填（primary source）

    # 边界
    production_enabled: bool = False
    performs_real_fetch: bool = False
```

---

## 2. key_claims / evidence_summary

### 2.1 EvidenceClaimSkeleton

```python
@dataclass
class EvidenceClaimSkeleton:
    claim_text: str           # 主张文本
    claim_type: str           # management_commentary / data_point / skeleton
    confidence: str           # high / medium / low
    quoted_span: str          # 直接引文（如有）
    span_location: str        # 在原文中的位置
```

### 2.2 evidence_summary

证据摘要是一段自然语言文本，概括该证据包的核心内容。**不包含投资判断**。

示例：
> NVIDIA 在最新业绩会中提到 AI 数据中心需求强劲，但未披露具体订单量或客户 allocation。

---

## 3. timestamp_confidence

| 值 | 说明 | 典型场景 |
|---|---|---|
| HIGH | 精确到日的发布时间 | 法定公告、年报 |
| MEDIUM | 精确到月或周 | 月度报告、行业报告 |
| LOW | 只有大概时间 | IR 活动记录、新闻 |
| NONE | 无时间信息 | dry-run skeleton |

---

## 4. access_level

| 值 | 说明 | Foundation 处理 |
|---|---|---|
| public | 公开访问 | ✅ 可采集 |
| registration_required | 需注册 | ✅ 可采集（需注意 ToS） |
| entitlement_required | 需授权 | ❌ 跳过，下游手动 |
| paid_license_required | 需付费许可 | ❌ 跳过，下游手动 |

---

## 5. confidence

证据置信度是 Foundation 对该证据整体可信度的评估：

| 值 | 说明 |
|---|---|
| high | 一手来源、直接披露、时间精确 |
| medium | 一手来源但间接、或时间模糊 |
| low | 媒体转述、代理信号、时间未知 |

---

## 6. cannot_conclude

**每个 primary source 的 evidence packet 必须填写 `cannot_conclude` 字段。**

这个字段说明「基于这个证据，不能得出什么结论」，是防止证据过度解读的核心防线。

示例：
> **cannot_conclude**: 管理层提到「AI 需求强劲」不构成具体订单确认；公司未披露单一客户供应份额和 ASP 数据；不能直接推断收入增长。

---

## 7. 下游可扩展字段

以下字段**不属于 Foundation**，由 th_capital_stock 在下游扩展：

| 字段 | 说明 | 负责方 |
|---|---|---|
| ticker | 公司交易代码 | 下游 |
| company_name | 公司全名 | 下游 |
| industry | 行业分类 | 下游 |
| analyst_name | 分析师姓名 | 下游 |
| bank_name | 投行名称 | 下游 |
| business_variable | 业务变量（800G/ASP 等） | 下游 |
| claim_type | 投资主张类型 | 下游 |
| investment_implication | 投资含义 | 下游 |
| expectation_change | 预期变化 | 下游 |
| valuation_impact | 估值影响 | 下游 |
| risk_view | 风险观点 | 下游 |

---

## 8. Foundation 禁止字段

以下字段**绝对禁止**出现在 BaseEvidencePacket 中。验证器会检测并拒绝：

| 禁止字段 | 说明 |
|---|---|
| rating | 投资评级 |
| target_price | 目标价 |
| buy_sell_hold | 买入/卖出/持有 |
| investment_recommendation | 投资建议 |
| position_size | 仓位大小 |
| trade_signal | 交易信号 |
| expected_return | 预期回报 |
| valuation_upside | 估值上行空间 |
| portfolio_action | 组合操作 |

```python
FORBIDDEN_INVESTMENT_FIELDS = (
    "rating",
    "target_price",
    "buy_sell_hold",
    "investment_recommendation",
    "position_size",
    "trade_signal",
    "expected_return",
    "valuation_upside",
    "portfolio_action",
)
```

---

## 9. 与 th_capital_stock Evidence Memory 的关系

th_capital_stock 有自己的 `evidence_memory_schema.json`，包含 22 个必填字段 + 12 个可选字段。

Foundation 的 BaseEvidencePacket 是**子集**：

| Foundation 层（base） | 下游扩展层（business） |
|---|---|
| evidence_id | + ticker |
| source_type | + company_name |
| source_name | + industry |
| source_url | + business_variable |
| published_at | + claim_type |
| timestamp_confidence | + investment_implication |
| evidence_strength | + expectation_change |
| confidence | + valuation_impact |
| cannot_conclude | + risk_view |
| key_claims | + analyst_name |
| evidence_summary | + bank_name |

**关系**：
- Foundation 输出 base EvidencePacket
- 下游接收后扩展为完整 Evidence Memory 记录
- 下游负责所有投资解读和业务判断
- Foundation 永不输出投资结论
