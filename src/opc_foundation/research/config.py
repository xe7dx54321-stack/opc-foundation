"""Research Source Foundation 的配置加载与校验。

功能说明（小白解读）：
    本文件负责读取 research_sources.yaml 这样的配置文件，
    把它解析成 models.ResearchArchiveConfig 对象供后续模块使用。

    复用仓库已有工具：
    - opc_foundation.config.loader.load_yaml_config（读取 YAML）
    - pydantic BaseModel（负责字段校验与类型转换）

典型用法：
    from opc_foundation.research.config import load_research_config
    cfg = load_research_config("configs/research_sources.example.yaml")
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError

from ..config.loader import load_yaml_config
from .models import (
    ResearchArchiveConfig,
    ResearchDefaults,
    ResearchSourceConfig,
)


# 合法的 legal_profile 取值
LEGAL_PROFILES = {
    "official_public",
    "public_ir",
    "licensed_media",
    "rebroadcast",
    "user_provided",
    "unknown",
}

# Phase 1 已实现的 source_type
IMPLEMENTED_SOURCE_TYPES = {
    "rss_feed",
    "wechat_archive",
    "manual_url",
    "official_public_research",  # Phase 2A 新增
}

# 模型中预留但尚未实现的 source_type（CLI run 时会标记 skipped）
RESERVED_SOURCE_TYPES = {
    "podcast_transcript",
    "conference_transcript",
    "analyst_action",
    "media_mention",
    "local_document",
}


class ResearchConfigError(ValueError):
    """配置文件有问题时抛出的异常。"""

    pass


def load_research_config(path: str | Path) -> ResearchArchiveConfig:
    """加载 research source 配置文件。

    参数：
        path: YAML 配置文件路径

    返回：
        一个 ResearchArchiveConfig 对象，包含 archive_root / defaults / sources

    异常：
        ResearchConfigError: 当文件缺失、字段不合法、source_id 重复时抛出
    """

    p = Path(path)
    if not p.exists():
        raise ResearchConfigError(f"配置文件不存在: {p}")

    try:
        raw: dict[str, Any] = load_yaml_config(p)
    except Exception as exc:
        raise ResearchConfigError(f"配置文件解析失败: {p} ({exc})") from exc

    # archive_root 必填
    archive_root = raw.get("archive_root")
    if not archive_root or not isinstance(archive_root, str):
        raise ResearchConfigError(
            "配置中缺少 'archive_root' 字段（请指定一个本地目录作为归档根目录）"
        )

    # defaults 可选
    defaults_raw: dict[str, Any] = raw.get("defaults") or {}
    try:
        defaults = ResearchDefaults(**defaults_raw)
    except ValidationError as exc:
        raise ResearchConfigError(f"defaults 字段不合法: {exc}") from exc

    # sources 必须是列表
    sources_raw = raw.get("sources") or []
    if not isinstance(sources_raw, list):
        raise ResearchConfigError("'sources' 必须是一个列表")

    sources: list[ResearchSourceConfig] = []
    seen_ids: set[str] = set()
    for idx, item in enumerate(sources_raw):
        if not isinstance(item, dict):
            raise ResearchConfigError(f"sources[{idx}] 必须是一个 dict 对象")

        # 基础字段存在性检查
        if "source_id" not in item or not item.get("source_id"):
            raise ResearchConfigError(f"sources[{idx}] 缺少 'source_id'")
        if "source_name" not in item or not item.get("source_name"):
            raise ResearchConfigError(f"sources[{idx}] 缺少 'source_name'")
        if "source_type" not in item or not item.get("source_type"):
            raise ResearchConfigError(f"sources[{idx}] 缺少 'source_type'")

        sid = item["source_id"]
        if sid in seen_ids:
            raise ResearchConfigError(f"source_id 重复: {sid}")
        seen_ids.add(sid)

        # legal_profile 合法性
        lp = item.get("legal_profile", "unknown")
        if lp not in LEGAL_PROFILES:
            raise ResearchConfigError(
                f"sources[{idx}] legal_profile 不合法: {lp}，"
                f"合法取值: {sorted(LEGAL_PROFILES)}"
            )

        try:
            sources.append(ResearchSourceConfig(**item))
        except ValidationError as exc:
            raise ResearchConfigError(
                f"sources[{idx}] 字段不合法: {exc}"
            ) from exc

    return ResearchArchiveConfig(
        archive_root=str(archive_root),
        defaults=defaults,
        sources=sources,
        raw=raw,
    )


def validate_research_config(config: ResearchArchiveConfig) -> list[str]:
    """校验配置，返回错误信息列表（空列表表示通过）。

    参数：
        config: 已加载的配置对象

    返回：
        错误信息列表；空列表表示校验通过
    """

    errors: list[str] = []

    if not config.archive_root:
        errors.append("archive_root 不能为空")

    seen_ids: set[str] = set()
    for idx, src in enumerate(config.sources):
        if not src.source_id:
            errors.append(f"sources[{idx}] source_id 为空")
            continue
        if src.source_id in seen_ids:
            errors.append(f"source_id 重复: {src.source_id}")
        seen_ids.add(src.source_id)

        if src.legal_profile not in LEGAL_PROFILES:
            errors.append(
                f"source [{src.source_id}] legal_profile 不合法: {src.legal_profile}"
            )

        # 至少要有一个入口
        all_known_types = IMPLEMENTED_SOURCE_TYPES | RESERVED_SOURCE_TYPES
        if src.source_type not in all_known_types:
            errors.append(
                f"source [{src.source_id}] source_type 未知: {src.source_type}"
            )

        # wechat_archive 用 url 指向本地 jsonl；rss_feed 用 feed_url；manual_url 用 manual_urls_path
        if src.source_type == "rss_feed" and not src.feed_url and not src.url:
            errors.append(
                f"source [{src.source_id}] rss_feed 需要 feed_url 或 url"
            )
        if src.source_type == "wechat_archive" and not src.url:
            errors.append(
                f"source [{src.source_id}] wechat_archive 需要 url 指向本地 jsonl"
            )
        if src.source_type == "manual_url" and not src.manual_urls_path and not src.url:
            errors.append(
                f"source [{src.source_id}] manual_url 需要 manual_urls_path 或 url"
            )
        if src.source_type == "official_public_research" and not src.url and not src.base_url:
            errors.append(
                f"source [{src.source_id}] official_public_research 需要 url 或 base_url"
            )

    return errors
