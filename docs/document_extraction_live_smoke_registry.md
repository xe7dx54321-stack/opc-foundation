# Document Extraction Foundation — Live Smoke Registry

## 1. Local Smoke 日期

- **日期**: 2026-06-23
- **版本**: M2 (Document Extraction Foundation)
- **Commit**: 9488b5a + production hardening
- **环境**: Windows 11 / Python 3.11 / PyMuPDF / beautifulsoup4
- **Fixture 来源**: `tests/document_extraction/fixtures/`

## 2. PDF / HTML / TXT / MD 结果

| 类型 | 样本 | 状态 | 抽取质量 | 页数 | 字符数 | 备注 |
|------|------|------|----------|------|--------|------|
| PDF | sample.pdf | ✅ success | medium | 2 | ~1194 | 正常抽取文本和 metadata |
| HTML | sample.html | ✅ success | medium | N/A | ~826 | 正常提取纯文本 |
| TXT | sample.txt | ✅ success | high | N/A | ~45 | 纯文本直接读取 |
| Markdown | sample.md | ✅ success | high | N/A | ~140 | Markdown 直接读取 |
| PDF (损坏) | malformed.pdf | ❌ failed | failed | N/A | N/A | 进入 failed_queue，fail-soft |

**汇总**: 4 success, 1 failed, 0 partial

## 3. Malformed PDF Fail-Soft

- **行为**: malformed.pdf 抽取失败后进入 `failed_queue.jsonl`，不拖垮全局运行
- **error_type**: `extractor_error`
- **错误信息**: PyMuPDF 读取失败
- **全局影响**: 其他 4 个文档正常抽取，仅该文档失败
- **重试支持**: retry-failed 命令可重试（但损坏文件仍会失败）

## 4. Saved / Partial / Failed / Duplicate

### 首次运行
- **Candidates**: 5
- **Saved**: 4
- **Partial**: 0
- **Failed**: 1 (malformed.pdf)
- **Duplicate**: 0

### 二次运行（duplicate run）
- **Candidates**: 5
- **Saved**: 0
- **Partial**: 0
- **Failed**: 1 (malformed.pdf)
- **Duplicate**: 4
- **验证**: 同一 canonical_key 的文档不会重复写入 documents.jsonl

## 5. Source Health 状态

| Source ID | 状态 | Last Error | Candidates | Saved | Failed |
|-----------|------|------------|------------|-------|--------|
| smoke_pdf_documents | ⚠️ degraded | 1 failed | 2 | 1 | 1 |
| smoke_html_documents | ✅ healthy | null | 1 | 1 | 0 |
| smoke_text_documents | ✅ healthy | null | 1 | 1 | 0 |
| smoke_markdown_documents | ✅ healthy | null | 1 | 1 | 0 |
| smoke_empty_source | ⚠️ degraded | empty_source | 0 | 0 | 0 |

**Health 语义验证**:
- ✅ enabled + candidates > 0 + no failures → healthy
- ✅ enabled + candidates > 0 + failed docs → degraded
- ✅ enabled + candidates = 0 → degraded + empty_source
- ✅ extractor exception → 单文档 failed，source 级别 degraded

## 6. OCR 默认关闭

- **默认配置**: `ocr_enabled: false`
- **配置验证**: 配置中 ocr_enabled=true 会被 validate-config 拒绝
- **代码层面**: 当前未实现 OCR 相关逻辑
- **表格抽取**: `extract_tables: false`（默认关闭）

## 7. 不支持 / 不做

- ❌ 不支持远程 PDF 下载
- ❌ 不支持付费研报抓取
- ❌ 不支持灰色报告包处理
- ❌ **不支持浏览器自动化 / Playwright / Selenium**：不做 JS 渲染，不模拟浏览器
- ❌ 不支持 OCR（当前版本）
- ❌ 不支持 LLM 摘要
- ❌ 不包含投资判断字段
- ❌ 不绕过 paywall / 登录 / captcha

## 8. Production Trial Ready 判断

### 已满足
- ✅ 本地 PDF / HTML / TXT / MD 全链路可运行
- ✅ fail-soft 设计（单文档失败不影响全局）
- ✅ 去重机制（canonical_key + document_hash）
- ✅ source health 语义完整
- ✅ CLI 命令齐全（validate-config / dry-run / run / source-health / report / retry-failed）
- ✅ 输出完整（documents.jsonl / source_health.jsonl / failed_queue.jsonl / reports / metadata / raw / text / markdown）
- ✅ OCR 默认关闭
- ✅ 无投资判断字段
- ✅ production scripts 齐全（PowerShell）

### 未满足 / 后续
- ⚠️ 仅支持本地文件，未接入官方披露网站（属于 M3+ 范围）
- ⚠️ retry-failed 为 MVP 实现（直接重跑所有 source）
- ⚠️ 无增量抽取机制（每次全量扫描）

**结论**: **Production Trial Ready for local/public documents with OCR disabled.**
