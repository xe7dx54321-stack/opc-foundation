# Foundation TRAE 运维手册

**Version**: 1.5
**Updated**: 2026-07-02
**Status**: M3C-3 Ready（15 个 Trial Source TRAE Trial Scheduling 已接入）+ M3C-5A5 审计完成

---

## 1. M3C-1 的目标

M3C-1 的目标是把信息源从"清单状态"推进到"可上线准备状态"：
> 注：M3C-0A 初始为 87 个源；后续配置扩展后，当前口径为 92 个源。

- 基于 source inventory 生成标准 run/check 脚本入口
- 基于 source group 生成 TRAE 调度模板
- 补齐日常运维文档
- 补齐每日状态检查脚本

> **注意**：本阶段不是 connector 开发阶段，不给信息源写爬虫。

---

## 2. 为什么 TRAE 只调用标准脚本

TRAE（个人助理）只调用标准 PowerShell 脚本，不直接调用 Python CLI，原因如下：

### 2.1 统一入口
所有任务都通过 `scripts/` 目录下的 `.ps1` 脚本启动，TRAE 不需要记复杂的 Python 命令。

### 2.2 自动定位
每个脚本都会自动定位仓库根目录，设置 `PYTHONPATH=src`，从任意目录都能正确运行。

### 2.3 Fail-Soft
配置文件不存在时，脚本会给出清晰的中文提示，告诉用户下一步该怎么做，而不是抛出难懂的 Python 错误。

### 2.4 统一风格
所有脚本的输出风格一致，退出码规范，方便 TRAE 做结果解析。

---

## 3. 每个脚本用途

### 3.1 Research Archive 脚本

| 脚本 | 用途 | 覆盖 source group |
|---|---|---|
| `scripts/run_research_archive.ps1` | 运行公开研究 / RSS / 播客 / 会议纪要 / 媒体 mention / analyst action 归档 | official_public_research、official_podcast_transcript、bank_conference_transcripts、media_research_mentions、analyst_actions |
| `scripts/check_research_archive.ps1` | 检查 research archive 产物是否存在 | - |

### 3.2 Official Filings 脚本

| 脚本 | 用途 | 覆盖能力 |
|---|---|---|
| `scripts/run_official_filings.ps1` | 运行 SEC / CNINFO / HKEX 官方披露归档 | official_filing.sec_edgar、official_filing.cninfo_announcement、official_filing.hkex_announcement |
| `scripts/check_official_filings.ps1` | 检查 official filings 产物是否存在 | - |

### 3.3 Wechat Archive 脚本（已有）

| 脚本 | 用途 |
|---|---|
| `scripts/run_wechat_archive.ps1` | 运行微信公众号归档 |
| `scripts/check_wechat_archive.ps1` | 检查微信归档产物 |

### 3.4 Document Extraction 脚本（已有）

| 脚本 | 用途 |
|---|---|
| `scripts/run_document_extraction.ps1` | 运行文档抽取后处理 |
| `scripts/check_document_extraction.ps1` | 检查文档抽取产物 |

### 3.5 Manual URL 脚本

| 脚本 | 用途 |
|---|---|
| `scripts/run_manual_url_archive.ps1` | 检查/处理 manual_url 待处理队列 |

### 3.6 Control Center 检查脚本

| 脚本 | 用途 |
|---|---|
| `scripts/check_foundation_control_center.ps1` | 只读检查 Control Center 所需配置是否完整 |
| `scripts/check_foundation_daily_status.ps1` | 生成每日 foundation 状态收口报告 |

---

## 4. TRAE 调度模板说明

配置文件：`configs/trae_foundation_schedule.example.yaml`

### 4.1 模板结构

```yaml
version: 1
updated_at: "2026-06-25"
timezone: local_machine

tasks:
  - task_id: foundation_xxx
    task_name: 中文任务名
    source_groups: [...]
    command: powershell -ExecutionPolicy Bypass -File scripts/xxx.ps1
    check_command: powershell -ExecutionPolicy Bypass -File scripts/check_xxx.ps1
    schedule_times:
      - "07:30"
    enabled_by_default: true
    notes: 说明文字
```

### 4.2 各字段说明

| 字段 | 说明 |
|---|---|
| `task_id` | 任务唯一 ID，英文 |
| `task_name` | 任务中文名称 |
| `source_groups` | 覆盖的 source group 列表 |
| `command` | 运行命令 |
| `check_command` | 检查命令（可选） |
| `schedule_times` | 调度时间列表，24 小时制 |
| `enabled_by_default` | 默认是否启用 |
| `notes` | 备注说明 |

---

## 5. 推荐调度时间表

### 5.1 早间批次（07:00 - 09:00）

| 时间 | 任务 | 说明 |
|---|---|---|
| 07:30 | 官方公开研究归档 | 覆盖美股隔夜研究 + 亚洲早盘前 |
| 08:00 | 官方披露归档 | SEC / CNINFO 早间披露 |
| 08:20 | 中文财经二次传播 | 早间中文财经内容 |
| 08:40 | 文档抽取后处理 | 处理早间批次文档 |
| 09:10 | Control Center 健康检查 | 检查上午运行结果 |

### 5.2 午间批次（12:00 - 15:30）

| 时间 | 任务 | 说明 |
|---|---|---|
| 12:20 | 中文财经二次传播 | 午间中文财经内容 |
| 12:45 | 官方披露归档 | 午间披露更新 |
| 13:05 | 文档抽取后处理 | 处理午间批次文档 |
| 13:30 | 官方公开研究归档 | 午间研究更新 |
| 15:20 | 媒体引用与分析师动作 | 午间媒体更新 |

### 5.3 晚间批次（17:00 - 23:59）

| 时间 | 任务 | 说明 |
|---|---|---|
| 17:30 | 官方披露归档 | 盘后披露更新 |
| 18:00 | 文档抽取后处理 | 处理下午批次文档 |
| 18:20 | 中文财经二次传播 | 晚间中文财经内容 |
| 18:30 | Control Center 健康检查 | 检查下午运行结果 |
| 20:30 | 官方公开研究归档 | 晚间研究更新 |
| 21:20 | 媒体引用与分析师动作 | 晚间媒体更新 |
| 22:20 | 中文财经二次传播 | 夜间中文财经内容 |
| 22:30 | 官方披露归档 | 晚间披露收尾 |
| 23:00 | 文档抽取后处理 | 处理全天文档 |
| 23:20 | 人工 URL 检查（默认禁用） | 按需启用 |
| 23:40 | Control Center 健康检查 | 全天最终检查 |
| 23:55 | 每日状态收口 | 生成日报 |

---

## 6. 各 source group 上线策略

### 6.1 第一批上线（S 级 scheduled）

| source group | 优先级 | 模式 | 说明 |
|---|---|---|---|
| official_public_research | S | scheduled | 投行官方公开研究 |
| official_podcast_transcript | S | scheduled | 投行官方播客/文字稿 |
| bank_conference_transcripts | S | scheduled | 核心投行会议纪要/公司 IR |

### 6.2 第二批上线（A 级 scheduled）

| source group | 优先级 | 模式 | 说明 |
|---|---|---|---|
| media_research_mentions | A | scheduled | 媒体研报二次引用 |
| analyst_actions | A | scheduled | 分析师评级/目标价变动 |

### 6.3 第三批上线（B 级 scheduled）

| source group | 优先级 | 模式 | 说明 |
|---|---|---|---|
| chinese_rebroadcast | B | scheduled | 主流中文财经媒体 |
| official_filings | A | scheduled | SEC / CNINFO / HKEX 官方披露 |

### 6.4 暂不自动上线

| source group | 优先级 | 模式 | 说明 |
|---|---|---|---|
| search_providers | supplement | on_demand | 搜索补充源，按需触发 |
| community_dev_signals | B / supplement | on_demand / dormant | 社区 / 开发者信号，按需启用 |
| manual_url | supplement | on_demand | 人工 URL，人工触发 |

### 6.5 禁止接入

| source group | 优先级 | 模式 | 说明 |
|---|---|---|---|
| blocked / high_risk | blocked | do_not_ingest / dormant | Telegram 群、网盘分享、研报下载站等 |

---

## 7. 哪些源不进入默认调度

### 7.1 Search Provider
- 所有 `search_providers` 组的源
- 原因：搜索 API 有调用成本，按需手动触发更合理
- 默认模式：`on_demand`

### 7.2 Community / Dev
- 所有 `community_dev_signals` 组的源
- 原因：社区源质量波动大，先观察再决定是否定期调度
- 默认模式：`on_demand` 或 `dormant`

### 7.3 Blocked / High Risk
- 所有 `activation_priority: blocked` 或 `legal_confidence: high_risk` 的源
- 原因：法律风险高，禁止接入
- 默认模式：`do_not_ingest` 或 `dormant`

### 7.4 Manual URL
- `manual_url` 组
- 原因：以人工触发为主，不建议高频调度
- 默认模式：`enabled_by_default: false`

---

## 8. 如何手动配置 TRAE

### 8.1 准备工作

1. 复制 example 配置为 local 配置
   ```powershell
   Copy-Item configs/trae_foundation_schedule.example.yaml configs/trae_foundation_schedule.local.yaml
   ```

2. 根据需要调整 `enabled_by_default` 和 `schedule_times`

### 8.2 在 TRAE 中配置任务

1. 打开 TRAE 的任务管理
2. 按照 `trae_foundation_schedule.local.yaml` 中的任务列表
3. 逐个创建定时任务
4. 粘贴对应的 `command` 字段作为任务命令
5. 设置对应的调度时间

### 8.3 验证配置

运行 Control Center 健康检查脚本：
```powershell
.\scripts\check_foundation_control_center.ps1
```

---

## 9. 如何查看 check 脚本结果

每个 check 脚本都会输出：
- ✅ 绿色 - 正常
- ⚠️ 黄色 - 警告（不阻断）
- ❌ 红色 - 错误（需要修复）

退出码：
- `0` - 成功或有警告
- `1` - 配置错误或脚本错误
- `2` - 部分失败（非阻塞）
- `3` - 严重错误

---

## 10. 如何进入 M3C-2 全信息源基线运行

M3C-2 的目标是让所有 scheduled 源稳定运行一周，建立基线数据。

### 10.1 前置条件

- [ ] M3C-1 所有脚本可运行
- [ ] TRAE 调度配置完成
- [ ] source inventory 配置检查全通过
- [ ] 第一批上线源配置了 production local 配置

### 10.2 步骤

1. 启用第一批 S 级 scheduled 任务
2. 运行 3 天，观察稳定性
3. 启用第二批 A 级 scheduled 任务
4. 运行 2 天，观察稳定性
5. 启用第三批 B 级 scheduled 任务
6. 运行 7 天，建立基线数据
7. 输出基线报告

---

## 11. 相关文档

- [Source Activation Plan](foundation_source_activation_plan.md)
- [Source Inventory Report](foundation_source_inventory_report.md)
- [Control Center 设计文档](foundation_control_center.md)
- [Control Center 使用指南](foundation_control_center_usage.md)

---

## 12. M3C-5A5 内容有效性审计 -- TRAE 操作说明

> 执行时间：2026-07-02
> 审计范围：21 operational deep audit + 92 inventory matrix
> 详细审计报告：[foundation_content_validity_audit_report.md](foundation_content_validity_audit_report.md)

### 12.1 审计结果对 TRAE 配置的影响

M3C-5A5 内容有效性审计完成，21 个 operational 源的审计结果如下：

| 状态 | 数量 | TRAE 操作 |
|---|---|---|
| content_ready | 4 | 纳入 trial_v2 scheduling（M3C-5A6 配置） |
| content_watch | 9 | 不纳入 scheduling，持续观察 |
| content_reject | 2 | 不纳入 scheduling，列入 backlog |
| technical_only | 5 | 不纳入 scheduling，列入 backlog（需 connector/网络修复） |

### 12.2 建议纳入 trial_v2 scheduling 的 4 个 content_ready 源

| source_id | source_name | 审计分数 | source_group | 建议频率 |
|---|---|---|---|---|
| barclays_our_insights | Barclays Our Insights | 90 | official_public_research | 每天1次 |
| markets_insider | Markets Insider | 90 | media_research_mentions | 每天1-2次 |
| wind_public | Wind 万得公开内容 | 85 | chinese_rebroadcast | 每天1次 |
| china_fund_news | 中国基金报 | 100 | chinese_rebroadcast | 每天1-2次 |

### 12.3 TRAE 操作步骤（M3C-5A6）

1. **不修改当前 15 个 trial_v1 的 TRAE scheduling 配置**
2. **为 4 个 content_ready 源配置新的 trial_v2 scheduling 任务**：
   - 使用 `scripts/run_foundation_trial_v2.ps1` 作为调度入口
   - trial_v2 scheduling 与 trial_v1 scheduling 独立运行
3. **content_watch 源不配置 scheduling**，等待 M3C-5B 阶段重新评估
4. **technical_only / content_reject 源不配置 scheduling**，等待 M3C-5C 阶段处理

### 12.4 边界确认

| 检查项 | 结果 |
|---|---|
| 是否修改当前 15 个 trial v1 scheduling | 否 |
| 是否修改 production 配置 | 否 |
| 是否调度 92 全量 | 否 |
| 是否配置 content_watch 源 | 否 |
| 是否配置 technical_only 源 | 否 |
| 是否配置 content_reject 源 | 否 |
| 是否引入 Playwright/Selenium | 否 |

### 12.5 后续阶段

| 阶段 | 目标 | 涉及源 |
|---|---|---|
| M3C-5B | Browser-like connector | goldman_sachs 系列（4个）、business_insider、briefing_com_upgrades、wallstreet_cn 等 |
| M3C-5C | 特殊 connector / 网络修复 | yahoo_finance、the_fly、benzinga_analyst_ratings、bofa_global_research、texas_instruments_ir |

---

## 13. M3C-5A9 / M3C-5B1：Trial V2 Content-Ready Command-Only 调度运维

> 执行时间：2026-07-02 ~ 2026-07-04
> 启用源数：9 个 content_ready 源（M3C-5B1.3 从 8 扩容到 9）
> 配置路径：`configs/trae_foundation_trial_v2_content_ready.example.yaml`

### 13.1 调度对象

只允许调度以下 9 个 source：

| source_id | source_name | priority |
|---|---|---|
| barclays_our_insights | Barclays Our Insights | P0 |
| markets_insider | Markets Insider | P0 |
| china_fund_news | 中国基金报 | P0 |
| wind_public | Wind 万得公开内容 | P0 |
| goldman_sachs_insights | Goldman Sachs Insights | P1 |
| business_insider | Business Insider | P1 |
| cls_cn | 财联社 | P1 |
| zhitong_caijing | 智通财经 | P1 |
| gelonghui | 格隆汇 | P0 |

**排除源**：merck_ir、benzinga_analyst_ratings、bofa_global_research、texas_instruments_ir、briefing_com_upgrades、wallstreet_cn、goldman_sachs_reports、goldman_sachs_top_of_mind、goldman_sachs_research、goldman_sachs_podcasts

### 13.2 TRAE 本地启用方式

TRAE 本地任务启用方式：
- 使用 **command-only shell command**
- **不要填自然语言 prompt**
- **不要让 TRAE 调模型解释命令**

**步骤**：
1. 在 TRAE 任务管理中新建定时任务
2. 任务命令粘贴以下 command-only 命令：
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/run_foundation_trial_v2_content_ready.ps1 -Mode run
   ```
3. 检查任务命令粘贴以下命令：
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/check_foundation_trial_v2_content_ready.ps1
   ```
4. 设置调度时间（建议 morning / afternoon / evening 三个时段）
5. 每日 run 后执行 check

**注意**：
- 示例配置 `configs/trae_foundation_trial_v2_content_ready.example.yaml` 中所有 job `enabled=false`
- 真实启用只发生在本地 TRAE，**不提交 local config 到 Git**
- 所有 job 必须是 command-only，不允许自然语言 prompt

### 13.3 代理配置（仅本地）

如果本地需要代理，真实命令可以使用：
```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_foundation_trial_v2_content_ready.ps1 -Mode run -Proxy "http://127.0.0.1:7890"
```

但注意：
- 代理命令只能出现在本地配置，不提交 Git
- docs / reports 中不得出现完整 proxy URL
- 只能记录 proxy_enabled=true/false、proxy_mode=cli/env/none

### 13.4 每日检查要点

运行 `scripts/check_foundation_trial_v2_content_ready.ps1` 后检查：

1. source_health.jsonl 是否新增 9 条记录
2. run_log.jsonl 是否新增 run 记录
3. failed_queue.jsonl 是否存在且 fail-soft
4. latest report 是否更新
5. check 是否 15/15 通过
6. gelonghui 是否在新增记录中

### 13.5 Wind Public 特殊观察

`wind_public` 存在 `garbled_text` 噪音风险，每日检查中需重点观察：
- 乱码率是否上升
- 有效候选数是否低于 2
- 如出现持续乱码，需降级为 content_watch 并暂停调度

### 13.6 状态分级

| 状态 | 含义 | 操作 |
|---|---|---|
| content_ready | 内容有效，可调度 | 正常纳入 trial_v2 run |
| content_watch | 内容不稳定 | 暂停调度，观察修复 |
| content_reject | 内容无效 | 不调度，列入 backlog |
| technical_only | 技术/网络问题 | 不调度，等待 connector 修复 |

### 13.7 边界确认

| 检查项 | 结果 |
|---|---|
| 是否修改 trial_v1 | 否 |
| 是否配置 production | 否 |
| 是否调度 92 全量 | 否 |
| 是否纳入 watch/reject/technical_only | 否 |
| 是否提交 data/local/secrets | 否 |
| 是否提交真实 TRAE local config | 否 |
| 是否恢复已删除 Dashboard 页面 | 否 |
| 是否引入 Playwright/Selenium | 否 |

---

## 14. M3C-5A10：24h 观察期运维

> 执行时间：2026-07-02 ~ 2026-07-03
> 观察对象：8 个 content_ready 源 trial_v2 command-only 调度
> observation_status：`completed_24h`

### 14.1 观察目标

验证 8 个 content_ready 源是否能在 TRAE 本地 command-only 调度下稳定运行 24 小时。

### 14.2 观察要求

至少观察以下运行：

- [x] morning_run：2026-07-03 09:02，8 源 × 8 records
- [x] afternoon_run：2026-07-03 15:01，8 源 × 8 records
- [x] evening_run：2026-07-03 21:01，8 源 × 8 records
- [x] daily_check：2026-07-03 21:32，检查通过

### 14.3 每次运行检查清单

1. source_health.jsonl 是否新增 8 条记录
2. run_log.jsonl 是否新增 run 记录
3. failed_queue.jsonl 是否存在且 fail-soft
4. latest report 是否更新
5. check 是否 15/15 通过
6. wind_public garbled_text 是否出现

### 14.4 8 源观察标准

| source_id | 合格标准 |
|---|---|
| barclays_our_insights | 能拿到 Barclays insights / press / sector links 相关内容 |
| markets_insider | 能拿到市场新闻、IPO、stock market、公司/行情相关标题 |
| china_fund_news | 能拿到中文基金/券商/行业资讯，有标题和时间 |
| wind_public | 能拿到 Wind 公开资讯，但必须重点记录 garbled_text ratio |
| goldman_sachs_insights | 能拿到 Goldman Sachs insights 文章链接、标题、发布日期 |
| business_insider | 能拿到 Business Insider 新闻标题、URL、日期或从 URL 推断日期 |
| cls_cn | 能拿到财联社中文快讯/新闻标题、URL、中文时间 |
| zhitong_caijing | 能拿到智通财经中文新闻标题、URL、时间或相对时间 |

### 14.5 wind_public 特殊处理

如果 wind_public 乱码过高：
- 不得直接判定失败
- 标记为 `content_ready_watch_flag`
- 后续进入 Wind text-cleaning 专项
- 如 valid_count < 2 或 relevant_count < 2，降级为 content_watch

### 14.6 24h Observation Report

- **报告路径**：`docs/foundation_trial_v2_24h_observation_report.md`
- **更新频率**：每完成一轮观察后更新
- **必须包含**：
  - observation_status（partial_observation / completed_24h）
  - 8/9 源逐源表现
  - wind_public garbled_text 观察结果
  - 是否建议进入下一阶段

---

## 15. M3C-5B1.4：9 源 24h Observation 运维

> 执行时间：2026-07-04
> 观察对象：9 个 content_ready 源 trial_v2 command-only 调度
> observation_status：`completed_24h`

### 15.1 扩容背景

M3C-5B1.3 将 trial_v2 allowlist 从 8 源扩容到 9 源：

- **新增源**：`gelonghui`（格隆汇）
- **扩容验证**：validate-config PASS、preflight PASS 9/9、dry-run PASS
- **扩容时间**：2026-07-04

### 15.2 9 源列表

在原有 8 源基础上增加 gelonghui：

| source_id | source_name | priority | 状态 |
|---|---|---|---|
| barclays_our_insights | Barclays Our Insights | P0 | content_ready |
| markets_insider | Markets Insider | P0 | content_ready |
| china_fund_news | 中国基金报 | P0 | content_ready |
| wind_public | Wind 万得公开内容 | P0 | content_ready（garbled_text watch） |
| goldman_sachs_insights | Goldman Sachs Insights | P1 | content_ready |
| business_insider | Business Insider | P1 | content_ready |
| cls_cn | 财联社 | P1 | content_ready |
| zhitong_caijing | 智通财经 | P1 | content_ready |
| gelonghui | 格隆汇 | P0 | content_ready |

### 15.3 观察进度（2026-07-04 全天）

- [x] morning_run：2026-07-04 09:03，9 源 × 9 records（含 gelonghui）
- [x] afternoon_run：2026-07-04 15:03，9 源 × 9 records（含 gelonghui）
- [x] evening_run：2026-07-04 21:03，9 源 × 9 records（含 gelonghui）
- [x] daily_check：2026-07-04 21:32，检查通过

### 15.4 收口标准（全部满足）

1. afternoon_run 已自动触发且 source_count=9 ✅
2. evening_run 已自动触发且 source_count=9 ✅
3. daily_check 已自动触发且通过 ✅
4. 三个 batch 均包含 gelonghui ✅
5. failed_queue 保持为空 ✅
6. production_enabled=false ✅

### 15.5 当前报告

- **报告路径**：`docs/foundation_m3c_5b1_4_9_source_24h_observation_report.md`
- **当前状态**：completed_24h（2026-07-04 21:32 收口）

### 14.7 Daily Status Trial V2 集成

`scripts/generate_daily_status_report.py` 已通过 sidecar 分支（M3C-5A10-sidecar）接入 trial_v2 content-ready 数据。

**已展示字段**：
- source_count
- last_run_at
- success_count
- failed_count
- failed_queue_count
- observation_status

**集成模块**：`src/opc_foundation/dashboard/trial_v2_status.py`
- fail-soft 设计：数据缺失时返回安全默认值
- 不修改 trial_v1
- 不恢复已删除 Dashboard 页面
   - latest_check_status
   - wind_public_watch_flag
   - production_enabled=false

### 14.8 边界确认

| 检查项 | 结果 |
|---|---|
| 是否修改 trial_v1 | 否 |
| 是否配置 production | 否 |
| 是否调度 92 全量 | 否 |
| 是否纳入 merck_ir | 否 |
| 是否纳入 watch/reject/technical_only | 否 |
| 是否提交 data/local/secrets | 否 |
| 是否提交真实 TRAE local config | 否 |
| 是否恢复已删除 Dashboard 页面 | 否 |
| 是否引入 Playwright/Selenium | 否 |
| 是否打 tag | 否 |

---

## 15. M3C-6C Low-frequency Source Pipeline (2026-07-05)

**阶段:** M3C-6C — Low-frequency Source Pipeline
**状态:** Pipeline v1 完成，TRAE task proposal only

### 15.1 新增 source layer

```
Layer 1: trial_v2_high_frequency (9 sources, daily 3 batches) — 不变
Layer 2: low_frequency_sources (merck_ir, weekly) — 新增
Layer 3: on_demand_sources — 未实现
```

### 15.2 TRAE low-frequency task proposal

- **source_id:** merck_ir
- **proposed_frequency:** weekly
- **proposed_command:** `python scripts/run_foundation_low_frequency_sources.py --source merck_ir --run-once`
- **create_trae_task_now:** false
- **manual_approval_required:** true
- **production_enabled:** false
- **不影响现有 4 个 trial_v2 task**

### 15.3 后续 gate

1. M3C-6C pipeline v1 完成（本阶段）
2. M3C-6C.1 24h/7d observation（连续观察一周）
3. 人工审核 observation 结果
4. 人工创建 TRAE scheduled task（手动操作）
5. 纳入更多低频候选源

### 15.4 边界确认

| 检查项 | 结果 |
|---|---|
| 是否修改 TRAE scheduling | 否 |
| 是否修改 TRAE local config | 否 |
| 是否创建永久自动化任务 | 否 |
| 是否修改 trial_v2 allowlist | 否 |
| 是否配置 production | 否 |
| 是否提交 data/local/secrets | 否 |
| 是否引入 Playwright/Selenium | 否 |
| 是否恢复已删除 Dashboard 页面 | 否 |
| 是否打 tag | 否 |

---

## 16. M3C-6C.1 Merck IR Low-frequency Observation Harness (2026-07-05)

**阶段:** M3C-6C.1 — Merck IR Low-frequency 7-Day Observation Harness
**状态:** Harness 完成，连续观察进行中（partial_observation）
**TRAE task 创建:** 否（proposal only）

### 16.1 新增能力

- 7 天 observation 状态机：`pending -> active -> completed_7d | partial_observation | failed`
- Daily run 记录：source_id, run_id, run_date, valid_item_count, dated_item_count, missing_date_count, navigation_rejected_count, timestamp_confidence_distribution, sample_items, risk_flags, status
- 7-day summary：observed_days, successful_days, partial_days, failed_days, total_runs, navigation_regression_count, blocking_error_count, final_observation_status
- Navigation regression 检测：连续 2 次 navigation-only run 触发 `failed`
- Blocking error 检测：login_required / paywall_observed / captcha_or_antibot_observed 任一出现即 `failed`
- Runtime data：`data/foundation_low_frequency_observation/`（gitignored）

### 16.2 新增脚本

| 脚本 | 用途 |
|---|---|
| `scripts/run_foundation_low_frequency_observation.py` | Observation runner（dry-run / run-once / summarize） |
| `scripts/check_foundation_low_frequency_observation.py` | Boundary checker |

### 16.3 命令

```bash
# Dry-run（不写 runtime data）
python scripts/run_foundation_low_frequency_observation.py --source merck_ir --dry-run

# Run once（写 runtime data，gitignored）
python scripts/run_foundation_low_frequency_observation.py --source merck_ir --run-once

# Summarize（输出 7-day summary）
python scripts/run_foundation_low_frequency_observation.py --source merck_ir --summarize

# Boundary check
python scripts/check_foundation_low_frequency_observation.py
```

注意：脚本为 command-only shell，不允许自然语言 prompt。真实启用只发生在本地 TRAE，不提交 local config。

### 16.4 merck_ir observation 当前结果

| 字段 | 值 |
|---|---|
| target_days | 7 |
| observed_days | 1 |
| successful_days | 1 |
| partial_days | 0 |
| failed_days | 0 |
| total_runs | 1 |
| min/max_valid_items_per_run | 15 / 15 |
| timestamp_confidence_distribution | `{"HIGH": 0, "MEDIUM": 0, "LOW": 15, "NONE": 0}` |
| navigation_regression_count | 0 |
| blocking_error_count | 0 |
| final_observation_status | partial_observation |
| recommended_next_action | continue_observation |
| completed_7d | false |
| missing_to_complete | 6 more days of observation |

### 16.5 与 trial_v2 的隔离

| 维度 | trial_v2 高频任务 | M3C-6C.1 observation |
|---|---|---|
| 源数 | 9 | 1 (merck_ir) |
| 频率 | 每日 3 批 | 每日 1 次（observation 阶段） |
| allowlist | trial_v2 allowlist（9 源） | low_frequency_sources（仅 merck_ir） |
| runtime data | `data/foundation_trial_v2/` | `data/foundation_low_frequency_observation/` |
| script | `scripts/run_foundation_trial_v2_content_ready.ps1` | `scripts/run_foundation_low_frequency_observation.py` |
| production_enabled | false | false |

### 16.6 后续 gate

```
Gate 1: M3C-6C pipeline v1 完成（已完成）
Gate 2: M3C-6C.1 7-day observation harness（当前，需连续观察 6 天）
Gate 3: 人工审核 observation 结果（completed_7d 必要条件）
Gate 4: 人工创建 TRAE scheduled task（手动操作）
Gate 5: 纳入更多低频候选源
```

### 16.7 边界确认

| 检查项 | 结果 |
|---|---|
| 是否修改 TRAE scheduling | 否 |
| 是否修改 TRAE local config | 否 |
| 是否创建永久自动化任务 | 否 |
| 是否修改 trial_v2 allowlist | 否 |
| 是否配置 production | 否 |
| 是否提交 data/local/secrets | 否 |
| 是否提交 proxy URL/cookie/token | 否 |
| 是否引入 Playwright/Selenium | 否 |
| 是否恢复已删除 Dashboard 页面 | 否 |
| 是否打 tag | 否 |

### 16.8 相关文档

- [M3C-6C.1 Observation Start Report](foundation_m3c_6c1_observation_start_report.md)
- [Low-frequency Observation Harness](foundation_low_frequency_observation_harness.md)
- [M3C-6C.1 Observation Report](foundation_m3c_6c1_merck_ir_low_frequency_observation_report.md)
- [M3C-6C.1 TRAE Observation Proposal](foundation_m3c_6c1_trae_low_frequency_observation_proposal.md)
- [Low-frequency Source Pipeline](foundation_low_frequency_source_pipeline.md)
- [TRAE Low-frequency Task Proposal](foundation_low_frequency_trae_task_proposal.md)

---

## 17. M3C-6C.1 Merge + Observation Start (2026-07-05)

**阶段:** M3C-6C.1 Merge + Merck IR Low-frequency 7-Day Observation Start
**状态:** Harness 已合并到 master，observation 启动
**TRAE task 创建:** 本地 command-only observation task（不提交 TRAE local config）

### 17.1 Merge 结果

| 项 | 值 |
|---|---|
| starting master commit | a5b7f06 |
| 6C.1 branch commit | 8e963c4 |
| 6C.1 merge commit | 45438b4 |
| origin/master latest | 45438b4 |
| full pytest | 2483 passed, 0 failed |
| low-frequency check | PASS |
| observation check | PASS |
| trial_v2 allowlist | 仍 9 源（未变化） |
| production_enabled | false（未变化） |

### 17.2 Observation Baseline

| 字段 | 值 |
|---|---|
| source_id | merck_ir |
| target_days | 7 |
| observed_days | 1 |
| successful_days | 1 |
| final_observation_status | partial_observation |
| recommended_next_action | continue_observation |
| completed_7d | false |
| missing_to_complete | 6 days |

### 17.3 本地 TRAE command-only observation task

在本地 TRAE 中创建 command-only observation task（不提交 TRAE local config）：

- **task name:** `foundation_low_frequency_merck_ir_observation_daily`
- **command (command-only):**
  ```bash
  cd "/Users/apple/Documents/一人公司OPC/opc-foundation" && \
  python3 scripts/run_foundation_low_frequency_observation.py --source merck_ir --run-once && \
  python3 scripts/check_foundation_low_frequency_observation.py
  ```
- **frequency:** daily 1 次
- **count:** 6 次（补齐到 7 天）
- **suggested_time:** 10:30 本地时间
- **is_production:** false
- **stop_condition:** 第 6 次运行后人工关闭，或由 M3C-6C.2 close 阶段处理

### 17.4 边界确认

| 检查项 | 结果 |
|---|---|
| 是否修改 trial_v2 scheduling | 否 |
| 是否修改 trial_v2 allowlist | 否（仍 9 源） |
| 是否配置 production | 否 |
| 是否提交 TRAE local config | 否 |
| 是否提交 data/local/secrets | 否 |
| 是否提交 proxy URL/cookie/token | 否 |
| 是否引入 Playwright/Selenium | 否 |
| 是否恢复已删除 Dashboard 页面 | 否 |
| 是否打 tag | 否 |

### 17.5 后续 close 标准

第 7 天 observation 完成后，进入 M3C-6C.2 阶段：

```
M3C-6C.2: Merck IR 7-Day Observation Close
```

详细记录见 [M3C-6C.1 Observation Start Report](foundation_m3c_6c1_observation_start_report.md)。
