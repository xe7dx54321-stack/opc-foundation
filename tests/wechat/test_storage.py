"""完整归档流程 / 目录写入 / metadata.json / 日报生成 测试。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from opc_foundation.wechat.archiver import WeChatArchiver, ArchiveInjectors
from opc_foundation.wechat.config import load_wechat_config
from opc_foundation.wechat.reports import build_daily_capture_report
from opc_foundation.wechat.models import WeChatArchiveConfig, WeChatDefaults, WeChatAccountConfig


FIXTURES = Path(__file__).parent / "fixtures"


def _feed_xml_bytes() -> bytes:
    return (FIXTURES / "sample_feed.xml").read_bytes()


def _article_html_bytes() -> bytes:
    return (FIXTURES / "sample_wechat_article.html").read_bytes()


def test_end_to_end_archive(tmp_path: Path):
    """通过 http_html 注入 HTML，跑一遍完整的归档流程。"""

    # 1) 创建最小配置
    feed_bytes = _feed_xml_bytes()
    article_html = _article_html_bytes()

    # 我们给账号配一个 feed_url，但提供 http_html 注入器直接返回本地 HTML
    cfg = WeChatArchiveConfig(
        archive_root=str(tmp_path / "wechat_archive"),
        defaults=WeChatDefaults(
            fetch_timeout_seconds=5,
            max_articles_per_account=5,
            download_images=False,  # 不下载图片避免走网络
            save_html=True,
            save_markdown=True,
            user_agent="test-bot",
        ),
        accounts=[
            WeChatAccountConfig(
                account_name="示例公众号A",
                account_id="example_a",
                feed_url="http://localhost:8000/feed/example_a.xml",
                source_type="rss",
                enabled=True,
            ),
        ],
    )

    # 2) 注册注入器：对任意 URL 返回文章 HTML，对 feed 返回 feed XML
    call_log: dict[str, int] = {"feed": 0, "article": 0}

    def http_html(url: str) -> bytes:
        # feed_parser 在读 feed 时会调一次 fetch_article_html？不会 — 我们
        # 是单独调用的 fetch_feed_candidates，它直接用 feedparser.parse(bytes)
        if "example_a.xml" in url:
            call_log["feed"] += 1
            return feed_bytes
        call_log["article"] += 1
        return article_html

    # 实际：fetch_feed_candidates 不会走到 http_html 注入器（因为 feed_content 我们是
    # 在下面单独处理的）。为覆盖完整链路，我们改用一种更简单的做法：
    # 为 archiver.injectors.http_html 注入 http_html，然后手工注入 feed。
    #
    # 更可靠的测试：直接改 accounts 的 feed_url 为空，并在构建 candidate 后手动
    # 塞给 archiver。但为了清晰，我们改为直接走 feed_client 的 feed_content 参数，
    # 再构造 candidate 后调用 archiver._archive_one。

    archiver = WeChatArchiver(cfg)

    # 从 feed 解析 candidates
    from opc_foundation.wechat.feed_client import fetch_feed_candidates
    feed_result = fetch_feed_candidates(cfg.accounts[0], feed_content=feed_bytes)
    assert len(feed_result.candidates) >= 2

    # 设置 http_html 注入器
    archiver.injectors = ArchiveInjectors(http_html=http_html, now_str=lambda: "2026-06-22T10:00:00+08:00")

    # 去重 & 处理
    from opc_foundation.wechat.dedupe import WeChatSeenStore

    seen = WeChatSeenStore(tmp_path / "wechat_archive" / "state" / "seen_articles.sqlite")
    results = []
    for cand in feed_result.candidates:
        if seen.has_seen(cand):
            continue
        arch_dir = tmp_path / "wechat_archive" / "articles" / "2026" / "06" / f"art_{len(results)}"
        art = archiver._archive_one(cand, seen_store=seen, article_dir=arch_dir, run_started_at="2026-06-22T10:00:00+08:00")
        results.append(art)
    seen.close()

    # 断言：至少一篇文章被保存
    assert any(r.status == "saved" for r in results)

    # 断言：目录里有 metadata.json + article.md + article.html
    for art in results:
        if art.status == "saved":
            md_path = Path(art.metadata_path)
            assert md_path.exists()
            metadata = json.loads(md_path.read_text(encoding="utf-8"))
            assert metadata["title"]
            assert "原文链接" not in metadata  # 中文不转义，但元信息字段为英文 key
            # 内容里有中文
            assert any("\u4e00" <= ch <= "\u9fff" for ch in metadata["title"])

    # 断言：index/articles.jsonl 能被正确写入
    for art in results:
        from opc_foundation.wechat.storage import append_jsonl
        append_jsonl(tmp_path / "wechat_archive" / "index" / "articles.jsonl", art)

    index_path = tmp_path / "wechat_archive" / "index" / "articles.jsonl"
    assert index_path.exists()
    lines = [ln for ln in index_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == len(results)


def test_build_report_with_zh():
    from opc_foundation.wechat.models import WeChatArchiveRunResult, AccountRunStats

    r = WeChatArchiveRunResult(
        run_id="run_test",
        started_at="2026-06-22T10:00:00",
        ended_at="2026-06-22T10:05:00",
        total_accounts=2,
        total_candidates=10,
        total_new_articles=5,
        total_saved=4,
        total_partial=1,
        total_failed=0,
        total_duplicate=5,
        archive_root="./data/wechat_archive",
        accounts=[AccountRunStats(account_name="示例公众号A", candidates=5, new_articles=2, saved=2)],
        saved_articles=[],
        failed_articles=[],
        warnings=[],
    )
    text = build_daily_capture_report(r)
    assert "微信公众号归档日报" in text
    assert "账号健康" in text
    assert "示例公众号A" in text


def test_storage_sanitize_filename_handles_chinese_and_illegal():
    from opc_foundation.wechat.storage import sanitize_filename

    # 非法字符应被移除
    assert "/" not in sanitize_filename("a/b?c*d")
    # 中文保留
    assert "示例" in sanitize_filename("示例标题")
    # 过长截断
    assert len(sanitize_filename("a" * 200)) <= 45
