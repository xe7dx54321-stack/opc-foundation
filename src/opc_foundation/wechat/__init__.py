"""微信公众号文章归档子模块。

功能说明（小白解读）：
    这个包提供一套可复用的微信公众号文章抓取、去重、本地归档与日报生成能力。
    它不依赖微信客户端，而是通过 RSS / 第三方 feed 服务 / 手工投喂 URL 等外部输入来工作。

典型用法：
    from opc_foundation.wechat.config import load_wechat_config
    from opc_foundation.wechat.archiver import WeChatArchiver

    cfg = load_wechat_config("path/to/wechat_accounts.yaml")
    archiver = WeChatArchiver(cfg)
    result = archiver.run()

模块子文件职责：
    - config.py: 配置加载（accounts.yaml + 默认参数）
    - models.py: 数据模型（账号、候选文章、归档文章、运行结果）
    - feed_client.py: 读取 RSS/Atom feed 并转换为 ArticleCandidate
    - manual_url.py: 从纯 URL 生成 ArticleCandidate
    - dedupe.py: SQLite 去重 SeenStore
    - fetcher.py: HTTP 抓取正文（对 mp.weixin.qq.com 做基础解析）
    - extractor.py: 正文提取与噪声清洗
    - cleaner.py: 可配置噪声规则集
    - markdown.py: Markdown 生成
    - images.py: 图片下载 + Markdown/Html URL 改写
    - storage.py: 本地目录与文件写入辅助
    - archiver.py: 串联上面所有模块的主入口
    - reports.py: 中文 Markdown 日报
    - cli.py: typer CLI 命令入口
"""
from __future__ import annotations
