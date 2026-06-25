# OPC Foundation Control Center 使用指南

## 1. 如何启动

### 前置条件

- Python 3.11+
- Streamlit（如未安装，运行 `pip install streamlit`）

### 启动命令

```powershell
cd opc-foundation
streamlit run src/opc_foundation/dashboard/app.py
```

启动后浏览器会自动打开 `http://localhost:8501`。

如果没有 streamlit，app.py 会提示：

```text
Streamlit is required to run the dashboard. Install with: pip install streamlit
```

## 2. 如何维护 foundation_capabilities.yaml

### 文件位置

`configs/foundation_capabilities.yaml`

### 新增一个能力

1. 在 `capabilities` 列表中添加一条：

```yaml
  - capability_id: research.new_source
    name: New Source
    track: research
    category: research_source
    maturity_status: planned
    description: 新的数据源。
    input_type: new_source_url
    primary_output: data/research_archive/index/documents.latest.jsonl
    health_file: data/research_archive/index/source_health.jsonl
    run_log_file: data/research_archive/index/run_log.jsonl
    failed_queue_file: data/research_archive/index/failed_queue.jsonl
    docs:
      - docs/research_source_foundation.md
```

2. 确保 `track` 在 `tracks` 列表中存在。
3. 确保 `docs` 路径指向真实存在的文件。
4. 确保 `capability_id` 全局唯一。
5. 重启 dashboard 即可看到新能力。

### 新增一个主线

1. 在 `tracks` 列表中添加：

```yaml
  - track_id: new_track
    name: New Track Foundation
    status: planned
    description: 新的主线。
```

2. 然后在 `capabilities` 中添加属于这个 track 的能力。

## 3. 如何维护 runtime binding

### 文件位置

- 主配置：`configs/capability_runtime_bindings.yaml`（可提交）
- 本地配置：`configs/capability_runtime_bindings.local.yaml`（不提交）

### 什么是 runtime binding

runtime binding 告诉 Dashboard 每个能力应该从哪些真实运行数据文件中读取信息。

M3B-3 之前，健康数据是简化配置的；M3B-3 之后，通过 binding 机制可以从同一个 archive 的大文件中，精确筛选出属于某个能力的记录。

### 新增一个能力的 binding

```yaml
bindings:
  - capability_id: research.new_source
    archive_root: data/research_archive
    source_types:
      - new_source_type
    source_ids: []
    health_file: data/research_archive/index/source_health.jsonl
    run_log_file: data/research_archive/index/run_log.jsonl
    failed_queue_file: data/research_archive/index/failed_queue.jsonl
    report_dir: data/research_archive/reports
```

### 匹配规则

1. 先按 `source_types` 匹配（最常用）
2. 如果配置了 `source_ids`，再按 source_id 精确匹配
3. 都没配置就返回全部记录（兜底）

### 不需要绑定的能力

以下能力可以不配置 binding：
- runtime 工具类能力（被其他模块调用，没有独立运行数据）
- 规划中（planned）的能力
- 还没开始使用的能力

没有 binding 的能力显示为「未配置」，属于正常情况。

详细说明见 [Control Center 运行时数据接入说明](foundation_control_center_runtime_data.md)。

---

## 5. 如何维护 usage registry

### 文件位置

- 示例：`configs/capability_usage_registry.example.yaml`（可提交）
- 本地：`configs/capability_usage_registry.local.yaml`（不提交）

### 新增项目使用关系

```yaml
  - project_id: my_project
    project_name: 我的项目
    status: active
    workflows:
      - workflow_id: my_workflow
        workflow_name: 我的工作流
        status: active
        stages:
          - stage_id: my_stage
            stage_name: 我的阶段
            agent: My Agent
            status: active
            purpose: 做什么用
            capabilities:
              - research.rss_feed
              - document_extraction.pdf
```

### 注意事项

- `capabilities` 中的 ID 必须在 `foundation_capabilities.yaml` 中存在
- `status` 可用值：active / planned / candidate / deprecated / disabled
- local 文件不会被提交（已在 .gitignore 中）

## 6. 如何理解 maturity_status

maturity_status 表示能力的建设程度：

| 状态 | 含义 |
|---|---|
| production_trial_ready | 已完成，可试运行 |
| mvp_ready | MVP 完成，基本可用 |
| degraded | 降级（如 HKEX 因客户端渲染受限） |
| planned | 规划中，尚未实现 |
| dormant | 休眠，暂时不用 |
| disabled | 已禁用 |
| failed | 建设失败 |

## 7. 如何理解 runtime_health

runtime_health 表示能力最近的运行状态（M3B-3 之后通过 runtime binding 从真实运行数据中聚合）：

| 状态 | 含义 |
|---|---|
| not_configured | 没有配置 runtime binding（如 runtime 工具类能力） |
| unknown | 配置了 binding 但没有匹配到记录（可能还没运行过） |
| healthy | 最近一次运行健康 |
| degraded | 最近一次运行降级 |
| failed | 最近一次运行失败 |
| needs_attention | 最近多次失败，需要人工关注 |
| stale | 长时间没运行，可能已过期 |

### M3B-3 真实数据聚合

M3B-3 之后，健康状态不再是简单读取整个 health_file，而是：

1. 通过 `capability_runtime_bindings.yaml` 找到对应能力的 binding
2. 按 `source_types` / `source_ids` 从 source_health / run_log / failed_queue 中筛选匹配记录
3. 用匹配到的真实记录计算 runtime_health

这样展示的是**这个能力真实的运行状态**，而不是整个 archive 的笼统状态。

### 区分 maturity 和 runtime

- maturity_status = 建设到什么程度（静态）
- runtime_health = 最近跑得好不好（动态）

一个 production_trial_ready 的能力可能 runtime_health=failed（建设完成但最近运行失败）。

详细说明见 [Control Center 运行时数据接入说明](foundation_control_center_runtime_data.md)。

## 8. 如何排查 failed / degraded / stale

### failed

1. 打开「健康监控」页面，找到 runtime_health=failed 的能力
2. 查看 latest_error 字段
3. 打开「失败队列」页面，查看具体失败项
4. 检查对应 data 目录下的 source_health.jsonl
5. 修复问题后运行 `retry-failed` 命令

### degraded

1. 打开「健康监控」页面，找到 runtime_health=degraded 的能力
2. 检查是否有 empty_source（候选数为 0）
3. 检查是否有部分失败
4. 查看 source_health.jsonl 中的详细信息

### stale

1. 打开「健康监控」页面，找到 stale=True 的能力
2. 检查 latest_run_at 时间
3. 如果确实需要运行，执行对应模块的 run 命令
4. 如果不需要运行（如 runtime 工具类），可以忽略

### needs_attention

1. 打开「健康监控」页面，找到 needs_attention=True 的能力
2. 检查 consecutive_failures 和 recent_failure_count
3. 检查 failed_queue_count
4. 优先处理连续失败和积压较多的能力

## 9. 如何新增能力后让 dashboard 显示

1. 在 `configs/foundation_capabilities.yaml` 中添加新能力
2. 在 `configs/capability_runtime_bindings.yaml` 中添加 runtime binding（如果这个能力有真实运行数据）
3. 在 `configs/capability_runbooks.yaml` 中添加运行手册（可选但推荐）
4. 确保所有字段填写完整
5. 确保 docs 路径指向真实文件
6. 确保 track 在 tracks 列表中
7. 确保 capability_id 唯一
8. 重启 dashboard（`streamlit run src/opc_foundation/dashboard/app.py`）
9. 打开「配置检查」页面确认无错误
10. 新能力会自动出现在「能力地图」和「总览」中

## 10. 相关文档

- [Foundation Control Center](foundation_control_center.md)
- [Foundation Control Center 运行手册](foundation_control_center_runbook.md)
- [Control Center 运行时数据接入说明](foundation_control_center_runtime_data.md)
- [Foundation Capability Registry](foundation_capability_registry.md)
- [Foundation Readiness Summary](foundation_readiness_summary.md)
