"""文档收集。

功能说明（小白解读）：
    收集 dashboard 文档入口页面需要展示的文档列表。
    包括从能力配置中收集的文档，和核心文档列表。

    不包含任何投资判断字段。
"""
from __future__ import annotations

from pathlib import Path

from .models import Capability


def collect_docs_from_capabilities(
    capabilities: list[Capability],
) -> list[str]:
    """从能力列表中收集所有文档路径。

    功能说明：
        遍历所有能力的 docs 列表，去重后返回。
        顺序按首次出现顺序保持稳定。

    参数：
        capabilities: 能力列表

    返回：
        去重后的文档路径列表
    """
    seen: set[str] = set()
    result: list[str] = []
    for cap in capabilities:
        for doc in cap.docs:
            if doc not in seen:
                seen.add(doc)
                result.append(doc)
    return result


def collect_core_docs(project_root: Path) -> list[str]:
    """返回核心文档列表（检查是否存在）。

    功能说明：
        返回 dashboard 文档入口页面需要展示的核心文档列表。
        只返回在 project_root 下实际存在的文档。

    参数：
        project_root: 项目根目录

    返回：
        存在的核心文档路径列表（相对路径）
    """
    root = Path(project_root)
    candidates = [
        "docs/foundation_capability_registry.md",
        "docs/foundation_readiness_summary.md",
        "docs/runtime_foundation.md",
        "docs/runtime_output_contract.md",
        "docs/research_source_foundation.md",
        "docs/official_filing_foundation.md",
        "docs/document_extraction_foundation.md",
    ]
    result: list[str] = []
    for doc in candidates:
        if (root / doc).exists():
            result.append(doc)
    return result
