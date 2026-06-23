"""Document Extraction Foundation 测试配置。

提供测试所需的 fixtures：
- PROJECT_ROOT: 项目根目录
- FIXTURES_DIR: 测试数据目录
- sample_pdf: 示例 PDF 路径
- sample_html: 示例 HTML 路径
- sample_txt: 示例文本路径
- sample_md: 示例 Markdown 路径
- malformed_pdf: 损坏的 PDF 路径
"""
from __future__ import annotations

from pathlib import Path

import pytest

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
FIXTURES_DIR = PROJECT_ROOT / "tests" / "document_extraction" / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    """返回测试 fixtures 目录。"""
    return FIXTURES_DIR


@pytest.fixture
def sample_pdf(fixtures_dir: Path) -> Path:
    """返回示例 PDF 文件路径。"""
    return fixtures_dir / "sample.pdf"


@pytest.fixture
def sample_html(fixtures_dir: Path) -> Path:
    """返回示例 HTML 文件路径。"""
    return fixtures_dir / "sample.html"


@pytest.fixture
def sample_txt(fixtures_dir: Path) -> Path:
    """返回示例文本文件路径。"""
    return fixtures_dir / "sample.txt"


@pytest.fixture
def sample_md(fixtures_dir: Path) -> Path:
    """返回示例 Markdown 文件路径。"""
    return fixtures_dir / "sample.md"


@pytest.fixture
def malformed_pdf(fixtures_dir: Path) -> Path:
    """返回损坏的 PDF 文件路径。"""
    return fixtures_dir / "malformed.pdf"


@pytest.fixture
def temp_archive_dir(tmp_path: Path) -> Path:
    """返回临时归档目录。"""
    archive_dir = tmp_path / "test_archive"
    archive_dir.mkdir()
    return archive_dir
