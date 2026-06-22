# 微信公众号归档 Live Smoke 验证指南

> Phase 1.6 — 验证 opc-foundation v0.1.4 wechat archive 能力能否稳定归档真实公众号文章。
>
> **本阶段不是继续开发新功能，而是用真实 feed 跑一遍现有能力的最小验证。**

---

## A. 本阶段目的

确认 `opc-foundation` 在 Phase 1.5 / v0.1.4 中开发的 wechat archive 能力，在接入真实 we-mp-rss / WeRSS feed 时能：

- 稳定发现公众号新文章
- 正确保存到本地归档目录
- 生成可读的 Markdown / HTML / metadata
- 运行日志和日报数字准确
- 重复运行不重复保存

**不需要** cookie / 微信登录 / 微信协议逆向 / 本地微信数据库 / UI 自动化。

---

## B. 前置条件

在开始之前，请确保满足以下全部条件：

1. **we-mp-rss / WeRSS 已部署并运行**
   - 推荐私有化部署 [we-mp-rss](https://github.com/zhegexiaohuozi/we-mp-rss) 或类似服务
   - 服务地址假设为 `http://localhost:8000`（如有不同，在配置里替换）

2. **已在 we-mp-rss 中添加 2-3 个真实公众号**
   - 建议选择更新频率适中的账号（每天 1-3 篇最佳）
   - 建议选择图文消息为主的账号（便于验证正文提取）

3. **能通过浏览器访问 feed URL**
   - 例如 `http://localhost:8000/feed/your_account_a.xml`
   - 浏览器打开后应能看到 XML 内容（RSS 2.0 / Atom 格式）

4. **opc-foundation 已更新到最新版本**
   ```bash
   git pull origin master
   git checkout v0.1.4  # 或最新 tag
   ```

5. **Python 环境已安装依赖**
   ```bash
   pip install -e opc-foundation/
   # 或
   pip install feedparser httpx pydantic typer
   ```

---

## C. 配置方式

### 1. 复制配置模板

```bash
cd opc-foundation
cp configs/wechat_live_smoke.example.yaml configs/wechat_live_smoke.local.yaml
```

### 2. 编辑 `configs/wechat_live_smoke.local.yaml`

需要修改的内容：

```yaml
# 1. 归档根目录（可自定义）
archive_root: "./data/wechat_live_smoke_archive"

accounts:
  # 2. 把下面的 feed_url 替换为你在 we-mp-rss 中实际生成的地址
  - account_name: "你的公众号A"          # 易读的名字，会出现在目录名和报告里
    account_id: "your_account_a"        # 稳定 ID，可自定义
    feed_url: "http://localhost:8000/feed/your_account_a.xml"  # ← 替换这里
    enabled: true                        # true 表示启用
    tags: ["live_smoke"]

  - account_name: "你的公众号B"
    account_id: "your_account_b"
    feed_url: "http://localhost:8000/feed/your_account_b.xml"  # ← 替换这里
    enabled: true
    tags: ["live_smoke"]
```

> 注意：`configs/wechat_live_smoke.local.yaml` 已在 `.gitignore` 中，不会被提交到仓库。

### 3. （可选）配置手工 URL 投喂

如果你想把一些不在 RSS 里的文章手动归档，在 `manual_urls.txt` 文件中写入 URL：

```text
https://mp.weixin.qq.com/s/xxxxx_article_1
https://mp.weixin.qq.com/s/xxxxx_article_2
```

然后在 YAML 的 `defaults` 部分取消注释：
```yaml
manual_urls_file: "./data/wechat_archive/manual_urls.txt"
```

---

## D. dry-run：先看看能发现什么

在真正抓取之前，先用 dry-run 只读 feed、不写文件，验证配置是否正确：

```bash
python -m opc_foundation.wechat.cli dry-run \
  --config configs/wechat_live_smoke.local.yaml
```

**预期输出（示例）：**

```
运行 ID：dry_2026-06-22_10-00-00_+08-00
开始：2026-06-22T10:00:00+08:00
结束：2026-06-22T10:00:01+08:00
监控账号：2 个
发现候选：8 篇
新文章：6 篇
成功保存：0 篇
部分保存：0 篇
失败：0 篇
重复跳过：0 篇
```

**如果看到错误**：
- `feed 解析异常` → 检查 feed_url 是否可访问
- `账号 [xxx] 已禁用` → 把 `enabled: false` 改为 `true`
- `HTTP 请求失败` → 检查 we-mp-rss 服务是否正常运行

---

## E. run：开始真实归档

确认 dry-run 正常后，执行完整归档：

```bash
python -m opc_foundation.wechat.cli run \
  --config configs/wechat_live_smoke.local.yaml
```

**预期输出（示例）：**

```
运行 ID：run_2026-06-22_10-05-00_+08-00
开始：2026-06-22T10:05:00+08:00
结束：2026-06-22T10:06:30+08:00
监控账号：2 个
发现候选：8 篇
新文章：6 篇
成功保存：5 篇
部分保存：1 篇
失败：0 篇
重复跳过：0 篇

生成的报告：
  - data/wechat_live_smoke_archive/reports/daily_capture_2026-06-22.md
```

**退出码含义**：
- `0` — 全部成功
- `2` — 部分失败（不影响程序正常运行，仍会生成报告）
- `3` — 全部失败（严重错误）
- `1` — 配置文件错误

---

## F. 查看归档结果

### 目录结构

```
data/wechat_live_smoke_archive/
  articles/
    2026/
      06/
        2026-06-22__公众号名__文章标题slug/
          article.md       ← Markdown 正文（推荐查看）
          article.html     ← 原始 HTML
          metadata.json    ← 完整元数据
          cover.jpg       ← 封面图（如有）
          images/         ← 正文内联图片
  index/
    articles.jsonl       ← 所有文章的 JSONL 索引
  state/
    seen_articles.sqlite ← SQLite 去重数据库
    run_log.jsonl        ← 运行日志
    failed_queue.jsonl   ← 失败队列（有待重试文章时）
  reports/
    daily_capture_2026-06-22.md  ← 日报
```

### 检查文章质量

```bash
# 查看归档了多少篇文章
ls data/wechat_live_smoke_archive/articles/2026/06/ | wc -l

# 打开一篇文章的 Markdown
cat "data/wechat_live_smoke_archive/articles/2026/06/2026-06-22__公众号名__文章标题/article.md"

# 查看元数据
cat "data/wechat_live_smoke_archive/articles/2026/06/2026-06-22__公众号名__文章标题/metadata.json"
```

**预期**：
- `article.md` 包含标题、公众号名、原文链接、发布时间、Markdown 正文
- `metadata.json` 包含 `article_id`、`title`、`url`、`canonical_url`、`published_at`、`captured_at`、`author`、`status`、`content_hash` 等字段

---

## G. 重复运行验证

再次执行归档，验证去重是否正常：

```bash
python -m opc_foundation.wechat.cli run \
  --config configs/wechat_live_smoke.local.yaml
```

**预期**：
- 所有文章被标记为 `重复跳过`
- `duplicate_count` 数字增加
- **不会**重复创建文章目录
- `articles.jsonl` 中不会出现重复 `canonical_url`

---

## H. 日报验证

### 查看当天日报

```bash
python -m opc_foundation.wechat.cli report \
  --archive-root ./data/wechat_live_smoke_archive
```

### 查看指定日期日报

```bash
python -m opc_foundation.wechat.cli report \
  --archive-root ./data/wechat_live_smoke_archive \
  --date 2026-06-22
```

**预期**：
- 日报只统计指定日期新增的文章，不混入历史记录
- 包含：总览、账号健康、新保存文章列表

---

## I. 失败重试

如果某些文章抓取失败（网络问题、正文提取失败等），它们会进入失败队列：

```bash
python -m opc_foundation.wechat.cli retry-failed \
  --archive-root ./data/wechat_live_smoke_archive
```

重试成功后：
- 失败条目从队列移除
- 文章正常保存到 `articles/`
- 日报中只显示本次重试结果，不混入历史失败

---

## J. 验收 Checklist

在完成以上步骤后，逐项检查：

```
[ ] dry-run 能发现候选文章（不是 0）
[ ] run 能保存真实文章（至少 1 篇）
[ ] article.md 可读，包含标题、正文、来源链接
[ ] article.html 存在
[ ] metadata.json 字段完整（article_id、status、content_hash 等）
[ ] articles.jsonl 有记录
[ ] seen_articles.sqlite 存在
[ ] run_log.jsonl 有 run_summary 条目
[ ] daily_capture 日报数字准确（与实际保存数一致）
[ ] 重复运行后 duplicate_count 正常增加
[ ] run_log.jsonl 中 run_summary 的 entry_type="run_summary"
[ ] 图片下载失败时不影响正文保存（正文仍正常归档）
[ ] 全程不需要 cookie / 微信登录 / 逆向 / 数据库访问
```

---

## K. 常见问题

### Q: feed 解析失败？

检查：
- we-mp-rss 服务是否正常运行
- `feed_url` 是否正确（浏览器打开能看到 XML）
- 网络是否可达（Windows 防火墙）

### Q: 文章正文提取为空（partial）？

可能原因：
- we-mp-rss 返回的文章 HTML 结构与预期不同
- 文章是纯图片消息（无文字内容）

解决方法：
- 查看 `state/failed_queue.jsonl` 中的 `error` 字段
- 可以用 `retry-failed` 重试
- 后续可在账号配置里调整 `clean_rules`

### Q: 图片下载失败？

- 检查网络是否能访问微信图片域名
- 图片失败不影响正文归档（只记 warning）
- 如果内网无法访问外网图片，可以把 `download_images: false`

### Q: 想只归档特定账号？

在 YAML 中把其他账号设为 `enabled: false`。

### Q: 如何清空重来？

删除归档目录：
```bash
rm -rf data/wechat_live_smoke_archive
```
`seen_articles.sqlite` 也会被清空，重新跑会重新归档所有文章。

---

## L. 下一步：Phase 1.7

Phase 1.6 验证通过后，可以考虑：

- **Phase 1.7：Downstream Integration Contract**
  - 定义内容生产 Agent / Demand Radar 如何以只读方式消费 `wechat_archive/index/articles.jsonl` 和 `articles/**/metadata.json`
  - 定义 metadata 中的 `status`、`content_hash`、`account_name` 等字段的契约

- **业务系统接入**
  - 在 Demand Radar 中定期调用 `WeChatArchiver(config).run()`
  - 用 `articles.jsonl` 做增量内容输入
  - 用 `metadata.json` 中的 `tags` 做分类过滤
