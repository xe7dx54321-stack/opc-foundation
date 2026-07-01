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
