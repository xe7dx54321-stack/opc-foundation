"""微信公众号归档的配置加载。

功能说明（小白解读）：
    本文件负责读取 wechat_accounts.yaml 这样的配置文件，
    把它解析成 models.WeChatArchiveConfig 对象供后续模块使用。

我们复用仓库已有工具：
    - opc_foundation.config.loader.load_yaml_config（读取 YAML）
    - pydantic BaseModel（负责字段校验与类型转换）

典型用法：
    from opc_foundation.wechat.config import load_wechat_config
    cfg = load_wechat_config("configs/wechat_accounts.example.yaml")
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError

from ..config.loader import load_yaml_config
from .models import (
    WeChatAccountConfig,
    WeChatArchiveConfig,
    WeChatDefaults,
)


class WeChatConfigError(ValueError):
    """配置文件有问题时抛出的异常。"""

    pass


def load_wechat_config(path: str | Path) -> WeChatArchiveConfig:
    """加载微信公众号归档配置文件。

    参数：
        path: YAML 配置文件路径

    返回：
        一个 WeChatArchiveConfig 对象，包含 archive_root / defaults / accounts

    异常：
        WeChatConfigError: 当文件缺失、字段不合法、账号配置格式错误时抛出
    """

    p = Path(path)
    if not p.exists():
        raise WeChatConfigError(f"配置文件不存在: {p}")

    try:
        raw: dict[str, Any] = load_yaml_config(p)
    except Exception as exc:
        raise WeChatConfigError(f"配置文件解析失败: {p} ({exc})") from exc

    # archive_root 必填
    archive_root = raw.get("archive_root")
    if not archive_root or not isinstance(archive_root, str):
        raise WeChatConfigError(
            "配置中缺少 'archive_root' 字段（请指定一个本地目录作为归档根目录）"
        )

    # defaults 可选
    defaults_raw: dict[str, Any] = raw.get("defaults") or {}
    try:
        defaults = WeChatDefaults(**defaults_raw)
    except ValidationError as exc:
        raise WeChatConfigError(f"defaults 字段不合法: {exc}") from exc

    # accounts 必须是列表
    accounts_raw = raw.get("accounts") or []
    if not isinstance(accounts_raw, list):
        raise WeChatConfigError("'accounts' 必须是一个列表")

    accounts: list[WeChatAccountConfig] = []
    for idx, item in enumerate(accounts_raw):
        if not isinstance(item, dict):
            raise WeChatConfigError(f"accounts[{idx}] 必须是一个 dict 对象")

        # 基础字段存在性检查（便于给出可读错误）
        if "account_name" not in item or not item.get("account_name"):
            raise WeChatConfigError(f"accounts[{idx}] 缺少 'account_name'")

        try:
            accounts.append(WeChatAccountConfig(**item))
        except ValidationError as exc:
            raise WeChatConfigError(
                f"accounts[{idx}] 字段不合法: {exc}"
            ) from exc

    return WeChatArchiveConfig(
        archive_root=str(archive_root),
        defaults=defaults,
        accounts=accounts,
        raw=raw,
    )
