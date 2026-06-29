"""Trial Runtime Health 测试（M3C-4）。

功能说明（小白解读）：
    测试 trial runtime loader 和 health aggregation 是否正确工作。
    包括：data 不存在时 fail-soft、读取 source_health、统计 success/failed/transient、
    cls_cn HTTP 418 归类为 transient_watch 等。
"""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from opc_foundation.dashboard.loaders import (
    build_trial_runtime_summary,
    load_trial_runtime_data,
)
from opc_foundation.dashboard.models import (
    TrialRuntimeSummary,
    TrialSourceStatus,
)


# ===========================================================================
# Fixtures
# ===========================================================================


@pytest.fixture
def trial_data_dir_with_health():
    """创建一个包含 source_health.jsonl 的临时目录（fixture）。

    功能说明（小白解读）：
        用 Python 的 tempfile 创建一个临时文件夹，里面放几条模拟的
        source_health 数据，测试用完后自动删除。

    返回：
        str: 临时目录的路径
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        health_path = os.path.join(tmpdir, "source_health.jsonl")
        rows = [
            {
                "source_id": "yahoo_finance",
                "source_name": "Yahoo Finance",
                "status": "success",
                "run_at": "2026-06-29T10:00:00",
                "candidate_count": 10,
                "error": "",
            },
            {
                "source_id": "business_insider",
                "source_name": "Business Insider",
                "status": "success",
                "run_at": "2026-06-29T10:01:00",
                "candidate_count": 5,
                "error": "",
            },
            {
                "source_id": "cls_cn",
                "source_name": "财联社",
                "status": "http_error",
                "run_at": "2026-06-29T10:02:00",
                "candidate_count": 0,
                "error": "HTTP 418",
            },
            {
                "source_id": "the_fly",
                "source_name": "The Fly",
                "status": "url_error",
                "run_at": "2026-06-29T10:03:00",
                "candidate_count": 0,
                "error": "Connection refused",
            },
        ]
        with open(health_path, "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        yield tmpdir


@pytest.fixture
def trial_data_dir_with_multiple_runs():
    """创建包含多条同一 source 记录的临时目录（测试取最新记录）。

    功能说明（小白解读）：
        同一个 source 跑了好几次，我们只应该取最新的一次结果。
        这个 fixture 给 cls_cn 放了两条记录，旧的 success 和新的 http_error。
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        health_path = os.path.join(tmpdir, "source_health.jsonl")
        rows = [
            {
                "source_id": "cls_cn",
                "source_name": "财联社",
                "status": "success",
                "run_at": "2026-06-29T09:00:00",
                "candidate_count": 8,
                "error": "",
            },
            {
                "source_id": "cls_cn",
                "source_name": "财联社",
                "status": "http_error",
                "run_at": "2026-06-29T10:00:00",
                "candidate_count": 0,
                "error": "HTTP 418",
            },
        ]
        with open(health_path, "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        yield tmpdir


@pytest.fixture
def trial_data_dir_healthy():
    """创建 15 个全部 success 的 trial 数据（测试 healthy 状态）。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        health_path = os.path.join(tmpdir, "source_health.jsonl")
        rows = []
        for i in range(15):
            rows.append({
                "source_id": f"source_{i:02d}",
                "source_name": f"Source {i}",
                "status": "success",
                "run_at": "2026-06-29T10:00:00",
                "candidate_count": 5,
                "error": "",
            })
        with open(health_path, "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        yield tmpdir


@pytest.fixture
def trial_data_dir_degraded():
    """创建 14 success + 1 cls_cn transient 的数据（测试 degraded 状态）。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        health_path = os.path.join(tmpdir, "source_health.jsonl")
        rows = []
        for i in range(14):
            rows.append({
                "source_id": f"source_{i:02d}",
                "source_name": f"Source {i}",
                "status": "success",
                "run_at": "2026-06-29T10:00:00",
                "candidate_count": 5,
                "error": "",
            })
        rows.append({
            "source_id": "cls_cn",
            "source_name": "财联社",
            "status": "http_error",
            "run_at": "2026-06-29T10:00:00",
            "candidate_count": 0,
            "error": "HTTP 418",
        })
        with open(health_path, "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        yield tmpdir


@pytest.fixture
def trial_data_dir_failed():
    """创建大量失败的数据（测试 failed 状态）。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        health_path = os.path.join(tmpdir, "source_health.jsonl")
        rows = []
        for i in range(10):
            rows.append({
                "source_id": f"source_{i:02d}",
                "source_name": f"Source {i}",
                "status": "failed",
                "run_at": "2026-06-29T10:00:00",
                "candidate_count": 0,
                "error": "Timeout",
            })
        with open(health_path, "w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        yield tmpdir


# ===========================================================================
# 测试 load_trial_runtime_data
# ===========================================================================


def test_load_trial_runtime_data_missing_dir():
    """测试 data 目录不存在时的 fail-soft 行为。

    验证点：
        - 当 trial 数据目录不存在时，loader 不应该崩溃
        - 应该返回三个空列表
    """
    nonexistent_dir = "/tmp/nonexistent_trial_data_12345"
    health, run_log, failed = load_trial_runtime_data(nonexistent_dir)
    assert health == []
    assert run_log == []
    assert failed == []


def test_load_trial_runtime_data_reads_source_health(trial_data_dir_with_health):
    """测试能正确读取 source_health.jsonl。

    验证点：
        - 返回的 health rows 数量和 fixture 一致
        - 每个 row 都包含 source_id 字段
    """
    health, run_log, failed = load_trial_runtime_data(trial_data_dir_with_health)
    assert len(health) == 4
    source_ids = {row["source_id"] for row in health}
    assert "yahoo_finance" in source_ids
    assert "cls_cn" in source_ids


def test_load_trial_runtime_data_reads_run_log(trial_data_dir_with_health):
    """测试能正确读取 run_log.jsonl（即使为空）。

    验证点：
        - run_log.jsonl 不存在时返回空列表
    """
    health, run_log, failed = load_trial_runtime_data(trial_data_dir_with_health)
    assert run_log == []


def test_load_trial_runtime_data_reads_failed_queue(trial_data_dir_with_health):
    """测试能正确读取 failed_queue.jsonl（即使为空）。

    验证点：
        - failed_queue.jsonl 不存在时返回空列表
    """
    health, run_log, failed = load_trial_runtime_data(trial_data_dir_with_health)
    assert failed == []


# ===========================================================================
# 测试 build_trial_runtime_summary
# ===========================================================================


def test_build_trial_runtime_summary_missing_data():
    """测试 data 缺失时的 fail-soft 返回。

    验证点：
        - data_exists = False
        - overall_health = "unknown"
        - 不抛出异常
    """
    nonexistent_dir = "/tmp/nonexistent_trial_data_12345"
    summary = build_trial_runtime_summary(nonexistent_dir)
    assert summary.data_exists is False
    assert summary.overall_health == "unknown"
    assert summary.total_sources == 0


def test_build_trial_runtime_summary_success_failed_transient(trial_data_dir_with_health):
    """测试 success / failed / transient 统计。

    验证点：
        - yahoo_finance 和 business_insider 是 success（2 个）
        - cls_cn HTTP 418 是 transient watch（1 个）
        - the_fly url_error 是 failed（1 个）
        - total = 4
    """
    summary = build_trial_runtime_summary(trial_data_dir_with_health)
    assert summary.data_exists is True
    assert summary.total_sources == 4
    assert summary.success_count == 2
    assert summary.failed_count == 1  # the_fly url_error
    assert summary.transient_count == 1  # cls_cn HTTP 418
    assert summary.transient_sources == ["cls_cn"]


def test_build_trial_runtime_summary_latest_record(trial_data_dir_with_multiple_runs):
    """测试同一 source 多条记录时取最新的一条。

    验证点：
        - cls_cn 有两条记录：旧的 success（09:00）和新的 http_error（10:00）
        - 应该取 10:00 的 http_error
    """
    summary = build_trial_runtime_summary(trial_data_dir_with_multiple_runs)
    assert summary.total_sources == 1
    cls_status = summary.source_statuses[0]
    assert cls_status.status == "http_error"
    assert cls_status.run_at == "2026-06-29T10:00:00"


def test_build_trial_runtime_summary_healthy(trial_data_dir_healthy):
    """测试成功率 >= 90% 时 overall_health = healthy。

    验证点：
        - 15 个 source 全部 success
        - success_rate = 100%
        - overall_health = "healthy"
    """
    summary = build_trial_runtime_summary(trial_data_dir_healthy)
    assert summary.total_sources == 15
    assert summary.success_count == 15
    assert summary.overall_health == "healthy"


def test_build_trial_runtime_summary_degraded(trial_data_dir_degraded):
    """测试存在 transient watch 时 overall_health = degraded。

    验证点：
        - 14 success + 1 cls_cn transient
        - success_rate = 14/15 = 93.3% >= 90%
        - 但因为存在 transient，overall_health = "degraded"
    """
    summary = build_trial_runtime_summary(trial_data_dir_degraded)
    assert summary.total_sources == 15
    assert summary.success_count == 14
    assert summary.transient_count == 1
    assert summary.overall_health == "degraded"


def test_build_trial_runtime_summary_failed(trial_data_dir_failed):
    """测试大量失败时 overall_health = failed。

    验证点：
        - 10 个 source 全部 failed
        - success_rate = 0%
        - overall_health = "failed"
    """
    summary = build_trial_runtime_summary(trial_data_dir_failed)
    assert summary.total_sources == 10
    assert summary.success_count == 0
    assert summary.failed_count == 10
    assert summary.overall_health == "failed"


def test_cls_cn_http_418_is_transient_watch(trial_data_dir_with_health):
    """测试 cls_cn HTTP 418 被归类为 transient_watch。

    验证点：
        - cls_cn 在 TRANSIENT_WATCH_SOURCES 集合中
        - cls_cn 的 status 是 http_error
        - transient_count = 1
        - cls_cn 不计入 failed_count
    """
    summary = build_trial_runtime_summary(trial_data_dir_with_health)
    cls_status = next((s for s in summary.source_statuses if s.source_id == "cls_cn"), None)
    assert cls_status is not None
    assert cls_status.status == "http_error"
    assert summary.transient_count == 1
    assert "cls_cn" in summary.transient_sources


def test_non_transient_http_error_is_failed(trial_data_dir_with_health):
    """测试非 transient 源的 http_error 被归类为 failed。

    验证点：
        - the_fly 不在 TRANSIENT_WATCH_SOURCES 中
        - the_fly 的 status 是 url_error（类似 http_error）
        - the_fly 计入 failed_count，不计入 transient_count
    """
    summary = build_trial_runtime_summary(trial_data_dir_with_health)
    fly_status = next((s for s in summary.source_statuses if s.source_id == "the_fly"), None)
    assert fly_status is not None
    assert fly_status.status == "url_error"
    assert summary.failed_count == 1  # the_fly
    assert summary.transient_count == 1  # cls_cn only


def test_empty_candidate_count_tracking(trial_data_dir_with_health):
    """测试 candidate_count=0 的 success 源被计入 empty_count。

    验证点：
        - 如果后续需要跟踪 empty source，这个字段会被统计
    """
    summary = build_trial_runtime_summary(trial_data_dir_with_health)
    # 当前 fixture 中所有 success 的 candidate_count 都 > 0，所以 empty_count = 0
    assert summary.empty_count == 0


def test_source_statuses_sorted(trial_data_dir_with_health):
    """测试 source_statuses 按 source_id 排序。

    验证点：
        - source_statuses 列表按 source_id 字母顺序排列
    """
    summary = build_trial_runtime_summary(trial_data_dir_with_health)
    ids = [s.source_id for s in summary.source_statuses]
    assert ids == sorted(ids)


# ===========================================================================
# 测试 TrialRuntimeSummary 数据模型
# ===========================================================================


def test_trial_runtime_summary_default_values():
    """测试 TrialRuntimeSummary 默认值。

    验证点：
        - 不传入参数时，所有字段都有合理的默认值
    """
    summary = TrialRuntimeSummary()
    assert summary.total_sources == 0
    assert summary.success_count == 0
    assert summary.failed_count == 0
    assert summary.overall_health == "unknown"
    assert summary.data_exists is False
    assert summary.source_statuses == []
    assert summary.transient_sources == []


def test_trial_source_status_creation():
    """测试 TrialSourceStatus 创建。

    验证点：
        - 可以正常创建 TrialSourceStatus 对象
        - 字段值正确
    """
    status = TrialSourceStatus(
        source_id="test_source",
        source_name="Test Source",
        status="success",
        run_at="2026-06-29T10:00:00",
        candidate_count=5,
        error="",
    )
    assert status.source_id == "test_source"
    assert status.candidate_count == 5


# ===========================================================================
# 测试边界条件
# ===========================================================================


def test_malformed_jsonl_skipped():
    """测试 malformed JSON 行被跳过。

    验证点：
        - JSONL 中有坏行时，不影响其他行的读取
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        health_path = os.path.join(tmpdir, "source_health.jsonl")
        with open(health_path, "w", encoding="utf-8") as f:
            f.write('{"source_id": "good", "status": "success", "run_at": "2026-06-29T10:00:00"}\n')
            f.write('this is not json\n')
            f.write('{"source_id": "also_good", "status": "success", "run_at": "2026-06-29T10:01:00"}\n')

        health, _, _ = load_trial_runtime_data(tmpdir)
        assert len(health) == 2
        ids = {row["source_id"] for row in health}
        assert "good" in ids
        assert "also_good" in ids


def test_source_id_missing_skipped():
    """测试缺少 source_id 的行被跳过。

    验证点：
        - source_id 为空的行不应该被计入统计
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        health_path = os.path.join(tmpdir, "source_health.jsonl")
        with open(health_path, "w", encoding="utf-8") as f:
            f.write('{"source_id": "", "status": "success", "run_at": "2026-06-29T10:00:00"}\n')
            f.write('{"status": "success", "run_at": "2026-06-29T10:01:00"}\n')
            f.write('{"source_id": "valid", "status": "success", "run_at": "2026-06-29T10:02:00"}\n')

        summary = build_trial_runtime_summary(tmpdir)
        assert summary.total_sources == 1
        assert summary.source_statuses[0].source_id == "valid"


def test_dry_run_status_counted_as_skipped(trial_data_dir_with_health):
    """测试 dry_run 状态被计入 skipped_count。

    验证点：
        - 在 fixture 中没有 dry_run 数据
        - 这里单独测试 dry_run 的统计
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        health_path = os.path.join(tmpdir, "source_health.jsonl")
        with open(health_path, "w", encoding="utf-8") as f:
            f.write('{"source_id": "s1", "status": "dry_run", "run_at": "2026-06-29T10:00:00"}\n')
            f.write('{"source_id": "s2", "status": "success", "run_at": "2026-06-29T10:01:00", "candidate_count": 3}\n')

        summary = build_trial_runtime_summary(tmpdir)
        assert summary.total_sources == 2
        assert summary.skipped_count == 1
        assert summary.success_count == 1


def test_empty_data_returns_unknown():
    """测试空 source_health.jsonl 返回 unknown。

    验证点：
        - 文件存在但为空时，应该返回 unknown（不是崩溃）
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        health_path = os.path.join(tmpdir, "source_health.jsonl")
        open(health_path, "w", encoding="utf-8").close()  # 创建空文件

        summary = build_trial_runtime_summary(tmpdir)
        assert summary.data_exists is False
        assert summary.overall_health == "unknown"


# ===========================================================================
# 测试文件存在性
# ===========================================================================


def test_trial_operating_report_exists():
    """测试 trial operating report 文件存在。

    验证点：
        - docs/foundation_trial_operating_report.md 存在
    """
    report_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "docs", "foundation_trial_operating_report.md"
    )
    assert os.path.exists(report_path), "docs/foundation_trial_operating_report.md should exist"
