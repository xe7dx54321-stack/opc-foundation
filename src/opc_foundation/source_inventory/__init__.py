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
from .execution_capabilities import (
    ExecutionMode,
    SourceExecutionCapability,
    TraeBrowserAssessment,
    SampleItem,
    validate_execution_capability,
    compute_recommended_execution_mode,
    compute_allowlist_flags,
    apply_recommendations,
    is_candidate_source,
    make_default_capability,
    M3C_6B_ALLOWED_CANDIDATES,
    TRIAL_V2_ALLOWLIST_ELIGIBLE_DECISIONS,
    TRAE_AUTOMATION_ELIGIBLE_DECISIONS,
    FINAL_DECISIONS,
)
from .trae_execution_assessment import (
    TraeBrowserSampleItem,
    TraeBrowserObservation,
    TraeSkillObservation,
    TraeAutomationDryRunObservation,
    TraeAssistedDecision,
    TraeExecutionAssessmentReport,
    validate_trae_assessment,
    compute_trae_decision,
    apply_trae_decision,
    is_m3c_6g_candidate,
    make_default_trae_report,
    M3C_6G_ALLOWED_CANDIDATES,
    TRAE_FINAL_DECISIONS,
    TRAE_AUTOMATION_ALLOWED_VALUES,
)
from .proxy_retry_assessment import (
    ProxyRetrySampleItem,
    ProxyRetryAttempt,
    ProxyRetryDecision,
    ProxyRetrySourceResult,
    ProxyRetryBatchReport,
    validate_proxy_retry_result,
    compute_proxy_retry_decision,
    apply_proxy_retry_decision,
    is_m3c_6f_candidate,
    make_default_proxy_result,
    check_proxy_env_configured,
    M3C_6F_ALLOWED_CANDIDATES,
    PROXY_FINAL_DECISIONS,
    NETWORK_STATUS_VALUES,
    ERROR_TYPE_VALUES,
)

__all__ = [
    "LiveSmokeStatus",
    "SourceLiveResult",
    "SourceGroupLiveResult",
    "LiveSmokeSummary",
    "LiveSmokeRunConfig",
    "run_live_smoke",
    "generate_live_smoke_report",
    "ExecutionMode",
    "SourceExecutionCapability",
    "TraeBrowserAssessment",
    "SampleItem",
    "validate_execution_capability",
    "compute_recommended_execution_mode",
    "compute_allowlist_flags",
    "apply_recommendations",
    "is_candidate_source",
    "make_default_capability",
    "M3C_6B_ALLOWED_CANDIDATES",
    "TRIAL_V2_ALLOWLIST_ELIGIBLE_DECISIONS",
    "TRAE_AUTOMATION_ELIGIBLE_DECISIONS",
    "FINAL_DECISIONS",
    "TraeBrowserSampleItem",
    "TraeBrowserObservation",
    "TraeSkillObservation",
    "TraeAutomationDryRunObservation",
    "TraeAssistedDecision",
    "TraeExecutionAssessmentReport",
    "validate_trae_assessment",
    "compute_trae_decision",
    "apply_trae_decision",
    "is_m3c_6g_candidate",
    "make_default_trae_report",
    "M3C_6G_ALLOWED_CANDIDATES",
    "TRAE_FINAL_DECISIONS",
    "TRAE_AUTOMATION_ALLOWED_VALUES",
    "ProxyRetrySampleItem",
    "ProxyRetryAttempt",
    "ProxyRetryDecision",
    "ProxyRetrySourceResult",
    "ProxyRetryBatchReport",
    "validate_proxy_retry_result",
    "compute_proxy_retry_decision",
    "apply_proxy_retry_decision",
    "is_m3c_6f_candidate",
    "make_default_proxy_result",
    "check_proxy_env_configured",
    "M3C_6F_ALLOWED_CANDIDATES",
    "PROXY_FINAL_DECISIONS",
    "NETWORK_STATUS_VALUES",
    "ERROR_TYPE_VALUES",
]
