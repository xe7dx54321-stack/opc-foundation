"""OPC Foundation Dashboard Streamlit 应用。

功能说明（小白解读）：
    这是一个 Streamlit dashboard，用来查看 opc-foundation 的能力地图、
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

from .loaders import (
    check_docs_exist,
    load_capabilities_config,
    load_jsonl_safe,
    load_usage_registry,
    validate_capabilities,
)
from .health import build_dashboard_summary, build_runtime_summary
from .usage import (
    build_usage_index,
    find_unused_capabilities,
    find_unknown_usage_references,
)
from .docs import collect_core_docs, collect_docs_from_capabilities
from .models import Capability, CapabilityRegistry, CapabilityUsageRegistry

# 品牌配色
COLORS = {
    "dark": "#141413",
    "light": "#faf9f5",
    "orange": "#d97757",
    "blue": "#6a9bcc",
    "green": "#788c5d",
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

    功能说明：
        加载能力配置、使用注册表、运行时摘要。
        一次性加载，避免重复读取文件。

    参数：
        project_root: 项目根目录

    返回：
        (registry, usage_registry, runtime_summaries) 三元组
    """
    cap_path = project_root / "configs" / "foundation_capabilities.yaml"
    registry = load_capabilities_config(cap_path)

    # 优先用 local 配置，没有就用 example
    usage_path = project_root / "configs" / "capability_usage_registry.local.yaml"
    if not usage_path.exists():
        usage_path = project_root / "configs" / "capability_usage_registry.example.yaml"
    usage_registry = load_usage_registry(usage_path)

    # 构建运行时摘要
    runtime_summaries = {}
    for cap in registry.capabilities:
        runtime_summaries[cap.capability_id] = build_runtime_summary(
            cap, project_root
        )

    return registry, usage_registry, runtime_summaries


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
    st.header("总览 Dashboard")
    summary = build_dashboard_summary(
        registry.capabilities, runtime_summaries, usage_registry
    )

    st.subheader("能力成熟度")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("能力总数", summary.total_capabilities)
    col2.metric("Production Trial Ready", summary.production_trial_ready_count)
    col3.metric("MVP Ready", summary.mvp_ready_count)
    col4.metric("Degraded", summary.degraded_count)

    st.subheader("运行健康")
    col1, col2, col3 = st.columns(3)
    col1.metric("Failed", summary.failed_count)
    col2.metric("Unknown", summary.unknown_count)
    col3.metric("Not Configured", summary.not_configured_count)

    st.subheader("关注与使用")
    col1, col2, col3 = st.columns(3)
    col1.metric("需要关注", summary.needs_attention_count)
    col2.metric("已过期", summary.stale_count)
    col3.metric("已使用 / 未使用", f"{summary.used_count} / {summary.unused_count}")

    st.markdown("---")
    st.caption(
        "核心原则：Foundation provides infrastructure. Business systems keep judgment."
    )


def _render_capability_map(st, registry):
    """渲染能力地图页面。

    功能说明：
        按主线分组展示所有能力，包括名称、成熟度、输入类型、主输出。

    参数：
        st:       streamlit 模块
        registry: 能力注册表
    """
    st.header("能力地图 Capability Map")

    for track in registry.tracks:
        st.subheader(f"{track.name} ({track.track_id})")
        st.caption(f"状态：{track.status} | {track.description}")

        caps = [c for c in registry.capabilities if c.track == track.track_id]
        if not caps:
            st.info("该主线下暂无能力。")
            continue

        rows = []
        for cap in caps:
            rows.append(
                {
                    "capability_id": cap.capability_id,
                    "name": cap.name,
                    "category": cap.category,
                    "maturity": cap.maturity_status,
                    "input_type": cap.input_type,
                    "primary_output": cap.primary_output,
                    "docs_count": len(cap.docs),
                }
            )
        st.dataframe(rows, use_container_width=True, hide_index=True)


def _render_workflow_map(st, usage_registry):
    """渲染项目工作流页面。

    功能说明：
        展示所有项目、工作流、阶段，以及每个阶段引用的能力。

    参数：
        st:             streamlit 模块
        usage_registry: 使用注册表
    """
    st.header("项目工作流 Workflow Map")

    if not usage_registry.projects:
        st.info("暂无项目工作流配置。")
        return

    for project in usage_registry.projects:
        st.subheader(f"{project.project_name} ({project.project_id})")
        st.caption(f"状态：{project.status}")

        for workflow in project.workflows:
            st.markdown(f"**工作流：{workflow.workflow_name}** ({workflow.status})")

            for stage in workflow.stages:
                st.markdown(f"- **{stage.stage_name}** ({stage.stage_id})")
                st.markdown(f"  - Agent: `{stage.agent}` | 状态: {stage.status}")
                st.markdown(f"  - 目的: {stage.purpose}")
                if stage.capabilities:
                    caps_text = ", ".join(f"`{c}`" for c in stage.capabilities)
                    st.markdown(f"  - 能力: {caps_text}")
                else:
                    st.markdown("  - 能力: （无）")
                st.markdown("")
            st.markdown("---")


def _render_health_monitor(st, registry, runtime_summaries):
    """渲染健康监控页面。

    功能说明：
        展示每个能力的运行时健康状态，高亮需要关注和过期的能力。

    参数：
        st:                streamlit 模块
        registry:          能力注册表
        runtime_summaries: 运行时摘要字典
    """
    st.header("健康监控 Health Monitor")

    rows = []
    for cap in registry.capabilities:
        s = runtime_summaries.get(cap.capability_id)
        if s is None:
            continue
        rows.append(
            {
                "capability_id": s.capability_id,
                "runtime_health": s.runtime_health,
                "latest_status": s.latest_status,
                "latest_run_at": s.latest_run_at,
                "recent_runs": s.recent_run_count,
                "recent_failures": s.recent_failure_count,
                "consecutive_failures": s.consecutive_failures,
                "failed_queue": s.failed_queue_count,
                "needs_attention": "是" if s.needs_attention else "",
                "stale": "是" if s.stale else "",
                "latest_error": s.latest_error,
            }
        )

    if not rows:
        st.info("暂无能力健康数据。")
        return

    st.dataframe(rows, use_container_width=True, hide_index=True)

    # 高亮需要关注的
    attention = [r for r in rows if r["needs_attention"]]
    if attention:
        st.subheader("需要关注")
        for r in attention:
            color = _health_color(r["runtime_health"])
            st.markdown(
                f"<span style='color:{color}'>●</span> "
                f"**{r['capability_id']}** — {r['runtime_health']} | "
                f"连续失败 {r['consecutive_failures']} 次 | "
                f"失败队列 {r['failed_queue']} 条 | {r['latest_error']}",
                unsafe_allow_html=True,
            )


def _render_run_history(st, registry, project_root):
    """渲染运行日志页面。

    功能说明：
        选择一个能力，展示最近的运行日志记录。

    参数：
        st:           streamlit 模块
        registry:     能力注册表
        project_root: 项目根目录
    """
    st.header("运行日志 Run History")

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
                "run_id": r.get("run_id", ""),
                "command": r.get("command", ""),
                "status": r.get("status", ""),
                "started_at": r.get("started_at", ""),
                "finished_at": r.get("finished_at", ""),
                "candidate_count": r.get("candidate_count", ""),
                "saved_count": r.get("saved_count", ""),
                "failed_count": r.get("failed_count", ""),
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
    st.header("失败队列 Failed Queue")

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
                "source_id": r.get("source_id", ""),
                "source_type": r.get("source_type", ""),
                "item_key": r.get("item_key", ""),
                "error_type": r.get("error_type", ""),
                "error_message": r.get("error_message", ""),
                "retry_count": r.get("retry_count", ""),
                "created_at": r.get("created_at", ""),
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
    st.header("文档入口 Docs Hub")

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


def _render_config_check(st, registry, usage_registry, project_root):
    """渲染配置检查页面。

    功能说明：
        运行配置校验，展示错误、文档缺失、未使用能力、未知引用。

    参数：
        st:             streamlit 模块
        registry:       能力注册表
        usage_registry: 使用注册表
        project_root:   项目根目录
    """
    st.header("配置检查 Config Check")

    # 1. 校验 capability_id 唯一性和 track 引用
    st.subheader("能力注册表校验")
    errors = validate_capabilities(registry)
    if errors:
        for err in errors:
            st.error(err)
    else:
        st.success("能力注册表校验通过。")

    # 2. 文档存在性检查
    st.subheader("文档存在性检查")
    missing_docs = check_docs_exist(registry.capabilities, project_root)
    if missing_docs:
        for cap_id, docs in missing_docs.items():
            st.warning(f"{cap_id} 缺失文档: {', '.join(docs)}")
    else:
        st.success("所有文档路径都存在。")

    # 3. 未使用能力
    st.subheader("未使用能力")
    unused = find_unused_capabilities(registry.capabilities, usage_registry)
    if unused:
        for cap_id in unused:
            st.info(f"未使用: {cap_id}")
    else:
        st.success("所有能力都被使用。")

    # 4. 未知引用
    st.subheader("未知引用检查")
    unknown = find_unknown_usage_references(registry.capabilities, usage_registry)
    if unknown:
        for project_id, cap_id in unknown:
            st.error(f"项目 {project_id} 引用了未知能力: {cap_id}")
    else:
        st.success("没有未知引用。")


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
        page_title="OPC Foundation Dashboard",
        page_icon="📊",
        layout="wide",
    )

    # 注入品牌配色 CSS
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-color: {COLORS["light"]};
        }}
        h1, h2, h3 {{
            color: {COLORS["dark"]};
        }}
        .stMetric {{
            background-color: white;
            border-radius: 8px;
            padding: 12px;
            border-left: 4px solid {COLORS["orange"]};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # 侧边栏导航
    st.sidebar.title("OPC Foundation")
    st.sidebar.caption("Foundation provides infrastructure.")

    pages = [
        "总览 Dashboard",
        "能力地图 Capability Map",
        "项目工作流 Workflow Map",
        "健康监控 Health Monitor",
        "运行日志 Run History",
        "失败队列 Failed Queue",
        "文档入口 Docs Hub",
        "配置检查 Config Check",
    ]
    page = st.sidebar.radio("页面导航", pages)

    # 加载数据
    project_root = _find_project_root()
    registry, usage_registry, runtime_summaries = _load_all_data(project_root)

    # 根据选择渲染对应页面
    if page == "总览 Dashboard":
        _render_overview(st, registry, usage_registry, runtime_summaries)
    elif page == "能力地图 Capability Map":
        _render_capability_map(st, registry)
    elif page == "项目工作流 Workflow Map":
        _render_workflow_map(st, usage_registry)
    elif page == "健康监控 Health Monitor":
        _render_health_monitor(st, registry, runtime_summaries)
    elif page == "运行日志 Run History":
        _render_run_history(st, registry, project_root)
    elif page == "失败队列 Failed Queue":
        _render_failed_queue(st, registry, project_root)
    elif page == "文档入口 Docs Hub":
        _render_docs_hub(st, registry, project_root)
    elif page == "配置检查 Config Check":
        _render_config_check(st, registry, usage_registry, project_root)


if __name__ == "__main__":
    main()
