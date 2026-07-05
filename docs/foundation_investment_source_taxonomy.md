# Investment Source Taxonomy

> 阶段：M3C-6E1
> 模块：`src/opc_foundation/source_inventory/investment_on_demand.py`

---

## 1. 分类总览

Foundation 将投资信息源分为 9 大类，每类有明确的边界：

| source_type | 描述 | foundation_allowed | requires_downstream |
|---|---|---|---|
| official_filing | 公司公告、法定披露、交易所文件 | ✅ | ❌ |
| company_ir | IR 页面、新闻稿、活动、演示稿 | ✅ | ❌ |
| sellside_research_public | 公开洞察、播客、会议纪要、公开研究摘要 | ✅ | ❌ |
| sellside_research_paid_or_entitled | 付费或授权经纪商研究 | ❌ | ✅ |
| public_news | 公开新闻和媒体摘要 | ✅ | ❌ |
| transcript | 公开电话会、会议或访谈文字稿 | ✅ | ❌ |
| market_data | 行情 / K线 / 因子数据 | ❌ | ✅ |
| macro | 宏观数据和评论 | ✅ | ❌ |
| industry_report | 公开行业报告、白皮书、会议材料 | ✅ | ❌ |

---

## 2. 各分类详解

### 2.1 official_filing

- **描述**：公司公告、法定披露、交易所文件
- **foundation_allowed**: ✅ true
- **requires_downstream**: ❌ false
- **典型来源**：CNINFO（A 股公告）、HKEX（港股公告）、SEC（美股申报）
- **证据强度**：strong_direct_disclosure（最高）
- **风险边界**：公开信息，可直接采集

### 2.2 company_ir

- **描述**：投资者关系页面、新闻稿、活动、演示稿
- **foundation_allowed**: ✅ true
- **requires_downstream**: ❌ false
- **典型来源**：公司 IR 页面、业绩稿、演示稿、webcast 页面
- **证据强度**：management_commentary
- **风险边界**：公开信息，可直接采集

### 2.3 sellside_research_public

- **描述**：公开洞察、播客、会议纪要、公开研究摘要
- **foundation_allowed**: ✅ true
- **requires_downstream**: ❌ false
- **典型来源**：Goldman Sachs Podcasts、MarketScreener 公开摘要、公开会议纪要
- **证据强度**：business_context / proxy_signal
- **风险边界**：只采集公开部分，不绕付费墙

### 2.4 sellside_research_paid_or_entitled

- **描述**：付费或授权经纪商研究
- **foundation_allowed**: ❌ false
- **requires_downstream**: ✅ true
- **典型来源**：Morgan Stanley Research、J.P. Morgan Research、Citi Research
- **风险边界**：**不绕过授权或许可**。Foundation 跳过此类源，建议下游手动或通过授权链路接入。
- **路由行为**：route 被放入 `skipped_routes`，`risk_flags` 包含 `entitlement_required`，`recommended_action = downstream_manual_or_entitled_access_only`

### 2.5 public_news

- **描述**：公开新闻和媒体摘要
- **foundation_allowed**: ✅ true
- **requires_downstream**: ❌ false
- **典型来源**：东方财富新闻、财联社、公开媒体
- **证据强度**：proxy_signal / risk_or_contradictory_signal
- **风险边界**：公开信息，可直接采集

### 2.6 transcript

- **描述**：公开电话会、会议或访谈文字稿
- **foundation_allowed**: ✅ true
- **requires_downstream**: ❌ false
- **典型来源**：The Motley Fool transcripts、公开 earnings call 文字稿
- **证据强度**：management_commentary
- **风险边界**：公开信息，可直接采集

### 2.7 market_data

- **描述**：行情 / K线 / 因子数据
- **foundation_allowed**: ❌ false
- **requires_downstream**: ✅ true
- **典型来源**：A/H/US 日线行情、趋势因子、基本面因子
- **风险边界**：**行情数据是投资业务逻辑**，由下游 th_capital_stock 负责。Foundation 不承接。
- **路由行为**：route 被放入 `skipped_routes`，`recommended_action = handled_by_th_capital_stock`

### 2.8 macro

- **描述**：宏观数据和评论
- **foundation_allowed**: ✅ true
- **requires_downstream**: ❌ false
- **典型来源**：国家统计局、人民银行、海关进出口数据
- **证据强度**：business_context
- **风险边界**：公开信息，可直接采集

### 2.9 industry_report

- **描述**：公开行业报告、白皮书、会议材料
- **foundation_allowed**: ✅ true
- **requires_downstream**: ❌ false
- **典型来源**：公开行业白皮书、会议材料、行业评论
- **证据强度**：business_context / proxy_signal
- **风险边界**：公开信息，可直接采集

---

## 3. 边界规则

### 3.1 付费研报不绕过

```python
# 验证规则
if source_type == "sellside_research_paid_or_entitled":
    foundation_allowed = false
    requires_downstream = true
    risk_flags includes "entitlement_required"
    recommended_action = "downstream_manual_or_entitled_access_only"
```

### 3.2 市场数据由下游负责

```python
# 验证规则
if source_type == "market_data":
    foundation_allowed = false
    requires_downstream = true
    recommended_action = "handled_by_th_capital_stock"
```

### 3.3 Foundation 允许的源类型

```python
FOUNDATION_ALLOWED_SOURCE_TYPES = {
    "official_filing",
    "company_ir",
    "sellside_research_public",
    "public_news",
    "transcript",
    "macro",
    "industry_report",
}
```

### 3.4 下游专属源类型

```python
DOWNSTREAM_ONLY_SOURCE_TYPES = {
    "sellside_research_paid_or_entitled",
    "market_data",
}
```
