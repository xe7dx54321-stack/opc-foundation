# OPC Foundation Control Center

更新时间：2026-06-25
状态：M3B-3b Ready（健康状态校准完成）

## 1. 目标

Foundation Control Center 是 `opc-foundation` 的本地可视化中控台。

核心价值：

```text
看清楚 foundation 有哪些能力
每个能力属于哪个模块
每个能力当前状态如何
每个能力输入/输出/文档入口是什么
每个能力最近运行是否健康
哪些能力 degraded / failed / stale / needs_attention
哪些能力被哪些项目、工作流、Agent 使用
后续新增能力后，可以通过配置文件自动呈现在界面中
```

核心原则：

```text
Foundation provides infrastructure.
Business systems keep judgment.
Control Center provides visibility.
```

Control Center 是可视化管理界面，不是新的数据源主线。

## 2. 页面结构

Control Center 包含 8 个页面：

| 页面 | 功能 |
|---|---|
| 总览 Dashboard | 能力总数、各状态数量、使用情况汇总 |
| 能力地图 Capability Map | 所有能力的详细信息，支持筛选 |
| 项目工作流 Workflow Map | 项目→工作流→阶段→Agent→能力映射 |
| 健康监控 Health Monitor | 每个能力的运行健康状态 |
| 运行日志 Run History | 最近运行记录 |
| 失败队列 Failed Queue | 失败项列表 |
| 文档入口 Docs Hub | 核心文档和能力文档入口 |
| 配置检查 Config Check | 配置文件完整性检查 |

## 3. 数据来源

| 数据 | 来源 |
|---|---|
| 能力台账 | `configs/foundation_capabilities.yaml` |
| 使用关系 | `configs/capability_usage_registry.example.yaml`（或 local 版本） |
| 运行时绑定 | `configs/capability_runtime_bindings.yaml`（或 local 版本） |
| 健康状态 | `data/*/index/source_health.jsonl`（通过 runtime binding 匹配） |
| 运行日志 | `data/*/index/run_log.jsonl`（通过 runtime binding 匹配） |
| 失败队列 | `data/*/index/failed_queue.jsonl`（通过 runtime binding 匹配） |
| 文档入口 | `docs/` 目录 |

Control Center 只读取数据，不写回 data 文件。

### M3B-3 真实运行数据接入

M3B-3 引入了 **runtime binding** 机制，实现了从真实运行数据中精确匹配每个能力的健康状态。

核心变化：
- 不再是简单的「一个能力对应一个 health_file」
- 而是通过 `capability_runtime_bindings.yaml` 配置能力与 source_type/source_id 的映射关系
- Dashboard 从同一个 archive 的数据文件中，按 binding 规则筛选出属于该能力的记录
- 健康监控页展示真实运行状态，能力详情弹窗展示真实运行摘要

详细说明见 [Control Center 运行时数据接入说明](foundation_control_center_runtime_data.md)。

## 4. 能力台账

能力台账文件：`configs/foundation_capabilities.yaml`

结构：

```yaml
version: 1
updated_at: "2026-06-24"

tracks:
  - track_id: research
    name: Research Source Foundation
    status: production_trial_ready
    ...

capabilities:
  - capability_id: research.rss_feed
    name: RSS Feed Archive
    track: research
    category: research_source
    maturity_status: production_trial_ready
    description: Archive public RSS/Atom feeds.
    input_type: RSS/Atom feed URL
    primary_output: data/research_archive/index/documents.latest.jsonl
    health_file: data/research_archive/index/source_health.jsonl
    run_log_file: data/research_archive/index/run_log.jsonl
    failed_queue_file: data/research_archive/index/failed_queue.jsonl
    docs:
      - docs/research_source_foundation.md
  ...
```

当前共 4 个 track、20 个 capability。

## 5. 使用关系 Registry

使用关系文件：`configs/capability_usage_registry.example.yaml`

结构：

```yaml
version: 1
updated_at: "2026-06-24"

projects:
  - project_id: th_capital_stock
    project_name: 二级市场投研 Agent
    status: planned
    workflows:
      - workflow_id: disclosure_monitoring
        workflow_name: 官方披露监控
        status: planned
        stages:
          - stage_id: collect_filings
            stage_name: 采集官方公告
            agent: Filing Collector Agent
            status: planned
            purpose: 获取 SEC / CNINFO / HKEX 官方披露原始材料
            capabilities:
              - official_filing.sec_edgar
              - official_filing.cninfo_announcement
              - official_filing.hkex_announcement
```

local 版本不提交：`configs/capability_usage_registry.local.yaml`

## 6. 健康聚合规则

能力成熟度状态（maturity_status）：

```text
production_trial_ready  # 已可试运行
mvp_ready               # MVP 完成
degraded                # 降级（如 HKEX）
planned                 # 规划中
dormant                 # 休眠
disabled                # 禁用
failed                  # 失败
```

运行健康状态（runtime_health）：

```text
not_configured   # 没有配置 runtime binding
unknown          # 有 binding 但没有匹配记录
healthy          # 最近一次为 healthy/success
degraded         # 最近一次为 degraded
failed           # 最近一次为 failed
needs_attention  # 最近 N 次中 failed/degraded >= 2
stale            # 最近运行时间超过 stale_days 天
```

二者必须分开：
- 能力成熟度 = 这个能力建设到什么程度
- 运行健康 = 这个能力最近跑得好不好

### M3B-3 健康聚合方式

M3B-3 之后，健康状态通过 **runtime binding** 从真实运行数据中聚合：

1. Dashboard 读取 `capability_runtime_bindings.yaml` 中的绑定配置
2. 根据 `source_types` / `source_ids` 从 source_health / run_log / failed_queue 中筛选匹配记录
3. 用匹配到的记录计算 runtime_health
4. 没有 binding 的能力显示为 `not_configured`
5. 有 binding 但没匹配到记录显示为 `unknown`（fail-soft）

详细聚合规则见 [Control Center 运行时数据接入说明](foundation_control_center_runtime_data.md) 第 4 节。

## 7. 不做什么

Control Center 不做：

```text
云端部署
登录权限
数据库
真实调度
告警推送
复杂图谱
跨仓库自动扫描
自动识别 Agent 调用关系
投资判断
ticker mapping
watchlist scoring
trade signal
```

## 8. 启动方式

```powershell
# 如果没有 streamlit，先安装
pip install streamlit

# 启动 dashboard
streamlit run src/opc_foundation/dashboard/app.py
```

如果本地没有 Streamlit，app.py 会提示安装命令，不会崩溃。

## 9. 后续路线

```text
✅ M3B-1: Control Center MVP（能力地图、健康监控、配置检查）
✅ M3B-2: Control Center 增强（运行手册、能力详情、文档入口）
✅ M3B-3b: 健康状态校准（runtime_mode / document_extraction 文件类型归因）
✅ M3B-3: Control Center 真实运行数据接入（runtime binding、健康聚合）
M3C: Runtime 层接入已有主线
M4: Research/News Source Harmonization
M5: Partial Candidates
M6: th_capital_stock Consumption Bridge
```

## 10. 相关文档

- [Control Center 使用指南](foundation_control_center_usage.md)
- [Control Center 运行手册](foundation_control_center_runbook.md)
- [Control Center 运行时数据接入说明](foundation_control_center_runtime_data.md)
- [Foundation Capability Registry](foundation_capability_registry.md)
- [Foundation Readiness Summary](foundation_readiness_summary.md)
- [Runtime Foundation](runtime_foundation.md)
