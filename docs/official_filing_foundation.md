# Official Filing Foundation

## 一、模块目标

Official Filing Foundation 是 OPC Foundation 中负责**官方披露/公告归档**的基础模块。

它提供从各国证券监管机构官方平台采集、标准化、归档上市公司披露公告的基础设施能力。

**核心原则：Foundation 提供基础设施；业务系统保留判断力。**

本模块只做：

- 发现官方披露源的公告列表
- 标准化公告元数据（发行方、日期、类型、标题、URL 等）
- 本地归档存储（原始响应、HTML、PDF 元数据等）
- 去重（canonical_key / content_hash）
- Source Health 监控
- 失败队列与重试
- 日报生成

本模块**不做**：

- 投资判断（利好/利空/超预期）
- Ticker impact 分析
- 估值影响评估
- 交易信号生成
- Watchlist mapping
- 任何形式的投资建议

---

## 二、边界与约束

### 2.1 硬性边界

| 类别 | 约束 |
|------|------|
| 数据源 | 仅官方公开披露源，不使用 vendor/API/licensed 数据 |
| 访问方式 | 公开 HTTP/HTTPS，不使用 cookie/token，不绕过登录/paywall |
| 业务逻辑 | 不包含任何投资判断逻辑 |
| 数据范围 | 只保存元数据和公开可访问的原始内容 |
| 外部依赖 | 不引入 akshare、iFinD、浏览器自动化、OCR |

### 2.2 禁止字段

以下字段**不得**进入模型或标准输出：

- `affected_tickers`
- `expectation_delta`
- `investment_rating`
- `trade_signal`
- `watchlist`
- `action_decision`
- `recommendation`
- `opportunity_score`
- `risk_score`
- `position_size`
- `target_price`

> 注：这些字段可以出现在文档的"禁止项说明"中，但不能成为 model/schema/output 字段。

---

## 三、支持的 source_type

### 3.1 已实现（MVP）

| source_type | 名称 | 市场 | 司法辖区 | 数据来源 |
|-------------|------|------|----------|----------|
| `sec_edgar` | SEC EDGAR | US | US | 美国证监会 EDGAR 系统 submissions JSON |
| `cninfo_announcement` | CNINFO 巨潮资讯 | CN | CN | 巨潮资讯公告查询 API |
| `hkex_announcement` | HKEXnews 港交所披露易 | HK | HK | 港交所披露易公告列表 |

### 3.2 数据模型

每个 source 产出统一的 `FilingCandidate`，然后标准化为 `NormalizedFiling`。

核心字段说明：

- `issuer_code`：发行方代码（CIK / 股票代码等），foundation **不解释**其投资含义
- `filing_type`：披露类型（10-K / 年度报告 / 业绩公告 等）
- `filing_date`：披露日期（YYYY-MM-DD）
- `accession_number` / `announcement_id`：源平台的唯一标识
- `canonical_key`：去重用的标准化 key
- `content_hash`：内容哈希，用于检测更新

---

## 四、目录结构

```
data/official_filings/
  raw/                    # 原始响应（按 source_type 分子目录）
    sec/
    cninfo/
    hkex/
  html/                   # HTML 版本（可选）
  pdf_metadata/           # PDF 元数据（可选，不下载 PDF 本体）
  metadata/               # 每个 filing 的元数据 sidecar JSON
  index/
    filings.jsonl         # 全量披露索引（追加写）
    filings.latest.jsonl  # 最新状态快照（覆盖写）
    source_health.jsonl   # source 健康状态历史
    failed_queue.jsonl    # 失败队列
    run_log.jsonl         # 运行日志
  reports/                # 日报（Markdown）
```

---

## 五、数据模型

### 5.1 FilingSourceConfig

单个披露源的配置。

关键字段：`source_id`, `source_type`, `enabled`, `legal_profile`, `max_items`, `filing_types`, `issuer_filter`, `date_from`, `date_to`

### 5.2 FilingCandidate

Connector 输出的候选披露。

关键字段：`source_id`, `source_type`, `issuer_name`, `issuer_code`, `filing_type`, `filing_title`, `filing_date`, `accession_number`, `announcement_id`, `document_url`, `pdf_url`, `html_url`

### 5.3 NormalizedFiling

归档后的标准化披露（核心输出）。

关键字段：`filing_id`, `canonical_key`, `content_hash`, `status`（saved/duplicate/partial/failed/skipped）, `metadata_path`, `raw_path`, `html_path`, `pdf_metadata_path`

### 5.4 FilingSourceHealth

Source 健康状态。

`status` 取值：`healthy` / `degraded` / `failed` / `disabled` / `unknown`

---

## 六、CLI 命令

```bash
# 校验配置
python -m opc_foundation.official_filings.cli validate-config --config configs/official_filings.local.yaml

# 试运行（只发现，不写归档）
python -m opc_foundation.official_filings.cli dry-run --config configs/official_filings.local.yaml

# 正式运行
python -m opc_foundation.official_filings.cli run --config configs/official_filings.local.yaml

# 查看 source health
python -m opc_foundation.official_filings.cli source-health --archive-root data/official_filings
python -m opc_foundation.official_filings.cli source-health --archive-root data/official_filings --format json

# 查看日报
python -m opc_foundation.official_filings.cli report --archive-root data/official_filings --date 2024-01-15

# 重试失败
python -m opc_foundation.official_filings.cli retry-failed --archive-root data/official_filings
```

---

## 七、Source Health

每个 source 都有健康状态，记录在 `index/source_health.jsonl` 中。

### 状态判定规则

| 状态 | 条件 |
|------|------|
| `healthy` | 最近运行成功，失败数为 0 |
| `degraded` | 能 discover 或部分保存，但存在 partial/failed |
| `failed` | connector 失败、连续失败 >= 3 次 |
| `disabled` | 配置中 `enabled=false` |
| `unknown` | 尚未运行过 |

### 监控字段

- `consecutive_failures`：连续失败次数
- `candidate_count_last_run`：上次运行候选数
- `saved_count_last_run`：上次运行保存数
- `failed_count_last_run`：上次运行失败数
- `last_error` / `last_error_type`：最近错误信息与类型

---

## 八、Failed Queue

失败的披露会写入 `index/failed_queue.jsonl`。

每条记录包含：`source_id`, `filing_title`, `document_url`, `canonical_key`, `error`, `error_type`, `retryable`, `retry_count`, `run_id`

使用 `retry-failed` 命令重试（MVP 版本：重新运行全量 run）。

---

## 九、下游消费契约

### 9.1 核心输出文件

| 文件 | 写入方式 | 说明 |
|------|----------|------|
| `index/filings.jsonl` | 追加 | 全量披露索引，每条状态变化都会追加 |
| `index/filings.latest.jsonl` | 覆盖 | 最新状态快照，下游直接读这个即可 |
| `index/source_health.jsonl` | 追加 | Source 健康状态历史 |
| `index/failed_queue.jsonl` | 追加 | 失败队列 |
| `reports/daily_filing_YYYY-MM-DD.md` | 覆盖 | 每日日报 |

### 9.2 消费建议

1. **定期轮询** `filings.latest.jsonl` 获取最新披露
2. **按 source_type 过滤**：只关心美股就过滤 `source_type=sec_edgar`
3. **按 filing_type 过滤**：只看年报就过滤 `filing_type=10-K` / `年度报告`
4. **按 issuer_code 过滤**：只关注特定公司
5. **结合业务逻辑**：在你的业务系统中做投资判断，不要修改 foundation 代码

### 9.3 重要提醒

> **Foundation 只提供归档和元数据，不做投资判断。**
>
> 下游业务系统自行决定如何使用这些披露信息。
> 任何投资判断（利好/利空/超预期/买卖建议）都应在业务层实现，不应污染 foundation 层。

---

## 十、与 th_capital_stock 的关系

- **本模块是 foundation 层**：提供通用的官方披露归档能力
- **th_capital_stock 是业务系统**：消费 foundation 的输出，加入业务判断
- **不直接迁移业务逻辑**：迁移的是基础设施，不是投研判断
- **th_capital_stock 后续可接入**：作为下游消费者使用本模块的输出

---

## 十一、扩展方向

未来可扩展的方向（不在 MVP 范围内）：

1. **更多披露源**：上交所、深交所、新加坡交易所等
2. **正文提取**：从 PDF/HTML 中提取正文文本
3. **结构化字段**：从年报中提取财务数据（XBRL 解析等）
4. **增量同步**：基于 date_from/date_to 的增量抓取
5. **真实网络抓取**：MVP 仅支持 fixture，后续可加真实 HTTP fetcher


---

## 十三、Production Trial Status

Official Filing Foundation 在 M1 阶段完成 live smoke 验证后，已达到 **Production Trial Ready** 状态。

### Source 状态

| Source | Source Type | Status | 说明 |
|--------|-------------|--------|------|
| SEC EDGAR | sec_edgar | ✅ ready | 真实 HTTP fetch 正常 |
| CNINFO | cninfo_announcement | ✅ ready | 真实 HTTP POST 正常 |
| HKEXnews | hkex_announcement | ⚠️ degraded | 客户端渲染限制，无静态数据 |

### Health 语义规则

```text
enabled + candidate_count = 0 → degraded + empty_source
```

这确保不会对可达但无数据的 source 误标为 healthy。

### 相关文档

- [Live Smoke Registry](./official_filing_live_smoke_registry.md)
- [Production Readiness Summary](./official_filing_production_readiness.md)
- [生产运行指南](./official_filing_production_run.md)
- [Live Smoke 报告](./official_filing_live_smoke.md)

### M1 完成状态

```
M1: Official Filing Foundation ✅ Production Trial Ready
- SEC EDGAR: ready
- CNINFO: ready
- HKEXnews: degraded (limitation documented)

Next: M2 Document Extraction Foundation
```
