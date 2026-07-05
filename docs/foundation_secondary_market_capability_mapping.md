# OPC Foundation × th_capital_stock 二级地市能力映射矩阵

> 阶段：M3C-6E0 Secondary Market Capability Reuse Audit
> 生成时间：2026-07-05
> th_capital_stock commit: ce83e4d
> OPC Foundation commit: c7ecb15

## 分类说明

| 分类 | 含义 |
|------|------|
| A. direct_reuse_candidate | 可较少改动后复用到 OPC Foundation |
| B. design_reference_only | 设计值得参考，代码与业务耦合较深，不直接搬 |
| C. foundation_should_own | 应下沉为 OPC Foundation 通用能力 |
| D. downstream_should_own | 应继续由 th_capital_stock 负责，Foundation 不承接 |
| E. do_not_migrate | 不应迁移，涉及业务判断、敏感配置、付费数据或项目专属逻辑 |

## 能力映射表

| capability_name | secondary_market_path | observed_files | current_owner | recommended_owner | reuse_category | dependencies | business_coupling | migration_difficulty | recommended_next_action | notes |
|---|---|---|---|---|---|---|---|---|---|---|
| Source Registry (Markdown-based) | 00_control/source_registry.md | smr_source_registry.py | th_capital_stock | split | C. foundation_should_own | markdown parser | low | low | 提取 source metadata schema 到 Foundation；保留下游业务层字段在 SMR | SMR 注册表有 40+ 源，字段比 Foundation 更丰富（Layer/Provider/Source Class/Entity Scope/Markets/Cadence/Freshness SLA/Cost/Confidence/Owner Profile） |
| Source Health / Freshness Gate | 08_scripts/lib/smr_data_health.py | smr_data_health.py, data_freshness_rules.json | th_capital_stock | split | C. foundation_should_own | sqlite3, market calendar | medium | medium | 提取 freshness status enum + health table schema 到 Foundation；下游保留 blocking level / module dependency 业务规则 | SMR 的 data health 有完整状态机（fresh/degraded/stale/missing/disabled/planned/unknown）+ 阻塞级别（none/warn/degrade/block）+ 模块依赖映射 |
| Evidence Memory Schema | config/evidence_memory_schema.json | smr_evidence_memory_schema.py, smr_evidence_memory_writer.py | th_capital_stock | split | A. direct_reuse_candidate | json schema validation | low | low | 提取 base EvidencePacket 字段（evidence_id/source_id/source_type/evidence_strength/confidence/limitation/cannot_conclude）到 Foundation | SMR schema 有 22 个必填字段 + 12 个可选字段，枚举完整（strength/confidence/usage/review_status） |
| Evidence Packet (Unified) | 08_scripts/lib/smr_evidence_lifecycle.py | smr_evidence_packet*, smr_phase200~207 | th_capital_stock | split | B. design_reference_only | LLM extraction, dirty-to-clean pipeline | high | medium | 只参考 packet 生命周期设计（dirty→clean→verified→reviewed），不搬代码 | SMR 有完整的证据包生命周期：dirty intake → clean classification → cross-source verification → formal packet → owner approval → execution |
| Document Text Extraction (PDF/HTML) | 08_scripts/lib/smr_document_text_extractor.py | smr_document_text_extraction.py, smr_document_text_extractor.py | th_capital_stock | foundation | A. direct_reuse_candidate | fitz/pypdf, BeautifulSoup | low | low | 可直接复用抽取原语（PDF/HTML/Markdown 抽取 + 空白归一化） | Foundation 已有 document_extraction 模块；SMR 版本多了 IR section splitter、quality flags、cache 机制 |
| IR Section Splitter | 08_scripts/lib/smr_ir_section_splitter.py | smr_ir_section_splitter.py, smr_ir_semantic_extractor.py | th_capital_stock | split | B. design_reference_only | LLM semantic extraction | medium | medium | 参考 section-aware 抽取设计；具体 IR 语义分类由下游定义 | SMR 有专门的 IR 文本分节 + 语义抽取，针对业绩稿/电话会/年报优化 |
| CNINFO PDF URL Extractor | 08_scripts/lib/smr_cninfo_pdf_url_extractor.py | smr_cninfo_pdf_url_extractor.py, smr_cninfo_source_identity.py | th_capital_stock | foundation | A. direct_reuse_candidate | requests, regex | low | low | 可直接复用到 official_filings/cninfo 模块 | Foundation 已有 cninfo connector；SMR 版本有更细的 PDF URL 提取和 source identity 规范化 |
| CNINFO Table Parser | 08_scripts/lib/smr_cninfo_table_parser.py | smr_cninfo_table_parser.py | th_capital_stock | foundation | B. design_reference_only | pdfplumber, table detection | medium | low | 参考表格解析思路，暂不迁移代码 | 针对 A 股公告 PDF 表格的专用解析器 |
| HKEX Table Parser | 08_scripts/lib/smr_hkex_table_parser.py | smr_hkex_table_parser.py | th_capital_stock | foundation | B. design_reference_only | html table parsing | medium | low | 参考港交所 HTML 表格解析模式 | 针对港交所披露易页面的表格解析 |
| Company IR Page Discovery | 08_scripts/lib/smr_company_ir_page_discovery.py | smr_company_ir_page_discovery.py, smr_real_ir_source_connector.py | th_capital_stock | split | C. foundation_should_own | web discovery, URL pattern matching | medium | medium | 下沉 IR 入口发现原语；具体公司 IR 模板匹配由下游维护 | SMR 有完整的 IR 页面发现 → 材料清单 → 文本抽取链路 |
| IR Semantic Extractor | 08_scripts/lib/smr_ir_semantic_extractor.py | smr_ir_semantic_extractor.py, smr_semantic_ir_evidence.py | th_capital_stock | downstream | B. design_reference_only | LLM, business variable taxonomy | high | high | 只参考提取模式；业务变量定义是下游核心资产 | 针对光模块/AI 等行业的业务变量（800G/1.6T/ASP/capacity/order visibility）语义提取 |
| Filings Ingestion Pipeline | 08_scripts/jobs/ingest_filings.py | smr_filings_ingestion.py, smr_filing_freshness.py, smr_filing_chunk_selector.py | th_capital_stock | split | B. design_reference_only | sqlite, chunking, freshness tracking | medium | medium | 参考 ingestion 流水线设计；具体业务过滤逻辑保留在下游 | SMR 有完整的公告摄取 → 分块 → 新鲜度跟踪 → 质量门禁流水线 |
| News Ingestion Pipeline | 08_scripts/jobs/ingest_news.py | smr_news_ingestion.py | th_capital_stock | split | B. design_reference_only | news search, dedup | medium | medium | 参考新闻摄取设计；具体新闻源和过滤逻辑保留在下游 | 东方财富新闻搜索 + 正文抓取 + 去重 |
| Market Data (Daily Bar) | 08_scripts/data_harvester/ah_daily_bar.py | ah_daily_bar.py, factor_engine/ | th_capital_stock | downstream | D. downstream_should_own | akshare, market calendar | high | high | 保留在二级市场项目；行情数据是投资业务专属 | A/H/US 日线行情、趋势因子、基本面因子、美股联动因子 |
| Watchlist / Universe | 08_scripts/lib/smr_paper_watchlist_*.py | smr_paper_watchlist_entry.py, smr_paper_watchlist_lifecycle.py, smr_paper_watchlist_triggers.py | th_capital_stock | downstream | D. downstream_should_own | paper portfolio, activation rules | high | high | 完全保留在下游；watchlist 业务含义是二级市场核心 | SMR 有完整的 watchlist 生命周期：entry → activation → tracking → review → closeout |
| Multi-ticker Universe | 08_scripts/lib/smr_multi_ticker_universe.py | smr_multi_ticker_universe.py, smr_phase84_daily_monitoring_universe.py | th_capital_stock | downstream | D. downstream_should_own | sector taxonomy, ticker mapping | high | high | 保留在下游；universe 定义是投资业务的一部分 | 动态公司池、行业映射、板块分类 |
| Query Builder / Prompt Pack | 08_scripts/lib/smr_phase182_intelligence_scout_prompt_pack.py | smr_phase182_*.py, smr_cn_tender_query_planner.py | th_capital_stock | split | B. design_reference_only | LLM prompt engineering | medium | medium | 参考 query pack 设计模式；具体 query 模板由下游维护 | SMR 有按行业/主题定制的 scout prompt pack + 查询规划器 |
| Entity Expansion (Ticker/Company/Industry) | 08_scripts/lib/smr_phase92_ticker_entity_resolver.py | smr_phase92_*, smr_phase93_*, smr_phase94_entity_resolver.py | th_capital_stock | split | C. foundation_should_own | entity resolution, ticker normalization | medium | medium | 下沉实体解析原语（ticker 归一化、别名扩展）；行业/供应链实体由下游维护 | SMR 有多层级实体解析：ticker → company → supply chain → customer → guidance/exploration |
| Claim Graph / Claim State Memory | 08_scripts/lib/smr_claim_graph.py | smr_claim_graph.py, smr_claim_state_memory.py | th_capital_stock | downstream | B. design_reference_only | graph structure, state tracking | high | high | 只参考设计；claim 状态追踪是投资研究业务核心 | 主张图谱：证据 → 主张 → 状态变化 → 预期影响 |
| Expectation Gap Model | 08_scripts/lib/smr_expectation_gap.py | smr_expectation_gap.py, smr_consensus_proxy.py, smr_live_consensus_proxy.py | th_capital_stock | downstream | E. do_not_migrate | consensus data, expectation model | very high | very high | 禁止下沉；预期差模型是二级市场核心 alpha 来源 | 一致预期代理、预期差计算、管理层语言变化 → 预期修正 |
| Valuation Model | 08_scripts/lib/smr_valuation.py | smr_valuation.py, smr_valuation_gate_v2.py, smr_phase85_valuation_*.py, smr_demand_valuation_linkage.py | th_capital_stock | downstream | E. do_not_migrate | DCF/PE/PB, peer valuation, demand-valuation linkage | very high | very high | 禁止下沉；估值模型是投资业务核心判断 | 同行估值、需求-估值联动、估值门禁、估值快照修复 |
| Target Price / Investment Rating | 08_scripts/lib/smr_recommendation_promotion.py | smr_recommendation_promotion.py, smr_promotion_*.py, smr_single_stock_thesis_builder.py | th_capital_stock | downstream | E. do_not_migrate | rating methodology, promotion criteria | very high | very high | 禁止下沉；投资评级和目标价是受监管的投资建议 | 评级提升/降级标准、目标价计算、个股论文构建 |
| Paper Portfolio / Position Sizing | 03_stock_pool/, 04_portfolio/ | smr_paper_portfolio.py, smr_portfolio_risk.py, smr_paper_watchlist_audit.py | th_capital_stock | downstream | E. do_not_migrate | portfolio construction, risk management | very high | very high | 禁止下沉；组合管理和仓位是交易业务核心 | 模拟组合、仓位计算、风险监控、回撤管理 |
| Trade Signal / Risk Control | 05_risk/ | smr_portfolio_risk.py, smr_proxy_signal_gate.py, smr_phase89_opportunity_risk.py | th_capital_stock | downstream | E. do_not_migrate | signal generation, risk rules | very high | very high | 禁止下沉；交易信号和风控是交易业务核心 | 风控规则、信号门禁、机会-风险评估 |
| Business Driver Tree | 08_scripts/lib/smr_business_driver_tree.py | smr_business_driver_tree.py, smr_business_source_inventory.py | th_capital_stock | downstream | D. downstream_should_own | industry knowledge, driver mapping | high | high | 保留在下游；业务驱动因子是行业研究核心资产 | 公司 → 业务线 → 驱动因子 → 信息源 映射树 |
| Human Review Workflow | 08_scripts/lib/smr_human_review_workflow.py | smr_human_review_workflow.py, smr_evidence_review_workbench.py, smr_evidence_review_queue.py | th_capital_stock | split | B. design_reference_only | review state machine, quality gate | medium | medium | 参考人工审核工作流设计；具体审核标准由下游定义 | 证据审核队列 → 工作台 → 批准/拒绝 → 质量门禁 |
| Event-driven Refresh Task | 08_scripts/lib/smr_event_driven_refresh_task.py | smr_event_driven_refresh_task.py, smr_event_trigger_audit.py | th_capital_stock | split | C. foundation_should_own | event detection, task triggering | medium | medium | 下沉事件驱动刷新原语；具体事件定义和触发规则由下游维护 | 事件检测 → 任务触发 → 证据刷新 → 状态更新 |
| Backtest Engine | 08_scripts/backtest/simple_backtest.py | simple_backtest.py | th_capital_stock | downstream | E. do_not_migrate | historical data, strategy backtest | high | high | 禁止下沉；回测是交易策略验证专属 | 简易回测、信号历史验证 |
| Report Generator (Investment Brief) | 06_reports/ | smr_investment_reports.py, smr_executive_brief_builder.py, smr_brief_style_contract.py | th_capital_stock | split | B. design_reference_only | LLM generation, style linting | high | medium | 参考报告生成器骨架；投资结论和风格由下游维护 | SMR 有完整的简报生成流水线 + 风格合约 + Lint 检查 |
| Thesis Builder / Thesis Memory | 02_research/ | smr_single_stock_thesis_builder.py, smr_thesis_strength_tracking.py, smr_thesis_inference.py | th_capital_stock | downstream | E. do_not_migrate | investment thesis, thesis state | very high | very high | 禁止下沉；投资论文是核心业务判断 | 个股论文构建、论文强度追踪、论文推理、论文依赖 |
| Market Calendar | 08_scripts/lib/smr_market_calendar.py | smr_market_calendar.py | th_capital_stock | foundation | A. direct_reuse_candidate | holiday data, trading session | low | low | 可直接复用交易日历工具（A/H/US 市场假期） | Foundation 可以抽象通用市场日历接口 |
| Chinese Text Normalizer | 08_scripts/lib/smr_chinese_text_normalizer.py | smr_chinese_text_normalizer.py | th_capital_stock | foundation | A. direct_reuse_candidate | regex, unicode normalization | low | low | 可直接复用到 Foundation 的文本预处理模块 | 中文繁简、全角半角、空格/换行归一化 |
| Chunk Quality Classifier | 08_scripts/lib/smr_chunk_quality_classifier.py | smr_chunk_quality_classifier.py | th_capital_stock | foundation | B. design_reference_only | text quality scoring | low | low | 参考分块质量评估方法 | 文本分块质量评分、低质量分块过滤 |
| Data Quality Gate | 08_scripts/lib/smr_data_quality_gate.py | smr_data_quality_gate.py, smr_phase100_quality_gate.py | th_capital_stock | split | C. foundation_should_own | quality rules, gate state machine | medium | medium | 下沉质量门禁框架；具体业务质量规则由下游维护 | 数据质量门禁、阶段门控、降级处理 |
| Fallback Text Fetcher / Normalizer | 08_scripts/lib/smr_fallback_text_fetcher.py | smr_fallback_text_fetcher.py, smr_fallback_text_normalizer.py | th_capital_stock | foundation | A. direct_reuse_candidate | HTTP fetch, retry, fallback | low | low | 可直接复用降级抓取 + 文本归一化链路 | 多源降级抓取、异常恢复、文本规范化 |
| Ifind Adapter (同花顺) | 08_scripts/lib/smr_ifind_adapter.py | smr_ifind_adapter.py, diagnose_ifind.py, ifind_client.py | th_capital_stock | downstream | E. do_not_migrate | commercial data, licensed API | high | high | 禁止下沉；付费数据源是下游专属 | iFinD 金融终端适配器、数据诊断 |
| External Sources (Sell-side Research) | 08_scripts/lib/smr_external_sources.py | smr_external_sources.py, smr_external_research.py | th_capital_stock | downstream | D. downstream_should_own | research aggregators, licensed content | medium | medium | 保留在下游；卖方研报接入是投资研究专属 | 东方财富研报、MarketScreener、公开电话会稿 |
| Bull/Bear/Base Framework | 08_scripts/lib/smr_bull_base_bear_frame.py | smr_bull_base_bear_frame.py, smr_bear_case*.py | th_capital_stock | downstream | E. do_not_migrate | investment framework, scenario analysis | very high | very high | 禁止下沉；多空框架是投资方法论核心 | 多空情景分析、看空论点、看空缓解、看空回应 |
| Phase-based Workflow Engine | 08_scripts/lib/smr_phase100_*.py ~ smr_phase130_*.py | 100+ phase modules | th_capital_stock | downstream | B. design_reference_only | state machine, phase orchestration | very high | high | 只参考阶段化工作流设计模式；不迁移 phase 引擎 | SMR 有 100+ 阶段模块，构成完整的投研自动化流水线 |
| Domain Registry | 08_scripts/lib/smr_phase101_domain_registry.py | smr_phase117_domain_registry.py, smr_phase115_domain_registry.py | th_capital_stock | split | B. design_reference_only | domain metadata, module registry | medium | low | 参考域注册表模式；具体域定义由下游维护 | 模块化域注册、能力发现、依赖管理 |
| Evidence-to-Claim Mapper | 08_scripts/lib/smr_evidence_to_claim_mapper.py | smr_evidence_to_claim_mapper.py | th_capital_stock | downstream | D. downstream_should_own | claim extraction, mapping logic | high | high | 保留在下游；主张提取是投研业务逻辑 | 证据 → 主张映射、主张类型分类 |
| Final Research Conclusion | 08_scripts/lib/smr_final_research_conclusion.py | smr_final_research_conclusion.py, smr_final_thesis_review.py | th_capital_stock | downstream | E. do_not_migrate | conclusion synthesis, review | very high | very high | 禁止下沉；最终研究结论是投资建议前置 | 研究结论综合、最终论文评审 |
| Supply Chain Source Registry | 08_scripts/lib/smr_phase93_supply_chain_source_registry.py | smr_phase93_supply_chain_source_registry.py, smr_supplier_exposure_model.py | th_capital_stock | downstream | D. downstream_should_own | supply chain data, exposure model | high | high | 保留在下游；供应链分析是行业研究专属 | 供应链源注册、供应商敞口模型、上下游映射 |
| Source Router (Blocker-aware) | 08_scripts/lib/smr_blocker_source_router.py | smr_blocker_source_router.py, smr_blocker_taxonomy.py | th_capital_stock | split | C. foundation_should_own | routing logic, blocker taxonomy | medium | medium | 下沉源路由框架；阻塞类型和路由策略由下游配置 | 阻塞感知的源路由、阻塞分类、降级路径 |

## 统计汇总

| reuse_category | count |
|---|---:|
| A. direct_reuse_candidate | 5 |
| B. design_reference_only | 14 |
| C. foundation_should_own | 8 |
| D. downstream_should_own | 10 |
| E. do_not_migrate | 10 |
| **总计** | **47** |

## 关键发现

1. **Foundation 可直接复用 5 项**：市场日历、中文文本归一化、PDF/HTML 文本抽取、CNINFO PDF URL 提取、降级抓取器
2. **应下沉为 Foundation 通用能力 8 项**：Source Registry 元数据、Source Health/Freshness、Evidence Packet 基础 schema、IR 页面发现、实体解析原语、事件驱动刷新、质量门禁框架、源路由框架
3. **设计参考 14 项**：证据包生命周期、IR 语义抽取、摄取流水线、查询规划、人工审核工作流、报告生成骨架、阶段化工作流等
4. **必须保留在下游 10 项**：行情数据、Watchlist/Universe、业务驱动树、卖方研报接入、主张映射、供应链源注册等
5. **绝对禁止迁移 10 项**：预期差模型、估值模型、目标价/投资评级、模拟组合、交易信号、回测引擎、iFinD 付费源、多空框架、论文构建、最终研究结论
