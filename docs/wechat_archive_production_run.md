# 微信公众号归档生产运行指南

> 适用版本：opc-foundation v0.1.5+
> 文档目的：说明如何手动运行微信公众号归档生产任务，以及如何供后续 TRAE 调度调用。
> 本文档**不包含** TRAE 自动化任务设置，那是 Phase 1.8B 的内容。

---

## 1. 本文目的

本文档说明：

- 生产归档目录结构
- 生产配置方式
- 推荐生产参数
- 手动运行命令
- 手动检查命令
- 日报与失败重试
- 后续 TRAE 调度建议时间

**不包含**：

- TRAE 自动化任务配置
- Windows Task Scheduler 配置
- cron / LaunchAgent 配置
- LLM 接入
- 业务线接入（Demand Radar / 内容 Agent / 投研 Agent）

---

## 2. 目录结构

生产归档位置：

```
data/wechat_archive/
├── articles/                          # 文章正文目录
│   └── YYYY/MM/
│       └── YYYY-MM-DD__<account>__<title-slug>/
│           ├── article.md             # Markdown 正文
│           ├── article.html           # 原始 HTML
│           ├── metadata.json          # 文章元数据
│           └── images/                # 图片（生产初期 download_images=false，暂无）
├── index/
│   └── articles.jsonl                 # 所有归档文章索引（append-only）
├── state/
│   ├── seen_articles.sqlite           # foundation 内部去重（不对外暴露）
│   ├── run_log.jsonl                  # 运行日志（含 run_summary）
│   ├── failed_queue.jsonl             # 失败队列
│   └── consumers/                     # 下游消费回执（per-consumer）
│       ├── content_agent.receipts.jsonl
│       └── demand_radar.receipts.jsonl
└── reports/
    └── daily_capture_YYYY-MM-DD.md    # 中文日报
```

**重要**：
- `data/wechat_archive/` 已在 `.gitignore` 中，不会被提交
- `configs/wechat_archive.production.local.yaml` 已在 `.gitignore` 中，不会被提交
- 真实文章正文、图片、cookie、token 都不会进入 git

---

## 3. 配置方式

### 3.1 复制模板

```powershell
Copy-Item configs/wechat_archive.production.example.yaml configs/wechat_archive.production.local.yaml
```

### 3.2 编辑 local config

打开 `configs/wechat_archive.production.local.yaml`，修改以下字段：

| 字段 | 说明 | 示例 |
|------|------|------|
| `feed_url` | WeRSS 服务中该公众号的 feed 地址 | `http://192.168.1.128:8001/rss/MP_WXS_xxx` |
| `archive_root` | 归档根目录（一般保持默认） | `./data/wechat_archive` |
| `max_articles_per_account` | 单次运行最多处理文章数 | `300` |
| `download_images` | 是否下载正文图片 | `false`（生产初期推荐） |

可以添加多个公众号，复制 `accounts` 下的条目即可。

### 3.3 添加更多公众号

```yaml
accounts:
  - account_name: "第四维的梦想"
    account_id: "disiweidemengxiang"
    source_type: "werss"
    feed_url: "http://<mac-mini-ip>:8001/rss/<feed_id_1>"
    enabled: true
    tags: ["wechat", "rss", "production"]

  - account_name: "另一个公众号"
    account_id: "another_account"
    source_type: "werss"
    feed_url: "http://<mac-mini-ip>:8001/rss/<feed_id_2>"
    enabled: true
    tags: ["wechat", "rss", "production"]
```

---

## 4. 推荐生产参数

```yaml
defaults:
  fetch_timeout_seconds: 30         # 网络抖动留余量
  max_articles_per_account: 300     # 适配每日可能 200 篇文章
  download_images: false            # 生产初期先保证正文稳定，图片后续再补
  save_html: true                   # 保留原始 HTML，便于后续重新抽取
  save_markdown: true               # 提供下游最直接可读正文
  user_agent: "Mozilla/5.0 (compatible; opc-foundation-wechat/1.0)"
```

**参数选择理由**：

- `max_articles_per_account=300`：每日 RSS 刷新 8 次，每次可能有新文章，单次运行上限 300 足够覆盖单日吞吐
- `download_images=false`：图片下载是已知的潜在故障点（cover image 目录创建 bug），生产初期先关闭，保证正文和 metadata 稳定归档
- `save_html=true`：保留原始 HTML，未来如果 extractor 改进，可以重新抽取
- `save_markdown=true`：下游业务线最直接可读的正文格式
- `fetch_timeout_seconds=30`：网络抖动留余量，避免单篇文章超时拖慢整体

---

## 5. 手动运行

### 5.1 使用运行脚本（推荐）

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_wechat_archive.ps1
```

脚本会：

1. 自动切换到仓库根目录
2. 读取 `configs/wechat_archive.production.local.yaml`
3. 执行 `python -m opc_foundation.wechat.cli run`
4. 输出中文摘要
5. 根据退出码显示绿色/黄色/红色提示

### 5.2 直接使用 CLI

```powershell
python -m opc_foundation.wechat.cli run --config configs/wechat_archive.production.local.yaml
```

### 5.3 退出码说明

| 退出码 | 含义 |
|--------|------|
| 0 | 成功 |
| 1 | 配置错误或脚本错误 |
| 2 | 部分失败（非阻塞，请查看日报和 failed_queue） |
| 3 | 严重错误 |

---

## 6. 手动检查

### 6.1 使用检查脚本（推荐）

```powershell
powershell -ExecutionPolicy Bypass -File scripts/check_wechat_archive.ps1
```

脚本会：

1. 自动切换到仓库根目录
2. 检查 `./data/wechat_archive` 目录结构
3. 统计 articles.jsonl 中的 saved/failed/partial 数量
4. 检查 articles/ 目录下的文章文件
5. 显示 run_log.jsonl 中的最近运行记录
6. 输出中文摘要

### 6.2 直接使用 check 命令

```powershell
python scripts/wechat_live_smoke.py check --archive-root ./data/wechat_archive
```

### 6.3 检查项说明

检查脚本会验证以下目录/文件是否存在：

- `index/articles.jsonl`
- `state/seen_articles.sqlite`
- `state/run_log.jsonl`
- `reports/`

并统计：

- 总记录数
- 成功保存数
- 部分保存数
- 失败数
- 唯一 URL 数
- 文章目录数

---

## 7. 日报查看

### 7.1 查看今日日报

```powershell
python -m opc_foundation.wechat.cli report --archive-root ./data/wechat_archive
```

### 7.2 查看指定日期日报

```powershell
python -m opc_foundation.wechat.cli report --archive-root ./data/wechat_archive --date 2026-06-22
```

### 7.3 日报文件位置

```
data/wechat_archive/reports/daily_capture_YYYY-MM-DD.md
data/wechat_archive/reports/daily_capture_YYYY-MM-DD_manual.md
```

日报包含：

- 当日新增文章数
- 成功/部分/失败统计
- 失败队列当日新增
- 账号健康度

---

## 8. 失败重试

### 8.1 重试失败文章

```powershell
python -m opc_foundation.wechat.cli retry-failed --archive-root ./data/wechat_archive
```

### 8.2 失败队列位置

```
data/wechat_archive/state/failed_queue.jsonl
```

### 8.3 重试说明

- 重试只处理 `failed_queue.jsonl` 中的文章
- 重试成功后，文章会从失败队列中移除
- 重试失败会保留在队列中，下次重试时再次尝试
- 重试不会重复保存已成功的文章（seen_articles.sqlite 去重）

---

## 9. 后续 TRAE 调度建议

**本节只是建议，本阶段不实际配置 TRAE 任务。**

### 9.1 RSS 刷新节奏

用户的 WeRSS 已设置每日 8 次刷新：

```
01:28
04:48
07:48
10:08
13:08
16:08
19:08
22:18
```

### 9.2 建议归档时间

建议 TRAE 在每次 RSS 刷新后约 15 分钟执行归档，确保 RSS 已刷新完成：

```
01:45
05:05
08:05
10:25
13:25
16:25
19:25
22:35
```

### 9.3 TRAE 调用命令

TRAE 只需要执行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_wechat_archive.ps1
```

### 9.4 调度注意事项

- 如果某次运行失败（exit_code=3），TRAE 可以选择立即重试一次
- 如果某次运行部分失败（exit_code=2），不需要立即重试，等下次调度时 `retry-failed` 会自动处理
- 建议每周手动跑一次 `check` 脚本，确认归档目录健康

---

## 10. 边界

本脚本和本文档明确不做以下事情：

1. **不调用 LLM**：不评估文章价值、不生成摘要、不分类
2. **不判断文章价值**：不筛选、不打分、不决定是否进入业务流程
3. **不接业务线**：不接 Demand Radar、不接内容 Agent、不接投研 Agent
4. **只归档 RSS 中的新文章**：foundation 只负责采集、去重、标准化输出
5. **后续由业务线通过 Phase 1.7 consumer contract 读取文章**：业务线自己判断价值、自己记录消费状态

---

## 11. 常见问题

### Q1: 运行时报 "缺少生产配置文件"

**A**: 需要先复制模板并填入真实 feed_url：

```powershell
Copy-Item configs/wechat_archive.production.example.yaml configs/wechat_archive.production.local.yaml
# 然后编辑 wechat_archive.production.local.yaml
```

### Q2: 运行时报 "无法连接 RSS 服务"

**A**: 检查 Mac mini 是否开机、WeRSS 服务是否运行、IP 是否正确。

### Q3: 运行后没有新文章

**A**: 可能是 RSS 还没刷新，或者所有文章都已被归档（去重生效）。查看 run_log.jsonl 中的 duplicate_count。

### Q4: 部分文章状态为 partial

**A**: 表示正文提取失败但保留了原始 HTML。可以后续用 retry-failed 重试，或手动检查 article.html。

### Q5: 如何添加新的公众号

**A**: 编辑 `configs/wechat_archive.production.local.yaml`，在 `accounts` 下添加新条目，填入该公众号的 feed_url。

### Q6: 如何查看某天的归档情况

**A**: 使用 report 命令：

```powershell
python -m opc_foundation.wechat.cli report --archive-root ./data/wechat_archive --date 2026-06-22
```

---

## 12. 相关文档

- [微信文章归档消费契约](wechat_archive_consumer_contract.md)：下游业务线如何读取归档文章
- [Live Smoke 指南](wechat_live_smoke.md)：Phase 1.6 验证流程
- [配置示例](../configs/wechat_archive.production.example.yaml)：生产配置模板
