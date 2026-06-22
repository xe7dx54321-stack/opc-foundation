"""加载测试 fixture 的共享工具。"""
from __future__ import annotations

from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    """加载 fixture 文件的内容，返回字符串。"""

    with open(FIXTURES_DIR / name, "rb") as fh:
        return fh.read().decode("utf-8")
