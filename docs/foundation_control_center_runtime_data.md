# Control Center 运行时数据接入说明

更新时间：2026-06-25
状态：M3B-3b Ready（健康状态校准完成）
版本：1.1

## 1. 为什么需要 runtime binding

### 背景

在 M3B-3 之前，Control Center 的健康数据是简化配置的：每个能力直接配置一个 `health_file` 路径，Dashboard 读取整个文件来判断健康状态。

但实际运行中，同一个 archive 目录下可能有多种不同类型的数据源。比如 `data/research_archive/index/source_health.jsonl` 里同时包含了 RSS、微信公众号、手动 URL 等多种 source_type 的记录。如果直接读整个文件，就无法区分每条记录属于哪个能力。

### 解决方案

M3B-3 引入了 **runtime binding** 机制：

```text
capability_id ←→ source_type / source_id ←→ 真实运行数据文件
```

通过 `capability_runtime_bindings.yaml` 配置文件，告诉 Dashboard：

- 某个 capability_id 对应哪些 source_type
- 健康数据、运行日志、失败队列分别在哪个文件
- 报告目录在哪里

这样 Dashboard 就能从同一个大文件中，精确筛选出属于某个能力的记录，展示真实的运行状态。

### 核心原则

```text
配置文件声明绑定关系
Dashboard 只读不写
匹配不到时 fail-soft，不崩溃
```

---

## 2. capability_runtime_bindings.yaml 怎么维护

### 文件位置

- 主配置：`configs/capability_runtime_bindings.yaml`（可提交）
- 本地配置：`configs/capability_runtime_bindings.local.yaml`（不提交，已加入 .gitignore）

### 配置结构

```yaml
version: "1.0"
updated_at: "2026-06-25"

bindings:
  - capability_id: research.rss_feed
    archive_root: data/research_archive
    source_types:
      - rss_feed
    source_ids: []
    health_file: data/research_archive/index/source_health.jsonl
    run_log_file: data/research_archive/index/run_log.jsonl
    failed_queue_file: data/research_archive/index/failed_queue.jsonl
    report_dir: data/research_archive/reports
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `capability_id` | string | ✅ | 能力 ID，必须存在于 foundation_capabilities.yaml |
| `archive_root` | string | ⚪ | 归档根目录，目前主要用于标识，可选 |
| `source_types` | list[string] | ⚪ | 匹配的 source_type 列表，为空表示不限制 |
| `source_ids` | list[string] | ⚪ | 精确匹配的 source_id 列表，为空表示不限制 |
| `file_extensions` | list[string] | ⚪ | 文件扩展名列表，文档抽取类能力使用 |
| `health_file` | string | ⚪ | 健康状态文件路径（source_health.jsonl） |
| `run_log_file` | string | ⚪ | 运行日志文件路径（run_log.jsonl） |
| `failed_queue_file` | string | ⚪ | 失败队列文件路径（failed_queue.jsonl） |
| `report_dir` | string | ⚪ | 报告目录路径 |

### 维护步骤

#### 新增一个能力的绑定

1. 打开 `configs/capability_runtime_bindings.yaml`
2. 在 `bindings` 列表末尾添加一条：

```yaml
  - capability_id: your.new_capability
    archive_root: data/your_archive
    source_types:
      - your_source_type
    source_ids: []
    health_file: data/your_archive/index/source_health.jsonl
    run_log_file: data/your_archive/index/run_log.jsonl
    failed_queue_file: data/your_archive/index/failed_queue.jsonl
    report_dir: data/your_archive/reports
```

3. 确保 `capability_id` 在 `foundation_capabilities.yaml` 中存在
4. 保存文件，刷新 Dashboard 页面即可生效

#### 不需要绑定的情况

以下能力可以不配置 binding：

- runtime 工具类能力（被其他模块调用，没有独立的运行数据）
- 还没开始使用的能力
- 规划中（planned）的能力

没有 binding 的能力在 Dashboard 中显示为「未配置」状态，属于正常情况。

---

## 3. capability_id 和 source_id/source_type 的关系

### 匹配逻辑

Dashboard 从真实数据文件中筛选记录时，按以下优先级匹配：

```text
优先级 1：source_types 匹配（最常用）
  ↓
优先级 2：source_ids 精确匹配（可选）
  ↓
优先级 3：file_extensions 辅助匹配（文档抽取类）
```

#### 详细规则

1. **先按 source_types 过滤**
   - 如果配置了 `source_types`，只保留 `source_type` 在列表中的记录
   - 如果过滤后一条都没有，退回全部记录（兜底，避免完全没数据）

2. **再按 source_ids 过滤（如果配置了的话）**
   - 如果配置了 `source_ids`（非空列表），在第一步结果中再按 `source_id` 精确匹配
   - 匹配到就用匹配结果，匹配不到就用第一步的结果

3. **file_extensions 辅助匹配**
   - 主要用于 document_extraction 类能力
   - 比如 PDF 抽取能力只关心 `.pdf` 后缀的文件

### 举例说明

#### 例 1：research.rss_feed

```yaml
capability_id: research.rss_feed
source_types:
  - rss_feed
source_ids: []
```

匹配逻辑：
- 从 source_health.jsonl 中筛选所有 `source_type = "rss_feed"` 的记录
- 因为 source_ids 为空，不再按 source_id 过滤
- 这些记录就是 research.rss_feed 能力的健康数据

#### 例 2：document_extraction.pdf

```yaml
capability_id: document_extraction.pdf
source_types:
  - local_document
  - official_filing_pdf
  - public_report
file_extensions:
  - .pdf
```

匹配逻辑：
- 先筛选 source_type 为 `local_document` / `official_filing_pdf` / `public_report` 的记录
- 再结合文件扩展名判断（具体实现中会检查文件路径）

#### 例 3：某个特定源

```yaml
capability_id: research.specific_source
source_types:
  - rss_feed
source_ids:
  - hacker_news
  - techcrunch
```

匹配逻辑：
- 先筛选 source_type = "rss_feed" 的记录
- 再在这些记录中筛选 source_id 为 "hacker_news" 或 "techcrunch" 的

---

## 4. Dashboard 如何聚合运行数据

### 三类数据来源

| 数据类型 | 文件 | 作用 |
|---|---|---|
| source_health | `source_health.jsonl` | 每个源的健康状态快照 |
| run_log | `run_log.jsonl` | 每次运行的完整记录 |
| failed_queue | `failed_queue.jsonl` | 失败任务队列 |

### 健康判断规则

Dashboard 按以下规则判断每个能力的运行健康状态：

#### 状态流转

```text
not_configured → unknown → healthy / degraded / failed / needs_attention / stale
```

#### 各状态含义

| 状态 | 触发条件 |
|---|---|
| **not_configured** | 没有配置 runtime binding |
| **unknown** | 有 binding，但 source_health 和 run_log 都没有匹配记录 |
| **healthy** | 最近一次 source_health 为 healthy，或最近一次 run_log 为 success |
| **degraded** | 最近一次 source_health 为 degraded，或有部分失败 |
| **failed** | 最近一次 source_health 为 failed，或最近一次 run_log 为 failed |
| **needs_attention** | 最近 3 次中失败/降级 ≥ 2，或连续失败 ≥ 2，或失败队列有积压且最近非健康 |
| **stale** | 最近运行时间超过 7 天（可配置 stale_days） |

#### 判断优先级

1. 先看有没有 binding → 没有就是 `not_configured`
2. 再看有没有匹配记录 → 没有就是 `unknown`
3. 有记录就用最新的判断：
   - 优先用 source_health 的 status 字段
   - 如果没有 source_health，用 run_log 的 status 字段
4. 再检查 needs_attention 和 stale

### 聚合过程

以 research.rss_feed 为例：

```text
1. 读取 data/research_archive/index/source_health.jsonl
2. 按 source_type = "rss_feed" 过滤
3. 按 checked_at 排序，取最新的一条
4. 读取 data/research_archive/index/run_log.jsonl
5. 按 source_type = "rss_feed" 过滤
6. 按 started_at 排序，取最近 3 条
7. 读取 data/research_archive/index/failed_queue.jsonl
8. 按 source_type = "rss_feed" 过滤，统计数量
9. 根据以上数据计算 runtime_health
10. 生成 CapabilityRuntimeSummary
```

---

## 5. 为什么没有 data 时会显示「未知」

### fail-soft 设计

Control Center 采用 **fail-soft（软失败）** 设计：

> 数据不存在或格式错误时，展示「未知」或「未配置」，而不是崩溃报错。

### 设计原因

1. **data 目录不提交**：仓库里没有 `data/` 目录，刚 clone 下来的项目肯定没有运行数据
2. **能力逐步接入**：不是所有能力同时上线，有些能力可能还没开始运行
3. **本地环境差异**：每个人本地跑的能力不一样，有的跑了有的没跑
4. **Dashboard 是只读的**：它只负责展示，不负责生成数据，数据缺失不是它的问题

### 各层级的 fail-soft

| 层级 | 失败情况 | 处理方式 |
|---|---|---|
| 配置文件 | YAML 文件不存在 | 返回空 registry，不崩溃 |
| 配置文件 | YAML 格式错误 | 返回空 registry，记录 load_error |
| 数据文件 | JSONL 文件不存在 | 返回空列表 |
| 数据文件 | JSONL 某行格式错误 | 跳过坏行，继续读好的 |
| 时间解析 | 时间字符串格式不对 | 返回 None，按未知处理 |
| 匹配过滤 | 没有匹配的记录 | 退回全部记录（兜底） |
| 报告目录 | 目录不存在 | 返回空字符串 |

### 「未知」不等于「失败」

重要区别：

| 状态 | 含义 | 该做什么 |
|---|---|---|
| unknown（未知） | 还没运行过，或没找到数据 | 运行一次这个能力 |
| failed（失败） | 运行过，但失败了 | 排查失败原因 |

---

## 6. 如何让一个能力从「未知」变成真实健康状态

### 操作步骤

以 `research.rss_feed` 为例：

#### 第一步：确认 runtime binding 配置正确

1. 打开 `configs/capability_runtime_bindings.yaml`
2. 找到 `research.rss_feed` 对应的 binding
3. 确认 `health_file` / `run_log_file` / `failed_queue_file` 路径正确
4. 确认 `source_types` 配置正确（应该是 `["rss_feed"]`）

#### 第二步：确认能力配置完整

1. 打开 `configs/foundation_capabilities.yaml`
2. 确认 `research.rss_feed` 能力存在
3. 确认 `maturity_status` 不是 `planned` 或 `disabled`

#### 第三步：运行一次这个能力

按照能力详情页的命令，运行一次：

```powershell
# 示例：运行 research RSS 采集
python -m opc_foundation.research.cli archive --config configs/research_sources.local.yaml
```

具体命令请参考对应能力的运行手册。

#### 第四步：检查 data 目录

运行完成后，检查以下文件是否生成：

```text
data/research_archive/index/source_health.jsonl
data/research_archive/index/run_log.jsonl
data/research_archive/index/failed_queue.jsonl  # 可能没有，没失败就不生成
```

#### 第五步：刷新 Dashboard

刷新浏览器页面，或者按 `R` 键重新运行 Streamlit。

现在应该能看到：
- 健康监控页：这个能力的状态变成 `healthy` 或 `degraded` 或 `failed`
- 能力详情弹窗：展示真实的运行摘要数据
- 运行日志页：能看到刚才的运行记录
- 失败队列页：如果有失败，能看到失败项

#### 第六步：如果还是「未知」

按以下顺序排查：

1. **binding 配置对不对？**
   - 检查 `capability_id` 拼写
   - 检查 `source_types` 和实际数据中的 `source_type` 是否一致
   - 检查文件路径是否正确（相对项目根目录）

2. **数据文件里有没有记录？**
   - 打开 JSONL 文件，看看是不是空的
   - 看看记录里的 `source_type` 是什么

3. **运行的命令对不对？**
   - 确认运行的是对应能力的命令
   - 确认运行成功了，不是报错退出

4. **路径是不是相对项目根目录？**
   - Dashboard 是从项目根目录启动的，所有路径都是相对根目录的
   - 如果你从子目录启动 streamlit，路径会不对

---

## 7. 常见问题 FAQ

### Q1：为什么有的能力显示「未配置」？

**A：** 这些能力没有配置 runtime binding。通常是工具类能力（如 LLM 缓存、ArtifactManifest 等），它们被其他模块调用，没有独立的运行数据文件，所以不需要绑定。显示「未配置」是正常的。

### Q2：配置了 binding 为什么还是「未知」？

**A：** 有 binding 但没有匹配到记录，可能的原因：
- 还没运行过这个能力，data 文件还没生成
- source_types 配置不对，匹配不到记录
- 文件路径配置错了，找不到文件

可以按第 6 节的步骤排查。

### Q3：可以手动修改 source_health.jsonl 吗？

**A：** 不建议。Dashboard 是只读的，它只读取不写入。source_health.jsonl 应该由对应的运行命令自动生成和维护。手动修改可能导致数据不一致。

### Q4：一个能力可以绑定多个 source_type 吗？

**A：** 可以。比如 `document_extraction.pdf` 就绑定了 `local_document`、`official_filing_pdf`、`public_report` 三种 source_type。只要在 `source_types` 列表里都列出来就行。

### Q5：local 版本的 binding 怎么用？

**A：** 如果你有本地特有的绑定配置（比如测试用的数据源），可以创建 `configs/capability_runtime_bindings.local.yaml`，格式和主配置一样。这个文件已经在 `.gitignore` 里，不会被提交。

Dashboard 会优先加载 local 版本，如果没有再加载主配置。

### Q6：健康状态多久刷新一次？

**A：** Dashboard 是 Streamlit 应用，每次页面刷新（或按 R 键）都会重新读取所有数据文件。所以数据是实时的，你运行完一个能力后刷新页面就能看到最新状态。

### Q7：为什么 needs_attention 是 true 但 runtime_health 是 healthy？

**A：** 这两个是独立的判断维度：
- `runtime_health` 看的是最近一次的状态
- `needs_attention` 看的是趋势（最近多次失败、连续失败、失败队列积压）

可能出现「最近一次成功了，但之前连续失败好几次，失败队列还有积压」的情况，这时候 needs_attention 还是 true，提醒你继续关注。

### Q8：stale 的阈值是多少天？

**A：** 默认 7 天。可以在代码中通过 `stale_days` 参数调整。如果一个能力超过 7 天没运行，就会标记为 stale，提醒你是不是该跑一下了。

### Q9：运行数据文件很大，会不会很慢？

**A：** Dashboard 只读取 JSONL 文件，不做复杂计算。一般来说几千条记录都是秒级加载。如果文件特别大，可能会慢一点，但通常不是问题。

### Q10：怎么确认 binding 配置对不对？

**A：** 打开 Dashboard 的「配置检查」页面，里面有「Runtime Binding 检查」一项，会告诉你：
- 有没有引用不存在的 capability_id
- 有没有重复的 capability_id
- 哪些 binding 指向的文件不存在（这个是 warning，不是错误）

---

## 8. M3B-3b 健康状态校准

### 8.1 校准目标

M3B-3 接入真实数据后，发现 Dashboard 有以下误报问题：

- 工具能力（runtime.*）被显示为「未配置」
- HKEX 等已知限制被显示为「需关注」
- research / SEC / CNINFO 还未运行被显示为「未知」（容易被误解为故障）
- document_extraction 全员降级（一个 PDF 失败扩散到全部文档类型）

M3B-3b 引入 **runtime_mode（运行模式）** 概念，校准 Dashboard 显示。

### 8.2 运行模式

在 `foundation_capabilities.yaml` 中为每个能力配置 `runtime_mode` 字段：

```yaml
- capability_id: runtime.jsonl
  runtime_mode: utility  # 工具能力
  ...

- capability_id: official_filing.hkex_announcement
  runtime_mode: known_limited  # 已知限制
  ...
```

四种模式：

| 模式 | 中文 | 适用场景 | 异常计入 |
|---|---|---|---|
| `data_source` | 数据能力 | research / official_filing / document_extraction | 是 |
| `utility` | 工具能力 | runtime.* 工具函数 | ❌ 否 |
| `known_limited` | 已知限制 | HKEX 等外部限制 | 降级不算 |
| `manual_only` | 人工触发 | manual_url | 无记录不视为故障 |

### 8.3 document_extraction 按文件类型精准归因

M3B-3b 重构了匹配逻辑，document_extraction 类能力严格按文件扩展名匹配：

```yaml
- capability_id: document_extraction.pdf
  file_extensions:
    - .pdf  # 只匹配 .pdf 失败
  ...

- capability_id: document_extraction.html
  file_extensions:
    - .html
    - .htm  # 匹配 .html 和 .htm
  ...
```

匹配优先级：
1. `file_extension` 字段
2. `original_path` / `document_path` / `file_path` / `path` 后缀
3. `raw_entry.path` / `raw_entry.file_path` 后缀
4. `metadata.file_extension`
5. `mime_type` 推断
6. 都不行则不匹配（不扩散到其他能力）

**关键校准**：匹配到 0 条就返回 0 条，**不 fallback**。这避免了一个 PDF 失败扩散到全部文档类型。

### 8.4 HKEX 已知限制

`official_filing.hkex_announcement` 的 `runtime_mode` 设为 `known_limited`：

- 降级（degraded）**不**触发 needs_attention
- failed_queue 积压可以展示，但标注为已知限制
- 配置检查中不显示为 error
- 健康监控中排在「需关注」之后

### 8.5 未知 ≠ 失败

校准后，状态从 `unknown` 改为 `unknown_never_run`，显示为「未知 · 尚未运行」：

- 适用：已绑定运行数据路径但本地暂无记录的能力
- 含义：「能力已绑定运行数据路径，但本地尚未发现运行记录。运行对应能力后，Dashboard 会自动读取状态。」
- 不视为故障

### 8.6 工具能力

runtime.* 工具类能力的显示从「未配置」改为「工具能力」：

- 适用：`runtime.archive_paths` / `runtime.jsonl` / `runtime.failed_queue` / `runtime.run_log` / `runtime.health_status`
- 不计入未知、需关注、失败、降级
- 配置检查中标注为「说明」（正常设计）

### 8.7 配置检查三分类

M3B-3b 后，配置检查区分三类：

| 分类 | 含义 | 示例 |
|---|---|---|
| 错误 | 必须修复 | binding capability_id 不存在、重复 |
| 警告 | 不影响运行，需知晓 | 运行文件不存在（data/ 不提交是正常的） |
| 说明 | 正常设计 | 工具能力无 binding、HKEX known_limited |

### 8.8 状态解释

每个能力的状态解释通过 `runtime_mode` 和 `runtime_health` 综合生成：

- 工具能力：「工具能力，不需要单独运行，也不会产生 source_health 记录。」
- 已知限制：「该能力当前属于已知限制，不作为每日修复项；除非需要推进相关能力增强，否则无需重复关注。」
- 人工触发：「该能力是人工触发能力，等待人工触发运行后才会产生记录。」
- 未知 · 尚未运行：「能力已绑定运行数据路径，但本地尚未发现运行记录。」
- document_extraction：「当前能力按文件类型归因：.pdf 失败只影响 document_extraction.pdf。」

### 8.9 FAQ（新增）

#### Q11：为什么工具能力显示「工具能力」而不是「未配置」？

**A：** 工具能力（runtime.*）不需要单独运行，也不会产生 source_health 记录。显示「工具能力」是 M3B-3b 的校准，避免误报成「未配置」。

#### Q12：为什么 HKEX 降级不触发需关注？

**A：** HKEX 的 `runtime_mode` 是 `known_limited`，表示当前有外部限制（HKEXnews 客户端渲染）。按 M3B-3b 规则，已知限制的降级不算需关注，不作为每日修复项。

#### Q13：一个 PDF 失败会不会影响 HTML/TXT/Markdown？

**A：** 不会。M3B-3b 重构了匹配逻辑，document_extraction 类能力严格按文件扩展名匹配：
- document_extraction.pdf 只看 .pdf 失败
- document_extraction.html 只看 .html / .htm 失败
- document_extraction.txt 只看 .txt 失败
- document_extraction.markdown 只看 .md / .markdown 失败

一个 PDF 失败只会触发 document_extraction.pdf，其他不受影响。

#### Q14：怎么给一个能力设置 runtime_mode？

**A：** 在 `configs/foundation_capabilities.yaml` 中给该能力添加 `runtime_mode` 字段，可选值：`data_source`（默认）/ `utility` / `known_limited` / `manual_only`。

---

## 9. 相关文档

- [Foundation Control Center](foundation_control_center.md) — 中控台产品说明
- [Foundation Control Center 使用指南](foundation_control_center_usage.md) — 使用指南
- [Foundation Control Center 运行手册](foundation_control_center_runbook.md) — 运行手册
- [Runtime Foundation](runtime_foundation.md) — Runtime 层基础说明
- [Runtime Output Contract](runtime_output_contract.md) — 运行时输出契约
