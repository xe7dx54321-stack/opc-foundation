# Cross-Repo Source Migration Spec: th_capital_stock → opc-foundation

> 中文名：跨仓库信息源迁移规划
> 英文名：Cross-Repo Source Migration
> 所属项目：`opc-foundation`
> 变更类型：新增文档与路线图（ADD，仅文档）
> 阶段：Phase M0

---

## Why

`opc-foundation` 的 Research Source Foundation 已完成非微信自动源主线，标记为 Production Trial Ready。审计发现 `th_capital_stock` 仓库中存在大量可复用的信息源采集能力，但这些能力与业务判断逻辑（ticker 映射、估值、机会发现、风险判断等）混合在一起。

需要一个迁移 SPEC 明确：哪些能力应迁入 foundation、哪些不迁、迁移后的标准输出契约是什么，为后续 M1+ 开发提供路线图。

**核心原则：Foundation 提供基础设施，业务系统保留判断力。**

---

## What Changes

### 新增（ADDED）

- 新增迁移 SPEC 文档 `docs/source_migration_from_th_capital_stock.md`，包含完整的迁移决策矩阵、目标架构、下游消费契约、禁止字段清单
- 新增测试 `tests/research/test_source_migration_spec_docs.py`，验证文档完整性与边界约束
- 更新 `docs/research_source_foundation.md`，新增 Cross-Repo Source Migration 章节
- 更新 `docs/research_source_production_readiness.md`，新增 Cross-Repo Migration Outlook 章节

### 不做（NOT DOING）

- 不迁移 th_capital_stock 代码
- 不新增 connector
- 不新增 official_filing / market_data / document_extraction 实现
- 不访问真实网站
- 不新增依赖
- 不修改 th_capital_stock 仓库
- 不打 tag

---

## Impact

- Affected specs: `add-research-source-foundation`
- Affected code: `docs/research_source_foundation.md`、`docs/research_source_production_readiness.md`、`tests/research/`
- 新增文档为后续 M1-M6 开发提供路线图

---

## ADDED Requirements

### Requirement: Cross-Repo Source Migration SPEC Document

系统 SHALL 提供一份完整的跨仓库迁移 SPEC 文档，明确 th_capital_stock 中各类信息源的迁移决策、优先级、目标模块和边界约束。

#### Scenario: 文档存在且完整
- **WHEN** 开发者查看 `docs/source_migration_from_th_capital_stock.md`
- **THEN** 文档包含 13 个章节：Purpose、Source Audit Summary、Migration Decision Matrix、P0 Target、P1 Target、P1/P2 Target、P2 Target、Partial Migration、Do Not Migrate、Target Architecture、Downstream Consumption Contract、Forbidden Business Fields、Recommended Roadmap

#### Scenario: 迁移决策矩阵明确
- **WHEN** 开发者查看 Migration Decision Matrix
- **THEN** 矩阵包含所有 source family 的 Decision、Priority、Target Foundation Module
- **AND** official_filing 标记为 P0
- **AND** factor/valuation/opportunity/risk 标记为 No（不迁）

#### Scenario: 禁止字段清单明确
- **WHEN** 开发者查看 Forbidden Business Fields
- **THEN** 清单包含 affected_tickers、expectation_delta、investment_rating、trade_signal、watchlist、action_decision、recommendation、opportunity_score、risk_score、position_size、target_price
- **AND** 这些字段不得成为 foundation model/schema/output 字段

### Requirement: Migration Spec Test

系统 SHALL 提供测试验证迁移 SPEC 文档的完整性与边界约束。

#### Scenario: 测试通过
- **WHEN** 运行 `python -m pytest tests/research/test_source_migration_spec_docs.py -v`
- **THEN** 所有测试用例通过
- **AND** 验证文档存在、包含关键章节、明确 P0 方向、明确禁止字段

### Requirement: Foundation 文档更新

`docs/research_source_foundation.md` SHALL 包含 Cross-Repo Source Migration 章节，链接到迁移 SPEC 文档。

`docs/research_source_production_readiness.md` SHALL 包含 Cross-Repo Migration Outlook 章节，说明 official filings 是下一扩展方向。

#### Scenario: 主文档更新
- **WHEN** 开发者查看 `docs/research_source_foundation.md`
- **THEN** 文档包含 Cross-Repo Source Migration 章节
- **AND** 链接到 `docs/source_migration_from_th_capital_stock.md`

#### Scenario: 生产就绪文档更新
- **WHEN** 开发者查看 `docs/research_source_production_readiness.md`
- **THEN** 文档包含 Cross-Repo Migration Outlook 章节
- **AND** 提到 official filings 作为下一扩展方向
