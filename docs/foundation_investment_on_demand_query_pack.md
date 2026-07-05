# Investment On-demand Query Pack

> 阶段：M3C-6E1
> 模块：`src/opc_foundation/source_inventory/investment_on_demand.py`

---

## 1. Query Pack 的作用

Query Pack 是 on-demand 查询的**标准化输入格式**。它不是一个搜索词，而是一个结构化的研究需求描述，包含：

- 关注的公司 / 投行 / 行业 / 主题
- 时间窗口
- 研究问题
- 偏好的源类型
- 输出模式

Foundation 接收 Query Pack，计算路由计划，生成证据包骨架（dry-run）。

---

## 2. Dynamic Watchlist Input

**Foundation 不拥有 watchlist。** Watchlist 是下游（th_capital_stock）的概念。

Foundation 只接收查询时刻的 watchlist 快照：

```python
# 下游传入
query_pack = InvestmentQueryPack(
    request_id="research_2026_07_05_001",
    companies=[
        InvestmentEntity(name="NVIDIA", tickers=["NVDA"]),
        InvestmentEntity(name="Broadcom", tickers=["AVGO"]),
    ],
    industries=["AI optical interconnect"],
    banks=["Goldman Sachs"],
    research_questions=["What are top sell-side views on AI networking?"],
)
```

关键原则：
- **Foundation 不存 watchlist**：只接收查询时刻的快照
- **Foundation 不解释 watchlist**：entry 的业务含义由下游负责
- **Foundation 只做采集**：根据快照生成 evidence packets

---

## 3. 输入字段

### 3.1 Company / Ticker

```python
@dataclass
class InvestmentEntity:
    entity_type: str = "company"  # company / bank / industry / product / person
    name: str = ""
    tickers: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    entity_id: str = ""  # Foundation 内部实体 ID（解析后填充）
```

### 3.2 Industry

```python
industries: list[str]  # 行业名称列表
```

### 3.3 Topic

```python
@dataclass
class InvestmentTopic:
    topic_id: str = ""
    keywords: list[str] = field(default_factory=list)
    related_entities: list[str] = field(default_factory=list)
```

### 3.4 Bank

```python
banks: list[str]  # 投行名称列表
```

### 3.5 Research Questions

```python
research_questions: list[str]  # 研究问题列表
```

### 3.6 Time Window

```python
@dataclass
class TimeWindow:
    lookback_days: int = 30
    start_date: str = ""  # YYYY-MM-DD（可选覆盖）
    end_date: str = ""  # YYYY-MM-DD（可选覆盖）
    relative_window: str = ""  # e.g., "last_earnings_call"
```

---

## 4. Source Type 偏好

### 4.1 preferred_source_types

指定优先查询的源类型。如果为空，则查询所有 foundation_allowed 的源类型。

```python
preferred_source_types: list[str] = ["official_filing", "company_ir", "transcript"]
```

### 4.2 excluded_source_types

明确排除的源类型。

```python
excluded_source_types: list[str] = ["public_news"]  # 不要新闻
```

---

## 5. Output Mode

| 模式 | 说明 |
|---|---|
| `evidence_packet_skeleton_only` | 只生成证据包骨架（默认） |
| `route_plan_only` | 只生成路由计划 |
| `full_dry_run` | 路由计划 + 证据包骨架 |

M3C-6E1 阶段所有模式都是 dry-run，不真实抓取。

---

## 6. 示例

```yaml
example_query_pack:
  request_id: "example_ai_optical_interconnect"
  time_window:
    lookback_days: 30
  entities:
    companies:
      - name: "NVIDIA"
        tickers: ["NVDA"]
      - name: "Broadcom"
        tickers: ["AVGO"]
    industries:
      - "AI optical interconnect"
      - "silicon photonics"
    banks:
      - "Goldman Sachs"
      - "Morgan Stanley"
  research_questions:
    - "What are top sell-side views on AI data center networking demand?"
    - "What changed in optical interconnect expectations?"
  output_mode: "evidence_packet_skeleton_only"
```

> ⚠️ example_query_pack 只是样例，不是真实固定覆盖池。

---

## 7. 与 th_capital_stock 的接口

### Foundation 输入

下游（th_capital_stock）生成 Query Pack 并传入 Foundation：

```
th_capital_stock → Query Pack → Foundation
```

### Foundation 输出

Foundation 返回路由计划 + 证据包骨架：

```
Foundation → Route Plan + Evidence Packets → th_capital_stock
```

### 下游责任

th_capital_stock 负责：
- 生成 Query Pack（从 watchlist / research question 生成）
- 消费 Evidence Packets（转为 SMR 内部格式）
- 投资解读（在 evidence 基础上生成 expectation_change / valuation_impact）
- 所有投资判断（评级 / 目标价 / 交易信号）

---

## 8. 验证规则

Query Pack 验证器检查：
- `request_id` 不为空
- `production_enabled = false`
- `performs_real_fetch = false`
- `affects_trial_v2_allowlist = false`
- `affects_trae_scheduling = false`
- `output_mode` 在合法枚举内
- 至少包含一个 company / industry / topic / bank
- `preferred_source_types` 和 `excluded_source_types` 中的源类型合法
- 研究问题不含敏感关键词（cookie / token / proxy URL / secret）
