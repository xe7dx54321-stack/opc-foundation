"""Archive 路径 helper。

功能说明（小白解读）：
    根据 archive_root 和索引文件名，构建所有标准路径。
    只构建路径对象，不写文件，不创建目录（除非调用 ensure_archive_dirs）。

    支持相对路径和绝对路径，支持 Windows 路径。
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .constants import (
    FAILED_QUEUE_FILE,
    RUN_LOG_FILE,
    SOURCE_HEALTH_FILE,
    STANDARD_INDEX_DIR,
    STANDARD_REPORTS_DIR,
)


@dataclass(frozen=True)
class ArchivePaths:
    """Archive 目录的标准路径集合。

    功能说明：
        包含一个 archive_root 下所有标准文件和目录的路径。
        用 frozen dataclass，创建后不可修改。

    属性：
        archive_root:   归档根目录
        index_dir:      index 目录路径
        reports_dir:    reports 目录路径
        primary_index:  主索引文件路径（documents.jsonl 或 filings.jsonl）
        latest_index:   最新快照文件路径
        source_health:  源健康状态文件路径
        failed_queue:   失败队列文件路径
        run_log:        运行日志文件路径
    """

    archive_root: Path
    index_dir: Path
    reports_dir: Path
    primary_index: Path
    latest_index: Path
    source_health: Path
    failed_queue: Path
    run_log: Path


def build_archive_paths(
    archive_root: str | Path,
    primary_index_name: str,
    latest_index_name: str,
) -> ArchivePaths:
    """构建 archive 目录的标准路径集合。

    功能说明：
        根据 archive_root 和主索引文件名，构建所有标准路径。
        只构建路径对象，不写文件，不创建目录。

    参数：
        archive_root:         归档根目录路径（相对或绝对）
        primary_index_name:   主索引文件名（如 "documents.jsonl"）
        latest_index_name:    最新快照文件名（如 "documents.latest.jsonl"）

    返回：
        ArchivePaths 对象，包含所有标准路径

    异常处理：
        不抛异常，纯路径拼接操作
    """
    root = Path(archive_root)
    index_dir = root / STANDARD_INDEX_DIR
    reports_dir = root / STANDARD_REPORTS_DIR

    return ArchivePaths(
        archive_root=root,
        index_dir=index_dir,
        reports_dir=reports_dir,
        primary_index=index_dir / primary_index_name,
        latest_index=index_dir / latest_index_name,
        source_health=index_dir / SOURCE_HEALTH_FILE,
        failed_queue=index_dir / FAILED_QUEUE_FILE,
        run_log=index_dir / RUN_LOG_FILE,
    )


def ensure_archive_dirs(paths: ArchivePaths) -> None:
    """创建 archive 目录结构（index + reports）。

    功能说明：
        确保 index 目录和 reports 目录存在。
        如果目录已存在，不做任何操作。
        只创建目录，不创建文件。

    参数：
        paths: ArchivePaths 对象

    异常处理：
        如果创建目录失败，抛出 OSError（由调用方处理）
    """
    paths.index_dir.mkdir(parents=True, exist_ok=True)
    paths.reports_dir.mkdir(parents=True, exist_ok=True)
