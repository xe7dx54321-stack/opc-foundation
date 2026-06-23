# Document Extraction Foundation

## Production Trial Status

**Status: Production Trial Ready for local/public documents with OCR disabled.**

已验证：本地 PDF / HTML / TXT / Markdown 全链路可运行，fail-soft 设计完整，source health 语义正确。

详细说明见：
- [Live Smoke Registry](document_extraction_live_smoke_registry.md)
- [Production Readiness](document_extraction_production_readiness.md)

## 模块目标

Document Extraction Foundation 为 `opc-foundation` 提供**通用公开文档抽取基础设施**，用于服务：

- CNINFO 公告 PDF
- HKEX 公告 PDF metadata
- SEC filing exhibits
- 公司 IR presentation
- 公开白皮书
- 公开行业报告
- 公开政策文件
- 本地用户提供文档

**核心原则**：

```
Foundation 提供基础设施；
业务系统保留判断力。
```

## 支持文档类型

| 类型 | 扩展名 | 描述 |
|------|--------|------|
| PDF | .pdf | 便携文档格式 |
| HTML | .html, .htm | 超文本标记语言 |
| Text | .txt | 纯文本文件 |
| Markdown | .md, .markdown | Markdown 文档 |

## 边界

### 禁止事项（绝对不允许）

```
1. 不修改 th_capital_stock
2. 不访问真实外部网站
3. 不下载远程 PDF
4. 不批量抓研报
5. 不处理付费研报
6. 不处理疑似泄露报告包
7. 不绕过登录 / paywall / captcha
8. 不保存 cookie/token
9. 不引入浏览器自动化
10. 不做 OCR
11. 不做 LLM 摘要
12. 不做投资判断
13. 不做 ticker impact
14. 不做 watchlist mapping
15. 不做 trade signal
16. 不提交 data/
17. 不提交 local config
18. 不提交 secrets
19. 不打 tag
```

### 允许事项

```
1. 处理 fixture PDF / HTML / TXT / MD
2. 处理本地用户提供文档
3. 记录 PDF metadata
4. 提取 PDF 文本
5. 生成 markdown
6. 记录 extraction_quality
7. 记录 failed_queue
8. 使用现有依赖
```

## 数据模型

### DocumentExtractionConfig

单个文档源的配置。

| 字段 | 类型 | 描述 |
|------|------|------|
| source_id | str | 稳定唯一 ID |
| source_name | str | 人类可读名称 |
| source_type | str | 文档类型 |
| input_path | str | 输入目录路径 |
| input_glob | str | 文件匹配模式 |
| enabled | bool | 是否启用 |
| legal_profile | str | 合规档案 |
| max_documents | int | 最大文档数 |
| save_raw | bool | 保存原始文件 |
| save_markdown | bool | 保存 markdown |
| save_metadata | bool | 保存元数据 |
| extract_text | bool | 提取文本 |
| ocr_enabled | bool | OCR 启用（默认 false） |

### ExtractedDocument

抽取后的标准文档（核心输出）。

| 字段 | 类型 | 描述 |
|------|------|------|
| document_id | str | 文档 ID |
| source_id | str | 源 ID |
| source_type | str | 源类型 |
| document_title | str | 文档标题 |
| original_path | str | 原始路径 |
| page_count | int | 页数 |
| char_count | int | 字符数 |
| word_count | int | 词数 |
| content_hash | str | 内容哈希 |
| document_hash | str | 文档哈希 |
| canonical_key | str | 规范化 key |
| extraction_quality | str | 抽取质量 |
| extraction_status | str | 抽取状态 |

### extraction_quality 取值

| 值 | 描述 |
|------|------|
| high | 字符数 >= 5000 |
| medium | 1000 <= 字符数 < 5000 |
| low | 0 < 字符数 < 1000 |
| empty | 字符数 == 0 |
| failed | 抽取失败 |

### extraction_status 取值

| 值 | 描述 |
|------|------|
| success | 成功抽取 |
| partial | 部分成功 |
| failed | 抽取失败 |
| skipped | 被跳过 |

## 目录结构

```
data/document_extraction/
  raw/                   # 原始文件副本
  text/                  # 纯文本版本
  markdown/              # markdown 版本
  metadata/              # 元数据 sidecar
  index/
    documents.jsonl          # 所有文档索引（全量）
    documents.latest.jsonl   # 最新抽取的文档索引
    source_health.jsonl      # 源健康状态
    failed_queue.jsonl        # 失败队列
    run_log.jsonl             # 运行日志
  reports/
    YYYY-MM-DD_document_extraction_report.md
```

## CLI

### validate-config

验证配置文件：

```bash
python -m opc_foundation.document_extraction.cli validate-config \
  --config configs/document_extraction.example.yaml
```

### dry-run

试运行（不写归档）：

```bash
python -m opc_foundation.document_extraction.cli dry-run \
  --config configs/document_extraction.example.yaml
```

### run

正式运行：

```bash
python -m opc_foundation.document_extraction.cli run \
  --config configs/document_extraction.example.yaml
```

### source-health

查看源健康状态：

```bash
python -m opc_foundation.document_extraction.cli source-health \
  --archive-root data/document_extraction

python -m opc_foundation.document_extraction.cli source-health \
  --archive-root data/document_extraction --format json

python -m opc_foundation.document_extraction.cli source-health \
  --archive-root data/document_extraction --source-id example_local_documents
```

### report

查看日报：

```bash
python -m opc_foundation.document_extraction.cli report \
  --archive-root data/document_extraction --date 2024-01-01
```

### retry-failed

重试失败队列：

```bash
python -m opc_foundation.document_extraction.cli retry-failed \
  --archive-root data/document_extraction
```

## Source Health

### Health Status

| 状态 | 描述 |
|------|------|
| healthy | 正常运行，failed_count = 0 |
| degraded | 部分问题（partial/failed/warnings） |
| failed | connector/read/parse 失败 |
| disabled | 配置中 enabled=false |
| unknown | 尚未运行 |

### 计算规则

```
1. enabled=True 但 candidate_count=0 → degraded（empty_source）
2. enabled=True 且 candidate_count>0 → 按 compute_health_status 结果
3. enabled=False → disabled
```

## Failed Queue

失败的文档会记录到 `failed_queue.jsonl`，包含：

- source_id
- source_type
- document_title
- original_path
- failed_at
- error
- error_type
- retry_count

## Downstream Contract

下游消费者应从以下入口读取数据：

```
data/document_extraction/index/documents.jsonl
data/document_extraction/index/documents.latest.jsonl
```

## 不做 OCR

OCR 功能默认关闭（`ocr_enabled: false`），本阶段不实现。

原因：
- OCR 依赖重型模型
- 增加复杂性
- 不符合 MVP 原则

## 不做投资判断

本模块**绝对不包含**以下字段：

```
affected_tickers
expectation_delta
investment_rating
trade_signal
watchlist
action_decision
recommendation
opportunity_score
risk_score
position_size
target_price
```

## 与 Official Filings 的关系

Document Extraction Foundation 是 Official Filings Foundation 的基础设施补充：

- **Official Filings** 负责发现和抓取披露信息
- **Document Extraction** 负责抽取 PDF/HTML/TXT/MD 等文档内容

两者可以结合使用：
- Official Filings 发现披露 URL/HTML
- Document Extraction 抽取文档内容

## 禁止字段清单

以下字段**不得**出现在模型或标准输出中：

```
affected_tickers
expectation_delta
investment_rating
trade_signal
watchlist
action_decision
recommendation
opportunity_score
risk_score
position_size
target_price
```

这些字段只允许出现在禁止项说明文档中。
