"""Research Source Foundation —— 研究信息源采集与归档底座。

功能说明（小白解读）：
    这个包提供一套可复用的"研究型信息源"采集、标准化、归档、去重、
    健康检查和索引输出能力，供多个下游项目（th_capital_stock、
    thcapital-content-department、opc_Demand_Radar 等）消费。

    它只负责把外部研究信息稳定、合规、结构化地搬回本地，形成可被下游
    系统消费的标准文档资产。Foundation 不做任何投研判断。

Phase 1 MVP 支持的 source types：
    - rss_feed          读取 RSS/Atom feed
    - wechat_archive    读取已有微信公众号归档索引
    - manual_url        读取手工 URL 文件并抓取

典型用法：
    from opc_foundation.research.config import load_research_config
    from opc_foundation.research.archiver import ResearchArchiver

    cfg = load_research_config("configs/research_sources.example.yaml")
    archiver = ResearchArchiver(cfg)
    result = archiver.run()

模块子文件职责：
    - models.py        数据模型（source config / candidate / document / health / run result）
    - config.py        配置加载与校验
    - canonicalize.py  URL 规范化
    - connectors/      各类 source 的连接器
    - fetcher.py       HTTP 抓取
    - extractor.py     HTML 正文抽取
    - markdown.py      Markdown 生成
    - dedupe.py        SQLite 去重 SeenStore
    - storage.py       本地目录与文件写入
    - reports.py       中文 Markdown 日报
    - archiver.py      串联所有模块的主入口
    - cli.py           typer CLI 命令入口
"""
from __future__ import annotations
