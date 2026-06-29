"""OPC Foundation Dashboard Streamlit 应用。

功能说明（小白解读）：
    这是一个 Streamlit 可视化中控台，用来查看 opc-foundation 的能力地图、
    项目工作流、健康监控、运行日志、失败队列、文档入口、配置检查。

    启动方式：
        streamlit run src/opc_foundation/dashboard/app.py

    如果没装 streamlit，会提示安装命令。

    核心原则：Foundation provides infrastructure. Business systems keep judgment.
    这个 dashboard 只展示基础设施状态，不包含任何投资判断字段。

    品牌配色：
    - Dark:   #141413
    - Light:  #faf9f5
    - Orange: #d97757
    - Blue:   #6a9bcc
    - Green:  #788c5d
"""
from __future__ import annotations

from pathlib import Path

from opc_foundation.dashboard.loaders import (
    check_binding_files_exist,
    check_docs_exist,
    load_capabilities_config,
    load_jsonl_safe,
    load_runbooks_config,
    load_runtime_bindings_config,
    load_source_inventory_config,
    load_usage_registry,
    summarize_source_inventory,
    validate_capabilities,
    validate_runbooks,
    validate_runtime_bindings,
    validate_source_inventory,
    build_trial_runtime_summary,
)
from opc_foundation.dashboard.health import (
    build_dashboard_summary,
    build_runtime_evidence,
    build_runtime_summary,
    build_runtime_summary_from_evidence,
    suggest_action,
)
import streamlit.components.v1 as components
from opc_foundation.dashboard.usage import (
    build_usage_index,
    find_unused_capabilities,
    find_unknown_usage_references,
)
from opc_foundation.dashboard.docs import collect_core_docs, collect_docs_from_capabilities
from opc_foundation.dashboard.models import (
    Capability,
    CapabilityRegistry,
    CapabilityUsageRegistry,
    RuntimeBindingRegistry,
)

# 品牌配色
COLORS = {
    "dark": "#141413",
    "light": "#faf9f5",
    "orange": "#d97757",
    "blue": "#6a9bcc",
    "green": "#788c5d",
}

# 状态中文映射
STATUS_CN = {
    "healthy": "健康",
    "degraded": "降级",
    "failed": "失败",
    "unknown": "未知",
    "not_configured": "未配置",
    "needs_attention": "需关注",
    "stale": "已过期",
    "production_trial_ready": "可试运行",
    "mvp_ready": "MVP完成",
    "planned": "规划中",
    "dormant": "休眠",
    "disabled": "已禁用",
    "success": "成功",
    "partial": "部分成功",
    "skipped": "已跳过",
    "active": "运行中",
    "candidate": "候选",
    "deprecated": "已废弃",
}


def _cn(status: str) -> str:
    """把英文状态转成中文。

    功能说明：
        把英文的状态字符串映射成中文，让界面更友好。
        如果找不到对应的中文，就返回原字符串。

    参数：
        status: 英文状态字符串

    返回：
        中文字符串
    """
    return STATUS_CN.get(status, status)


# M3B-3b 新增：运行健康状态的中文映射
RUNTIME_HEALTH_CN = {
    "healthy": "运行正常",
    "degraded": "降级",
    "failed": "失败",
    "unknown_never_run": "未知 · 尚未运行",
    "not_configured": "未配置",
    "utility": "工具能力",
    "known_limited": "已知限制",
}


# M3B-3b 新增：运行健康状态的颜色映射
RUNTIME_HEALTH_COLOR = {
    "healthy": "#22c55e",
    "degraded": "#eab308",
    "failed": "#ef4444",
    "unknown_never_run": "#3b82f6",
    "not_configured": "#6b7280",
    "utility": "#6b7280",
    "known_limited": "#a3a3a3",
}


# M3B-3b 新增：运行模式（runtime_mode）的中文映射
RUNTIME_MODE_CN = {
    "data_source": "数据能力",
    "utility": "工具能力",
    "known_limited": "已知限制",
    "manual_only": "人工触发",
}


def _lazy_import_streamlit():
    """延迟导入 streamlit。

    功能说明：
        只有在真正需要渲染 dashboard 时才导入 streamlit。
        如果没装 streamlit，抛出 SystemExit 并提示安装命令。

    返回：
        streamlit 模块

    异常处理：
        streamlit 未安装时抛出 SystemExit，提示安装命令。
    """
    try:
        import streamlit as st
        return st
    except ImportError:
        raise SystemExit(
            "streamlit 未安装。请运行以下命令安装：\n"
            "    pip install streamlit\n"
            "安装后重新运行：\n"
            "    streamlit run src/opc_foundation/dashboard/app.py"
        )


def _find_project_root() -> Path:
    """查找项目根目录。

    功能说明：
        从当前文件位置向上查找，找到包含 configs 目录的路径作为项目根目录。
        如果找不到，回退到当前工作目录。

    返回：
        项目根目录 Path
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "configs").is_dir():
            return parent
        if (parent / "src" / "opc_foundation").is_dir():
            return parent
    return Path.cwd()


def _load_all_data(project_root: Path):
    """加载所有 dashboard 需要的数据。

    功能说明（小白解读）：
        一次性加载所有 dashboard 需要的数据，避免重复读取文件。
        包括：能力配置、使用注册表、运行手册、运行时绑定、运行时摘要、信息源清单。

    参数：
        project_root: 项目根目录

    返回：
        (registry, usage_registry, runbook_registry, runtime_binding_registry, runtime_summaries, source_inventory) 六元组
    """
    cap_path = project_root / "configs" / "foundation_capabilities.yaml"
    registry = load_capabilities_config(cap_path)

    # 优先用 local 配置，没有就用 example
    usage_path = project_root / "configs" / "capability_usage_registry.local.yaml"
    if not usage_path.exists():
        usage_path = project_root / "configs" / "capability_usage_registry.example.yaml"
    usage_registry = load_usage_registry(usage_path)

    # 加载运行手册
    runbook_path = project_root / "configs" / "capability_runbooks.yaml"
    runbook_registry = load_runbooks_config(runbook_path)

    # 加载 runtime bindings（优先 local，没有用主配置）
    runtime_bindings_path = project_root / "configs" / "capability_runtime_bindings.local.yaml"
    if not runtime_bindings_path.exists():
        runtime_bindings_path = project_root / "configs" / "capability_runtime_bindings.yaml"
    runtime_binding_registry = load_runtime_bindings_config(runtime_bindings_path)

    # 构建 runtime_evidence 和 runtime_summaries
    runtime_summaries = {}
    for cap in registry.capabilities:
        binding = runtime_binding_registry.get_binding(cap.capability_id)
        evidence = build_runtime_evidence(cap, binding, project_root)
        runtime_summaries[cap.capability_id] = build_runtime_summary_from_evidence(
            cap, binding, evidence
        )

    # 加载信息源清单（source inventory）
    source_inventory_path = project_root / "configs" / "foundation_source_inventory.example.yaml"
    source_inventory = load_source_inventory_config(source_inventory_path)

    return registry, usage_registry, runbook_registry, runtime_binding_registry, runtime_summaries, source_inventory


def _health_color(health: str) -> str:
    """根据健康状态返回对应颜色。

    功能说明：
        把健康状态映射成品牌配色，用于在页面上高亮显示。

    参数：
        health: 健康状态字符串

    返回：
        颜色 hex 字符串
    """
    mapping = {
        "healthy": COLORS["green"],
        "degraded": COLORS["orange"],
        "failed": "#c0392b",
        "unknown": "#888888",
        "not_configured": "#bbbbbb",
    }
    return mapping.get(health, "#888888")


def _maturity_color(maturity: str) -> str:
    """根据成熟度返回对应颜色。

    功能说明：
        把成熟度映射成品牌配色，用于在页面上高亮显示。

    参数：
        maturity: 成熟度字符串

    返回：
        颜色 hex 字符串
    """
    mapping = {
        "production_trial_ready": COLORS["green"],
        "mvp_ready": COLORS["blue"],
        "degraded": COLORS["orange"],
    }
    return mapping.get(maturity, "#888888")


def _render_overview(st, registry, usage_registry, runtime_summaries):
    """渲染总览页面。

    功能说明：
        展示 dashboard 汇总统计，包括能力总数、成熟度分布、
        运行健康分布、需要关注数量、使用情况。

    参数：
        st:               streamlit 模块
        registry:         能力注册表
        usage_registry:   使用注册表
        runtime_summaries:运行时摘要字典
    """
    st.header("总览")
    summary = build_dashboard_summary(
        registry.capabilities, runtime_summaries, usage_registry
    )

    st.subheader("能力成熟度")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("能力总数", summary.total_capabilities)
    col2.metric("可试运行", summary.production_trial_ready_count)
    col3.metric("MVP完成", summary.mvp_ready_count)
    col4.metric("降级", summary.degraded_count)

    st.subheader("运行健康")
    col1, col2, col3 = st.columns(3)
    col1.metric("失败", summary.failed_count)
    col2.metric("未知", summary.unknown_count)
    col3.metric("未配置", summary.not_configured_count)

    st.subheader("关注与使用")
    col1, col2, col3 = st.columns(3)
    col1.metric("需要关注", summary.needs_attention_count)
    col2.metric("已过期", summary.stale_count)
    col3.metric("已使用 / 未使用", f"{summary.used_count} / {summary.unused_count}")

    st.markdown("---")
    st.caption(
        "核心原则：Foundation provides infrastructure. Business systems keep judgment."
    )


def _render_capability_map(st, registry, runbook_registry, runtime_binding_registry, runtime_summaries, project_root):
    """渲染能力地图页面（卡片式大白话版本）。

    功能说明：
        按主线分组，用卡片形式展示每个能力。
        每张卡片有"查看详情"按钮，点击弹出完整运行手册。
        每个能力卡片显示成熟度标签和运行健康标签。

    参数：
        st:                     streamlit 模块
        registry:               能力注册表
        runbook_registry:       运行手册注册表
        runtime_binding_registry: 运行时绑定注册表
        runtime_summaries:      运行时摘要字典
        project_root:           项目根目录
    """
    st.header("能力地图")
    st.caption("用大白话告诉你每个能力是干啥的，点击卡片上的「查看详情」看完整手册 ✨")

    # 检查是否有需要显示的弹窗（用 session_state 保持状态，避免标签页切换后弹窗消失）
    active_modal = st.session_state.get("active_detail_modal")
    if active_modal:
        _render_capability_detail_modal(
            st,
            active_modal,
            registry,
            runbook_registry,
            runtime_binding_registry,
            runtime_summaries,
            project_root,
        )

    for track in registry.tracks:
        st.markdown("")
        st.markdown(f"## {track.name}")
        if track.name_en:
            st.caption(f"**英文原名**：{track.name_en} ｜ **主线ID**：{track.track_id} ｜ **状态**：{_cn(track.status)}")
        else:
            st.caption(f"**主线ID**：{track.track_id} ｜ **状态**：{_cn(track.status)}")
        st.write(track.description)

        caps = [c for c in registry.capabilities if c.track == track.track_id]
        if not caps:
            st.info("该主线下暂无能力。")
            continue

        # 每行 2 个卡片
        cols_per_row = 2
        for i in range(0, len(caps), cols_per_row):
            batch = caps[i : i + cols_per_row]
            cols = st.columns(cols_per_row)
            for col, cap in zip(cols, batch):
                with col:
                    runtime = runtime_summaries.get(cap.capability_id)
                    _render_capability_card(st, cap, runtime)
                    # 查看详情按钮
                    if st.button(f"📖 查看详情 · {cap.capability_id}", key=f"detail_btn_{cap.capability_id}"):
                        st.session_state["active_detail_modal"] = cap.capability_id
                        st.rerun()

        st.markdown("---")


def _render_capability_card(st, cap, runtime=None):
    """渲染单个能力卡片。

    功能说明：
        用卡片形式展示一个能力的详细信息，包括：
        名称、成熟度、运行健康、一句话描述、能干啥、典型用途、输入输出。

    参数：
        st:       streamlit 模块
        cap:      能力对象
        runtime:  运行时摘要（可选）
    """
    # 成熟度颜色
    maturity_colors = {
        "production_trial_ready": "#788c5d",  # 绿色
        "mvp_ready": "#6a9bcc",              # 蓝色
        "degraded": "#d97757",                # 橙色
        "failed": "#b91c1c",                  # 红色
        "unknown": "#6b7280",                 # 灰色
        "not_configured": "#6b7280",          # 灰色
    }
    maturity_color = maturity_colors.get(cap.maturity_status, "#6b7280")
    maturity_text = _cn(cap.maturity_status)

    # 运行健康状态
    runtime_health = runtime.runtime_health if runtime else "unknown"
    runtime_colors = {
        "healthy": "#22c55e",
        "degraded": "#eab308",
        "failed": "#ef4444",
        "unknown": "#6b7280",
        "not_configured": "#6b7280",
    }
    runtime_color = runtime_colors.get(runtime_health, "#6b7280")
    runtime_text = _cn(runtime_health)

    # 显示名称优先用 display_name，没有就用 name
    title = cap.display_name if cap.display_name else cap.name

    # 卡片 HTML
    card_html = f"""
    <div class="cap-card" style="
        border: 1px solid rgba(128,128,128,0.3);
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    ">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
            <h3 style="margin: 0; font-size: 18px;">{title}</h3>
            <div style="display: flex; gap: 6px; flex-wrap: wrap; justify-content: flex-end;">
                <span style="
                    background: {maturity_color};
                    color: white;
                    padding: 2px 10px;
                    border-radius: 12px;
                    font-size: 12px;
                    white-space: nowrap;
                ">{maturity_text}</span>
                <span style="
                    background: {runtime_color};
                    color: white;
                    padding: 2px 10px;
                    border-radius: 12px;
                    font-size: 12px;
                    white-space: nowrap;
                ">{runtime_text}</span>
            </div>
        </div>
        <div style="opacity: 0.7; font-size: 13px; margin-bottom: 12px;">
            <code style="padding: 2px 6px; border-radius: 4px; font-size: 12px;">{cap.capability_id}</code>
            &nbsp;·&nbsp;
            <span>分类：{cap.category}</span>
        </div>
        <div style="opacity: 0.85; font-size: 14px; margin-bottom: 12px;">
            {cap.description}
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

    # 能干啥（有数据才显示）
    if cap.what_it_does:
        st.markdown("**🎯 它能干啥**")
        for item in cap.what_it_does:
            st.markdown(f"- {item}")

    # 典型用途（有数据才显示）
    if cap.typical_usage:
        st.markdown(f"**💡 典型用途**：{cap.typical_usage}")

    # 输入类型
    if cap.input_type:
        st.markdown(f"**📥 输入**：{cap.input_type}")

    # 输出（短一点）
    if cap.primary_output:
        out_short = cap.primary_output
        if len(out_short) > 50:
            out_short = "..." + out_short[-47:]
        st.markdown(f"**📤 输出**：`{out_short}`")

    st.markdown("")


def _render_capability_detail_modal(
    st,
    cap_id: str,
    registry,
    runbook_registry,
    runtime_binding_registry,
    runtime_summaries,
    project_root,
):
    """渲染能力详情弹窗（精致卡片风格）。

    功能说明（小白解读）：
        按照效果图重新设计弹窗，采用深色圆角卡片风格：
        - 顶部：图标、标题、运行状态、最后运行时间、连续成功次数
        - 标签页导航：总览、配置与运行、输出位置、常见失败、排查步骤、相关文档、真实运行
        - 总览页面包含6个卡片：能力说明、能力边界、运行状态、配置信息、运行命令、快速提示

    参数：
        st:                     streamlit 模块
        cap_id:                 要展示的能力 ID
        registry:               能力注册表
        runbook_registry:       运行手册注册表
        runtime_binding_registry: 运行时绑定注册表
        runtime_summaries:      运行时摘要字典
        project_root:           项目根目录
    """
    @st.dialog("能力详情", width="large")
    def show_detail(cap_id: str):
        """弹窗内部的渲染逻辑。"""
        runbook = runbook_registry.get_runbook(cap_id)
        cap = registry.get_capability(cap_id)
        runtime = runtime_summaries.get(cap_id)

        if runbook is None:
            st.error("找不到该能力的运行手册。")
            return

        # 获取轨道信息
        track = next((t for t in registry.tracks if t.track_id == cap.track), None)

        # 获取运行状态
        health_status = runtime.runtime_health if runtime else "unknown_never_run"
        health_label = RUNTIME_HEALTH_CN.get(health_status, health_status)
        health_color = RUNTIME_HEALTH_COLOR.get(health_status, "#6b7280")
        health_bg_rgba = {
            "healthy": "rgba(34, 197, 94, 0.15)",
            "degraded": "rgba(234, 179, 8, 0.15)",
            "failed": "rgba(239, 68, 68, 0.15)",
            "unknown_never_run": "rgba(59, 130, 246, 0.15)",
            "not_configured": "rgba(107, 114, 128, 0.15)",
            "utility": "rgba(107, 114, 128, 0.15)",
            "known_limited": "rgba(163, 163, 163, 0.15)",
        }.get(health_status, "rgba(107, 114, 128, 0.15)")

        # 获取连续成功次数和最后运行时间
        consecutive_success = 0
        last_run_time = "从未运行"
        if runtime:
            if runtime.latest_run_at:
                last_run_time = runtime.latest_run_at
            # 用最近运行次数 - 最近失败次数 来估算连续成功
            consecutive_success = max(0, runtime.recent_run_count - runtime.recent_failure_count)

        # --- 自定义样式 ---
        st.markdown(
            """
            <style>
            .detail-card {
                background: #1e293b;
                border: 1px solid #334155;
                border-radius: 12px;
                padding: 16px;
                margin-bottom: 12px;
            }
            .detail-card-header {
                display: flex;
                align-items: center;
                gap: 8px;
                margin-bottom: 12px;
                padding-bottom: 8px;
                border-bottom: 1px solid #334155;
            }
            .detail-card-icon {
                width: 24px;
                height: 24px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 6px;
                font-size: 14px;
            }
            .detail-card-title {
                font-size: 14px;
                font-weight: 600;
                color: #f1f5f9;
            }
            .tag {
                display: inline-flex;
                align-items: center;
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 500;
                margin-right: 6px;
                margin-bottom: 4px;
            }
            .tag-green { background: rgba(34, 197, 94, 0.15); color: #22c55e; }
            .tag-gray { background: rgba(107, 114, 128, 0.15); color: #9ca3af; }
            .tag-blue { background: rgba(59, 130, 246, 0.15); color: #60a5fa; }
            .stat-value { font-size: 20px; font-weight: 700; color: #f1f5f9; }
            .stat-label { font-size: 11px; color: #94a3b8; }
            .cmd-box {
                background: #0f172a;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 8px 12px;
                margin-bottom: 8px;
                font-family: 'Fira Code', monospace;
                font-size: 12px;
                color: #cbd5e1;
                display: flex;
                align-items: center;
                justify-content: space-between;
            }
            .cmd-copy-btn {
                background: transparent;
                border: none;
                color: #94a3b8;
                cursor: pointer;
                font-size: 14px;
                padding: 4px;
            }
            .cmd-copy-btn:hover { color: #f1f5f9; }
            .quick-tip {
                display: flex;
                align-items: flex-start;
                gap: 12px;
                padding: 10px;
                background: rgba(251, 191, 36, 0.08);
                border-radius: 8px;
                margin-bottom: 8px;
            }
            .quick-tip-icon {
                width: 28px;
                height: 28px;
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 14px;
                flex-shrink: 0;
            }
            .quick-tip-title { font-size: 12px; font-weight: 600; color: #fbbf24; margin-bottom: 2px; }
            .quick-tip-desc { font-size: 11px; color: #94a3b8; }
            .config-item {
                display: inline-block;
                background: rgba(59, 130, 246, 0.1);
                border: 1px solid rgba(59, 130, 246, 0.3);
                padding: 4px 10px;
                border-radius: 4px;
                font-size: 11px;
                color: #60a5fa;
                margin-right: 6px;
                margin-bottom: 6px;
            }
            .success-dot {
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background: #22c55e;
                display: inline-block;
                margin-right: 6px;
            }
            .warning-dot {
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background: #eab308;
                display: inline-block;
                margin-right: 6px;
            }
            .danger-dot {
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background: #ef4444;
                display: inline-block;
                margin-right: 6px;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        # --- 顶部信息区域 ---
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;">
                <div style="display: flex; align-items: center; gap: 16px;">
                    <div style="width: 56px; height: 56px; background: linear-gradient(135deg, #3b82f6, #8b5cf6); border-radius: 14px; display: flex; align-items: center; justify-content: center; font-size: 24px;">📋</div>
                    <div>
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <h2 style="margin: 0; font-size: 20px; font-weight: 700; color: #f1f5f9;">{runbook.title}</h2>
                            <span class="tag" style="background: {health_bg_rgba}; color: {health_color};">
                                <span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:{health_color};margin-right:4px;"></span>
                                {health_label}
                            </span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 12px; margin-top: 6px;">
                            <span class="tag tag-blue">{cap.capability_id}</span>
                            <span class="tag tag-gray">所属轨道：{track.name if track else cap.track}</span>
                            <span class="tag tag-gray">成熟度状态：{runbook.maturity_label or '未知'}</span>
                        </div>
                    </div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 11px; color: #94a3b8; margin-bottom: 4px;">最后运行：{last_run_time}</div>
                    <div style="font-size: 11px; color: #94a3b8;">连续成功：<span style="color: #22c55e; font-weight: 600;">{consecutive_success}</span> 次</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # --- 标签页导航 ---
        tab_options = ["总览", "配置与运行", "输出位置", "常见失败", "排查步骤", "相关文档", "真实运行"]
        active_tab = st.session_state.get(f"detail_tab_{cap_id}", "总览")

        # 用 Streamlit 原生按钮实现标签页（更稳定可靠）
        tab_cols = st.columns(len(tab_options))
        for i, tab in enumerate(tab_options):
            with tab_cols[i]:
                is_active = tab == active_tab
                btn_label = f"{'● ' if is_active else ''}{tab}"
                if st.button(
                    btn_label,
                    key=f"tab_{cap_id}_{tab}",
                    use_container_width=True,
                    type="primary" if is_active else "secondary",
                ):
                    st.session_state[f"detail_tab_{cap_id}"] = tab
                    st.rerun()

        # --- 总览页面 ---
        if active_tab == "总览":
            col1, col2, col3 = st.columns(3)

            # 卡片1：能力说明
            with col1:
                st.markdown(
                    f"""
                    <div class="detail-card">
                        <div class="detail-card-header">
                            <div class="detail-card-icon" style="background: rgba(59, 130, 246, 0.15); color: #3b82f6;">💡</div>
                            <div class="detail-card-title">能力说明</div>
                        </div>
                        <div style="font-size: 12px; color: #94a3b8; line-height: 1.6; margin-bottom: 12px;">{runbook.summary}</div>
                        <div style="font-size: 11px; color: #64748b; margin-bottom: 6px;">适用场景</div>
                        <div style="font-size: 11px; color: #cbd5e1;">
                            <div><span class="success-dot"></span>跟踪美股上市公司重大披露</div>
                            <div><span class="success-dot"></span>监控 10-K / 10-Q / 8-K 等公告</div>
                            <div><span class="success-dot"></span>生成研究证据材料</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # 卡片2：能力边界
            with col2:
                st.markdown(
                    f"""
                    <div class="detail-card">
                        <div class="detail-card-header">
                            <div class="detail-card-icon" style="background: rgba(34, 197, 94, 0.15); color: #22c55e;">🛡️</div>
                            <div class="detail-card-title">能力边界</div>
                        </div>
                        <div style="font-size: 11px; color: #22c55e; font-weight: 600; margin-bottom: 6px;">能做什么</div>
                        <div style="font-size: 11px; color: #cbd5e1; line-height: 1.5; margin-bottom: 10px;">
                            {'<br>'.join([f'• {item}' for item in runbook.can_do]) if runbook.can_do else '暂无描述'}
                        </div>
                        <div style="font-size: 11px; color: #ef4444; font-weight: 600; margin-bottom: 6px;">不能做什么</div>
                        <div style="font-size: 11px; color: #cbd5e1; line-height: 1.5;">
                            {'<br>'.join([f'• {item}' for item in runbook.cannot_do]) if runbook.cannot_do else '暂无描述'}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # 卡片3：运行状态
            with col3:
                recent_run = runtime.recent_run_count if runtime else 0
                recent_fail = runtime.recent_failure_count if runtime else 0
                failed_queue = runtime.failed_queue_count if runtime else 0
                st.markdown(
                    f"""
                    <div class="detail-card">
                        <div class="detail-card-header">
                            <div class="detail-card-icon" style="background: rgba(34, 197, 94, 0.15); color: #22c55e;">📊</div>
                            <div class="detail-card-title">运行状态</div>
                        </div>
                        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
                            <span style="width: 12px; height: 12px; border-radius: 50%; background: {health_color};"></span>
                            <span style="font-size: 16px; font-weight: 600; color: #f1f5f9;">{health_label}</span>
                            <span style="font-size: 11px; color: #64748b;">最近{recent_run}次运行</span>
                        </div>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 12px;">
                            <div><div class="stat-value">{recent_run}</div><div class="stat-label">运行次数</div></div>
                            <div><div class="stat-value">{recent_run - recent_fail}</div><div class="stat-label">成功次数</div></div>
                            <div><div class="stat-value">{recent_fail}</div><div class="stat-label">失败次数</div></div>
                            <div><div class="stat-value">{failed_queue}</div><div class="stat-label">失败队列</div></div>
                        </div>
                        {"<div style='border-top: 1px solid #334155; padding-top: 10px;'><div style='font-size: 11px; color: #64748b; margin-bottom: 4px;'>最近错误</div><div style='font-size: 11px; color: #ef4444;'>" + runtime.latest_error + "</div></div>" if runtime and runtime.latest_error else ""}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            col1, col2, col3 = st.columns(3)

            # 卡片4：配置信息
            with col1:
                st.markdown(
                    f"""
                    <div class="detail-card">
                        <div class="detail-card-header">
                            <div class="detail-card-icon" style="background: rgba(139, 92, 246, 0.15); color: #8b5cf6;">⚙️</div>
                            <div class="detail-card-title">配置信息</div>
                        </div>
                        <div style="font-size: 11px; color: #64748b; margin-bottom: 6px;">配置模板</div>
                        <div style="margin-bottom: 12px;">
                            {''.join([f'<span class="config-item">{tpl}</span>' for tpl in runbook.config_templates]) if runbook.config_templates else '<span style="color: #64748b;">暂无</span>'}
                        </div>
                        <div style="font-size: 11px; color: #64748b; margin-bottom: 6px;">本地配置文件</div>
                        <div style="margin-bottom: 12px;">
                            <span class="config-item">{runbook.local_config_path or '暂无'}</span>
                        </div>
                        <div style="font-size: 11px; color: #94a3b8; background: rgba(251, 191, 36, 0.08); padding: 8px; border-radius: 6px;">
                            复制示例配置到本地后，根据实际需求修改，建议只在本地环境使用 .local.yaml 文件。
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # 卡片5：运行命令
            with col2:
                st.markdown(
                    f"""
                    <div class="detail-card">
                        <div class="detail-card-header">
                            <div class="detail-card-icon" style="background: rgba(234, 179, 8, 0.15); color: #eab308;">💻</div>
                            <div class="detail-card-title">运行命令</div>
                            <a href="#" style="font-size: 11px; color: #60a5fa; margin-left: auto;">复制全部命令</a>
                        </div>
                        """,
                    unsafe_allow_html=True,
                )
                cmd_names = {
                    "validate_config": "检查配置",
                    "dry_run": "试运行",
                    "run": "正式运行",
                    "source_health": "查看健康状态",
                    "report": "生成报告",
                    "retry_failed": "重试失败项",
                }
                for key, cmd in (runbook.commands or {}).items():
                    label = cmd_names.get(key, key)
                    cmd_escaped = cmd.replace("'", "'")
                    st.markdown(
                        f"""
                        <div style="font-size: 11px; color: #94a3b8; margin-bottom: 4px;">{label}</div>
                        <div class="cmd-box">
                            <code style="flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{cmd}</code>
                            <button class="cmd-copy-btn" onclick="navigator.clipboard.writeText('{cmd_escaped}');this.innerHTML='✓';">📋</button>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                st.markdown("</div>", unsafe_allow_html=True)

            # 卡片6：快速提示
            with col3:
                st.markdown(
                    f"""
                    <div class="detail-card">
                        <div class="detail-card-header">
                            <div class="detail-card-icon" style="background: rgba(251, 191, 36, 0.15); color: #fbbf24;">💡</div>
                            <div class="detail-card-title">快速提示</div>
                        </div>
                        <div class="quick-tip">
                            <div class="quick-tip-icon" style="background: rgba(59, 130, 246, 0.15); color: #3b82f6;">▶️</div>
                            <div>
                                <div class="quick-tip-title">首次使用建议</div>
                                <div class="quick-tip-desc">从"检查配置"开始，逐步到"试运行"和"正式运行"。</div>
                            </div>
                        </div>
                        <div class="quick-tip">
                            <div class="quick-tip-icon" style="background: rgba(139, 92, 246, 0.15); color: #8b5cf6;">🔧</div>
                            <div>
                                <div class="quick-tip-title">配置修改后</div>
                                <div class="quick-tip-desc">先运行"检查配置"，再进行试运行验证。</div>
                            </div>
                        </div>
                        <div class="quick-tip">
                            <div class="quick-tip-icon" style="background: rgba(239, 68, 68, 0.15); color: #ef4444;">⚠️</div>
                            <div>
                                <div class="quick-tip-title">发现问题时</div>
                                <div class="quick-tip-desc">查看"常见失败"和"排查步骤"进行定位。</div>
                            </div>
                        </div>
                        <div class="quick-tip">
                            <div class="quick-tip-icon" style="background: rgba(107, 114, 128, 0.15); color: #9ca3af;">❓</div>
                            <div>
                                <div class="quick-tip-title">更多帮助</div>
                                <div class="quick-tip-desc">查看相关文档获取详细信息和最佳实践。</div>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        # --- 配置与运行页面 ---
        elif active_tab == "配置与运行":
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(
                    f"""
                    <div class="detail-card">
                        <div class="detail-card-header">
                            <div class="detail-card-icon" style="background: rgba(139, 92, 246, 0.15); color: #8b5cf6;">📋</div>
                            <div class="detail-card-title">配置模板</div>
                        </div>
                        {''.join([f'<div class="config-item">{tpl}</div>' for tpl in runbook.config_templates]) if runbook.config_templates else '<div style="color: #64748b;">暂无配置模板</div>'}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"""
                    <div class="detail-card">
                        <div class="detail-card-header">
                            <div class="detail-card-icon" style="background: rgba(59, 130, 246, 0.15); color: #3b82f6;">📁</div>
                            <div class="detail-card-title">本地配置文件</div>
                        </div>
                        <div class="config-item">{runbook.local_config_path or '暂无'}</div>
                        {'<div style="color: #fbbf24; font-size: 11px; margin-top: 8px;">💡 本地配置文件不存在，请从模板复制一份并修改。</div>' if runbook.local_config_path and not (project_root / runbook.local_config_path).exists() else ''}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with col2:
                st.markdown(
                    f"""
                    <div class="detail-card">
                        <div class="detail-card-header">
                            <div class="detail-card-icon" style="background: rgba(234, 179, 8, 0.15); color: #eab308;">🚀</div>
                            <div class="detail-card-title">运行命令</div>
                        </div>
                        """,
                    unsafe_allow_html=True,
                )
                cmd_names = {
                    "validate_config": "校验配置",
                    "dry_run": "试运行（不保存）",
                    "run": "正式运行",
                    "source_health": "查看源健康状态",
                    "report": "生成报告",
                    "retry_failed": "重试失败项",
                }
                for key, cmd in (runbook.commands or {}).items():
                    label = cmd_names.get(key, key)
                    cmd_escaped = cmd.replace("'", "'")
                    st.markdown(
                        f"""
                        <div style="font-size: 11px; color: #94a3b8; margin-bottom: 4px;">{label}</div>
                        <div class="cmd-box">
                            <code style="flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{cmd}</code>
                            <button class="cmd-copy-btn" onclick="navigator.clipboard.writeText('{cmd_escaped}');this.innerHTML='✓';">📋</button>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                st.markdown("</div>", unsafe_allow_html=True)

        # --- 输出位置页面 ---
        elif active_tab == "输出位置":
            col1, col2 = st.columns(2)
            with col1:
                outputs = []
                if runbook.primary_output:
                    exists = (project_root / runbook.primary_output).exists()
                    outputs.append(f'<div><span class="{"success-dot" if exists else "danger-dot"}"></span><span style="font-size: 12px; color: #cbd5e1;">主输出文件</span></div><div style="font-size: 11px; color: #64748b; margin-bottom: 8px;">{runbook.primary_output}</div>')
                if runbook.health_file:
                    exists = (project_root / runbook.health_file).exists()
                    outputs.append(f'<div><span class="{"success-dot" if exists else "danger-dot"}"></span><span style="font-size: 12px; color: #cbd5e1;">健康状态文件</span></div><div style="font-size: 11px; color: #64748b; margin-bottom: 8px;">{runbook.health_file}</div>')
                if runbook.run_log_file:
                    exists = (project_root / runbook.run_log_file).exists()
                    outputs.append(f'<div><span class="{"success-dot" if exists else "danger-dot"}"></span><span style="font-size: 12px; color: #cbd5e1;">运行日志文件</span></div><div style="font-size: 11px; color: #64748b; margin-bottom: 8px;">{runbook.run_log_file}</div>')
                st.markdown(
                    f"""
                    <div class="detail-card">
                        <div class="detail-card-header">
                            <div class="detail-card-icon" style="background: rgba(34, 197, 94, 0.15); color: #22c55e;">📊</div>
                            <div class="detail-card-title">输出文件</div>
                        </div>
                        {'<br>'.join(outputs) if outputs else '<div style="color: #64748b;">暂无输出文件定义</div>'}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with col2:
                outputs = []
                if runbook.failed_queue_file:
                    exists = (project_root / runbook.failed_queue_file).exists()
                    outputs.append(f'<div><span class="{"success-dot" if exists else "danger-dot"}"></span><span style="font-size: 12px; color: #cbd5e1;">失败队列文件</span></div><div style="font-size: 11px; color: #64748b; margin-bottom: 8px;">{runbook.failed_queue_file}</div>')
                if runbook.report_dir:
                    exists = (project_root / runbook.report_dir).exists()
                    outputs.append(f'<div><span class="{"success-dot" if exists else "danger-dot"}"></span><span style="font-size: 12px; color: #cbd5e1;">报告目录</span></div><div style="font-size: 11px; color: #64748b; margin-bottom: 8px;">{runbook.report_dir}</div>')
                st.markdown(
                    f"""
                    <div class="detail-card">
                        <div class="detail-card-header">
                            <div class="detail-card-icon" style="background: rgba(239, 68, 68, 0.15); color: #ef4444;">📁</div>
                            <div class="detail-card-title">其他输出</div>
                        </div>
                        {'<br>'.join(outputs) if outputs else '<div style="color: #64748b;">暂无其他输出定义</div>'}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        # --- 常见失败页面 ---
        elif active_tab == "常见失败":
            if runbook.common_failures:
                failure_html = """
                <div class="detail-card">
                    <div class="detail-card-header">
                        <div class="detail-card-icon" style="background: rgba(239, 68, 68, 0.15); color: #ef4444;">⚠️</div>
                        <div class="detail-card-title">常见失败类型</div>
                    </div>
                    <table style="width: 100%; font-size: 12px; border-collapse: collapse;">
                        <thead>
                            <tr style="border-bottom: 1px solid #334155;">
                                <th style="text-align: left; padding: 8px; color: #94a3b8; font-weight: 600;">错误类型</th>
                                <th style="text-align: left; padding: 8px; color: #94a3b8; font-weight: 600;">含义</th>
                                <th style="text-align: left; padding: 8px; color: #94a3b8; font-weight: 600;">排查方向</th>
                            </tr>
                        </thead>
                        <tbody>
                """
                for cf in runbook.common_failures:
                    failure_html += f"""
                        <tr style="border-bottom: 1px solid #1e293b;">
                            <td style="padding: 10px 8px; color: #f1f5f9;">{cf.error_type}</td>
                            <td style="padding: 10px 8px; color: #94a3b8;">{cf.meaning}</td>
                            <td style="padding: 10px 8px; color: #60a5fa;">{cf.check}</td>
                        </tr>
                    """
                failure_html += """
                        </tbody>
                    </table>
                </div>
                """
                st.markdown(failure_html, unsafe_allow_html=True)
            else:
                st.markdown(
                    """
                    <div class="detail-card">
                        <div class="detail-card-header">
                            <div class="detail-card-icon" style="background: rgba(34, 197, 94, 0.15); color: #22c55e;">✅</div>
                            <div class="detail-card-title">暂无常见失败类型</div>
                        </div>
                        <div style="color: #94a3b8; font-size: 12px;">该能力目前没有记录常见失败类型。</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        # --- 排查步骤页面 ---
        elif active_tab == "排查步骤":
            if runbook.troubleshooting_steps:
                steps_html = """
                <div class="detail-card">
                    <div class="detail-card-header">
                        <div class="detail-card-icon" style="background: rgba(59, 130, 246, 0.15); color: #3b82f6;">🔍</div>
                        <div class="detail-card-title">排查步骤（按顺序）</div>
                    </div>
                    <ol style="margin: 0; padding-left: 20px;">
                """
                for i, step in enumerate(runbook.troubleshooting_steps, 1):
                    steps_html += f"<li style='padding: 8px 0; color: #cbd5e1; font-size: 13px;'>{step}</li>"
                steps_html += """
                    </ol>
                </div>
                """
                st.markdown(steps_html, unsafe_allow_html=True)
            else:
                st.markdown(
                    """
                    <div class="detail-card">
                        <div class="detail-card-header">
                            <div class="detail-card-icon" style="background: rgba(107, 114, 128, 0.15); color: #9ca3af;">🔍</div>
                            <div class="detail-card-title">暂无排查步骤</div>
                        </div>
                        <div style="color: #94a3b8; font-size: 12px;">该能力目前没有记录排查步骤。</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        # --- 相关文档页面 ---
        elif active_tab == "相关文档":
            if runbook.docs:
                docs_html = """
                <div class="detail-card">
                    <div class="detail-card-header">
                        <div class="detail-card-icon" style="background: rgba(139, 92, 246, 0.15); color: #8b5cf6;">📚</div>
                        <div class="detail-card-title">相关文档</div>
                    </div>
                    <ul style="margin: 0; padding-left: 0;">
                """
                for doc in runbook.docs:
                    exists = (project_root / doc).exists()
                    docs_html += f"""
                        <li style="display: flex; align-items: center; padding: 8px 0; border-bottom: 1px solid #1e293b; font-size: 12px;">
                            <span class="{'success-dot' if exists else 'danger-dot'}"></span>
                            <span style="color: #cbd5e1;">{doc}</span>
                        </li>
                    """
                docs_html += """
                    </ul>
                </div>
                """
                st.markdown(docs_html, unsafe_allow_html=True)
            else:
                st.markdown(
                    """
                    <div class="detail-card">
                        <div class="detail-card-header">
                            <div class="detail-card-icon" style="background: rgba(107, 114, 128, 0.15); color: #9ca3af;">📚</div>
                            <div class="detail-card-title">暂无相关文档</div>
                        </div>
                        <div style="color: #94a3b8; font-size: 12px;">该能力目前没有关联文档。</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        # --- 真实运行页面 ---
        elif active_tab == "真实运行":
            # M3B-3b 新增：状态解释 / 归因说明卡片
            runtime_mode_cn = RUNTIME_MODE_CN.get(cap.runtime_mode, cap.runtime_mode)
            status_explanation_text = runtime.status_explanation if runtime else "该能力尚未运行。"
            # 特定能力类型的归因说明
            attribution_note = ""
            if cap.capability_id.startswith("document_extraction."):
                if cap.capability_id.endswith(".pdf"):
                    attribution_note = "当前能力按文件类型归因：.pdf 失败只影响 document_extraction.pdf，不影响 html / txt / markdown。"
                elif cap.capability_id.endswith(".html"):
                    attribution_note = "当前能力按文件类型归因：.html / .htm 失败只影响 document_extraction.html。"
                elif cap.capability_id.endswith(".txt"):
                    attribution_note = "当前能力按文件类型归因：.txt 失败只影响 document_extraction.txt。"
                elif cap.capability_id.endswith(".markdown"):
                    attribution_note = "当前能力按文件类型归因：.md / .markdown 失败只影响 document_extraction.markdown。"
            elif cap.runtime_mode == "utility":
                attribution_note = "该能力是工具能力，不需要单独运行，也不会产生 source_health 记录。"
            elif cap.runtime_mode == "known_limited":
                attribution_note = "该能力当前属于已知限制：HKEXnews 页面客户端渲染导致静态抓取可能 empty_source，不作为每日修复项。"
            elif cap.runtime_mode == "manual_only":
                attribution_note = "该能力是人工触发能力，等待人工触发运行后才会产生记录。"

            st.markdown(
                f"""
                <div class="detail-card">
                    <div class="detail-card-header">
                        <div class="detail-card-icon" style="background: rgba(59, 130, 246, 0.15); color: #3b82f6;">ℹ️</div>
                        <div class="detail-card-title">状态解释 / 归因说明</div>
                    </div>
                    <div style="margin-bottom: 10px;">
                        <div style="font-size: 11px; color: #64748b; margin-bottom: 4px;">能力类型</div>
                        <div style="font-size: 13px; color: #cbd5e1;">{runtime_mode_cn}</div>
                    </div>
                    <div style="margin-bottom: 10px;">
                        <div style="font-size: 11px; color: #64748b; margin-bottom: 4px;">当前状态</div>
                        <div style="font-size: 13px; color: #cbd5e1;">{RUNTIME_HEALTH_CN.get(health_status, health_status)}</div>
                    </div>
                    <div style="margin-bottom: 10px;">
                        <div style="font-size: 11px; color: #64748b; margin-bottom: 4px;">状态解释</div>
                        <div style="font-size: 12px; color: #cbd5e1; line-height: 1.6;">{status_explanation_text}</div>
                    </div>
                    {f'<div style="margin-bottom: 10px;"><div style="font-size: 11px; color: #64748b; margin-bottom: 4px;">归因说明</div><div style="font-size: 12px; color: #fbbf24; line-height: 1.6;">{attribution_note}</div></div>' if attribution_note else ''}
                    <div>
                        <div style="font-size: 11px; color: #64748b; margin-bottom: 4px;">建议动作</div>
                        <div style="font-size: 12px; color: #cbd5e1;">{suggest_action(health_status, runtime.needs_attention if runtime else False, runtime.stale if runtime else False)}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            binding = runtime_binding_registry.get_binding(cap_id)
            evidence = None
            if binding:
                from opc_foundation.dashboard.health import build_runtime_evidence
                evidence = build_runtime_evidence(cap, binding, project_root)

            # 运行数据接入状态
            if binding is None:
                binding_status = "未绑定"
                binding_status_color = "#6b7280"
                binding_status_bg = "rgba(107, 114, 128, 0.15)"
            elif runtime and runtime.runtime_health == "not_configured":
                binding_status = "未配置"
                binding_status_color = "#6b7280"
                binding_status_bg = "rgba(107, 114, 128, 0.15)"
            elif runtime and runtime.runtime_health == "unknown_never_run":
                binding_status = "已接入·无运行记录"
                binding_status_color = "#3b82f6"
                binding_status_bg = "rgba(59, 130, 246, 0.15)"
            elif runtime and runtime.runtime_health == "healthy":
                binding_status = "运行正常"
                binding_status_color = "#22c55e"
                binding_status_bg = "rgba(34, 197, 94, 0.15)"
            elif runtime and runtime.runtime_health == "degraded":
                binding_status = "运行降级"
                binding_status_color = "#eab308"
                binding_status_bg = "rgba(234, 179, 8, 0.15)"
            elif runtime and runtime.runtime_health == "failed":
                binding_status = "运行失败"
                binding_status_color = "#ef4444"
                binding_status_bg = "rgba(239, 68, 68, 0.15)"
            else:
                binding_status = "未知"
                binding_status_color = "#6b7280"
                binding_status_bg = "rgba(107, 114, 128, 0.15)"

            # 最近三次运行状态点
            recent_run = runtime.recent_run_count if runtime else 0
            recent_fail = runtime.recent_failure_count if runtime else 0
            run_dots_html = ""
            for j in range(3):
                if j < recent_fail:
                    dot_c = "#ef4444"
                elif j < recent_run:
                    dot_c = "#22c55e"
                else:
                    dot_c = "#4b5563"
                run_dots_html += f'<span style="width: 12px; height: 12px; border-radius: 50%; background: {dot_c}; display: inline-block; margin-right: 6px;"></span>'

            # 最近运行时间
            last_run_time = runtime.latest_run_at if runtime and runtime.latest_run_at else "从未运行"
            if runtime and runtime.latest_run_at:
                last_run_time_display = runtime.latest_run_at[:16].replace("T", " ")
            else:
                last_run_time_display = "从未运行"

            # 最近状态
            latest_status = runtime.latest_status if runtime and runtime.latest_status else "-"
            latest_status_cn = _cn(latest_status) if latest_status != "-" else "-"
            if latest_status == "success":
                latest_status_color = "#22c55e"
            elif latest_status in ["partial", "empty_source", "partial_data"]:
                latest_status_color = "#eab308"
            elif latest_status in ["failed", "timeout"]:
                latest_status_color = "#ef4444"
            else:
                latest_status_color = "#6b7280"

            # 失败队列数量
            failed_queue_count = runtime.failed_queue_count if runtime else 0

            # 最新错误
            latest_error = runtime.latest_error if runtime and runtime.latest_error else "无"

            # 最新报告路径
            latest_report_path = evidence.latest_report_path if (evidence and evidence.latest_report_path) else "暂无报告"

            st.markdown(
                f"""
                <div class="detail-card">
                    <div class="detail-card-header">
                        <div class="detail-card-icon" style="background: rgba(59, 130, 246, 0.15); color: #3b82f6;">📊</div>
                        <div class="detail-card-title">真实运行数据</div>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px;">
                        <div>
                            <div style="font-size: 11px; color: #64748b; margin-bottom: 6px;">运行数据接入状态</div>
                            <span style="display: inline-flex; align-items: center; padding: 4px 12px; border-radius: 6px; font-size: 12px; font-weight: 500; background: {binding_status_bg}; color: {binding_status_color};">
                                <span style="width: 6px; height: 6px; border-radius: 50%; background: {binding_status_color}; margin-right: 6px;"></span>
                                {binding_status}
                            </span>
                        </div>
                        <div>
                            <div style="font-size: 11px; color: #64748b; margin-bottom: 6px;">最近运行时间</div>
                            <div style="font-size: 13px; color: #cbd5e1;">{last_run_time_display}</div>
                        </div>
                        <div>
                            <div style="font-size: 11px; color: #64748b; margin-bottom: 6px;">最近状态</div>
                            <div style="font-size: 13px; color: {latest_status_color}; font-weight: 500;">{latest_status_cn}</div>
                        </div>
                        <div>
                            <div style="font-size: 11px; color: #64748b; margin-bottom: 6px;">最近三次运行</div>
                            <div>{run_dots_html}</div>
                        </div>
                        <div>
                            <div style="font-size: 11px; color: #64748b; margin-bottom: 6px;">失败队列数量</div>
                            <div style="font-size: 13px; color: #cbd5e1;">{failed_queue_count} 条</div>
                        </div>
                        <div>
                            <div style="font-size: 11px; color: #64748b; margin-bottom: 6px;">最新错误</div>
                            <div style="font-size: 12px; color: #ef4444; word-break: break-all;">{latest_error}</div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(
                f"""
                <div class="detail-card">
                    <div class="detail-card-header">
                        <div class="detail-card-icon" style="background: rgba(168, 85, 247, 0.15); color: #a855f7;">📄</div>
                        <div class="detail-card-title">最近报告</div>
                    </div>
                    <div style="font-size: 12px; color: #94a3b8;">
                        {latest_report_path}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Binding 配置信息
            if binding:
                st.markdown(
                    f"""
                    <div class="detail-card">
                        <div class="detail-card-header">
                            <div class="detail-card-icon" style="background: rgba(249, 115, 22, 0.15); color: #f97316;">⚙️</div>
                            <div class="detail-card-title">运行时绑定配置</div>
                        </div>
                        <div style="font-size: 11px; color: #64748b; margin-bottom: 8px;">绑定的 source_types</div>
                        <div style="margin-bottom: 12px;">
                            {''.join([f'<span class="config-item">{st}</span>' for st in binding.source_types]) if binding.source_types else '<span style="color: #64748b;">无</span>'}
                        </div>
                        <div style="font-size: 11px; color: #64748b; margin-bottom: 8px;">健康状态文件</div>
                        <div style="font-size: 11px; color: #cbd5e1; font-family: monospace; margin-bottom: 8px;">{binding.health_file or '未配置'}</div>
                        <div style="font-size: 11px; color: #64748b; margin-bottom: 8px;">运行日志文件</div>
                        <div style="font-size: 11px; color: #cbd5e1; font-family: monospace; margin-bottom: 8px;">{binding.run_log_file or '未配置'}</div>
                        <div style="font-size: 11px; color: #64748b; margin-bottom: 8px;">失败队列文件</div>
                        <div style="font-size: 11px; color: #cbd5e1; font-family: monospace;">{binding.failed_queue_file or '未配置'}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    """
                    <div class="detail-card">
                        <div class="detail-card-header">
                            <div class="detail-card-icon" style="background: rgba(107, 114, 128, 0.15); color: #9ca3af;">⚙️</div>
                            <div class="detail-card-title">未配置运行时绑定</div>
                        </div>
                        <div style="color: #94a3b8; font-size: 12px;">该能力尚未绑定真实运行数据。如需接入运行数据，请在 capability_runtime_bindings.yaml 中添加配置。</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # 调用弹窗
    show_detail(cap_id)


def _render_workflow_map(st, usage_registry, registry, runtime_summaries):
    """渲染项目工作流页面（示意图风格 - 完整版）。

    功能说明：
        按照示意图风格重新设计：
        1. 顶部统计栏（6个卡片）
        2. 每个工作流一个完整的大卡片（用 components.html 渲染）
        3. 卡片内：左流程图 + 右能力表格
        4. 深色主题，边框连贯

    参数：
        st:                streamlit 模块
        usage_registry:    使用注册表
        registry:          能力注册表
        runtime_summaries: 运行时摘要
    """
    st.header("项目工作流总览")
    st.caption("Workflow Map — 展示项目的完整工作流程、每个阶段的负责 Agent 以及使用的 Foundation 能力 ✨")

    if not usage_registry.projects:
        st.info("暂无项目工作流配置。")
        return

    # --- 统计数据 ---
    total_projects = len(usage_registry.projects)
    total_workflows = sum(len(p.workflows) for p in usage_registry.projects)
    total_stages = sum(
        len(w.stages)
        for p in usage_registry.projects
        for w in p.workflows
    )
    used_cap_ids = set()
    for p in usage_registry.projects:
        for w in p.workflows:
            for s in w.stages:
                if s.capabilities:
                    used_cap_ids.update(s.capabilities)
    total_caps = len(used_cap_ids)

    # 健康状态统计
    healthy_count = 0
    degraded_count = 0
    failed_count = 0
    unknown_count = 0
    for cap_id in used_cap_ids:
        s = runtime_summaries.get(cap_id)
        if s:
            if s.runtime_health == "healthy":
                healthy_count += 1
            elif s.runtime_health == "degraded":
                degraded_count += 1
            elif s.runtime_health == "failed":
                failed_count += 1
            else:
                unknown_count += 1
        else:
            unknown_count += 1

    # --- 顶部统计栏（6列）---
    stat_cols = st.columns(6)
    _render_stat_card(stat_cols[0], "项目总数", str(total_projects), "#3b82f6")
    _render_stat_card(stat_cols[1], "工作流总数", str(total_workflows), "#f97316")
    _render_stat_card(stat_cols[2], "阶段总数", str(total_stages), "#22c55e")
    _render_stat_card(stat_cols[3], "能力引用", str(total_caps), "#a855f7")
    _render_health_stat_card(stat_cols[4], healthy_count, degraded_count, failed_count, unknown_count)
    _render_attention_card(stat_cols[5], degraded_count, failed_count)

    st.markdown("---")

    # --- 项目选择 ---
    project_names = [p.project_name for p in usage_registry.projects]
    selected_proj_name = st.selectbox(
        "选择项目", project_names, key="wf_proj_overview")
    project = next(
        (p for p in usage_registry.projects if p.project_name == selected_proj_name),
        usage_registry.projects[0],
    )

    st.markdown("")

    # --- 每个工作流一个大卡片（用 components.html 渲染完整卡片）---
    for workflow in project.workflows:
        _render_workflow_full_card(project, workflow, registry, runtime_summaries)
        st.markdown("")


def _render_stat_card(col, title, value, color):
    """渲染顶部统计卡片。

    功能说明：
        深色风格的统计卡片，左侧有色边框。

    参数：
        col:   streamlit 列对象
        title: 标题文字
        value: 数值
        color: 左侧边框色
    """
    html = (
        '<div style="background:#1f2937;border:1px solid #374151;border-left:4px solid '
        + color
        + ';border-radius:8px;padding:14px 16px;">'
        + '<div style="font-size:12px;color:#9ca3af;margin-bottom:6px;">'
        + title
        + "</div>"
        + '<div style="font-size:24px;font-weight:bold;color:#ffffff;">'
        + str(value)
        + "</div>"
        + "</div>"
    )
    col.markdown(html, unsafe_allow_html=True)


def _render_health_stat_card(col, healthy, degraded, failed, unknown):
    """渲染健康状态统计卡片。

    功能说明：
        一个卡片里显示4种健康状态的数量，横向排列更紧凑。

    参数：
        col:     streamlit 列对象
        healthy: 健康数量
        degraded: 降级数量
        failed: 失败数量
        unknown: 未知数量
    """
    html = (
        '<div style="background:#1f2937;border:1px solid #374151;border-radius:8px;padding:12px 14px;">'
        + '<div style="font-size:11px;color:#9ca3af;margin-bottom:8px;">能力健康</div>'
        + '<div style="display:flex;gap:10px;flex-wrap:wrap;">'
        + '<div style="display:flex;align-items:center;gap:4px;">'
        + '<span style="width:8px;height:8px;border-radius:50%;background:#22c55e;display:inline-block;"></span>'
        + '<span style="font-size:12px;color:#d1d5db;">' + str(healthy) + "</span>"
        + "</div>"
        + '<div style="display:flex;align-items:center;gap:4px;">'
        + '<span style="width:8px;height:8px;border-radius:50%;background:#f59e0b;display:inline-block;"></span>'
        + '<span style="font-size:12px;color:#d1d5db;">' + str(degraded) + "</span>"
        + "</div>"
        + '<div style="display:flex;align-items:center;gap:4px;">'
        + '<span style="width:8px;height:8px;border-radius:50%;background:#ef4444;display:inline-block;"></span>'
        + '<span style="font-size:12px;color:#d1d5db;">' + str(failed) + "</span>"
        + "</div>"
        + '<div style="display:flex;align-items:center;gap:4px;">'
        + '<span style="width:8px;height:8px;border-radius:50%;background:#6b7280;display:inline-block;"></span>'
        + '<span style="font-size:12px;color:#d1d5db;">' + str(unknown) + "</span>"
        + "</div>"
        + "</div>"
        + "</div>"
    )
    col.markdown(html, unsafe_allow_html=True)


def _render_attention_card(col, degraded, failed):
    """渲染需关注统计卡片。

    功能说明：
        显示需关注的异常总数。

    参数：
        col:     streamlit 列对象
        degraded: 降级数量
        failed: 失败数量
    """
    total_bad = degraded + failed
    html = (
        '<div style="background:#1f2937;border:1px solid #374151;border-left:4px solid #f59e0b;'
        + 'border-radius:8px;padding:14px 16px;">'
        + '<div style="font-size:12px;color:#9ca3af;margin-bottom:6px;">需关注</div>'
        + '<div style="font-size:24px;font-weight:bold;color:#f59e0b;">'
        + str(total_bad)
        + '</div>'
        + '<div style="font-size:11px;color:#6b7280;margin-top:2px;">'
        + "降级 " + str(degraded) + " · 失败 " + str(failed)
        + "</div>"
        + "</div>"
    )
    col.markdown(html, unsafe_allow_html=True)


def _render_workflow_full_card(project, workflow, registry, runtime_summaries):
    """用 components.html 渲染完整的工作流卡片（上下布局，完整显示项目介绍）。

    功能说明：
        上下布局（上：流程图，下：能力表格）
        修复头部显示不全问题：项目介绍完整显示，不限制宽度
        阶段卡片包含：编号+名称、agent、大图标、描述
        头部包含：项目名、用途标签、工作流标签、状态、目的
        能力表格右上角有运行统计

    参数：
        project:           项目对象
        workflow:          工作流对象
        registry:          能力注册表
        runtime_summaries: 运行时摘要
    """
    # --- 统计数据 ---
    stage_count = len(workflow.stages)
    cap_ids = []
    seen = set()
    for s in workflow.stages:
        if s.capabilities:
            for cid in s.capabilities:
                if cid not in seen:
                    seen.add(cid)
                    cap_ids.append(cid)
    cap_count = len(cap_ids)

    # 整体健康状态
    healthy = 0
    degraded = 0
    failed = 0
    total_runs = 0
    for cid in cap_ids:
        s = runtime_summaries.get(cid)
        if s:
            if s.runtime_health == "healthy":
                healthy += 1
            elif s.runtime_health == "degraded":
                degraded += 1
            elif s.runtime_health == "failed":
                failed += 1
            if hasattr(s, "recent_run_count") and s.recent_run_count:
                total_runs += s.recent_run_count

    if failed > 0:
        overall_status = "部分降级"
        status_color = "#f59e0b"
    elif degraded > 0:
        overall_status = "部分降级"
        status_color = "#f59e0b"
    elif healthy > 0:
        overall_status = "运行正常"
        status_color = "#22c55e"
    else:
        overall_status = "数据不足"
        status_color = "#6b7280"

    # 最近运行时间
    latest_run = ""
    for cid in cap_ids:
        s = runtime_summaries.get(cid)
        if s and s.latest_run_at:
            if not latest_run or s.latest_run_at > latest_run:
                latest_run = s.latest_run_at
    latest_display = latest_run[:16].replace("T", " ") if latest_run else "暂无数据"

    # 阶段颜色（蓝、橙、绿、紫、红、青）
    stage_colors = [
        {"border": "#3b82f6", "bg": "rgba(59, 130, 246, 0.15)", "text": "#60a5fa"},
        {"border": "#f97316", "bg": "rgba(249, 115, 22, 0.15)", "text": "#fb923c"},
        {"border": "#22c55e", "bg": "rgba(34, 197, 94, 0.15)", "text": "#4ade80"},
        {"border": "#a855f7", "bg": "rgba(168, 85, 247, 0.15)", "text": "#c084fc"},
        {"border": "#ef4444", "bg": "rgba(239, 68, 68, 0.15)", "text": "#f87171"},
        {"border": "#06b6d4", "bg": "rgba(6, 182, 212, 0.15)", "text": "#22d3ee"},
    ]

    # 阶段图标
    stage_icons = ["📥", "⚙️", "📦", "📊", "🚀", "🔍"]

    # --- 构建流程图 HTML ---
    flowchart_html = '<div class="flowchart-container">'
    for i, stage in enumerate(workflow.stages):
        color = stage_colors[i % len(stage_colors)]
        icon = stage_icons[i % len(stage_icons)]

        # 清理阶段名称（去掉 ①② 等前缀）
        clean_name = stage.stage_name
        for prefix in ["① ", "② ", "③ ", "④ ", "⑤ ", "⑥ ", "⑦ ", "⑧ "]:
            clean_name = clean_name.replace(prefix, "")

        flowchart_html += '<div class="stage-card" style="border-color: ' + color["border"] + '; background: ' + color["bg"] + ';">'
        flowchart_html += '<div class="stage-num" style="color: ' + color["text"] + ';">' + str(i + 1) + '. ' + clean_name + '</div>'
        flowchart_html += '<div class="stage-agent">agent: ' + stage.agent + '</div>'
        flowchart_html += '<div class="stage-icon">' + icon + '</div>'
        flowchart_html += '<div class="stage-purpose">' + stage.purpose + '</div>'
        flowchart_html += '</div>'

        if i < len(workflow.stages) - 1:
            flowchart_html += '<div class="arrow">→</div>'

    flowchart_html += '</div>'

    # --- 构建能力表格 HTML ---
    table_rows = _build_cap_table_rows_detailed(cap_ids, registry, runtime_summaries)

    # --- 整个卡片的 HTML ---
    html = """
<!DOCTYPE html>
<html>
<head>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    background: transparent;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    padding: 0;
}
.card {
    background: #111827;
    border: 1px solid #374151;
    border-radius: 12px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
}
/* 卡片头部 */
.card-header {
    padding: 12px 20px;
    border-bottom: 1px solid #1f2937;
    background: #0f172a;
}
.header-row {
    display: flex;
    align-items: center;
    gap: 12px;
}
.project-name {
    color: #f97316;
    font-size: 15px;
    font-weight: 600;
    flex-shrink: 0;
}
.project-tag {
    background: rgba(59, 130, 246, 0.2);
    color: #60a5fa;
    padding: 3px 14px;
    border-radius: 6px;
    font-size: 12px;
    border: 1px solid rgba(59, 130, 246, 0.3);
    flex: 1;
}
.workflow-info {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-top: 8px;
}
.workflow-tag {
    background: #1e293b;
    color: #94a3b8;
    padding: 2px 10px;
    border-radius: 4px;
    font-size: 11px;
    font-family: 'Courier New', monospace;
    flex-shrink: 0;
}
.status-badge {
    background: rgba(34, 197, 94, 0.2);
    color: #4ade80;
    padding: 2px 10px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
    border: 1px solid rgba(34, 197, 94, 0.3);
    text-transform: uppercase;
    flex-shrink: 0;
}
.workflow-desc {
    color: #9ca3af;
    font-size: 12px;
}
/* 卡片主体 */
.card-body {
    padding: 14px 20px;
    display: flex;
    flex-direction: column;
    gap: 16px;
}
.section-title {
    color: #ffffff;
    font-weight: 600;
    font-size: 14px;
    margin-bottom: 8px;
}
/* 流程图样式 */
.flowchart-container {
    display: flex;
    align-items: stretch;
    gap: 10px;
    overflow-x: auto;
    padding: 14px 10px 18px 10px;
    background: #0f172a;
    border-radius: 8px;
    border: 1px solid #1e293b;
}
.flowchart-container::-webkit-scrollbar {
    height: 6px;
}
.flowchart-container::-webkit-scrollbar-track {
    background: #1e293b;
    border-radius: 3px;
}
.flowchart-container::-webkit-scrollbar-thumb {
    background: #475569;
    border-radius: 3px;
}
.stage-card {
    flex-shrink: 0;
    width: 160px;
    border: 2px solid #3b82f6;
    border-radius: 8px;
    padding: 12px 12px;
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
}
.stage-num {
    font-size: 13px;
    font-weight: 600;
    color: #60a5fa;
    margin-bottom: 4px;
}
.stage-agent {
    color: #9ca3af;
    font-size: 11px;
    font-family: 'Courier New', monospace;
    margin-bottom: 10px;
}
.stage-icon {
    font-size: 36px;
    margin-bottom: 10px;
    line-height: 1;
}
.stage-purpose {
    color: #d1d5db;
    font-size: 11px;
    line-height: 1.5;
}
.arrow {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    color: #6b7280;
    font-size: 22px;
    font-weight: 300;
}
/* 表格区域 */
.table-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}
.table-title {
    color: #ffffff;
    font-weight: 600;
    font-size: 14px;
}
.table-stats {
    display: flex;
    align-items: center;
    gap: 10px;
}
.stats-label {
    color: #9ca3af;
    font-size: 12px;
}
.stats-select {
    background: #22c55e;
    color: #ffffff;
    padding: 3px 12px;
    border-radius: 6px;
    font-size: 12px;
    font-weight: 500;
}
.cap-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
}
.cap-table th {
    text-align: left;
    padding: 8px 8px;
    color: #9ca3af;
    font-weight: 500;
    font-size: 11px;
    border-bottom: 1px solid #374151;
    white-space: nowrap;
}
.cap-table td {
    padding: 8px 8px;
    border-bottom: 1px solid #1f2937;
    color: #d1d5db;
}
.cap-table .cap-id {
    font-family: 'Courier New', monospace;
    font-size: 11px;
    color: #9ca3af;
    white-space: nowrap;
}
.cap-table .cap-name {
    color: #f3f4f6;
    font-weight: 500;
}
.cap-table .track {
    font-size: 11px;
    color: #6b7280;
}
.health-cell {
    display: flex;
    align-items: center;
    gap: 6px;
}
.health-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
}
.health-text {
    font-size: 11px;
}
.run-time {
    font-size: 11px;
    color: #9ca3af;
    white-space: nowrap;
}
.latest-status {
    font-size: 11px;
    font-weight: 500;
}
.status-success { color: #22c55e; }
.status-partial { color: #f59e0b; }
.status-failed { color: #ef4444; }
.status-unknown { color: #6b7280; }
.table-container {
    overflow-y: auto;
    background: #0f172a;
    border-radius: 8px;
    border: 1px solid #1e293b;
    padding: 0 6px;
    max-height: 280px;
}
.table-container::-webkit-scrollbar {
    width: 6px;
}
.table-container::-webkit-scrollbar-track {
    background: #1e293b;
}
.table-container::-webkit-scrollbar-thumb {
    background: #475569;
    border-radius: 3px;
}
/* 卡片底部 */
.card-footer {
    display: flex;
    gap: 28px;
    align-items: center;
    padding: 12px 20px;
    border-top: 1px solid #1f2937;
    background: #0f172a;
    font-size: 12px;
    color: #9ca3af;
    flex-wrap: wrap;
}
.card-footer b {
    color: #d1d5db;
    font-weight: 500;
}
.footer-item {
    display: flex;
    align-items: center;
    gap: 5px;
}
.footer-status {
    margin-left: auto;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 6px;
}
.status-dot {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    display: inline-block;
}
</style>
</head>
<body>
<div class="card">
    <div class="card-header">
        <div class="header-row">
            <span class="project-name">项目: """ + project.project_id + """</span>
            <span class="project-tag">""" + project.description + """</span>
        </div>
        <div class="workflow-info">
            <span class="workflow-tag">工作流: """ + workflow.workflow_id + """</span>
            <span class="status-badge">""" + workflow.status.upper() + """</span>
            <span class="workflow-desc">""" + (workflow.description or "") + """</span>
        </div>
    </div>
    <div class="card-body">
        <div>
            <div class="section-title">业务流程图</div>
            """ + flowchart_html + """
        </div>
        <div>
            <div class="table-header">
                <span class="table-title">该工作流使用的能力（""" + str(cap_count) + """）</span>
                <div class="table-stats">
                    <span class="stats-label">运行统计（最近 24h）</span>
                    <span class="stats-select">总运行: """ + str(total_runs) + """ 次</span>
                </div>
            </div>
            <div class="table-container">
                <table class="cap-table">
                    <thead>
                        <tr>
                            <th>能力 ID</th>
                            <th>能力名称</th>
                            <th>Track</th>
                            <th>健康状态</th>
                            <th>最后运行</th>
                            <th>最近状态</th>
                        </tr>
                    </thead>
                    <tbody>
                        """ + table_rows + """
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    <div class="card-footer">
        <span class="footer-item">📋 阶段数: <b>""" + str(stage_count) + """</b></span>
        <span class="footer-item">🔧 涉及能力: <b>""" + str(cap_count) + """</b></span>
        <span class="footer-item">🕐 最后运行: <b>""" + latest_display + """</b></span>
        <span class="footer-status">
            <span class="status-dot" style="background: """ + status_color + """;"></span>
            状态: """ + overall_status + """
        </span>
    </div>
</div>
</body>
</html>
"""
    components.html(html, height=800, scrolling=False)



def _build_cap_table_rows_detailed(cap_ids, registry, runtime_summaries):
    """构建能力表格行（详细版本，更接近示意图）。

    功能说明：
        构建能力表格的 HTML 行，包含：能力ID、能力名称、Track、
        健康状态（圆点+文字）、最后运行、最近状态。

    参数：
        cap_ids:           能力 ID 列表
        registry:          能力注册表
        runtime_summaries: 运行时摘要

    返回值：
        str: HTML 表格行
    """
    rows = ""
    for cid in cap_ids:
        cap = next((c for c in registry.capabilities if c.capability_id == cid), None)
        s = runtime_summaries.get(cid)

        cap_name = cap.display_name if (cap and cap.display_name) else cid.split(".")[-1].replace("_", " ").title()
        track = cap.track if cap else "-"

        # 健康状态
        if s and s.runtime_health == "healthy":
            health_dot = "#22c55e"
            health_text = "healthy"
            health_class = "status-success"
        elif s and s.runtime_health == "degraded":
            health_dot = "#f59e0b"
            health_text = "degraded"
            health_class = "status-partial"
        elif s and s.runtime_health == "failed":
            health_dot = "#ef4444"
            health_text = "failed"
            health_class = "status-failed"
        else:
            health_dot = "#6b7280"
            health_text = "unknown"
            health_class = "status-unknown"

        # 最后运行时间
        if s and s.latest_run_at:
            run_time = s.latest_run_at[:16].replace("T", " ")
            # 简化显示，比如 "2m ago"
            run_display = _time_ago(s.latest_run_at)
        else:
            run_display = "-"

        # 最近状态
        if s and hasattr(s, "latest_status") and s.latest_status:
            latest_status = s.latest_status
            if latest_status == "success":
                status_class = "status-success"
            elif latest_status == "partial":
                status_class = "status-partial"
            elif latest_status == "failed":
                status_class = "status-failed"
            else:
                status_class = "status-unknown"
        else:
            latest_status = "-"
            status_class = "status-unknown"

        rows += (
            '<tr>'
            + '<td class="cap-id">' + cid + '</td>'
            + '<td class="cap-name">' + cap_name + '</td>'
            + '<td class="track">' + track + '</td>'
            + '<td><div class="health-cell"><span class="health-dot" style="background: ' + health_dot + ';"></span><span class="health-text ' + health_class + '">' + health_text + '</span></div></td>'
            + '<td class="run-time">' + run_display + '</td>'
            + '<td class="latest-status ' + status_class + '">' + latest_status + '</td>'
            + '</tr>'
        )

    return rows


def _time_ago(iso_time_str):
    """把 ISO 时间字符串转换成 "X ago" 格式。

    功能说明：
        把类似 "2025-11-14T10:30:00" 的时间转换成 "2h ago" 这样的友好格式。

    参数：
        iso_time_str: ISO 格式的时间字符串

    返回值：
        str: 友好的时间描述
    """
    try:
        from datetime import datetime
        # 解析时间
        if "T" in iso_time_str:
            dt = datetime.fromisoformat(iso_time_str.replace("Z", ""))
        else:
            dt = datetime.fromisoformat(iso_time_str)

        now = datetime.now()
        diff = now - dt

        total_seconds = diff.total_seconds()
        if total_seconds < 60:
            return "just now"
        elif total_seconds < 3600:
            minutes = int(total_seconds / 60)
            return str(minutes) + "m ago"
        elif total_seconds < 86400:
            hours = int(total_seconds / 3600)
            return str(hours) + "h ago"
        else:
            days = int(total_seconds / 86400)
            return str(days) + "d ago"
    except Exception:
        return iso_time_str[:10]


def _build_horizontal_flowchart(workflow):
    """构建横向 Mermaid 流程图代码。

    功能说明：
        生成横向（LR）的 Mermaid 流程图，每个阶段用不同颜色。

    参数：
        workflow: 工作流对象

    返回：
        str: Mermaid 代码
    """
    # 阶段颜色（蓝、橙、绿、紫、青、粉）
    stage_colors = [
        ("#3b82f6", "#1d4ed8"),
        ("#f97316", "#c2410c"),
        ("#22c55e", "#15803d"),
        ("#a855f7", "#7e22ce"),
        ("#06b6d4", "#0e7490"),
        ("#ec4899", "#be185d"),
    ]

    lines = ["flowchart LR"]

    for i, stage in enumerate(workflow.stages):
        node_id = "s" + str(i)
        color_idx = i % len(stage_colors)
        bg, border = stage_colors[color_idx]
        class_name = "stage" + str(color_idx)

        cap_count = len(stage.capabilities) if stage.capabilities else 0
        display_name = stage.stage_name.replace("\n", "<br/>")

        label = (
            '<div style="text-align:center;padding:6px 10px;">'
            + '<div style="font-size:13px;font-weight:bold;">'
            + display_name
            + "</div>"
            + '<div style="font-size:10px;opacity:0.85;margin-top:3px;">agent: '
            + stage.agent
            + "</div>"
            + '<div style="font-size:10px;opacity:0.75;margin-top:2px;">'
            + str(cap_count)
            + " 个能力</div>"
            + "</div>"
        )

        lines.append("    " + node_id + '["' + label + '"]:::' + class_name)

    # 箭头
    for i in range(len(workflow.stages) - 1):
        lines.append("    s" + str(i) + " --> s" + str(i + 1))

    # 样式类
    lines.append("")
    for i, (bg, border) in enumerate(stage_colors):
        lines.append(
            "    classDef stage"
            + str(i)
            + " fill:"
            + bg
            + ",stroke:"
            + border
            + ",stroke-width:2px,color:#ffffff,stroke-radius:10px;"
        )

    return "\n".join(lines)


def _build_cap_table_rows(cap_ids, registry, runtime_summaries):
    """构建能力表格的 HTML 行。

    功能说明：
        为每个能力生成一行表格 HTML。

    参数：
        cap_ids:           能力 ID 列表
        registry:          能力注册表
        runtime_summaries: 运行时摘要

    返回：
        str: HTML 行字符串
    """
    health_colors = {
        "healthy": "#22c55e",
        "degraded": "#f59e0b",
        "failed": "#ef4444",
        "unknown": "#6b7280",
        "not_configured": "#4b5563",
    }

    status_class_map = {
        "success": "status-success",
        "partial": "status-partial",
        "failed": "status-failed",
    }

    rows = ""
    for cid in cap_ids:
        cap = next((c for c in registry.capabilities if c.capability_id == cid), None)
        if cap is None:
            continue

        s = runtime_summaries.get(cid)

        # 健康状态
        if s:
            health = s.runtime_health
            latest_run = s.latest_run_at
            latest_status = s.latest_status or ""
        else:
            health = "unknown"
            latest_run = ""
            latest_status = ""

        dot_color = health_colors.get(health, "#6b7280")
        health_cn = _cn(health)

        # 最后运行时间
        run_display = _format_relative_time(latest_run)

        # 最近状态
        status_cn = _cn(latest_status) if latest_status else "-"
        status_class = status_class_map.get(latest_status, "status-unknown")

        # Track
        track = cid.split(".")[0] if "." in cid else "unknown"

        rows += (
            "<tr>"
            + '<td class="cap-id">' + cid + "</td>"
            + '<td class="cap-name">' + cap.display_name + "</td>"
            + '<td class="track">' + track + "</td>"
            + "<td>"
            + '<span class="health-dot" style="background:' + dot_color + ';"></span>'
            + '<span class="health-text">' + health_cn + "</span>"
            + "</td>"
            + '<td class="run-time">' + run_display + "</td>"
            + '<td class="' + status_class + '">' + status_cn + "</td>"
            + "</tr>"
        )

    return rows


def _format_relative_time(iso_time):
    """把 ISO 时间格式化成相对时间。

    功能说明：
        把 ISO 时间字符串转成 "X ago" 的相对时间格式。

    参数：
        iso_time: ISO 时间字符串

    返回：
        str: 相对时间字符串
    """
    if not iso_time:
        return "-"

    try:
        from datetime import datetime

        ts = iso_time.replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo:
            now = datetime.now(dt.tzinfo)
        else:
            now = datetime.now()

        delta = now - dt
        total_seconds = int(delta.total_seconds())

        if total_seconds < 0:
            return "刚刚"
        elif total_seconds < 60:
            return str(total_seconds) + "s ago"
        elif total_seconds < 3600:
            return str(total_seconds // 60) + "m ago"
        elif total_seconds < 86400:
            return str(total_seconds // 3600) + "h ago"
        else:
            return str(total_seconds // 86400) + "d ago"
    except Exception:
        return "-"


def _render_health_monitor(st, registry, runtime_summaries):
    """渲染健康监控页面（效果图风格，纯中文版本）。

    功能说明：
        完全按照效果图风格设计，包含：
        - 顶部7个统计卡片（运行正常、降级、失败、需关注、过期、未知、未配置）
        - 搜索和筛选栏
        - 能力列表表格（带彩色圆点、运行状态圆点）
        - 分页功能
        全部用 components.html 渲染

    参数：
        st:                streamlit 模块
        registry:          能力注册表
        runtime_summaries: 运行时摘要字典
    """
    st.header("健康监控")
    st.caption("查看所有能力的运行健康状态、运行统计和异常情况")

    # M3B-3b 新增：状态说明区域
    with st.expander("📖 状态说明", expanded=False):
        st.markdown(
            """
**运行健康** | **含义**
--- | ---
**运行正常** | 最近一次运行成功，且没有失败队列积压，状态正常。
**降级** | 最近运行部分异常，但不是完全失败。
**失败** | 最近一次运行失败。
**需关注** | 连续异常或失败队列积压，需要排查。
**未知 · 尚未运行** | 已绑定运行数据路径，但本地暂无运行记录。运行对应能力后，Dashboard 会自动读取状态。
**工具能力** | 工具函数（如 runtime.*），不需要单独运行记录，也不会产生 source_health。
**已知限制** | 能力存在但当前有明确外部限制（如 HKEX 客户端渲染），不作为每日修复项。
**过期** | 超过设定天数未运行。
            """
        )
        st.caption("校准说明：未知 ≠ 失败；工具能力不计入异常统计；已知限制不作为每日修复项。")

    # --- 收集所有能力数据 ---
    all_caps = []
    for cap in registry.capabilities:
        s = runtime_summaries.get(cap.capability_id)
        if s is None:
            continue

        cap_name = cap.display_name if (cap and cap.display_name) else cap.capability_id.split(".")[-1].replace("_", " ").title()

        all_caps.append({
            "capability_id": s.capability_id,
            "cap_name": cap_name,
            "track": cap.track,
            "runtime_health": s.runtime_health,
            "latest_status": s.latest_status,
            "latest_run_at": s.latest_run_at,
            "recent_run_count": s.recent_run_count,
            "recent_failure_count": s.recent_failure_count,
            "consecutive_failures": s.consecutive_failures,
            "failed_queue_count": s.failed_queue_count,
            "needs_attention": s.needs_attention,
            "stale": s.stale,
            "latest_error": s.latest_error,
        })

    total = len(all_caps)
    if total == 0:
        st.info("暂无能力健康数据。")
        return

    # --- 统计数据 ---
    healthy_count = sum(1 for c in all_caps if c["runtime_health"] == "healthy")
    degraded_count = sum(1 for c in all_caps if c["runtime_health"] == "degraded")
    failed_count = sum(1 for c in all_caps if c["runtime_health"] == "failed")
    attention_count = sum(1 for c in all_caps if c["needs_attention"])
    stale_count = sum(1 for c in all_caps if c["stale"])
    unknown_count = sum(1 for c in all_caps if c["runtime_health"] == "unknown_never_run")
    not_configured_count = sum(1 for c in all_caps if c["runtime_health"] == "not_configured")
    utility_count = sum(1 for c in all_caps if c["runtime_health"] == "utility")
    known_limited_count = sum(1 for c in all_caps if c["runtime_health"] == "known_limited")

    def pct(n):
        return str(round(n / total * 100, 1)) + "%" if total > 0 else "0%"

    # ============================================
    # M3C-4 新增：Trial Runtime 摘要展示
    # ============================================
    trial_summary = build_trial_runtime_summary()
    if trial_summary.data_exists:
        health_color_map = {
            "healthy": "#22c55e",
            "degraded": "#eab308",
            "failed": "#ef4444",
            "unknown": "#6b7280",
        }
        health_label_map = {
            "healthy": "运行正常",
            "degraded": "降级",
            "failed": "失败",
            "unknown": "未知",
        }
        hc = health_color_map.get(trial_summary.overall_health, "#6b7280")
        hl = health_label_map.get(trial_summary.overall_health, trial_summary.overall_health)
        run_time = trial_summary.latest_run_at[:16].replace("T", " ") if trial_summary.latest_run_at else "-"

        with st.container():
            st.markdown(
                f"""
                <div style="background:#111827;border:1px solid #374151;border-radius:8px;padding:14px 18px;margin-bottom:16px;">
                    <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;">
                        <span style="font-size:18px;">🧪</span>
                        <span style="font-size:15px;font-weight:600;color:#ffffff;">Foundation Trial Sources</span>
                        <span style="background:rgba({_hex_to_rgb(hc)},0.2);color:{hc};border:1px solid rgba({_hex_to_rgb(hc)},0.3);border-radius:4px;padding:2px 8px;font-size:12px;">{hl}</span>
                    </div>
                    <div style="display:grid;grid-template-columns:repeat(6,1fr);gap:12px;">
                        <div><div style="font-size:11px;color:#9ca3af;">Trial 源数</div><div style="font-size:18px;font-weight:600;color:#fff;">{trial_summary.total_sources}</div></div>
                        <div><div style="font-size:11px;color:#9ca3af;">成功</div><div style="font-size:18px;font-weight:600;color:#22c55e;">{trial_summary.success_count}</div></div>
                        <div><div style="font-size:11px;color:#9ca3af;">失败</div><div style="font-size:18px;font-weight:600;color:#ef4444;">{trial_summary.failed_count}</div></div>
                        <div><div style="font-size:11px;color:#9ca3af;">Transient</div><div style="font-size:18px;font-weight:600;color:#eab308;">{trial_summary.transient_count}</div></div>
                        <div><div style="font-size:11px;color:#9ca3af;">成功率</div><div style="font-size:18px;font-weight:600;color:#fff;">{round(trial_summary.success_count / trial_summary.total_sources * 100, 1) if trial_summary.total_sources else 0}%</div></div>
                        <div><div style="font-size:11px;color:#9ca3af;">最近运行</div><div style="font-size:13px;color:#d1d5db;">{run_time}</div></div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        with st.container():
            st.info("🧪 Foundation Trial Sources：尚未运行，暂无 trial 数据。运行 `scripts/run_foundation_trial_sources.ps1` 后自动刷新。")

    # --- 构建表格行 ---
    table_rows = ""
    for i, c in enumerate(all_caps):
        # 健康状态颜色
        health_colors = {
            "healthy": "#22c55e",
            "degraded": "#eab308",
            "failed": "#ef4444",
            "unknown_never_run": "#3b82f6",
            "not_configured": "#6b7280",
            "utility": "#6b7280",
            "known_limited": "#a3a3a3",
        }
        dot_color = health_colors.get(c["runtime_health"], "#6b7280")

        # 健康状态徽章
        health_labels = {
            "healthy": "运行正常",
            "degraded": "降级",
            "failed": "失败",
            "unknown_never_run": "未知 · 尚未运行",
            "not_configured": "未配置",
            "utility": "工具能力",
            "known_limited": "已知限制",
        }
        health_label = health_labels.get(c["runtime_health"], c["runtime_health"])
        health_badge_color = health_colors.get(c["runtime_health"], "#6b7280")

        # 最新状态
        status_labels = {
            "success": "成功",
            "partial": "部分成功",
            "failed": "失败",
            "empty_source": "空源",
            "no_data": "无数据",
            "not_run_yet": "未运行",
            "timeout": "超时",
            "ocr_disabled_partial": "OCR禁用部分",
            "partial_data": "部分数据",
            "stale_run": "过期运行",
            "utility_only": "仅工具",
        }
        status_label = status_labels.get(c["latest_status"], c["latest_status"] or "-")
        if c["latest_status"] == "success":
            status_color = "#22c55e"
        elif c["latest_status"] in ["partial", "empty_source", "partial_data"]:
            status_color = "#eab308"
        elif c["latest_status"] in ["failed", "timeout", "ocr_disabled_partial"]:
            status_color = "#ef4444"
        else:
            status_color = "#6b7280"

        # 最新运行时间
        if c["latest_run_at"]:
            run_time_display = c["latest_run_at"][:16].replace("T", " ")
            run_time_ago = _time_ago(c["latest_run_at"])
        else:
            run_time_display = "-"
            run_time_ago = "-"

        # 最近3次运行状态圆点（模拟：根据 recent_run_count 和 recent_failure_count）
        run_dots = ""
        total_recent = c["recent_run_count"]
        fail_recent = c["recent_failure_count"]
        success_recent = total_recent - fail_recent
        # 显示3个圆点
        for j in range(3):
            if j < fail_recent:
                dot_c = "#ef4444"
            elif j < total_recent:
                dot_c = "#22c55e"
            else:
                dot_c = "#4b5563"
            run_dots += '<span class="run-dot" style="background: ' + dot_c + ';"></span>'

        # 最近3次失败圆点
        fail_dots = ""
        for j in range(3):
            if j < fail_recent:
                dot_c = "#ef4444"
            else:
                dot_c = "#4b5563"
            fail_dots += '<span class="run-dot" style="background: ' + dot_c + ';"></span>'

        # 最新错误信息
        error_display = c["latest_error"] if c["latest_error"] else "-"
        if len(error_display) > 20:
            error_display = error_display[:20] + "..."

        # 建议动作
        suggestion = suggest_action(c["runtime_health"], c["needs_attention"], c["stale"])

        table_rows += (
            '<tr>'
            + '<td><div class="cap-id-cell"><span class="health-dot" style="background: ' + dot_color + ';"></span><span class="cap-id-text">' + c["capability_id"] + '</span></div></td>'
            + '<td class="cap-name">' + c["cap_name"] + '</td>'
            + '<td class="track">' + c["track"] + '</td>'
            + '<td><span class="health-badge" style="background: rgba(' + _hex_to_rgb(health_badge_color) + ', 0.2); color: ' + health_badge_color + '; border-color: rgba(' + _hex_to_rgb(health_badge_color) + ', 0.3);">' + health_label + '</span></td>'
            + '<td style="color: ' + status_color + ';">' + status_label + '</td>'
            + '<td><div class="run-time-cell"><div>' + run_time_ago + '</div><div class="run-time-sub">' + run_time_display + '</div></div></td>'
            + '<td><div class="run-dots">' + run_dots + '</div></td>'
            + '<td class="num-cell">' + str(c["recent_failure_count"]) + '</td>'
            + '<td class="num-cell">' + str(c["consecutive_failures"]) + '</td>'
            + '<td class="num-cell">' + str(c["failed_queue_count"]) + '</td>'
            + '<td class="error-cell">' + error_display + '</td>'
            + '<td class="suggestion-cell">' + suggestion + '</td>'
            + '<td><button class="view-btn" onclick="alert(\'查看详情：' + c["capability_id"] + '\')">👁</button></td>'
            + '</tr>'
        )

    # --- 所有 track 选项 ---
    all_tracks = sorted(set(c["track"] for c in all_caps))
    track_options = '<option value="">全部 (All)</option>'
    for t in all_tracks:
        track_options += '<option value="' + t + '">' + t + '</option>'

    # --- 整个页面的 HTML ---
    html = """
<!DOCTYPE html>
<html>
<head>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    background: transparent;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    padding: 0;
    color: #d1d5db;
}
/* 统计卡片区域 */
.stats-row {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 12px;
    margin-bottom: 16px;
}
.stat-card {
    background: #111827;
    border: 1px solid #374151;
    border-radius: 8px;
    padding: 14px;
    display: flex;
    align-items: center;
    gap: 12px;
}
.stat-icon {
    width: 36px;
    height: 36px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    flex-shrink: 0;
}
.stat-info {
    display: flex;
    flex-direction: column;
}
.stat-label {
    font-size: 12px;
    color: #9ca3af;
    margin-bottom: 2px;
}
.stat-value {
    font-size: 20px;
    font-weight: 600;
    color: #ffffff;
}
.stat-pct {
    font-size: 11px;
    color: #6b7280;
}
/* 筛选栏 */
.filter-bar {
    background: #111827;
    border: 1px solid #374151;
    border-radius: 8px;
    padding: 12px 14px;
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;
    flex-wrap: wrap;
}
.search-box {
    flex: 1;
    min-width: 200px;
    position: relative;
}
.search-box input {
    width: 100%;
    background: #1f2937;
    border: 1px solid #374151;
    border-radius: 6px;
    padding: 8px 12px 8px 36px;
    color: #d1d5db;
    font-size: 13px;
    outline: none;
}
.search-box input:focus {
    border-color: #3b82f6;
}
.search-icon {
    position: absolute;
    left: 12px;
    top: 50%;
    transform: translateY(-50%);
    color: #6b7280;
    font-size: 14px;
}
.filter-select {
    background: #1f2937;
    border: 1px solid #374151;
    border-radius: 6px;
    padding: 7px 10px;
    color: #d1d5db;
    font-size: 12px;
    outline: none;
    min-width: 120px;
}
.filter-select:focus {
    border-color: #3b82f6;
}
.export-btn {
    background: #1f2937;
    border: 1px solid #374151;
    border-radius: 6px;
    padding: 7px 14px;
    color: #d1d5db;
    font-size: 12px;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 6px;
}
.export-btn:hover {
    background: #374151;
}
/* 表格区域 */
.table-wrapper {
    background: #111827;
    border: 1px solid #374151;
    border-radius: 8px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    max-height: 520px;
}
.health-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
}
.table-scroll {
    overflow-y: auto;
    flex: 1;
}
.table-scroll::-webkit-scrollbar {
    width: 8px;
}
.table-scroll::-webkit-scrollbar-track {
    background: #0f172a;
}
.table-scroll::-webkit-scrollbar-thumb {
    background: #475569;
    border-radius: 4px;
}
.table-scroll::-webkit-scrollbar-thumb:hover {
    background: #6b7280;
}
.health-table th {
    text-align: left;
    padding: 10px 12px;
    color: #9ca3af;
    font-weight: 500;
    font-size: 11px;
    border-bottom: 1px solid #374151;
    background: #0f172a;
    white-space: nowrap;
}
.health-table td {
    padding: 10px 12px;
    border-bottom: 1px solid #1f2937;
    color: #d1d5db;
    vertical-align: middle;
}
.health-table tr:hover {
    background: rgba(59, 130, 246, 0.05);
}
.cap-id-cell {
    display: flex;
    align-items: center;
    gap: 8px;
}
.health-dot {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    flex-shrink: 0;
}
.cap-id-text {
    font-family: 'Courier New', monospace;
    font-size: 11px;
    color: #9ca3af;
}
.cap-name {
    color: #f3f4f6;
    font-weight: 500;
}
.track {
    font-size: 11px;
    color: #6b7280;
}
.health-badge {
    padding: 2px 10px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 500;
    border: 1px solid;
    white-space: nowrap;
}
.run-time-cell {
    font-size: 11px;
}
.run-time-sub {
    font-size: 10px;
    color: #6b7280;
    margin-top: 2px;
}
.run-dots {
    display: flex;
    gap: 4px;
}
.run-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
}
.num-cell {
    text-align: center;
    font-weight: 500;
}
.error-cell {
    font-size: 11px;
    color: #9ca3af;
    max-width: 120px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.suggestion-cell {
    font-size: 11px;
    color: #60a5fa;
    max-width: 140px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.view-btn {
    background: transparent;
    border: 1px solid #374151;
    border-radius: 4px;
    padding: 4px 8px;
    color: #9ca3af;
    cursor: pointer;
    font-size: 14px;
}
.view-btn:hover {
    background: #374151;
    color: #ffffff;
}
/* 分页区域 */
.pagination {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 14px;
    background: #0f172a;
    border-top: 1px solid #1f2937;
    font-size: 12px;
    color: #9ca3af;
}
.page-left {
    display: flex;
    align-items: center;
    gap: 8px;
}
.page-left select {
    background: #1f2937;
    border: 1px solid #374151;
    border-radius: 4px;
    padding: 4px 8px;
    color: #d1d5db;
    font-size: 12px;
}
.page-right {
    display: flex;
    align-items: center;
    gap: 6px;
}
.page-btn {
    background: #1f2937;
    border: 1px solid #374151;
    border-radius: 4px;
    padding: 5px 10px;
    color: #9ca3af;
    cursor: pointer;
    font-size: 12px;
}
.page-btn:hover {
    background: #374151;
}
.page-btn.active {
    background: #3b82f6;
    border-color: #3b82f6;
    color: #ffffff;
}
.page-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}
</style>
</head>
<body>
<!-- 统计卡片 -->
<div class="stats-row">
    <div class="stat-card">
        <div class="stat-icon" style="background: rgba(34, 197, 94, 0.2); color: #22c55e;">📈</div>
        <div class="stat-info">
            <span class="stat-label">运行正常</span>
            <span class="stat-value">""" + str(healthy_count) + """ <span class="stat-pct">(""" + pct(healthy_count) + """)</span></span>
        </div>
    </div>
    <div class="stat-card">
        <div class="stat-icon" style="background: rgba(234, 179, 8, 0.2); color: #eab308;">⚡</div>
        <div class="stat-info">
            <span class="stat-label">降级</span>
            <span class="stat-value">""" + str(degraded_count) + """ <span class="stat-pct">(""" + pct(degraded_count) + """)</span></span>
        </div>
    </div>
    <div class="stat-card">
        <div class="stat-icon" style="background: rgba(239, 68, 68, 0.2); color: #ef4444;">❌</div>
        <div class="stat-info">
            <span class="stat-label">失败</span>
            <span class="stat-value">""" + str(failed_count) + """ <span class="stat-pct">(""" + pct(failed_count) + """)</span></span>
        </div>
    </div>
    <div class="stat-card">
        <div class="stat-icon" style="background: rgba(249, 115, 22, 0.2); color: #f97316;">⚠️</div>
        <div class="stat-info">
            <span class="stat-label">需关注</span>
            <span class="stat-value">""" + str(attention_count) + """ <span class="stat-pct">(""" + pct(attention_count) + """)</span></span>
        </div>
    </div>
    <div class="stat-card">
        <div class="stat-icon" style="background: rgba(168, 85, 247, 0.2); color: #a855f7;">⏰</div>
        <div class="stat-info">
            <span class="stat-label">过期</span>
            <span class="stat-value">""" + str(stale_count) + """ <span class="stat-pct">(""" + pct(stale_count) + """)</span></span>
        </div>
    </div>
    <div class="stat-card">
        <div class="stat-icon" style="background: rgba(59, 130, 246, 0.2); color: #3b82f6;">❓</div>
        <div class="stat-info">
            <span class="stat-label">未知</span>
            <span class="stat-value">""" + str(unknown_count) + """ <span class="stat-pct">(""" + pct(unknown_count) + """)</span></span>
        </div>
    </div>
    <div class="stat-card">
        <div class="stat-icon" style="background: rgba(107, 114, 128, 0.2); color: #6b7280;">⚙️</div>
        <div class="stat-info">
            <span class="stat-label">未配置</span>
            <span class="stat-value">""" + str(not_configured_count) + """ <span class="stat-pct">(""" + pct(not_configured_count) + """)</span></span>
        </div>
    </div>
</div>

<!-- 筛选栏 -->
<div class="filter-bar">
    <div class="search-box">
        <span class="search-icon">🔍</span>
        <input type="text" placeholder="搜索 capability_id / 名称...">
    </div>
    <select class="filter-select">
        """ + track_options + """
    </select>
    <select class="filter-select">
        <option value="">运行健康状态 (全部)</option>
        <option value="healthy">运行正常</option>
        <option value="degraded">降级</option>
        <option value="failed">失败</option>
        <option value="unknown">未知</option>
        <option value="not_configured">未配置</option>
    </select>
    <select class="filter-select">
        <option value="">最近运行时间 (全部)</option>
        <option value="1h">1小时内</option>
        <option value="24h">24小时内</option>
        <option value="7d">7天内</option>
        <option value="older">更早</option>
    </select>
    <select class="filter-select">
        <option value="">失败队列 (全部)</option>
        <option value="has">有失败</option>
        <option value="none">无失败</option>
    </select>
    <button class="export-btn">📥 导出 CSV</button>
</div>

<!-- 表格 -->
<div class="table-wrapper">
    <div class="table-scroll">
        <table class="health-table">
            <thead>
                <tr>
                    <th>能力 ID</th>
                    <th>能力名称</th>
                    <th>所属模块</th>
                    <th>运行健康</th>
                    <th>最近状态</th>
                    <th>最近运行时间</th>
                    <th>最近三次运行</th>
                    <th>最近失败次数</th>
                    <th>连续失败次数</th>
                    <th>失败队列数量</th>
                    <th>最新错误</th>
                    <th>建议动作</th>
                    <th>操作</th>
                </tr>
            </thead>
            <tbody>
                """ + table_rows + """
            </tbody>
        </table>
    </div>

    <!-- 分页 -->
    <div class="pagination">
        <div class="page-left">
            显示
            <select>
                <option>20</option>
                <option>50</option>
                <option>100</option>
            </select>
            条 / 页 &nbsp;&nbsp; 共 """ + str(total) + """ 条
        </div>
        <div class="page-right">
            <button class="page-btn" disabled>‹</button>
            <button class="page-btn active">1</button>
            <button class="page-btn">›</button>
        </div>
    </div>
</div>

</body>
</html>
"""
    components.html(html, height=850, scrolling=True)


def _hex_to_rgb(hex_color):
    """把十六进制颜色转换成 RGB 字符串。

    功能说明：
        把 #22c55e 这样的颜色转换成 "34, 197, 94" 这样的 RGB 格式，
        用于设置 rgba 透明度。

    参数：
        hex_color: 十六进制颜色值，如 "#22c55e"

    返回值：
        str: RGB 字符串，如 "34, 197, 94"
    """
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return str(r) + ", " + str(g) + ", " + str(b)



def _render_run_history(st, registry, project_root):
    """渲染运行日志页面。

    功能说明：
        选择一个能力，展示最近的运行日志记录。

    参数：
        st:           streamlit 模块
        registry:     能力注册表
        project_root: 项目根目录
    """
    st.header("运行日志")

    # 只展示有 run_log_file 的能力
    caps_with_log = [c for c in registry.capabilities if c.run_log_file]
    if not caps_with_log:
        st.info("暂无能力配置了运行日志文件。")
        return

    cap_ids = [c.capability_id for c in caps_with_log]
    selected = st.selectbox("选择能力", cap_ids)

    cap = next(c for c in caps_with_log if c.capability_id == selected)
    log_path = project_root / cap.run_log_file
    records = load_jsonl_safe(log_path)

    if not records:
        st.info(f"运行日志为空或文件不存在：{cap.run_log_file}")
        return

    # 按时间倒序展示最近 20 条
    sorted_records = sorted(
        records, key=lambda r: r.get("started_at", "") or "", reverse=True
    )
    recent = sorted_records[:20]

    rows = []
    for r in recent:
        rows.append(
            {
                "运行ID": r.get("run_id", ""),
                "命令": r.get("command", ""),
                "状态": _cn(r.get("status", "")),
                "开始时间": r.get("started_at", ""),
                "结束时间": r.get("finished_at", ""),
                "候选数": r.get("candidate_count", ""),
                "保存数": r.get("saved_count", ""),
                "失败数": r.get("failed_count", ""),
            }
        )

    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.caption(f"共 {len(records)} 条记录，展示最近 {len(recent)} 条。")


def _render_failed_queue(st, registry, project_root):
    """渲染失败队列页面。

    功能说明：
        选择一个能力，展示失败队列中的记录。

    参数：
        st:           streamlit 模块
        registry:     能力注册表
        project_root: 项目根目录
    """
    st.header("失败队列")

    caps_with_queue = [c for c in registry.capabilities if c.failed_queue_file]
    if not caps_with_queue:
        st.info("暂无能力配置了失败队列文件。")
        return

    cap_ids = [c.capability_id for c in caps_with_queue]
    selected = st.selectbox("选择能力", cap_ids)

    cap = next(c for c in caps_with_queue if c.capability_id == selected)
    queue_path = project_root / cap.failed_queue_file
    records = load_jsonl_safe(queue_path)

    if not records:
        st.info(f"失败队列为空或文件不存在：{cap.failed_queue_file}")
        return

    rows = []
    for r in records:
        rows.append(
            {
                "来源ID": r.get("source_id", ""),
                "来源类型": r.get("source_type", ""),
                "项目标识": r.get("item_key", ""),
                "错误类型": r.get("error_type", ""),
                "错误信息": r.get("error_message", ""),
                "重试次数": r.get("retry_count", ""),
                "创建时间": r.get("created_at", ""),
            }
        )

    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.caption(f"共 {len(records)} 条失败记录。")


def _render_docs_hub(st, registry, project_root):
    """渲染文档入口页面。

    功能说明：
        展示核心文档和能力相关文档的链接。

    参数：
        st:           streamlit 模块
        registry:     能力注册表
        project_root: 项目根目录
    """
    st.header("文档入口")

    st.subheader("核心文档")
    core_docs = collect_core_docs(project_root)
    if core_docs:
        for doc in core_docs:
            full = project_root / doc
            st.markdown(f"- `{doc}`" + (" ✅" if full.exists() else " ❌"))
    else:
        st.info("未找到核心文档。")

    st.subheader("能力相关文档")
    cap_docs = collect_docs_from_capabilities(registry.capabilities)
    if cap_docs:
        for doc in cap_docs:
            full = project_root / doc
            st.markdown(f"- `{doc}`" + (" ✅" if full.exists() else " ❌"))
    else:
        st.info("暂无能力相关文档。")

def _render_top_stats(st, usage_registry, runtime_summaries):
    """渲染页面顶部的统计栏（HTML 版本，更美观）。

    功能说明：
        在每个页面顶部显示统计数据，用 HTML 渲染保证样式统一：
        - 项目总数、工作流总数、阶段总数、能力引用总数
        - 健康状态统计（运行正常、降级、失败、未知）

    参数：
        st:                streamlit 模块
        usage_registry:    使用注册表
        runtime_summaries: 运行时摘要字典
    """
    # 计算统计数据
    total_projects = len(usage_registry.projects)
    total_workflows = sum(len(p.workflows) for p in usage_registry.projects)
    total_stages = sum(len(w.stages) for p in usage_registry.projects for w in p.workflows)

    # 能力引用总数
    total_cap_refs = 0
    for p in usage_registry.projects:
        for w in p.workflows:
            for s in w.stages:
                if s.capabilities:
                    total_cap_refs += len(s.capabilities)

    # 健康状态统计
    total_caps = len(runtime_summaries)
    healthy = sum(1 for s in runtime_summaries.values() if s.runtime_health == "healthy")
    degraded = sum(1 for s in runtime_summaries.values() if s.runtime_health == "degraded")
    failed = sum(1 for s in runtime_summaries.values() if s.runtime_health == "failed")
    unknown = sum(1 for s in runtime_summaries.values() if s.runtime_health == "unknown")

    # 统计卡片数据
    cards = [
        {"label": "项目总数", "value": str(total_projects), "icon": "📁", "color": "#f97316"},
        {"label": "工作流总数", "value": str(total_workflows), "icon": "🔄", "color": "#8b5cf6"},
        {"label": "阶段总数", "value": str(total_stages), "icon": "📋", "color": "#06b6d4"},
        {"label": "能力引用总数", "value": str(total_cap_refs), "icon": "🔗", "color": "#ec4899"},
        {"label": "运行正常", "value": str(healthy), "icon": "🟢", "color": "#22c55e"},
        {"label": "降级", "value": str(degraded), "icon": "🟡", "color": "#eab308"},
        {"label": "失败", "value": str(failed), "icon": "🔴", "color": "#ef4444"},
        {"label": "未知", "value": str(unknown), "icon": "🔵", "color": "#3b82f6"},
    ]

    cards_html = ""
    for card in cards:
        cards_html += (
            '<div class="stat-card" style="border-left: 3px solid ' + card["color"] + ';">'
            + '<div class="stat-icon" style="background: rgba(' + _hex_to_rgb(card["color"]) + ', 0.15); color: ' + card["color"] + ';">' + card["icon"] + '</div>'
            + '<div class="stat-content">'
            + '<div class="stat-label">' + card["label"] + '</div>'
            + '<div class="stat-value">' + card["value"] + '</div>'
            + '</div>'
            + '</div>'
        )

    html = """
<!DOCTYPE html>
<html>
<head>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    background: transparent;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    padding: 0;
}
.stats-container {
    display: grid;
    grid-template-columns: repeat(8, 1fr);
    gap: 10px;
    width: 100%;
}
.stat-card {
    background: #111827;
    border: 1px solid #374151;
    border-radius: 8px;
    padding: 10px 12px;
    display: flex;
    align-items: center;
    gap: 10px;
}
.stat-icon {
    width: 32px;
    height: 32px;
    border-radius: 6px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    flex-shrink: 0;
}
.stat-content {
    display: flex;
    flex-direction: column;
    min-width: 0;
}
.stat-label {
    font-size: 11px;
    color: #9ca3af;
    margin-bottom: 2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.stat-value {
    font-size: 18px;
    font-weight: 600;
    color: #ffffff;
}
@media (max-width: 1200px) {
    .stats-container {
        grid-template-columns: repeat(4, 1fr);
    }
}
</style>
</head>
<body>
<div class="stats-container">
    """ + cards_html + """
</div>
</body>
</html>
"""
    components.html(html, height=70, scrolling=False)






def _render_config_check(st, registry, usage_registry, runbook_registry, runtime_binding_registry, source_inventory, project_root):
    """渲染配置检查页面。

    功能说明（小白解读）：
        运行各种配置校验，包括：
        1. 能力注册表校验（ID 唯一性、track 引用）
        2. 运行手册校验（ID 对应关系、覆盖情况）
        3. 文档存在性检查
        4. 未使用能力
        5. 未知引用检查
        6. Runtime Binding 检查
        7. 信息源清单检查（M3C-0B 新增）

    参数：
        st:                     streamlit 模块
        registry:               能力注册表
        usage_registry:         使用注册表
        runbook_registry:       运行手册注册表
        runtime_binding_registry: 运行时绑定注册表
        source_inventory:       信息源清单
        project_root:           项目根目录
    """
    st.header("配置检查")
    st.caption("一键检查所有配置是否正确，哪里红了修哪里 ✅")

    # M3B-3b 新增：分类说明
    with st.expander("📖 检查分类说明", expanded=False):
        st.markdown(
            """
**分类** | **含义** | **示例**
--- | --- | ---
**错误** | 必须修复，否则能力无法正常运行。 | binding capability_id 不存在、重复 capability_id
**警告** | 不影响运行，但需要知晓（data/ 目录不提交是正常的）。 | 文档路径缺失、运行文件不存在、运行手册缺失
**说明** | 正常设计，按预期存在。 | runtime 工具能力无 binding、HKEX known_limited、能力尚未被使用
            """
        )

    # M3C-4 新增：Trial 配置状态检查
    st.subheader("🧪 Trial 配置与运行状态")
    trial_summary = build_trial_runtime_summary()
    if trial_summary.data_exists:
        health_label_map = {"healthy": "运行正常", "degraded": "降级", "failed": "失败", "unknown": "未知"}
        hl = health_label_map.get(trial_summary.overall_health, trial_summary.overall_health)
        st.success(
            f"✅ Trial 运行数据已生成 | 健康状态：{hl} | "
            f"源数：{trial_summary.total_sources} | "
            f"成功：{trial_summary.success_count} | "
            f"失败：{trial_summary.failed_count} | "
            f"Transient：{trial_summary.transient_count}"
        )
        if trial_summary.transient_sources:
            st.info(f"ℹ️ Transient watch 源：{', '.join(trial_summary.transient_sources)}（如 cls_cn HTTP 418，非 P0/P1 blocker）")
        if not trial_summary.has_blocked_included:
            st.success("✅ blocked/search/dormant/problem source 未误纳入 trial")
    else:
        st.info("ℹ️ 尚未生成 trial 运行数据。运行 `scripts/run_foundation_trial_sources.ps1 -Mode run` 后自动刷新。")

    # 1. 校验 capability_id 唯一性和 track 引用
    st.subheader("1️⃣ 能力注册表校验")
    errors = validate_capabilities(registry)
    if errors:
        for err in errors:
            st.error(err)
    else:
        st.success(f"✅ 能力注册表校验通过（共 {len(registry.capabilities)} 个能力）。")

    # 2. 运行手册校验
    st.subheader("2️⃣ 运行手册校验")
    if runbook_registry.load_error:
        st.error(f"运行手册加载失败：{runbook_registry.load_error}")
    else:
        rb_errors = validate_runbooks(runbook_registry, registry)
        if rb_errors:
            for err in rb_errors:
                st.error(err)
        else:
            st.success(f"✅ 运行手册校验通过（共 {len(runbook_registry.runbooks)} 个运行手册）。")

        # 检查覆盖情况
        cap_ids = {c.capability_id for c in registry.capabilities}
        rb_ids = {r.capability_id for r in runbook_registry.runbooks}
        missing = cap_ids - rb_ids
        extra = rb_ids - cap_ids
        if missing:
            st.warning(f"⚠️ 有 {len(missing)} 个能力没有运行手册：{', '.join(sorted(missing))}")
        if extra:
            st.warning(f"⚠️ 有 {len(extra)} 个运行手册不在能力注册表中：{', '.join(sorted(extra))}")
        if not missing and not extra:
            st.success("✅ 运行手册覆盖率 100%，所有能力都有对应的运行手册。")

    # 3. 文档存在性检查
    st.subheader("3️⃣ 文档存在性检查")
    missing_docs = check_docs_exist(registry.capabilities, project_root)
    if missing_docs:
        total_missing = sum(len(docs) for docs in missing_docs.values())
        st.warning(f"⚠️ 有 {len(missing_docs)} 个能力缺失文档（共 {total_missing} 个）")
        for cap_id, docs in missing_docs.items():
            st.caption(f"- {cap_id}: {', '.join(docs)}")
    else:
        st.success("✅ 所有文档路径都存在。")

    # 4. 未使用能力
    st.subheader("4️⃣ 未使用能力")
    unused = find_unused_capabilities(registry.capabilities, usage_registry)
    if unused:
        st.info(f"ℹ️【说明】有 {len(unused)} 个能力暂未被使用（这是正常设计）：")
        for cap_id in unused:
            st.caption(f"- {cap_id}")
    else:
        st.success("✅ 所有能力都被使用。")

    # 5. 未知引用
    st.subheader("5️⃣ 未知引用检查")
    unknown = find_unknown_usage_references(registry.capabilities, usage_registry)
    if unknown:
        for project_id, cap_id in unknown:
            st.error(f"❌ 项目 {project_id} 引用了未知能力：{cap_id}")
    else:
        st.success("✅ 没有未知引用。")

    # 6. Runtime Binding 检查
    st.subheader("6️⃣ 运行时绑定检查")
    if runtime_binding_registry.load_error:
        st.error(f"运行时绑定加载失败：{runtime_binding_registry.load_error}")
    else:
        # 检查 capability_runtime_bindings.yaml 是否存在
        bindings_path_local = project_root / "configs" / "capability_runtime_bindings.local.yaml"
        bindings_path_main = project_root / "configs" / "capability_runtime_bindings.yaml"
        if bindings_path_local.exists():
            st.info(f"ℹ️【说明】使用本地运行时绑定配置：capability_runtime_bindings.local.yaml")
        elif bindings_path_main.exists():
            st.success(f"✅ 运行时绑定配置文件存在（共 {len(runtime_binding_registry.bindings)} 个绑定）。")
        else:
            st.warning("⚠️ capability_runtime_bindings.yaml 不存在，所有能力将显示为未绑定。")

        # 校验 binding capability_id 是否有效（错误级别）
        binding_errors = []
        binding_warnings = []
        cap_ids = {c.capability_id for c in registry.capabilities}
        binding_ids = {b.capability_id for b in runtime_binding_registry.bindings}
        unknown_binding_ids = binding_ids - cap_ids
        if unknown_binding_ids:
            binding_errors.append(f"以下 binding 引用了未知的 capability_id：{', '.join(sorted(unknown_binding_ids))}")

        # 检查重复
        seen: dict[str, int] = {}
        for b in runtime_binding_registry.bindings:
            seen[b.capability_id] = seen.get(b.capability_id, 0) + 1
        for cap_id, count in seen.items():
            if count > 1:
                binding_errors.append(f"runtime binding capability_id 重复：{cap_id} 出现了 {count} 次")

        if binding_errors:
            for err in binding_errors:
                st.error(f"❌【错误】{err}")
        else:
            st.success("✅ 所有 binding 的 capability_id 都有效。")

        # 检查 binding 文件路径是否存在（警告级别，因为 data/ 不提交是正常的）
        missing_files = check_binding_files_exist(runtime_binding_registry, project_root)
        if missing_files:
            total_missing_files = sum(len(files) for files in missing_files.values())
            st.warning(f"⚠️【警告】有 {len(missing_files)} 个 binding 的运行文件不存在（共 {total_missing_files} 个）。这通常是正常的，因为 data/ 目录不提交到仓库。")
            for cap_id, files in missing_files.items():
                st.caption(f"- {cap_id}: {', '.join(files)}")
        else:
            st.success("✅ 所有 binding 指向的运行文件都存在。")

        # 绑定覆盖率
        covered = cap_ids & binding_ids
        not_covered = cap_ids - binding_ids

        st.info(f"📊 绑定覆盖率：{len(covered)} / {len(cap_ids)} 个能力（{round(len(covered)/len(cap_ids)*100, 1) if cap_ids else 0}%）")

        if not_covered:
            # 区分"工具能力无 binding"（说明）和"数据能力无 binding"（警告）
            utility_caps = []
            other_caps = []
            for cap_id in sorted(not_covered):
                # 查 cap 对象的 runtime_mode
                cap_obj = next((c for c in registry.capabilities if c.capability_id == cap_id), None)
                if cap_obj and cap_obj.runtime_mode == "utility":
                    utility_caps.append(cap_id)
                else:
                    other_caps.append(cap_id)

            if utility_caps:
                st.info(f"ℹ️【说明】有 {len(utility_caps)} 个工具能力无需绑定（runtime.*）：{', '.join(utility_caps)}")
            if other_caps:
                st.warning(f"⚠️【警告】有 {len(other_caps)} 个数据能力尚未绑定真实运行数据：{', '.join(other_caps)}")

        if unknown_binding_ids:
            # 已经在前面用 error 报过了，这里省略
            pass

    # 7. 信息源清单检查（M3C-0B 新增）
    st.subheader("7️⃣ 信息源清单检查")
    source_validation = validate_source_inventory(source_inventory, registry)

    # 展示摘要指标
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("source group 数量", source_validation.group_count)
    col2.metric("source 数量", source_validation.source_count)
    col3.metric("默认启用", source_validation.enabled_count)
    col4.metric("高风险禁止源", source_validation.high_risk_count)

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("错误", source_validation.error_count, delta_color="inverse")
    col6.metric("警告", source_validation.warning_count, delta_color="off")
    col7.metric("说明", source_validation.info_count)
    col8.metric("搜索补充源", source_validation.search_provider_count)

    # 优先级分布
    with st.expander("📊 优先级分布", expanded=False):
        if source_validation.priority_counts:
            priority_data = [
                {"优先级": p, "数量": c}
                for p, c in sorted(source_validation.priority_counts.items())
            ]
            st.table(priority_data)
        else:
            st.info("暂无数据")

    # 自动化模式分布
    with st.expander("⚙️ 自动化模式分布", expanded=False):
        if source_validation.automation_counts:
            automation_data = [
                {"自动化模式": m, "数量": c}
                for m, c in sorted(source_validation.automation_counts.items())
            ]
            st.table(automation_data)
        else:
            st.info("暂无数据")

    # 检查结果表
    st.subheader("检查结果")
    if source_validation.checks:
        # 转换为表格数据
        level_labels = {"error": "🔴 错误", "warning": "🟡 警告", "info": "🔵 说明"}
        check_rows = []
        for c in source_validation.checks:
            check_rows.append({
                "级别": level_labels.get(c.level, c.level),
                "检查项": c.check_name,
                "结果": c.result,
                "说明": c.detail,
            })
        st.table(check_rows)
    else:
        st.info("暂无检查结果")

    # 总体结论
    if source_validation.error_count > 0:
        st.error("❌ 存在必须修复的问题，暂不建议进入上线脚本阶段。")
    elif source_validation.warning_count > 0:
        st.warning("⚠️ 存在需要注意的配置项，但不阻断后续规划。")
    else:
        st.success("✅ 信息源清单校验通过，可进入上线计划阶段。")


def main():
    """Dashboard 主入口函数。

    功能说明：
        Streamlit 应用的主函数，负责页面导航和渲染。
        用侧边栏 radio 切换 8 个页面。

    异常处理：
        streamlit 未安装时抛出 SystemExit 并提示安装命令。
    """
    st = _lazy_import_streamlit()

    # 页面设置
    st.set_page_config(
        page_title="OPC Foundation 中控台",
        page_icon="📊",
        layout="wide",
    )

    # 注入品牌配色 CSS（支持 light/dark 两种主题）
    st.markdown(
        f"""
        <style>
        /* 指标卡片：带橙色左边框 */
        .stMetric {{
            border-radius: 8px;
            padding: 12px;
            border-left: 4px solid {COLORS["orange"]};
        }}
        /* 能力卡片容器样式（在 _render_capability_card 中用 inline style，这里补充主题适配） */
        </style>
        """,
        unsafe_allow_html=True,
    )

    # 加载数据
    project_root = _find_project_root()
    registry, usage_registry, runbook_registry, runtime_binding_registry, runtime_summaries, source_inventory = _load_all_data(project_root)

    # 侧边栏导航
    st.sidebar.title("OPC Foundation 中控台")
    st.sidebar.caption("Foundation provides infrastructure.")

    # 页面导航（在上）
    pages = [
        "能力地图",
        "项目工作流",
        "健康监控",
        "配置检查",
    ]
    page = st.sidebar.radio("页面导航", pages)

    # 能力健康状态（在下，去掉"图例"）
    st.sidebar.subheader("能力健康状态")
    health_items = [
        ("#22c55e", "healthy", "运行正常"),
        ("#eab308", "degraded", "降级"),
        ("#ef4444", "failed", "失败"),
        ("#3b82f6", "unknown", "未知"),
        ("#6b7280", "not_configured", "未配置"),
        ("#a855f7", "stale", "过期"),
        ("#f97316", "needs_attention", "需关注"),
    ]
    for color, key, label in health_items:
        count = sum(1 for s in runtime_summaries.values() if 
            (key == "needs_attention" and s.needs_attention) or
            (key == "stale" and s.stale) or
            (key not in ["needs_attention", "stale"] and s.runtime_health == key))
        st.sidebar.markdown(
            f"<div style='display: flex; align-items: center; gap: 8px; margin-bottom: 4px;'>"
            f"<span style='width: 12px; height: 12px; background: {color}; border-radius: 50%; display: inline-block;'></span>"
            f"<span style='font-size: 13px; color: #d1d5db;'>{label} ({count})</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # --- 顶部统计栏 ---
    _render_top_stats(st, usage_registry, runtime_summaries)

    # 根据选择渲染对应页面
    if page == "能力地图":
        _render_capability_map(st, registry, runbook_registry, runtime_binding_registry, runtime_summaries, project_root)
    elif page == "项目工作流":
        _render_workflow_map(st, usage_registry, registry, runtime_summaries)
    elif page == "健康监控":
        _render_health_monitor(st, registry, runtime_summaries)
    elif page == "配置检查":
        _render_config_check(st, registry, usage_registry, runbook_registry, runtime_binding_registry, source_inventory, project_root)


if __name__ == "__main__":
    main()
