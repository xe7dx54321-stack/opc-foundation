# OPC Foundation M3C-5A7.1-clean 工作区清理报告

> 执行时间：2026-07-02
> 阶段：M3C-5A7.1-clean
> 目标：清理早期遗留修改，防止污染下一阶段 M3C-5A8

---

## 1. 初始 git status

```text
 M pyproject.toml
 M tests/source_inventory/test_trial_sources.py
 M tests/test_cli_provider_search.py
 M tests/test_skill_cli.py
 M tests/test_version.py
?? start_dashboard.sh
```

---

## 2. 遗留文件清单

| file | status | diff_summary | decision | reason |
|---|---|---|---|---|
| `pyproject.toml` | M | `requires-python >=3.11` → `>=3.10` | **commit** | 本地环境只有 Python 3.10，不改无法安装依赖和运行测试，属于必要兼容性修改 |
| `tests/test_skill_cli.py` | M | Windows 硬编码路径 `D:\李少博的文件\...` → 动态 `Path(__file__)` | **commit** | 跨平台兼容修复，属于必要测试修复 |
| `tests/test_version.py` | M | subprocess 缺少 PYTHONPATH 环境变量 | **commit** | 否则 `test_version_cli` 在 venv 中失败，属于必要测试修复 |
| `tests/test_cli_provider_search.py` | M | `extra_env.update(env)` 覆盖 PYTHONPATH → 改为先 merge 再设 PYTHONPATH | **commit** | 否则 PYTHONPATH 被覆盖导致 CLI 找不到模块，属于必要测试修复 |
| `tests/source_inventory/test_trial_sources.py` | M | subprocess 缺少 PYTHONPATH + `cwd="src/.."` 不可靠 → 动态计算 | **commit** | 否则 trial CLI 测试在 venv 中失败，属于必要测试修复 |
| `start_dashboard.sh` | ?? | 一键启动 Streamlit dashboard 脚本 | **commit** | Task 1 创建但漏提交，属于实用工具脚本 |

---

## 3. pyproject.toml 处理结果

- **是否有修改**：是
- **修改内容归因**：Task 1（环境搭建阶段）为兼容本地 Python 3.10 环境所做
- **最终处理**：commit
- **是否引入新依赖**：否，仅修改 `requires-python` 约束
- **是否引入 Playwright/Selenium**：否

---

## 4. data/local/secrets 检查

- **data 是否提交**：否，已在 `.gitignore` 中覆盖
- **local config 是否提交**：否
- **secrets 是否提交**：否
- **.env 是否提交**：否

---

## 5. 清理后 git status

```text
clean
```

---

## 6. 处理说明

本次清理确认所有遗留修改均为早期阶段（Task 1 ~ M3C-5A5 之前）漏提交的必要兼容性修复：

1. **pyproject.toml**：Python 版本约束降级，确保在 Python 3.10 环境下可安装
2. **测试修复（4 个文件）**：解决 subprocess 调用中 PYTHONPATH、cwd、跨平台路径等兼容性问题，是 full pytest 通过的前提
3. **start_dashboard.sh**：实用启动脚本，不属于实验性文件

以上修改统一提交为一个 commit，不单独拆分，因为都属于同一类"早期漏提交的必要兼容性修复"。
