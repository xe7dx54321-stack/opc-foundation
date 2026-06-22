# 微信文章归档消费契约（WeChat Archive Consumer Contract）

> 适用版本：opc-foundation v0.1.5+
> 文档目的：定义"微信文章归档后，如何作为标准资产被下游系统安全、稳定、只读消费"。

---

## 1. 本契约目的

`opc-foundation` 的微信归档模块负责把微信公众号文章采集、去重、归档到本地目录。归档完成后，下游业务系统（如内容生产 Agent、需求雷达、投研 Agent 等）需要读取这些归档文章并做自己的业务处理。

本契约定义：

- 归档目录的输出结构
- 下游系统如何只读读取归档文章
- 下游系统如何记录自己的消费状态（per-consumer）
- foundation 与业务线的边界

**核心原则**：

> opc-foundation 只负责"文章作为标准资产怎么交付"。
> 业务线负责"文章是否有价值、如何分析、是否进入业务流程"。

---

## 2. foundation 与业务线边界

### foundation 负责

- 采集（从 RSS / WeRSS / 手工 URL）
- 归档（article.md / article.html / metadata.json）
- 去重（SQLite seen_articles.sqlite）
- 标准化输出（articles.jsonl）
- 读取契约（WeChatArchiveReader）
- 消费回执基础机制（ConsumerReceiptStore）
- 失败队列与重试（failed_queue.jsonl）
- 运行日志与日报（run_log.jsonl / daily_capture_*.md）

### foundation 不负责

- 判断文章有没有投资价值
- 判断文章有没有需求痛点
- 判断文章适不适合做公众号选题
- 判断文章应该进入哪个业务流程
- 判断文章应该生成什么结论
- 调度业务线（由业务线或外部 orchestrator 负责）

### 业务线负责

- 读取归档文章（通过 WeChatArchiveReader）
- 自己判断文章价值、分类、是否进入业务流程
- 写入自己的消费回执（通过 ConsumerReceiptStore）
- 自己的重试与调度逻辑

---

## 3. 归档输出目录结构

```
<archive_root>/
├── articles/
│   └── YYYY/MM/
│       └── YYYY-MM-DD__<account>__<title-slug>/
│           ├── article.md
│           ├── article.html
│           ├── metadata.json
│           └── images/                # 可选，正文内联图片
├── index/
│   └── articles.jsonl                 # 所有归档文章的索引（append-only）
├── state/
│   ├── seen_articles.sqlite           # foundation 内部去重用（不对外暴露）
│   ├── run_log.jsonl                  # 运行日志
│   ├── failed_queue.jsonl             # 失败队列
│   └── consumers/                     # 消费回执目录（per-consumer）
│       ├── content_agent.receipts.jsonl
│       ├── demand_radar.receipts.jsonl
│       └── investment_agent.receipts.jsonl
└── reports/
    └── daily_capture_YYYY-MM-DD.md    # 中文日报
```

**重要**：
- `state/seen_articles.sqlite` 是 foundation 内部去重用的，下游系统不要读取
- `state/consumers/` 下的 JSONL 文件是 per-consumer 隔离的，每个业务线一个文件
- 下游系统不要修改 `articles/`、`index/`、`state/seen_articles.sqlite`、`state/run_log.jsonl`、`state/failed_queue.jsonl`

---

## 4. articles.jsonl 字段说明

`index/articles.jsonl` 是所有归档文章的索引文件，每行一个 JSON 对象，append-only。

字段说明（与 `ArchivedArticle` 模型一致）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `article_id` | string | 文章唯一 ID（基于 canonical_url 的 sha256 前缀） |
| `source` | string | 来源描述（如 `rss:xxx` 或 `manual`） |
| `account_name` | string \| null | 公众号名字 |
| `account_id` | string \| null | 公众号 ID |
| `title` | string | 文章标题 |
| `url` | string | 原始 URL |
| `canonical_url` | string | 规范化 URL（去重 key） |
| `published_at` | string \| null | 发布时间（ISO 格式） |
| `captured_at` | string | 归档抓取时间（ISO 格式） |
| `author` | string \| null | 作者 |
| `digest` | string \| null | 摘要 |
| `content_hash` | string | 正文内容 hash（sha256 前 32 位） |
| `status` | string | 归档状态（saved / partial / duplicate / failed） |
| `archive_dir` | string | 该文章的归档目录路径 |
| `metadata_path` | string | metadata.json 的路径 |
| `markdown_path` | string \| null | article.md 的路径 |
| `html_path` | string \| null | article.html 的路径 |
| `cover_image_path` | string \| null | 封面图本地路径 |
| `image_count` | int | 下载成功的正文内联图片数量 |
| `error` | string \| null | 错误信息（仅 failed/partial 时非空） |

**注意**：`tags` 字段不在 `articles.jsonl` 中（tags 在 account 配置里）。如果下游需要按 tag 过滤，需要在 reader 调用时手动传入，或在自己的 consumer 系统中维护。

---

## 5. metadata.json 稳定字段说明

每篇文章的 `metadata.json` 包含 `articles.jsonl` 的全部字段，外加：

| 字段 | 类型 | 说明 |
|------|------|------|
| `image_urls` | list[string] | 正文中出现的图片 URL（去重后顺序列表） |
| `warnings` | list[string] | 归档过程中的警告信息（可选） |

`metadata.json` 是下游系统读取文章详情的稳定来源。

---

## 6. ArticleRef 字段说明

`ArticleRef` 是 `WeChatArchiveReader` 返回的只读视图数据结构。

```python
@dataclass(frozen=True)
class ArticleRef:
    article_id: str
    source: str
    account_name: str | None
    account_id: str | None
    title: str
    url: str
    canonical_url: str
    published_at: str | None
    captured_at: str
    status: str
    content_hash: str
    archive_dir: str
    metadata_path: str
    markdown_path: str | None
    html_path: str | None
    tags: list[str]                  # 默认空列表（articles.jsonl 中无此字段）
    raw_metadata: dict[str, Any]     # 完整原始 metadata dict
```

**设计要点**：
- `frozen=True`：实例不可变，避免下游误改
- `raw_metadata` 保留 `articles.jsonl` 行的完整 dict，便于下游读取扩展字段
- `tags` 默认空列表（articles.jsonl 中无此字段，保留是为了未来扩展）

---

## 7. ConsumerReceipt 字段说明

`ConsumerReceipt` 是 `ConsumerReceiptStore` 写入和返回的消费回执数据结构。

```python
@dataclass(frozen=True)
class ConsumerReceipt:
    consumer: str                    # 业务消费者名称
    article_id: str                  # 文章唯一 ID
    canonical_url: str | None        # 辅助追踪
    content_hash: str | None         # 辅助检测内容变化
    status: str                      # consumed / skipped / failed
    received_at: str                 # 回执写入时间（ISO 格式）
    reason: str | None               # 可读原因
    decision: str | None             # 业务判断（opaque，foundation 不解释）
    metadata: dict[str, Any]         # 业务自定义信息（opaque）
```

**status 字段**（foundation 只识别这三种通用状态）：
- `consumed`：已消费（业务线成功处理）
- `skipped`：已跳过（业务线主动决定不处理）
- `failed`：消费失败（业务线尝试处理但失败）

**decision 字段**（opaque）：
- 业务线自己的业务判断，例如 `selected_for_topic` / `investment_signal_high`
- foundation 不解释、不校验内容，只保存

**metadata 字段**（opaque）：
- 业务线可写入任何自定义信息
- foundation 只保存，不解释

---

## 8. per-consumer receipt 为什么不能做全局 consumed

**错误设计**（不要这么做）：
```json
{
  "article_id": "wc_xxx",
  "consumed": true
}
```

**问题**：同一篇文章可能被多个业务系统分别消费。例如：
- `content_agent` 把它选为公众号选题素材
- `demand_radar` 把它作为需求信号来源
- `investment_agent` 把它作为投研证据

如果用全局 `consumed=true`，第一个 consumer 标记后，其他 consumer 就看不到这篇文章了。

**正确设计**（per-consumer）：
```json
{
  "consumer": "content_agent",
  "article_id": "wc_xxx",
  "status": "consumed",
  "consumed_at": "2026-06-22T10:00:00"
}
```

每个 consumer 独立记录自己的消费状态，互不影响。

---

## 9. 下游系统如何读取未消费文章

使用 `list_unconsumed_articles` 函数：

```python
from opc_foundation.wechat.consumer import (
    WeChatArchiveReader,
    ConsumerReceiptStore,
    list_unconsumed_articles,
)

reader = WeChatArchiveReader("./data/wechat_archive")
store = ConsumerReceiptStore("./data/wechat_archive", consumer="content_agent")

# 返回 content_agent 还没消费过的 saved 文章
articles = list_unconsumed_articles(
    reader,
    store,
    status="saved",
    captured_since="2026-06-22",
    limit=50,
)

for article in articles:
    # 下游业务系统自己做判断
    # foundation 不参与判断
    store.mark_consumed(article, decision="example_decision")
```

**重要**：
- `list_unconsumed_articles` 只按当前 consumer 的 receipt 判断
- `content_agent` consume 过的文章，不影响 `demand_radar` 的未消费列表
- 如果某篇文章被 `mark_failed`，它也会被视为"已处理"（不再出现在 unconsumed 列表）
  - 如果业务线想重试 failed 的文章，可以新建一个 consumer 或自行管理

---

## 10. 业务线示例

### content_agent（内容生产 Agent）

```python
from opc_foundation.wechat.consumer import (
    WeChatArchiveReader,
    ConsumerReceiptStore,
    list_unconsumed_articles,
)

reader = WeChatArchiveReader("./data/wechat_archive")
store = ConsumerReceiptStore("./data/wechat_archive", consumer="content_agent")

articles = list_unconsumed_articles(reader, store, status="saved")

for article in articles:
    # 读取正文
    md_text = reader.read_markdown(article)

    # 业务判断（foundation 不参与）
    if _is_good_topic(md_text):
        store.mark_consumed(article, decision="selected_for_topic")
        _generate_article(md_text)
    else:
        store.mark_skipped(article, decision="no_pain_signal")
```

### demand_radar（需求雷达）

```python
reader = WeChatArchiveReader("./data/wechat_archive")
store = ConsumerReceiptStore("./data/wechat_archive", consumer="demand_radar")

articles = list_unconsumed_articles(reader, store, status="saved")

for article in articles:
    md_text = reader.read_markdown(article)
    signal = _extract_demand_signal(md_text)

    if signal:
        store.mark_consumed(
            article,
            decision="demand_signal_found",
            metadata={"signal_strength": signal.strength},
        )
        _push_to_demand_queue(signal)
    else:
        store.mark_skipped(article, decision="no_demand_signal")
```

### investment_agent（投研 Agent）

```python
reader = WeChatArchiveReader("./data/wechat_archive")
store = ConsumerReceiptStore("./data/wechat_archive", consumer="investment_agent")

articles = list_unconsumed_articles(reader, store, status="saved")

for article in articles:
    md_text = reader.read_markdown(article)
    score = _score_investment_value(md_text)

    if score > 0.7:
        store.mark_consumed(
            article,
            decision="investment_signal_high",
            metadata={"score": score},
        )
        _add_to_research_queue(article, score)
    else:
        store.mark_skipped(article, decision="low_score")
```

---

## 11. 不允许业务线修改 archive 原始文件

下游业务系统**不允许**修改以下文件：

- `articles/YYYY/MM/*/article.md`
- `articles/YYYY/MM/*/article.html`
- `articles/YYYY/MM/*/metadata.json`
- `articles/YYYY/MM/*/images/*`
- `index/articles.jsonl`
- `state/seen_articles.sqlite`
- `state/run_log.jsonl`
- `state/failed_queue.jsonl`
- `reports/*.md`

业务线**只能**写入：
- `state/consumers/<consumer>.receipts.jsonl`（自己的回执文件）

如果业务线需要保存自己的处理结果（如生成的选题、需求信号、投研报告），请使用业务线自己的存储，不要写回归档目录。

---

## 12. 不允许 foundation 判断文章价值

foundation 的代码中**不会**出现以下逻辑：

- 关键词筛选策略
- 文章价值评分
- LLM 判断
- 业务分类
- 是否进入业务流程的决策

foundation 只识别三种通用消费状态：`consumed` / `skipped` / `failed`。

业务判断（如 `selected_for_topic` / `investment_signal_high`）只能作为 `ConsumerReceipt.decision` 字段的 opaque 值保存，foundation 不解释。

---

## 13. 调度由业务线或外部 orchestrator 负责

foundation **不负责**：

- 定时触发业务线消费
- 协调多个 consumer 的执行顺序
- 重试业务线的失败处理

业务线的调度应由：

- 业务线自己的定时任务
- 外部 orchestrator（如 cron / Airflow / Prefect）
- 业务线自己的事件订阅

负责。

foundation 只提供"读取未消费文章"和"写入消费回执"的基础能力。

---

## 14. 示例代码

### 完整消费流程

```python
from opc_foundation.wechat.consumer import (
    WeChatArchiveReader,
    ConsumerReceiptStore,
    list_unconsumed_articles,
)

# 1. 初始化 reader 和 store
reader = WeChatArchiveReader("./data/wechat_archive")
store = ConsumerReceiptStore("./data/wechat_archive", consumer="content_agent")

# 2. 读取未消费文章（只读 saved 状态）
articles = list_unconsumed_articles(
    reader,
    store,
    status="saved",
    captured_since="2026-06-22",
    limit=50,
)

print(f"共 {len(articles)} 篇未消费文章")

# 3. 逐篇处理
for article in articles:
    print(f"处理: {article.title}")

    # 读取正文
    md_text = reader.read_markdown(article)
    if md_text is None:
        store.mark_failed(article, reason="markdown 读取失败")
        continue

    # 业务判断（foundation 不参与）
    try:
        decision = _my_business_logic(md_text)
        store.mark_consumed(
            article,
            decision=decision,
            metadata={"processed_at": "2026-06-22T10:00:00"},
        )
    except Exception as e:
        store.mark_failed(article, reason=str(e))
```

### 查询某 consumer 的消费历史

```python
store = ConsumerReceiptStore("./data/wechat_archive", consumer="content_agent")

# 列出所有回执（包含历史）
receipts = store.list_receipts()
for r in receipts:
    print(f"{r.article_id} {r.status} {r.received_at} {r.decision}")

# 查询某文章的最新回执
receipt = store.get_receipt("wc_xxx")
if receipt:
    print(f"最新状态: {receipt.status}")

# 判断是否有回执
if store.has_receipt("wc_xxx"):
    print("已处理过")
```

### CLI 使用

```bash
# 列出归档文章
python -m opc_foundation.wechat.cli list-articles \
  --archive-root ./data/wechat_archive \
  --status saved \
  --limit 10

# 列出某 consumer 的未消费文章
python -m opc_foundation.wechat.cli list-unconsumed \
  --archive-root ./data/wechat_archive \
  --consumer content_agent \
  --limit 10

# 标记某文章为已消费
python -m opc_foundation.wechat.cli mark-consumed \
  --archive-root ./data/wechat_archive \
  --consumer content_agent \
  --article-id wc_xxx \
  --decision example_decision

# 标记为跳过
python -m opc_foundation.wechat.cli mark-consumed \
  --archive-root ./data/wechat_archive \
  --consumer content_agent \
  --article-id wc_xxx \
  --status skipped \
  --reason "不相关"
```

---

## 15. consumer 名称规范

consumer 名称会直接作为文件名（`<consumer>.receipts.jsonl`），所以有严格限制：

- 只允许小写字母、数字、下划线（`_`）、短横线（`-`）
- 必须以字母或数字开头
- 长度 1-64 字符
- 不能包含 `..` 或路径分隔符

**合法名称示例**：
- `content_agent`
- `demand_radar`
- `investment_agent`
- `topic-bot-1`

**非法名称示例**：
- `Content Agent`（含空格、大写）
- `../etc/passwd`（路径穿越）
- `消费者`（中文）
- `` （空字符串）

如果名称不合法，`ConsumerReceiptStore` 会抛出 `ValueError`。

---

## 16. append-only 与历史审计

`ConsumerReceiptStore` 采用 append-only 设计：

- 同一篇文章多次 `mark_consumed` / `mark_skipped` / `mark_failed`，每次都会追加一条新记录
- `get_receipt(article_id)` 返回该文章的**最新**一条回执
- `has_receipt(article_id)` 基于最新回执判断
- `list_receipts()` 返回全部历史记录（按写入顺序）

**为什么 append-only**：
- 便于审计：可以追溯某篇文章的消费状态变化历史
- 不丢数据：即使误操作标记，历史记录仍在
- 简化实现：无需 in-place 更新

---

## 17. 版本与兼容性

本契约从 opc-foundation v0.1.5 开始提供。

未来版本可能：
- 增加 ArticleRef 字段（向后兼容）
- 增加 ConsumerReceipt 字段（向后兼容）
- 增加新的通用 status（不删除现有 status）

不会：
- 删除现有字段
- 改变现有字段语义
- 改变文件路径结构（除非重大版本升级）
