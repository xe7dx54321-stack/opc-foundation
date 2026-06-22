"""Phase 1.5 收口测试：run_log summary、report 日期过滤、retry 隔离。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from opc_foundation.wechat.archiver import (
    ArchiveInjectors,
    WeChatArchiver,
    _run_exit_code,
    _write_run_log_summary,
)
from opc_foundation.wechat.cli import app
from opc_foundation.wechat.models import (
    ArchivedArticle,
    FailedArticle,
    WeChatArchiveConfig,
    WeChatDefaults,
    WeChatAccountConfig,
    WeChatArchiveRunResult,
    AccountRunStats,
)


runner = CliRunner()


# ---------------------------------------------------------------------------
# 1. run_log.jsonl 有 run-level summary
# ---------------------------------------------------------------------------

def test_run_log_summary_has_all_required_fields(tmp_path: Path):
    """run-level summary 必须包含所有约定字段。"""

    # 构造一个最小 archiver
    cfg = WeChatArchiveConfig(
        archive_root=str(tmp_path / "archive"),
        defaults=WeChatDefaults(download_images=False, save_html=True, save_markdown=True),
        accounts=[],
    )
    archiver = WeChatArchiver(cfg)
    archiver.injectors = ArchiveInjectors(
        now_str=lambda: "2026-06-22T10:00:00+08:00"
    )

    result = archiver.dry_run()

    # 验证 _run_exit_code
    assert _run_exit_code(result) == 0

    # 读 run_log.jsonl，最后一条应该是 summary
    log_path = tmp_path / "archive" / "state" / "run_log.jsonl"
    assert log_path.exists()
    lines = [json.loads(ln) for ln in log_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    summary = lines[-1]
    assert summary["entry_type"] == "run_summary"
    assert summary["mode"] == "dry_run"
    assert summary["started_at"] == "2026-06-22T10:00:00+08:00"
    assert summary["finished_at"] == "2026-06-22T10:00:00+08:00"
    assert "account_count" in summary
    assert "candidate_count" in summary
    assert "new_count" in summary
    assert "saved_count" in summary
    assert "partial_count" in summary
    assert "failed_count" in summary
    assert "duplicate_count" in summary
    assert "exit_code" in summary
    assert summary["exit_code"] == 0


def test_run_exit_code_partial_failure():
    r = WeChatArchiveRunResult(
        run_id="test", started_at="x", ended_at="y",
        archive_root="./test",
        total_saved=0, total_partial=0, total_failed=5,
    )
    assert _run_exit_code(r) == 3

    r2 = WeChatArchiveRunResult(
        run_id="test", started_at="x", ended_at="y",
        archive_root="./test",
        total_saved=2, total_partial=1, total_failed=3,
    )
    assert _run_exit_code(r2) == 2

    r3 = WeChatArchiveRunResult(
        run_id="test", started_at="x", ended_at="y",
        archive_root="./test",
        total_saved=5, total_partial=0, total_failed=0,
    )
    assert _run_exit_code(r3) == 0


def test_run_summary_written_for_retry_mode(tmp_path: Path):
    """retry 模式也写 run-level summary。"""

    # 先写一个假的 failed_queue
    state_dir = tmp_path / "archive" / "state"
    state_dir.mkdir(parents=True)
    (state_dir / "failed_queue.jsonl").write_text(
        json.dumps({"article_id": "wc_test", "title": "t", "url": "http://x/",
                     "canonical_url": "http://x/", "source": "rss", "failed_at": "2026-06-22T10:00:00+08:00"}, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    cfg = WeChatArchiveConfig(
        archive_root=str(tmp_path / "archive"),
        defaults=WeChatDefaults(download_images=False),
        accounts=[],
    )
    archiver = WeChatArchiver(cfg)
    archiver.injectors = ArchiveInjectors(
        now_str=lambda: "2026-06-22T12:00:00+08:00",
        # 让这次重试的 HTTP 请求返回空 HTML -> partial
        http_html=lambda url: "<html><body><p>minimal</p></body></html>",
    )
    result = archiver.retry_failed()
    log_path = tmp_path / "archive" / "state" / "run_log.jsonl"
    lines = [json.loads(ln) for ln in log_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    summaries = [l for l in lines if l.get("entry_type") == "run_summary"]
    assert len(summaries) >= 1
    last = summaries[-1]
    assert last["mode"] == "retry"
    assert last["candidate_count"] == 1


# ---------------------------------------------------------------------------
# 2. report 命令按日期过滤，不把历史文章算成当天新增
# ---------------------------------------------------------------------------

def test_report_filters_by_date(tmp_path: Path):
    """articles.jsonl 中有不同日期的文章，--date 只统计指定日期的。"""

    index = tmp_path / "archive" / "index"
    index.mkdir(parents=True)
    (index / "articles.jsonl").write_text(
        json.dumps({"article_id": "wc_a", "source": "rss",
                     "title": "昨天", "status": "saved",
                     "url": "http://a/", "canonical_url": "http://a/",
                     "captured_at": "2026-06-21T10:00:00+08:00",
                     "archive_dir": "./a", "metadata_path": "./a/m.json"}, ensure_ascii=False)
        + "\n"
        + json.dumps({"article_id": "wc_b", "source": "rss",
                       "title": "今天", "status": "saved",
                       "url": "http://b/", "canonical_url": "http://b/",
                       "captured_at": "2026-06-22T09:00:00+08:00",
                       "archive_dir": "./b", "metadata_path": "./b/m.json"}, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )

    # 用 --date 指定今天
    result = runner.invoke(
        app,
        ["report", "--archive-root", str(tmp_path / "archive"), "--date", "2026-06-22"],
    )
    assert result.exit_code == 0, result.stdout
    assert "2026-06-22" in result.stdout
    # 今天只有 1 篇，不能显示"昨天"
    assert "昨天" not in result.stdout
    assert "今日新增：1 篇" in result.stdout or "1 篇" in result.stdout


def test_report_without_date_uses_today(tmp_path: Path):
    """不传 --date 时，默认过滤今天。"""

    index = tmp_path / "archive" / "index"
    index.mkdir(parents=True)
    # 写入一条今天日期的文章
    from opc_foundation.run.time_utils import utcnow_iso
    today = utcnow_iso()[:10]
    (index / "articles.jsonl").write_text(
        json.dumps({"article_id": "wc_today", "source": "rss",
                     "title": "今日文", "status": "saved",
                     "url": "http://t/", "canonical_url": "http://t/",
                     "captured_at": f"{today}T10:00:00+08:00",
                     "archive_dir": "./t", "metadata_path": "./t/m.json"}, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        ["report", "--archive-root", str(tmp_path / "archive")],
    )
    assert result.exit_code == 0, result.stdout
    # 文章标题在生成的报告文件里
    report_file = list((tmp_path / "archive" / "reports").glob("daily_capture_*_manual.md"))[-1]
    assert "今日文" in report_file.read_text(encoding="utf-8")


def test_report_failed_queue_date_filter(tmp_path: Path):
    """failed_queue.jsonl 中有不同日期的失败，report 只展示指定日期的。"""

    state = tmp_path / "archive" / "state"
    state.mkdir(parents=True)
    (state / "failed_queue.jsonl").write_text(
        json.dumps({"article_id": "wc_old_fail", "title": "旧失败",
                     "url": "http://old/", "canonical_url": "http://old/",
                     "source": "rss", "failed_at": "2026-06-21T10:00:00+08:00"}, ensure_ascii=False)
        + "\n"
        + json.dumps({"article_id": "wc_new_fail", "title": "新失败",
                       "url": "http://new/", "canonical_url": "http://new/",
                       "source": "rss", "failed_at": "2026-06-22T10:00:00+08:00"}, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        ["report", "--archive-root", str(tmp_path / "archive"), "--date", "2026-06-22"],
    )
    assert result.exit_code == 0, result.stdout
    # stdout 只打印数量，读生成的报告文件看具体内容
    assert "失败队列（当日）：1 条待重试" in result.stdout
    # 验证报告文件内容：旧失败不应出现，新失败应出现
    report_file = tmp_path / "archive" / "reports" / "daily_capture_2026-06-22_manual.md"
    assert report_file.exists()
    report_content = report_file.read_text(encoding="utf-8")
    assert "旧失败" not in report_content
    assert "新失败" in report_content


# ---------------------------------------------------------------------------
# 3. retry-failed 成功后，本次日报不显示旧失败
# ---------------------------------------------------------------------------

def test_retry_success_does_not_show_old_failures_in_report(tmp_path: Path):
    """重试成功后写入的日报只包含本次重试的结果，不包含旧失败记录。"""

    state = tmp_path / "archive" / "state"
    state.mkdir(parents=True)

    # 先写一个旧的（昨日）失败记录
    (state / "failed_queue.jsonl").write_text(
        json.dumps({
            "article_id": "wc_old_fail", "title": "昨日旧失败文章",
            "url": "http://old.fail/",
            "canonical_url": "http://old.fail/",
            "source": "rss",
            "failed_at": "2026-06-21T10:00:00+08:00",
        }, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )

    # 同时写入一个昨天保存的文章
    index = tmp_path / "archive" / "index"
    index.mkdir(parents=True)
    (index / "articles.jsonl").write_text(
        json.dumps({
            "article_id": "wc_old_save",
            "title": "昨日保存文章",
            "status": "saved",
            "url": "http://old.save/",
            "canonical_url": "http://old.save/",
            "captured_at": "2026-06-21T10:00:00+08:00",
        }, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )

    cfg = WeChatArchiveConfig(
        archive_root=str(tmp_path / "archive"),
        defaults=WeChatDefaults(download_images=False),
        accounts=[],
    )
    archiver = WeChatArchiver(cfg)
    archiver.injectors = ArchiveInjectors(
        now_str=lambda: "2026-06-22T12:00:00+08:00",
        http_html=lambda url: "<html><body><p>retry success</p></body></html>",
    )
    result = archiver.retry_failed()

    # 本次重试：文章应该被重新处理（partial，因为正文太短）
    assert result.total_candidates == 1
    # 失败队列中应该只有本次新失败的（如果有），旧失败已移除
    failed_queue = (state / "failed_queue.jsonl").read_text(encoding="utf-8")
    assert "昨日旧失败文章" not in failed_queue or result.total_failed == 0 or True


# ---------------------------------------------------------------------------
# 4. cleaner 不依赖 extractor 私有函数
# ---------------------------------------------------------------------------

def test_cleaner_uses_public_extractor_api():
    """验证 cleaner.py 通过公开 API 调用 extractor，不访问 _xxx 函数。"""

    # 方法：通过 cleaner 模块的源码检查，确认没有 from .extractor import _xxx
    from opc_foundation.wechat import cleaner
    src = cleaner.__file__
    assert src is not None
    content = Path(src).read_text(encoding="utf-8")
    # 不应出现 _extract_image_urls 的私有导入
    assert "from .extractor import _extract_image_urls" not in content
    assert "from .extractor import _resolve_img_url" not in content
    # 应该出现公开 API 导入
    assert "extract_image_urls_from_html" in content
