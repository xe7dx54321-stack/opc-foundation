"""配置文件加载测试。"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from opc_foundation.wechat.config import load_wechat_config
from opc_foundation.wechat.config import WeChatConfigError


def test_load_example_yaml(tmp_path: Path):
    """示例 yaml 正确解析：验证示例配置文件能被成功加载。"""

    cfg = load_wechat_config(
        Path(__file__).resolve().parents[2] / "configs" / "wechat_accounts.example.yaml"
    )
    assert cfg.archive_root.endswith("wechat_archive") or cfg.archive_root.endswith("op-foundation/wechat_archive")
    assert cfg.defaults.fetch_timeout_seconds > 0
    assert len(cfg.accounts) >= 2


def test_unknown_config(tmp_path: Path):
    """字段缺失 / 非法 yaml：抛出 WeChatConfigError。"""

    bad = tmp_path / "bad.yaml"
    bad.write_text("accounts: 123\n", encoding="utf-8")
    with pytest.raises(WeChatConfigError):
        load_wechat_config(bad)


def test_missing_file(tmp_path: Path):
    """文件不存在也必须抛出异常。"""

    with pytest.raises(WeChatConfigError):
        load_wechat_config(tmp_path / "not_exist.yaml")
