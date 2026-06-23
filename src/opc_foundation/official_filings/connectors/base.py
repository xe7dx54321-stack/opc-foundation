"""Connector 基类与注册机制。

功能说明（小白解读）：
    定义所有 official filing connector 的统一接口：discover()。
    discover() 接收一个 source 配置，返回候选披露列表。
    失败时抛出异常由上层捕获，不影响其他 source。

    支持 fixture 注入：测试时可以传入 raw_response_by_url / html_by_url / json_by_url，
    让 connector 直接返回预置的响应数据，而不是真实访问网络。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable

from ..models import FilingArchiveConfig, FilingCandidate, FilingSourceConfig


# fixture 注入函数类型
JsonInjector = Callable[[str], dict | list | None]
HtmlInjector = Callable[[str], str | None]
RawInjector = Callable[[str], bytes | None]


class OfficialFilingConnector(ABC):
    """所有 official filing connector 的基类。

    子类必须实现 discover() 方法。
    """

    connector_id: str = "base"

    def __init__(
        self,
        json_by_url: JsonInjector | None = None,
        html_by_url: HtmlInjector | None = None,
        raw_by_url: RawInjector | None = None,
    ) -> None:
        """初始化 connector。

        参数（小白解读）：
            json_by_url:  测试用注入函数，按 URL 返回 JSON 响应（dict/list），
                          返回 None 表示走真实 HTTP
            html_by_url:  测试用注入函数，按 URL 返回 HTML 字符串，
                          返回 None 表示走真实 HTTP
            raw_by_url:   测试用注入函数，按 URL 返回原始 bytes，
                          返回 None 表示走真实 HTTP
        """
        self._json_by_url = json_by_url
        self._html_by_url = html_by_url
        self._raw_by_url = raw_by_url

    @abstractmethod
    def discover(
        self,
        source: FilingSourceConfig,
        config: FilingArchiveConfig,
    ) -> list[FilingCandidate]:
        """从外部信息源发现候选披露。

        参数：
            source:  信息源配置
            config:  整体配置（含 defaults）

        返回：
            FilingCandidate 列表；失败时抛出异常由上层捕获
        """
        ...


def get_connector(source_type: str) -> OfficialFilingConnector | None:
    """根据 source_type 返回对应的 connector 实例。

    参数：
        source_type: 信息源类型

    返回：
        connector 实例；未实现的类型返回 None（上层会标记 skipped）
    """

    # 延迟导入避免循环依赖
    if source_type == "sec_edgar":
        from .sec import SECFilingConnector
        return SECFilingConnector()
    if source_type == "cninfo_announcement":
        from .cninfo import CNINFOFilingConnector
        return CNINFOFilingConnector()
    if source_type == "hkex_announcement":
        from .hkex import HKEXFilingConnector
        return HKEXFilingConnector()
    return None
