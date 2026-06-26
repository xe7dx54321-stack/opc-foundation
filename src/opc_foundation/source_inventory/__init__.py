"""Source Inventory 模块。

功能说明（小白解读）：
    这个模块负责管理和验证 92 个信息源的真实接通状态。
    包含 live smoke（真实连通性测试）、报告生成等功能。

    为什么要有这个模块？
        - 之前只有 source inventory 清单（配置登记）
        - 现在需要真实验证每个源能不能访问、能不能解析
        - 这样才能知道哪些源可以进入正式上线，哪些需要补 connector

    注意：
        - 本模块不做投资判断
        - 不抓取 blocked/high_risk 源
        - 不绕登录/付费墙
        - 不下载不明 PDF
"""

from .models import (
    LiveSmokeStatus,
    SourceLiveResult,
    SourceGroupLiveResult,
    LiveSmokeSummary,
    LiveSmokeRunConfig,
)
from .live_smoke import run_live_smoke
from .reports import generate_live_smoke_report

__all__ = [
    "LiveSmokeStatus",
    "SourceLiveResult",
    "SourceGroupLiveResult",
    "LiveSmokeSummary",
    "LiveSmokeRunConfig",
    "run_live_smoke",
    "generate_live_smoke_report",
]
