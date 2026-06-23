# Checklist

## 文档完整性
- [ ] `docs/source_migration_from_th_capital_stock.md` 存在
- [ ] 文档包含 Purpose 章节（核心原则：Foundation 提供基础设施，业务系统保留判断力）
- [ ] 文档包含 Source Audit Summary（source family 决策表）
- [ ] 文档包含 Migration Decision Matrix（完整决策矩阵，含 Decision / Priority / Target Module）
- [ ] 文档包含 P0 Target: Official Filing Foundation（SEC / CNINFO / HKEX）
- [ ] 文档包含 P1 Target: Document Extraction Foundation
- [ ] 文档包含 P1/P2 Target: Market Data / Market Flow
- [ ] 文档包含 P2 Target: Research/News Harmonization
- [ ] 文档包含 Partial Migration Candidates（procurement / IR interaction / iFinD）
- [ ] 文档包含 Do Not Migrate（factor / valuation / opportunity / risk / trade signal）
- [ ] 文档包含 Target Architecture（长期目标架构图）
- [ ] 文档包含 Downstream Consumption Contract（标准输出路径）
- [ ] 文档包含 Forbidden Business Fields（禁止字段清单）
- [ ] 文档包含 Recommended Roadmap（M0-M6 路线图）

## 关键决策验证
- [ ] official_filing 标记为 P0
- [ ] M1A: Official Filing Foundation SPEC 是下一步
- [ ] iFinD 只迁 client，不迁业务 adapter
- [ ] tender / IR interaction 必须先解耦业务逻辑
- [ ] factor / valuation / opportunity / risk / trade signal 明确不迁

## 主文档更新
- [ ] `docs/research_source_foundation.md` 包含 Cross-Repo Source Migration 章节
- [ ] `docs/research_source_foundation.md` 链接到迁移 SPEC 文档
- [ ] `docs/research_source_production_readiness.md` 包含 Cross-Repo Migration Outlook 章节
- [ ] `docs/research_source_production_readiness.md` 提到 official filings 作为下一扩展方向

## 测试
- [ ] `tests/research/test_source_migration_spec_docs.py` 存在
- [ ] `python -m pytest tests/research -v` 全绿
- [ ] `python -m pytest tests/wechat -v` 全绿
- [ ] `python -m pytest -q` 全绿

## 边界检查
- [ ] 没有新增 connector
- [ ] 没有迁移 th_capital_stock 代码
- [ ] 没有访问真实网站
- [ ] 没有新增依赖
- [ ] 没有 local config
- [ ] 没有 data/
- [ ] 没有 secrets
- [ ] 没有 th_capital_stock 修改
- [ ] 没有业务判断字段进入模型或标准输出
- [ ] 没有打 tag