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

## 3. 如何维护 usage registry

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

## 4. 如何理解 maturity_status

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

## 5. 如何理解 runtime_health

runtime_health 表示能力最近的运行状态：

| 状态 | 含义 |
|---|---|
| not_configured | 没有配置 health_file（如 runtime 工具类能力） |
| unknown | 配置了但文件不存在或无记录（可能还没运行过） |
| healthy | 最近一次运行健康 |
| degraded | 最近一次运行降级 |
| failed | 最近一次运行失败 |
| needs_attention | 最近多次失败，需要人工关注 |
| stale | 长时间没运行，可能已过期 |

### 区分 maturity 和 runtime

- maturity_status = 建设到什么程度（静态）
- runtime_health = 最近跑得好不好（动态）

一个 production_trial_ready 的能力可能 runtime_health=failed（建设完成但最近运行失败）。

## 6. 如何排查 failed / degraded / stale

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

## 7. 如何新增能力后让 dashboard 显示

1. 在 `configs/foundation_capabilities.yaml` 中添加新能力
2. 确保所有字段填写完整
3. 确保 docs 路径指向真实文件
4. 确保 track 在 tracks 列表中
5. 确保 capability_id 唯一
6. 重启 dashboard（`streamlit run src/opc_foundation/dashboard/app.py`）
7. 打开「配置检查」页面确认无错误
8. 新能力会自动出现在「能力地图」和「总览」中

## 8. 相关文档

- [Foundation Control Center](foundation_control_center.md)
- [Foundation Capability Registry](foundation_capability_registry.md)
- [Foundation Readiness Summary](foundation_readiness_summary.md)
