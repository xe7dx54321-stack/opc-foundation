# Official Filing Foundation Production Readiness Summary

## 1. 执行摘要

Official Filing Foundation 已达到 **Production Trial Ready** 状态，但存在已知限制。

### Ready for Production Trial

| Source | Status | 说明 |
|--------|--------|------|
| SEC EDGAR | ✅ ready | 真实 HTTP fetch 正常 |
| CNINFO | ✅ ready | 真实 HTTP POST 正常 |

### Limited

| Source | Status | 说明 |
|--------|--------|------|
| HKEXnews | ⚠️ degraded | 客户端渲染限制，无静态数据 |

### 最终判断

> **Official Filing Foundation is Production Trial Ready with SEC/CNINFO live success and HKEX degraded due to client-side rendering.**

---

## 2. 什么是 Ready

### Ready 的模块和功能

- ✅ FilingSourceConfig（源配置）
- ✅ FilingCandidate（候选披露）
- ✅ NormalizedFiling（标准化披露）
- ✅ FilingSourceHealth（源健康状态）
- ✅ SEC connector 真实 HTTP fetch
- ✅ CNINFO connector 真实 HTTP POST
- ✅ HKEX connector fail-soft degraded 处理
- ✅ filings.jsonl（全量索引）
- ✅ filings.latest.jsonl（最新快照）
- ✅ source_health.jsonl（健康状态历史）
- ✅ failed_queue.jsonl（失败队列）
- ✅ run_log.jsonl（运行日志）
- ✅ metadata sidecars（元数据文件）
- ✅ 中文日报
- ✅ CLI 命令（validate-config/dry-run/run/source-health/report/retry-failed）
- ✅ PowerShell run/check 脚本
- ✅ production example config

---

## 3. Production Trial 输入

### 推荐本地配置

```
configs/official_filings.production.local.yaml
```

**不要将本地配置提交到 git。**

### 推荐的 Pilot 配置

```yaml
# SEC EDGAR：1-2 个发行人，max_items <= 5
sources:
  - source_id: "pilot_sec_apple"
    source_type: "sec_edgar"
    endpoint_url: "https://data.sec.gov/submissions/CIK0000320193.json"
    enabled: true
    max_items: 5

# CNINFO：1-2 个股票代码或小日期范围，max_items <= 5
  - source_id: "pilot_cninfo"
    source_type: "cninfo_announcement"
    enabled: true
    max_items: 5

# HKEXnews：保持 disabled，直到确认有静态官方端点
  - source_id: "pilot_hkex"
    source_type: "hkex_announcement"
    enabled: false
```

---

## 4. Downstream Consumption Contract

### 下游系统应消费的输出

| 文件 | 说明 | 消费方式 |
|------|------|----------|
| `index/filings.jsonl` | 全量披露索引（追加写） | 定期轮询 |
| `index/filings.latest.jsonl` | 最新状态快照（覆盖写） | **推荐直接读取** |

### 下游可使用的字段

Foundation 提供以下标准化字段：

```
source_id, source_type, market, jurisdiction,
issuer_name, issuer_code,
filing_type, filing_title, filing_date,
source_url, document_url, pdf_url, html_url,
canonical_key, content_hash,
metadata_path, extraction_quality,
raw_entry
```

### 下游必须自行实现的逻辑

以下逻辑**不属于 Foundation**，由下游业务系统实现：

```
- ticker mapping（股票代码映射）
- importance scoring（重要性评分）
- watchlist filtering（关注列表过滤）
- expectation comparison（预期对比）
- valuation impact（估值影响）
- risk interpretation（风险解读）
- report generation（报告生成）
- investment judgment（投资判断）
```

**Foundation 不做投资判断。**

---

## 5. 操作清单

首次生产试运行建议按顺序执行：

1. **validate-config** — 校验配置文件
2. **dry-run** — 试运行，验证候选发现
3. **run** — 正式运行
4. **check script** — 检查输出文件
5. **source-health** — 查看 source 健康状态
6. **source-health --format json** — JSON 格式检查
7. **report** — 生成/查看日报
8. **duplicate run** — 验证去重正常
9. **retry-failed** — 检查失败队列
10. **确认 local config/data 未被提交** — 最后一步

---

## 6. 已知限制

### HKEXnews 客户端渲染问题

HKEX 目前返回的页面中，公告数据通过 JavaScript 动态加载，静态 HTML 解析器无法获取。

**当前状态：**

```
status: degraded
last_error: empty_source
```

**不要将其标记为 healthy**，直到发现可达的静态端点。

**不推荐方案：**

- ❌ 在 foundation 层添加浏览器自动化
- ❌ 使用无头浏览器抓取

**推荐方案：**

- 🔍 寻找港交所官方静态 API（如果有）
- 🔍 使用官方可下载的元数据文件（如果有）
- 🔍 保持 degraded 状态，直到确认有公开静态端点

### PDF 处理

- PDF URL 和元数据可以被记录
- 默认不下载 PDF 本体（download_pdfs=false）
- OCR 超出范围

---

## 7. 最终决策

### Production Trial Ready 判断

```
Official Filing Foundation is Production Trial Ready
with SEC/CNINFO live success and HKEX degraded due to client-side rendering.
```

### 边界确认

| 功能 | 状态 | 说明 |
|------|------|------|
| 投资判断 | ❌ 不支持 | 违反 foundation 边界 |
| 浏览器自动化 | ❌ 不支持 | 无单独批准不添加 |
| OCR | ❌ 不支持 | 超出范围 |
| 批量 PDF 下载 | ❌ 默认禁用 | download_pdfs=false |
| Cookie/Token | ❌ 不支持 | 公开数据源优先 |
| 验证码绕过 | ❌ 不支持 | 违反使用条款 |

### 建议的下一步

```
M2: Document Extraction Foundation
```

在 M2 中可以考虑：

- PDF 正文文本提取
- HTML 正文文本抽取
- 结构化字段增强
- 更多披露源接入

---

## 8. 相关文档

- [Live Smoke Registry](./official_filing_live_smoke_registry.md)
- [Official Filing Foundation 主文档](./official_filing_foundation.md)
- [生产运行指南](./official_filing_production_run.md)
