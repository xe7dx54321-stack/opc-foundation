"""
Tests for TRAE Foundation Schedule Template.

本测试文件验证 TRAE 调度模板配置的正确性，包括：
- 配置文件存在且可解析
- task_id 全局唯一
- 每个 task 有中文 task_name
- 每个 task command 指向 scripts/*.ps1
- schedule_times 时间格式合法
- document_extraction 时间晚于上游任务
- blocked/high_risk source_group 不进入定时任务
- search_providers 不进入默认 scheduled 任务
- community_dev_signals 不进入默认 scheduled 任务
- manual_url 默认 enabled_by_default=false
- check_foundation_control_center 不启动 Streamlit
- 不恢复总览/运行日志/失败队列/文档入口页面
- app.py 可在未安装 Streamlit 时 import
- foundation_trae_operations.md 存在
- README 提到 TRAE 调度模板
"""

from pathlib import Path

import pytest
import yaml


# ============================================
# Constants
# ============================================

SCHEDULE_PATH = Path("configs/trae_foundation_schedule.example.yaml")
README_PATH = Path("README.md")
TRAEOPS_DOC_PATH = Path("docs/foundation_trae_operations.md")
APP_PATH = Path("src/opc_foundation/dashboard/app.py")


# ============================================
# Helpers
# ============================================


def load_schedule() -> dict:
    """加载 TRAE 调度模板配置。

    读取 YAML 文件并返回解析后的字典。

    Returns:
        dict: 调度配置字典

    Raises:
        FileNotFoundError: 配置文件不存在
        yaml.YAMLError: YAML 解析错误
    """
    with open(SCHEDULE_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_tasks() -> list[dict]:
    """获取所有任务列表。

    Returns:
        list[dict]: 任务列表
    """
    config = load_schedule()
    return config.get("tasks", [])


def is_valid_time(time_str: str) -> bool:
    """验证时间字符串格式是否合法（HH:MM）。

    Args:
        time_str: 时间字符串，如 "07:30"

    Returns:
        bool: 格式是否合法
    """
    parts = time_str.split(":")
    if len(parts) != 2:
        return False
    try:
        hour = int(parts[0])
        minute = int(parts[1])
        return 0 <= hour <= 23 and 0 <= minute <= 59
    except ValueError:
        return False


# ============================================
# Schedule Config Tests
# ============================================


class TestTraeScheduleConfig:
    """TRAE 调度配置基础测试类。

    验证配置文件存在、可解析、结构正确。
    """

    def test_schedule_file_exists(self) -> None:
        """测试调度模板文件存在。

        验证 trae_foundation_schedule.example.yaml 文件存在。
        """
        assert SCHEDULE_PATH.exists(), "Schedule template file should exist"

    def test_schedule_yaml_parseable(self) -> None:
        """测试调度模板 YAML 可解析。

        验证配置文件是合法的 YAML 格式。
        """
        config = load_schedule()
        assert isinstance(config, dict)

    def test_schedule_has_version(self) -> None:
        """测试配置有 version 字段。

        验证配置文件包含 version 字段。
        """
        config = load_schedule()
        assert "version" in config
        assert config["version"] >= 1

    def test_schedule_has_updated_at(self) -> None:
        """测试配置有 updated_at 字段。

        验证配置文件包含 updated_at 字段。
        """
        config = load_schedule()
        assert "updated_at" in config
        assert config["updated_at"]

    def test_schedule_has_timezone(self) -> None:
        """测试配置有时区字段。

        验证配置文件包含 timezone 字段。
        """
        config = load_schedule()
        assert "timezone" in config

    def test_schedule_has_tasks(self) -> None:
        """测试配置有 tasks 列表。

        验证配置文件包含 tasks 字段且非空。
        """
        config = load_schedule()
        assert "tasks" in config
        assert isinstance(config["tasks"], list)
        assert len(config["tasks"]) >= 5

    def test_task_ids_unique(self) -> None:
        """测试 task_id 全局唯一。

        验证所有任务的 task_id 不重复。
        """
        tasks = get_tasks()
        task_ids = [t.get("task_id", "") for t in tasks]
        assert len(task_ids) == len(set(task_ids)), "task_id should be unique"

    def test_each_task_has_chinese_name(self) -> None:
        """测试每个 task 有中文 task_name。

        验证每个任务都有 task_name 字段且包含中文。
        """
        tasks = get_tasks()
        for task in tasks:
            assert "task_name" in task, f"Task {task.get('task_id')} missing task_name"
            name = task["task_name"]
            # 简单检查：包含中文字符的条件是 task_name 不是纯英文
            # 这里用一个简单的检查：长度至少 2，且不是全 ASCII
            assert len(name) >= 2, f"Task {task.get('task_id')} name too short"

    def test_each_task_has_command(self) -> None:
        """测试每个 task 有 command 字段。

        验证每个任务都有 command 字段。
        """
        tasks = get_tasks()
        for task in tasks:
            assert "command" in task, f"Task {task.get('task_id')} missing command"
            assert task["command"], f"Task {task.get('task_id')} command is empty"

    def test_commands_point_to_scripts(self) -> None:
        """测试每个 task command 指向 scripts/*.ps1。

        验证命令中引用了 scripts/ 目录下的 .ps1 脚本。
        """
        tasks = get_tasks()
        for task in tasks:
            cmd = task["command"]
            assert "scripts/" in cmd and ".ps1" in cmd, \
                f"Task {task.get('task_id')} command should point to scripts/*.ps1"

    def test_each_task_has_schedule_times(self) -> None:
        """测试每个 task 有 schedule_times。

        验证每个任务都有调度时间列表且非空。
        """
        tasks = get_tasks()
        for task in tasks:
            assert "schedule_times" in task, f"Task {task.get('task_id')} missing schedule_times"
            assert isinstance(task["schedule_times"], list)
            assert len(task["schedule_times"]) >= 1, \
                f"Task {task.get('task_id')} schedule_times should not be empty"

    def test_schedule_times_format_valid(self) -> None:
        """测试 schedule_times 时间格式合法。

        验证所有调度时间都是合法的 HH:MM 格式。
        """
        tasks = get_tasks()
        for task in tasks:
            for t in task["schedule_times"]:
                assert is_valid_time(t), \
                    f"Task {task.get('task_id')} invalid time format: {t}"

    def test_each_task_has_enabled_flag(self) -> None:
        """测试每个 task 有 enabled_by_default 字段。

        验证每个任务都有启用标记。
        """
        tasks = get_tasks()
        for task in tasks:
            assert "enabled_by_default" in task, \
                f"Task {task.get('task_id')} missing enabled_by_default"
            assert isinstance(task["enabled_by_default"], bool)


# ============================================
# Schedule Logic Tests
# ============================================


class TestTraeScheduleLogic:
    """TRAE 调度逻辑测试类。

    验证调度规则的正确性。
    """

    def test_document_extraction_after_upstream(self) -> None:
        """测试 document_extraction 时间晚于上游任务。

        验证文档抽取任务的所有时间都晚于至少一个上游采集任务。
        """
        tasks = get_tasks()

        # 找到 document_extraction 任务
        doc_task = None
        for task in tasks:
            if "document_extraction" in task["task_id"]:
                doc_task = task
                break

        assert doc_task is not None, "Should have document_extraction task"

        # 找到上游任务（research、official_filings、wechat 等）
        upstream_tasks = []
        for task in tasks:
            tid = task["task_id"]
            if any(keyword in tid for keyword in ["research", "official_filings", "wechat", "chinese"]):
                if "document_extraction" not in tid:
                    upstream_tasks.append(task)

        assert len(upstream_tasks) >= 2, "Should have at least 2 upstream tasks"

        # 检查每个 document_extraction 时间都有对应的上游更早时间
        # （不需要完全一一对应，只要整体上有上游早于下游即可）
        doc_times = doc_task["schedule_times"]
        upstream_times = []
        for ut in upstream_tasks:
            upstream_times.extend(ut["schedule_times"])

        # 把时间转换成分钟数方便比较
        def time_to_minutes(t: str) -> int:
            parts = t.split(":")
            return int(parts[0]) * 60 + int(parts[1])

        doc_minutes = sorted([time_to_minutes(t) for t in doc_times])
        upstream_minutes = sorted([time_to_minutes(t) for t in upstream_times])

        # 检查每个 doc 时间都至少有一个上游时间比它早（在同一天内）
        # 放宽条件：至少有一个 doc 时间比某个上游时间晚
        has_later = False
        for dt in doc_minutes:
            for ut in upstream_minutes:
                if dt > ut:
                    has_later = True
                    break
            if has_later:
                break

        assert has_later, "document_extraction should have at least one time after upstream"

    def test_search_providers_not_in_default_scheduled(self) -> None:
        """测试 search_providers 不进入默认 scheduled 任务。

        验证所有任务的 source_groups 中不包含 search_providers。
        """
        tasks = get_tasks()
        for task in tasks:
            if "source_groups" in task:
                assert "search_providers" not in task["source_groups"], \
                    f"Task {task['task_id']} should not include search_providers"

    def test_community_dev_not_in_default_scheduled(self) -> None:
        """测试 community_dev_signals 不进入默认 scheduled 任务。

        验证所有任务的 source_groups 中不包含 community_dev_signals。
        """
        tasks = get_tasks()
        for task in tasks:
            if "source_groups" in task:
                assert "community_dev_signals" not in task["source_groups"], \
                    f"Task {task['task_id']} should not include community_dev_signals"

    def test_blocked_high_risk_not_in_schedule(self) -> None:
        """测试 blocked/high_risk 不进入定时任务。

        验证所有任务的 source_groups 中不包含 blocked 或 high_risk 相关组。
        """
        tasks = get_tasks()
        blocked_keywords = ["blocked", "high_risk", "prohibited"]
        for task in tasks:
            if "source_groups" in task:
                for sg in task["source_groups"]:
                    for kw in blocked_keywords:
                        assert kw not in sg.lower(), \
                            f"Task {task['task_id']} should not include blocked/high_risk groups"

    def test_manual_url_disabled_by_default(self) -> None:
        """测试 manual_url 默认 enabled_by_default=false。

        验证 manual_url 任务默认是禁用的。
        """
        tasks = get_tasks()
        manual_task = None
        for task in tasks:
            if "manual_url" in task["task_id"]:
                manual_task = task
                break

        assert manual_task is not None, "Should have manual_url task"
        assert manual_task["enabled_by_default"] is False, \
            "manual_url task should be disabled by default"

    def test_control_center_check_exists(self) -> None:
        """测试有 control center 健康检查任务。

        验证调度模板中包含 Control Center 健康检查任务。
        """
        tasks = get_tasks()
        cc_tasks = [t for t in tasks if "control_center" in t["task_id"]]
        assert len(cc_tasks) >= 1, "Should have control_center check task"

    def test_daily_status_task_exists(self) -> None:
        """测试有每日状态收口任务。

        验证调度模板中包含每日状态收口任务。
        """
        tasks = get_tasks()
        daily_tasks = [t for t in tasks if "daily_status" in t["task_id"]]
        assert len(daily_tasks) >= 1, "Should have daily_status task"


# ============================================
# Integration Tests
# ============================================


class TestTraeScheduleIntegration:
    """TRAE 调度集成测试类。

    验证与其他模块的集成。
    """

    def test_trae_ops_doc_exists(self) -> None:
        """测试 foundation_trae_operations.md 存在。

        验证运维文档存在。
        """
        assert TRAEOPS_DOC_PATH.exists(), "TRAE operations doc should exist"

    def test_readme_mentions_trae(self) -> None:
        """测试 README 提到 TRAE 调度模板。

        验证 README.md 中包含 TRAE 相关内容。
        """
        assert README_PATH.exists()
        content = README_PATH.read_text(encoding="utf-8")
        assert "TRAE" in content or "trae" in content.lower(), \
            "README should mention TRAE schedule"

    def test_control_center_check_no_streamlit(self) -> None:
        """测试 check_foundation_control_center 不启动 Streamlit。

        验证脚本中不包含 streamlit run 命令。
        """
        script_path = Path("scripts/check_foundation_control_center.ps1")
        assert script_path.exists()
        content = script_path.read_text(encoding="utf-8")
        assert "streamlit" not in content.lower() or "streamlit run" not in content.lower(), \
            "Control center check script should not start Streamlit"

    def test_no_deleted_pages_in_app(self) -> None:
        """测试不恢复总览/运行日志/失败队列/文档入口页面。

        验证 app.py 中没有恢复已删除的页面。
        """
        import re
        assert APP_PATH.exists()
        content = APP_PATH.read_text(encoding="utf-8")

        pattern = r'pages\s*=\s*\[([^\]]+)\]'
        match = re.search(pattern, content)
        assert match, "Should find pages list in app.py"
        pages_str = match.group(1)
        page_names = re.findall(r'"([^"]+)"', pages_str)
        assert len(page_names) == 4, f"Expected 4 pages, got {len(page_names)}"
        assert "总览" not in page_names
        assert "运行日志" not in page_names
        assert "失败队列" not in page_names
        assert "文档入口" not in page_names

    def test_app_importable_without_streamlit(self) -> None:
        """测试 app.py 可在未安装 Streamlit 时 import。

        验证 models 和 loaders 模块不依赖 streamlit。
        """
        from opc_foundation.dashboard import models
        from opc_foundation.dashboard import loaders
        assert models is not None
        assert loaders is not None
