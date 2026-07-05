# OPC Foundation M3C-6E0：Secondary Market Capability Reuse Audit Report

> 阶段：M3C-6E0
> 审计类型：静态代码审计 + 能力复用评估
> 执行时间：2026-07-05
> 审计员：OPC Foundation Audit Pipeline

---

## 1. 执行概览

### 1.1 OPC Foundation 基线

| 项目 | 值 |
|---|---|
| 仓库路径 | /Users/apple/Documents/一人公司OPC/opc-foundation |
| 基准分支 | master |
| 基准 commit | c7ecb15 |
| 审计分支 | feature/m3c-6e0-secondary-market-reuse-audit |
| git status | clean |

### 1.2 th_capital_stock 基线

| 项目 | 值 |
|---|---|
| 仓库路径 | /Users/apple/Documents/同行资本二级市场 |
| remote | https://github.com/xe7dx54321-stack/th_capital_stock.git |
| 分支 | main |
| commit | ce83e4d |
| git status | 少量本地修改（00_control/dispatch_board.md, memory/） |
| 审计方式 | 只读静态扫描，未修改任何文件 |

---

## 2. 审计方法

### 2.1 扫描范围

- **主目录**：08_scripts/lib/（核心库，~150+ 模块）
- **配置目录**：00_control/（source_registry.md, data_freshness_rules.json 等）
- **配置文件**：config/（evidence_memory_schema.json 等）
- **Jobs 目录**：08_scripts/jobs/（业务流水线）
- **总扫描文件数**：200+ Python 模块 + 30+ 配置文件

### 2.2 关键词分组

| 分组 | 关键词 |
|---|---|
| Source / Connector | source, connector, adapter, fetch, crawler, rss, sitemap, manual_url, pdf, html, extract, ingest |
| Query / Search | query, search, tavily, bing, topic, watchlist, keyword, entity, company, ticker, industry |
| Evidence / Memory | evidence, memory, packet, claim, citation, source_url, published_at, confidence, report, summary |
| Business (do-not-migrate) | valuation, target_price, rating, portfolio, position, trade_signal, risk, thesis, expectation_gap |

### 2.3 审计原则

1. **只读不写**：不修改 th_capital_stock 任何文件
2. **边界清晰**：严格区分 Foundation 通用能力 vs 下游业务能力
3. **分类明确**：每个能力归入 5 类之一
4. **最小迁移**：优先复用设计，谨慎迁移代码
5. **业务判断不下沉**：投资评级、估值、交易信号绝对禁止迁移

---

## 3. 能力总览

### 3.1 能力分组统计

| capability_group | found_count | representative_files | reuse_summary |
|---|---:|---|---|
| Source Registry & Metadata | 5 | smr_source_registry.py, source_registry.md | 8 项应下沉，元数据模型可直接复用 |
| Data Health & Freshness | 4 | smr_data_health.py, data_freshness_rules.json | 状态机 + 健康表可下沉，业务阻塞规则保留下游 |
| Document Extraction (PDF/HTML) | 6 | smr_document_text_extractor.py, smr_cninfo_pdf_url_extractor.py | 5 项可直接复用，IR 专用抽取保留下游 |
| Evidence Packet & Memory | 8 | smr_evidence_memory_schema.py, smr_evidence_lifecycle.py | base schema 可下沉，生命周期参考设计 |
| IR / Filings Ingestion | 7 | smr_filings_ingestion.py, smr_company_ir_page_discovery.py | IR 发现可下沉，摄取流水线参考设计 |
| Query / Entity Expansion | 5 | smr_phase92_ticker_entity_resolver.py, smr_phase182_intelligence_scout_prompt_pack.py | 实体解析原语可下沉，query 模板保留下游 |
| Watchlist / Universe | 6 | smr_paper_watchlist_lifecycle.py, smr_multi_ticker_universe.py | 全部保留下游，是投资业务核心 |
| Valuation / Expectation / Rating | 8 | smr_valuation.py, smr_expectation_gap.py, smr_recommendation_promotion.py | 全部禁止迁移，是 alpha 核心 |
| Portfolio / Risk / Trade | 5 | smr_paper_portfolio.py, smr_portfolio_risk.py | 全部禁止迁移，是交易业务核心 |
| Report / Thesis / Conclusion | 6 | smr_investment_reports.py, smr_single_stock_thesis_builder.py | 骨架可参考，业务内容禁止下沉 |
| Quality / Workflow / Phase | 8 | smr_data_quality_gate.py, smr_human_review_workflow.py, 100+ phase modules | 框架可下沉，阶段引擎参考设计 |
| Market Data / Utilities | 6 | ah_daily_bar.py, smr_market_calendar.py, smr_chinese_text_normalizer.py | 工具类可复用，行情数据保留下游 |

### 3.2 分类汇总

| reuse_category | count | 占比 |
|---|---:|---:|
| A. direct_reuse_candidate | 5 | 10.6% |
| B. design_reference_only | 14 | 29.8% |
| C. foundation_should_own | 8 | 17.0% |
| D. downstream_should_own | 10 | 21.3% |
| E. do_not_migrate | 10 | 21.3% |
| **总计** | **47** | **100%** |

---

## 4. 已发现能力清单

完整清单见 [foundation_secondary_market_capability_mapping.md](./foundation_secondary_market_capability_mapping.md)。

---

## 5. direct_reuse_candidate 清单

可较少改动后复用到 OPC Foundation：

1. **市场日历**（smr_market_calendar.py）
   - A/H/US 市场假期、交易日计算
   - 可直接作为 Foundation 通用工具

2. **中文文本归一化**（smr_chinese_text_normalizer.py）
   - 繁简转换、全角半角、空白归一化
   - 可直接用于 Foundation 文本预处理

3. **PDF/HTML 文本抽取原语**（smr_document_text_extractor.py）
   - fitz/pypdf 双后端 PDF 抽取
   - BeautifulSoup HTML 正文提取
   - 与 Foundation document_extraction 模块高度互补

4. **CNINFO PDF URL 提取**（smr_cninfo_pdf_url_extractor.py）
   - 巨潮资讯 PDF 链接提取 + source identity 规范化
   - Foundation 已有 cninfo connector，可直接合并

5. **降级抓取器 + 文本归一化**（smr_fallback_text_fetcher.py, smr_fallback_text_normalizer.py）
   - 多源降级、重试、异常恢复
   - 可作为 Foundation 通用抓取降级框架

---

## 6. design_reference_only 清单

设计值得参考，但代码与业务耦合较深，不直接搬：

1. **证据包生命周期**：dirty → clean → verified → reviewed → formal
2. **IR 语义抽取**：按业务变量（800G/1.6T/ASP 等）从 IR 文本提取证据
3. **公告摄取流水线**：filing ingestion + chunking + freshness tracking
4. **新闻摄取流水线**：news search + article fetch + dedup
5. **查询规划器 / Prompt Pack**：按行业/主题定制的 scout 查询模板
6. **人工审核工作流**：review queue → workbench → approval → quality gate
7. **报告生成骨架**：brief builder + style contract + linting
8. **阶段化工作流引擎**：100+ phase 模块组成的投研自动化流水线
9. **域注册表模式**：domain registry + capability discovery
10. **分块质量分类器**：chunk quality scoring + low-quality filtering
11. **CNINFO 表格解析器**：A 股公告 PDF 表格专用解析
12. **港交所表格解析器**：HKEX 披露易页面表格解析
13. **IR 分节器**：IR 文档按章节切分 + 语义分类
14. **主张图谱设计**：evidence → claim → state → expectation impact

---

## 7. foundation_should_own 清单

应下沉为 OPC Foundation 通用能力：

1. **Source Registry 元数据模型**
   - source_key / name / data_type / provider / source_class / entity_scope / markets / update_frequency / freshness_sla / status / cost / confidence
   - Foundation 当前 source_inventory 模型较薄，可吸收 SMR 注册表的丰富字段

2. **Source Health / Freshness 状态机**
   - freshness status: fresh / degraded / stale / missing / disabled / planned / unknown
   - health table schema + 索引设计
   - 下游保留 blocking level 和 module dependency 业务规则

3. **Evidence Packet 基础 Schema**
   - evidence_id / source_id / source_type / source_title / evidence_strength / confidence / limitation / cannot_conclude / allowed_usage
   - 基础枚举（strength/confidence/usage）可直接复用
   - 下游增加业务字段（ticker/industry/business_variable/claim_type）

4. **IR 页面发现原语**
   - company IR page discovery + material listing
   - 通用发现模式可下沉，具体公司 IR 模板由下游维护

5. **实体解析原语**
   - ticker 归一化（A/H/US 格式统一）
   - 公司别名扩展
   - 行业/供应链实体由下游维护

6. **事件驱动刷新框架**
   - event detection → task triggering → evidence refresh
   - 通用事件驱动模型可下沉，具体事件定义由下游配置

7. **质量门禁框架**
   - quality gate state machine + pass/warn/degrade/block
   - 通用门禁机制可下沉，具体业务规则由下游配置

8. **源路由框架（阻塞感知）**
   - blocker-aware source routing + fallback paths
   - 通用路由框架可下沉，阻塞分类和策略由下游配置

---

## 8. downstream_should_own 清单

应继续由 th_capital_stock 负责，Foundation 不承接：

1. **行情数据接入**（ah_daily_bar, us_daily_bar, factor_engine）
2. **Watchlist / Universe 管理**（paper_watchlist, multi_ticker_universe）
3. **业务驱动因子树**（business_driver_tree, business_source_inventory）
4. **卖方研报接入**（external_research, external_sources）
5. **主张提取与映射**（evidence_to_claim_mapper, claim_graph）
6. **供应链源注册与分析**（supply_chain_source_registry, supplier_exposure_model）
7. **IR 语义抽取（业务变量层）**（ir_semantic_extractor, semantic_ir_evidence）
8. **公告摄取（业务过滤层）**（filings_ingestion 业务逻辑部分）
9. **新闻摄取（业务过滤层）**（news_ingestion 业务逻辑部分）
10. **行业研究（主题定制）**（industry-specific research logic）

---

## 9. do_not_migrate 清单

不应迁移，涉及业务判断、敏感配置、付费数据或项目专属逻辑：

1. **预期差模型**（expectation_gap, consensus_proxy, live_consensus_proxy）
   - 是二级市场核心 alpha 来源，绝对禁止下沉

2. **估值模型**（valuation, valuation_gate_v2, demand_valuation_linkage）
   - 投资业务核心判断，禁止下沉

3. **目标价 / 投资评级**（recommendation_promotion, rating, target_price）
   - 受监管的投资建议，绝对禁止 Foundation 承接

4. **模拟组合 / 仓位管理**（paper_portfolio, position_sizing）
   - 交易业务核心，禁止下沉

5. **交易信号 / 风控**（trade_signal, portfolio_risk, proxy_signal_gate）
   - 交易业务核心，禁止下沉

6. **回测引擎**（backtest, simple_backtest）
   - 交易策略验证专属，禁止下沉

7. **iFinD 付费数据源**（ifind_adapter, ifind_client）
   - 商业授权数据，禁止下沉到 Foundation

8. **多空框架**（bull_base_bear_frame, bear_case_*）
   - 投资方法论核心，禁止下沉

9. **投资论文构建**（single_stock_thesis_builder, thesis_strength_tracking）
   - 核心业务判断，禁止下沉

10. **最终研究结论**（final_research_conclusion, final_thesis_review）
    - 投资建议前置，绝对禁止 Foundation 输出

---

## 10. 风险与边界

### 10.1 技术风险

| 风险 | 等级 | 缓解措施 |
|---|---|---|
| 证据包 schema 兼容性 | 中 | Foundation 只定义 base schema，下游通过扩展字段适配 |
| Source Registry 字段膨胀 | 低 | 区分 core metadata（Foundation）vs business metadata（下游） |
| 抽取器双维护 | 低 | 以 Foundation 版本为主，下游按需扩展 |
| 阶段引擎依赖过重 | 高 | 不迁移 phase 引擎，只参考设计模式 |

### 10.2 业务边界风险

| 风险 | 等级 | 缓解措施 |
|---|---|---|
| 业务判断意外下沉 | 高 | 严格的 do_not_migrate 清单 + CI 检查 |
| Foundation 输出投资结论 | 极高 | 接口层明确禁止；输出只有 EvidencePacket / SourceObservation / ExtractedDocument |
| 付费数据源泄漏 | 中 | .env + secrets 严格 gitignore；audit script 扫描敏感信息 |
| 下游业务逻辑碎片化 | 中 | 清晰的接口定义；Foundation 提供原语，下游组装业务 |

### 10.3 合规边界

- **Foundation 永不输出**：投资评级、目标价、买卖建议、交易信号、估值结论
- **Foundation 只输出**：原始证据、源健康状态、抽取文本、查询结果、时间戳置信度
- **下游负责**：所有投资解释、预期变化、估值含义、风险观点、组合决策

---

## 11. M3C-6E1 建议迁移范围

### 11.1 包含（最小施工）

1. **On-demand Query Pack Schema**
   - 定义通用查询包结构：entities / time_window / preferred_source_types / research_questions

2. **Source Routing Metadata**
   - 扩展 source_inventory 模型，增加 source routing 所需元数据字段

3. **Base Evidence Packet Schema**
   - 从 SMR evidence_memory_schema 提取基础字段
   - 定义 Foundation 级 EvidencePacket dataclass

4. **Investment Source Taxonomy**
   - 投资领域源分类：official_filing / company_ir / sellside_research / public_news / market_data / macro

5. **Dry-run Runner**
   - 可执行的 on-demand 查询干跑器
   - 只做元数据验证和源选择，不触发真实抓取

6. **No Production**
   - M3C-6E1 阶段完全非生产
   - 只做 schema 定义和 dry-run 验证

### 11.2 不包含

1. ❌ 投资评级
2. ❌ 估值模型
3. ❌ 预期差模型
4. ❌ 股票推荐
5. ❌ 目标价
6. ❌ 组合决策
7. ❌ 自动报告 agent
8. ❌ 真实数据抓取（只 dry-run）

### 11.3 预计工作量

- **Schema 定义**：~2 天
- **Source Routing 元数据**：~2 天
- **Evidence Packet base schema**：~2 天
- **Dry-run runner**：~3 天
- **测试 + 文档**：~3 天
- **总计**：~12 人天

---

## 12. 边界确认

### 12.1 审计期间操作确认

| 检查项 | 状态 |
|---|---|
| 是否修改 th_capital_stock | ❌ 否（只读静态扫描） |
| 是否修改 OPC Foundation runtime / scheduling | ❌ 否 |
| 是否修改 trial_v2 allowlist | ❌ 否 |
| 是否修改 merck_ir observation task | ❌ 否 |
| 是否配置 production | ❌ 否 |
| 是否提交 data/local/secrets | ❌ 否 |
| 是否迁移投资评级 / 估值 / target price / 交易逻辑 | ❌ 否 |
| 是否打 tag | ❌ 否 |
| 是否引入 Playwright / Selenium | ❌ 否 |
| 是否恢复 Dashboard 已删除页面 | ❌ 否 |

### 12.2 merck_ir observation 影响确认

- observation task `foundation_low_frequency_merck_ir_observation_daily` 未受影响
- `production_enabled=false` 保持不变
- `observed_days` 计数不受本次审计影响

---

## 13. 测试结果

> 测试在审计分支执行，验证文档新增无回归。

| 测试套件 | 结果 |
|---|---|
| tests/source_inventory | 待执行 |
| tests/scripts | 待执行 |
| tests/dashboard | 待执行 |
| full pytest | 待执行 |

（实际测试结果见第 13 节测试执行后更新）

---

## 14. 相关文档

- [能力映射矩阵](./foundation_secondary_market_capability_mapping.md)
- [Investment On-demand Registry 设计](./foundation_investment_on_demand_registry_design.md)
- [Foundation Low-frequency Observation Harness](./foundation_low_frequency_observation_harness.md)
- [Source Migration from th_capital_stock（历史文档）](./source_migration_from_th_capital_stock.md)
