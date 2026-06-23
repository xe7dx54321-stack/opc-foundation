# Document Extraction Foundation - Live Smoke Tests

## 概述

本文档记录 Document Extraction Foundation 的 **Live Smoke Tests**。

**重要**：本阶段只记录 fixture/local smoke，不记录真实网页。

## 测试环境

- 项目：opc-foundation
- 模块：document_extraction
- 测试数据：tests/document_extraction/fixtures/

## Fixture 测试

### PDF Fixture

| 测试 | 预期结果 | 状态 |
|------|----------|------|
| sample.pdf 成功抽取 | extraction_status=success, char_count>0 | ✅ |
| sample.pdf page_count 正确 | page_count >= 1 | ✅ |
| sample.pdf document_hash 稳定 | 多次计算相同 | ✅ |
| malformed.pdf fail-soft | extraction_status=failed, error_message 有值 | ✅ |

### HTML Fixture

| 测试 | 预期结果 | 状态 |
|------|----------|------|
| sample.html 成功抽取 | extraction_status=success, char_count>0 | ✅ |
| sample.html title 正确提取 | document_title 非空 | ✅ |
| sample.html content_hash 稳定 | 多次计算相同 | ✅ |

### TXT Fixture

| 测试 | 预期结果 | 状态 |
|------|----------|------|
| sample.txt 成功抽取 | extraction_status=success, char_count>0 | ✅ |
| sample.txt word_count 正确 | word_count > 0 | ✅ |
| sample.txt content_hash 稳定 | 多次计算相同 | ✅ |

### Markdown Fixture

| 测试 | 预期结果 | 状态 |
|------|----------|------|
| sample.md 成功抽取 | extraction_status=success, char_count>0 | ✅ |
| sample.md 去 markdown 语法后有文本 | char_count > 0 | ✅ |
| sample.md content_hash 稳定 | 多次计算相同 | ✅ |

## 重复运行测试

| 测试 | 预期结果 | 状态 |
|------|----------|------|
| 第二次运行检测到重复 | duplicate_count > 0 | ✅ |
| documents.latest.jsonl 更新 | 最新运行结果在文件中 | ✅ |

## Failed Queue 测试

| 测试 | 预期结果 | 状态 |
|------|----------|------|
| malformed.pdf 进入 failed_queue | failed_queue.jsonl 有记录 | ✅ |
| failed_queue 记录包含 error 信息 | error 和 error_type 非空 | ✅ |

## Health 状态测试

| 测试 | 预期结果 | 状态 |
|------|----------|------|
| enabled source 有候选 → healthy | status=healthy | ✅ |
| enabled source 无候选 → degraded | status=degraded | ✅ |
| disabled source → disabled | status=disabled | ✅ |

## 边界测试

| 测试 | 预期结果 | 状态 |
|------|----------|------|
| OCR 默认关闭 | ocr_enabled=false | ✅ |
| 不存在文件 fail-soft | extraction_status=failed | ✅ |
| 目录不存在 → 空候选 | candidate_count=0 | ✅ |

## 输出契约验证

| 测试 | 预期结果 | 状态 |
|------|----------|------|
| documents.jsonl 存在 | index/documents.jsonl 可读 | ✅ |
| documents.latest.jsonl 存在 | index/documents.latest.jsonl 可读 | ✅ |
| source_health.jsonl 存在 | index/source_health.jsonl 可读 | ✅ |
| failed_queue.jsonl 存在 | index/failed_queue.jsonl 可读 | ✅ |
| run_log.jsonl 存在 | index/run_log.jsonl 可读 | ✅ |

## 禁止字段验证

| 测试 | 预期结果 | 状态 |
|------|----------|------|
| 模型不包含 investment_rating | 字段不存在 | ✅ |
| 模型不包含 trade_signal | 字段不存在 | ✅ |
| 模型不包含 watchlist | 字段不存在 | ✅ |
| 模型不包含 target_price | 字段不存在 | ✅ |

## CLI 命令测试

| 命令 | 预期结果 | 状态 |
|------|----------|------|
| validate-config 有效配置 | exit_code=0 | ✅ |
| validate-config 无效配置 | exit_code!=0 | ✅ |
| dry-run 不写 documents | documents.jsonl 不变 | ✅ |
| source-health text 输出 | 可读的文本格式 | ✅ |
| source-health json 输出 | 有效的 JSON | ✅ |
| report 生成 | 报告文件存在 | ✅ |

## Registry

最新更新：2024-01-01

测试人员：OPC Foundation Team

状态：✅ All Tests Passed

## 历史

| 日期 | 更新内容 | 状态 |
|------|----------|------|
| 2024-01-01 | 初始 live smoke registry | ✅ |
