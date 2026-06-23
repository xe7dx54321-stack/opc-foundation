# Tasks

- [ ] Task 1: 创建迁移 SPEC 文档 `docs/source_migration_from_th_capital_stock.md`
  - [ ] SubTask 1.1: 编写 Purpose 章节（核心原则、可承接/不承接清单）
  - [ ] SubTask 1.2: 编写 Source Audit Summary 章节（source family 决策表）
  - [ ] SubTask 1.3: 编写 Migration Decision Matrix 章节（完整决策矩阵）
  - [ ] SubTask 1.4: 编写 P0 Target: Official Filing Foundation 章节
  - [ ] SubTask 1.5: 编写 P1 Target: Document Extraction Foundation 章节
  - [ ] SubTask 1.6: 编写 P1/P2 Target: Market Data / Market Flow 章节
  - [ ] SubTask 1.7: 编写 P2 Target: Research/News Harmonization 章节
  - [ ] SubTask 1.8: 编写 Partial Migration Candidates 章节（procurement / IR interaction / iFinD）
  - [ ] SubTask 1.9: 编写 Do Not Migrate 章节
  - [ ] SubTask 1.10: 编写 Target Architecture 章节
  - [ ] SubTask 1.11: 编写 Downstream Consumption Contract 章节
  - [ ] SubTask 1.12: 编写 Forbidden Business Fields 章节
  - [ ] SubTask 1.13: 编写 Recommended Roadmap 章节

- [ ] Task 2: 更新 `docs/research_source_foundation.md`
  - [ ] SubTask 2.1: 新增 Cross-Repo Source Migration 章节，包含决策摘要表和链接

- [ ] Task 3: 更新 `docs/research_source_production_readiness.md`
  - [ ] SubTask 3.1: 新增 Cross-Repo Migration Outlook 章节

- [ ] Task 4: 创建测试 `tests/research/test_source_migration_spec_docs.py`
  - [ ] SubTask 4.1: 测试迁移 SPEC 文档存在
  - [ ] SubTask 4.2: 测试文档包含 official_filing / SEC / CNINFO / HKEX
  - [ ] SubTask 4.3: 测试文档明确 Official Filing Foundation 是 P0
  - [ ] SubTask 4.4: 测试文档明确 M1A 是下一步
  - [ ] SubTask 4.5: 测试文档包含 document_extraction / market_data / market_flow
  - [ ] SubTask 4.6: 测试文档明确 factor / valuation / opportunity / risk / trade signal 不迁
  - [ ] SubTask 4.7: 测试文档明确 iFinD 只迁 client
  - [ ] SubTask 4.8: 测试文档明确 tender / IR interaction 必须先解耦
  - [ ] SubTask 4.9: 测试文档包含 downstream consumption contract
  - [ ] SubTask 4.10: 测试文档包含 Forbidden Business Fields
  - [ ] SubTask 4.11: 测试 research_source_foundation.md 链接迁移文档
  - [ ] SubTask 4.12: 测试 research_source_production_readiness.md 提到 official filings

- [ ] Task 5: 运行测试验证
  - [ ] SubTask 5.1: 运行 `python -m pytest tests/research -v`
  - [ ] SubTask 5.2: 运行 `python -m pytest tests/wechat -v`
  - [ ] SubTask 5.3: 运行 `python -m pytest -q`

# Task Dependencies
- [Task 4] depends on [Task 1] [Task 2] [Task 3]
- [Task 5] depends on [Task 4]
