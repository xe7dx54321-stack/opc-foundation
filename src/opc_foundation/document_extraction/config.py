"""Document Extraction Foundation 的配置加载。

功能说明（小白解读）：
    本文件负责从 YAML 文件加载配置，
    并将配置解析成 DocumentArchiveConfig 和 DocumentExtractionConfig 模型。

    遵循 official_filings 模块的配置加载风格。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from .models import (
    DocumentArchiveConfig,
    DocumentExtractionConfig,
    DocumentExtractionDefaults,
)


def load_config(config_path: str | Path) -> DocumentArchiveConfig:
    """从 YAML 文件加载配置。

    参数：
        config_path: 配置文件路径

    返回：
        DocumentArchiveConfig 配置对象

    异常：
        FileNotFoundError: 配置文件不存在
        ValidationError: 配置格式不正确
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if raw is None:
        raw = {}

    # 解析 defaults
    defaults_data = raw.get("defaults", {})
    defaults = DocumentExtractionDefaults(**defaults_data)

    # 解析 sources
    sources_data = raw.get("sources", [])
    sources = []
    for source_data in sources_data:
        # 合并 defaults
        merged = _merge_with_defaults(source_data, defaults)
        sources.append(DocumentExtractionConfig(**merged))

    # 构建 archive config
    config = DocumentArchiveConfig(
        archive_root=raw.get("archive_root", "./data/document_extraction"),
        defaults=defaults,
        sources=sources,
        raw=raw,
    )

    return config


def _merge_with_defaults(
    source_data: dict[str, Any],
    defaults: DocumentExtractionDefaults,
) -> dict[str, Any]:
    """将 source 配置与 defaults 合并。

    如果 source 没有覆盖某个字段，则使用 defaults 的值。
    """
    merged = dict(source_data)

    # 这些字段如果 source 没有设置，就用 defaults
    fields_to_merge = [
        "max_documents",
        "save_raw",
        "save_markdown",
        "save_metadata",
        "extract_text",
        "extract_tables",
        "ocr_enabled",
    ]

    for field in fields_to_merge:
        if field in source_data:
            # source 显式设置了这个字段
            value = source_data[field]
            # 如果是 None，表示想用 default
            if value is None:
                default_value = getattr(defaults, field)
                merged[field] = default_value
        else:
            # source 没有设置，使用 default
            merged[field] = getattr(defaults, field)

    return merged


def validate_config(config: DocumentArchiveConfig) -> list[str]:
    """验证配置，返回所有验证错误列表。

    参数：
        config: DocumentArchiveConfig 配置对象

    返回：
        错误信息列表，如果为空则表示配置有效
    """
    errors = []

    # 验证 archive_root
    if not config.archive_root:
        errors.append("archive_root 不能为空")

    # 验证 sources
    source_ids = set()
    for source in config.sources:
        # 检查 source_id 唯一性
        if source.source_id in source_ids:
            errors.append(f"重复的 source_id: {source.source_id}")
        source_ids.add(source.source_id)

        # 检查 enabled=true 的 source 必须有 input_path
        if source.enabled and not source.input_path:
            errors.append(f"Source [{source.source_id}] enabled=true 但没有设置 input_path")

        # 检查 input_path 是否存在（如果指定了的话）
        if source.input_path:
            input_path = Path(source.input_path)
            if not input_path.exists():
                errors.append(f"Source [{source.source_id}] input_path 不存在: {source.input_path}")

        # 检查 OCR 状态
        if source.ocr_enabled:
            errors.append(f"Source [{source.source_id}] OCR 当前不启用，ocr_enabled 必须为 false")

    return errors
