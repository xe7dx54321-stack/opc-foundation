"""测试 CLI 和 archiver 的集成（用 fixture 注入）。

注意：
    这里主要测试 archiver 的核心逻辑（dry-run / run / source health / failed queue），
    不实际调用 typer CLI（避免复杂的子进程调用）。
    CLI 的命令行参数由 typer 框架保证正确性。
"""
from __future__ import annotations

from pathlib import Path

import pytest

from opc_foundation.official_filings.archiver import FilingArchiver
from opc_foundation.official_filings.config import load_filing_config
from opc_foundation.official_filings.connectors.sec import SECFilingConnector
from opc_foundation.official_filings.connectors.cninfo import CNINFOFilingConnector
from opc_foundation.official_filings.connectors.base import get_connector
from opc_foundation.official_filings.health import load_source_health
from opc_foundation.official_filings.models import (
    FILING_STATUS_SAVED,
    HEALTH_STATUS_HEALTHY,
    HEALTH_STATUS_DISABLED,
)
from opc_foundation.official_filings.storage import (
    _failed_queue_path,
    _filings_latest_path,
    _filings_path,
    load_filings_index,
)


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


def _make_archiver(
    temp_archive_root: Path,
    sec_json: dict | None = None,
    cninfo_json: dict | None = None,
    hkex_html: str | None = None,
) -> FilingArchiver:
    """构造一个注入了 fixture 的 archiver（用于测试）。"""
    import yaml

    config_dict = {
        "archive_root": str(temp_archive_root),
        "defaults": {"max_items_per_source": 5},
        "sources": [
            {
                "source_id": "test_sec",
                "source_name": "Test SEC",
                "source_type": "sec_edgar",
                "base_url": "https://www.sec.gov",
                "endpoint_url": "https://data.sec.gov/submissions/test.json",
                "enabled": True,
                "legal_profile": "official_public",
                "max_items": 3,
            },
            {
                "source_id": "test_cninfo",
                "source_name": "Test CNINFO",
                "source_type": "cninfo_announcement",
                "base_url": "https://www.cninfo.com.cn",
                "endpoint_url": "https://www.cninfo.com.cn/new/hisAnnouncement/query",
                "enabled": True,
                "legal_profile": "official_public",
                "max_items": 3,
            },
            {
                "source_id": "test_hkex_disabled",
                "source_name": "Test HKEX (disabled)",
                "source_type": "hkex_announcement",
                "base_url": "https://www.hkexnews.hk",
                "endpoint_url": "https://www.hkexnews.hk/test",
                "enabled": False,
                "legal_profile": "official_public",
            },
        ],
    }

    config_path = temp_archive_root / "test_config.yaml"
    config_path.write_text(
        yaml.dump(config_dict, allow_unicode=True), encoding="utf-8"
    )
    config = load_filing_config(str(config_path))

    # 注入 connector
    overrides = {}
    if sec_json is not None:
        overrides["sec_edgar"] = SECFilingConnector(
            json_by_url=lambda url: sec_json
        )
    if cninfo_json is not None:
        overrides["cninfo_announcement"] = CNINFOFilingConnector(
            json_by_url=lambda url: cninfo_json
        )

    return FilingArchiver(config, connector_overrides=overrides)


# ---------------------------------------------------------------------------
# dry-run 测试
# ---------------------------------------------------------------------------


def test_dry_run_does_not_write_filings(
    temp_archive_root: Path,
    sec_submissions_sample: dict,
) -> None:
    """dry-run 只发现候选，不写归档文件。"""
    archiver = _make_archiver(temp_archive_root, sec_json=sec_submissions_sample)
    result = archiver.run(mode="dry-run")

    assert result.mode == "dry-run"
    assert result.candidate_count > 0
    # filings.jsonl 不应该存在（dry-run 不写）
    assert not _filings_path(temp_archive_root).exists()
    assert not _filings_latest_path(temp_archive_root).exists()


def test_dry_run_returns_saved_filings(
    temp_archive_root: Path,
    sec_submissions_sample: dict,
) -> None:
    """dry-run 也返回 saved_filings（内存中的）。"""
    archiver = _make_archiver(temp_archive_root, sec_json=sec_submissions_sample)
    result = archiver.run(mode="dry-run")

    assert len(result.saved_filings) > 0
    assert result.saved_filings[0].status == FILING_STATUS_SAVED


# ---------------------------------------------------------------------------
# run 测试
# ---------------------------------------------------------------------------


def test_run_writes_filings_index(
    temp_archive_root: Path,
    sec_submissions_sample: dict,
) -> None:
    """run 模式会写 filings.jsonl 和 filings.latest.jsonl。"""
    archiver = _make_archiver(temp_archive_root, sec_json=sec_submissions_sample)
    result = archiver.run(mode="run")

    assert result.mode == "run"
    assert result.saved_count > 0
    # 索引文件存在
    assert _filings_path(temp_archive_root).exists()
    assert _filings_latest_path(temp_archive_root).exists()
    # 日报存在
    assert result.report_path is not None
    assert Path(result.report_path).exists()


def test_run_updates_source_health(
    temp_archive_root: Path,
    sec_submissions_sample: dict,
) -> None:
    """run 模式会更新 source health。"""
    archiver = _make_archiver(temp_archive_root, sec_json=sec_submissions_sample)
    result = archiver.run(mode="run")

    health_map = load_source_health(temp_archive_root)
    assert "test_sec" in health_map
    assert health_map["test_sec"].status == HEALTH_STATUS_HEALTHY
    assert health_map["test_sec"].candidate_count_last_run > 0


def test_run_disabled_source_marked_disabled(
    temp_archive_root: Path,
    sec_submissions_sample: dict,
) -> None:
    """disabled source 的 health status 是 disabled。"""
    archiver = _make_archiver(temp_archive_root, sec_json=sec_submissions_sample)
    result = archiver.run(mode="run")

    health_map = load_source_health(temp_archive_root)
    assert "test_hkex_disabled" in health_map
    assert health_map["test_hkex_disabled"].status == HEALTH_STATUS_DISABLED


def test_run_duplicate_filings_skipped(
    temp_archive_root: Path,
    sec_submissions_sample: dict,
) -> None:
    """第二次 run 时重复披露会被跳过（duplicate_count > 0）。"""
    archiver = _make_archiver(temp_archive_root, sec_json=sec_submissions_sample)

    # 第一次 run
    result1 = archiver.run(mode="run")
    first_saved = result1.saved_count

    # 第二次 run（同样的数据）
    result2 = archiver.run(mode="run")

    assert result2.duplicate_count > 0
    assert result2.saved_count == 0  # 全是重复的


def test_run_multiple_sources(
    temp_archive_root: Path,
    sec_submissions_sample: dict,
    cninfo_announcements_sample: dict,
) -> None:
    """多 source 同时运行，互不影响。"""
    archiver = _make_archiver(
        temp_archive_root,
        sec_json=sec_submissions_sample,
        cninfo_json=cninfo_announcements_sample,
    )
    result = archiver.run(mode="run")

    assert result.enabled_source_count == 2  # SEC + CNINFO
    assert result.source_count == 3  # 包含 disabled 的 HKEX
    assert result.saved_count > 0

    # 两个 source 的 health 都有记录
    health_map = load_source_health(temp_archive_root)
    assert "test_sec" in health_map
    assert "test_cninfo" in health_map


# ---------------------------------------------------------------------------
# 失败场景
# ---------------------------------------------------------------------------


def test_run_connector_failure_fail_soft(
    temp_archive_root: Path,
) -> None:
    """单个 connector 失败不影响其他 source（fail-soft）。"""
    # SEC connector 会抛异常（没有注入 json_by_url 也没有真实网络）
    # 但我们注入一个总是失败的 connector
    class FailingSECConnector(SECFilingConnector):
        def discover(self, source, config):
            raise RuntimeError("Simulated connector failure")

    import yaml

    config_dict = {
        "archive_root": str(temp_archive_root),
        "defaults": {"max_items_per_source": 5},
        "sources": [
            {
                "source_id": "failing_sec",
                "source_name": "Failing SEC",
                "source_type": "sec_edgar",
                "base_url": "https://www.sec.gov",
                "endpoint_url": "https://example.com/test.json",
                "enabled": True,
                "legal_profile": "official_public",
            },
        ],
    }
    config_path = temp_archive_root / "test_config.yaml"
    config_path.write_text(
        yaml.dump(config_dict, allow_unicode=True), encoding="utf-8"
    )
    config = load_filing_config(str(config_path))

    archiver = FilingArchiver(
        config,
        connector_overrides={"sec_edgar": FailingSECConnector()},
    )
    result = archiver.run(mode="run")

    # 虽然 connector 失败了，但整体运行不崩溃
    assert result.exit_code == 2  # 部分失败
    assert result.failed_count > 0
    assert len(result.warnings) > 0
    # health 记录了失败
    health_map = load_source_health(temp_archive_root)
    assert "failing_sec" in health_map
    assert health_map["failing_sec"].status == "failed"


# ---------------------------------------------------------------------------
# 报告生成
# ---------------------------------------------------------------------------


def test_run_generates_report(
    temp_archive_root: Path,
    sec_submissions_sample: dict,
) -> None:
    """run 模式生成日报文件。"""
    archiver = _make_archiver(temp_archive_root, sec_json=sec_submissions_sample)
    result = archiver.run(mode="run")

    assert result.report_path is not None
    report_path = Path(result.report_path)
    assert report_path.exists()

    content = report_path.read_text(encoding="utf-8")
    assert "Official Filing Foundation 采集日报" in content
