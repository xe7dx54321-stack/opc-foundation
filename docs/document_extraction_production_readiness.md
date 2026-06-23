# Document Extraction Foundation — Production Readiness

## 1. Executive Summary

Document Extraction Foundation 是 OPC Foundation 的通用文档抽取底座，为下游业务系统提供标准化的文档抽取、索引、去重和健康检查能力。

**当前状态**: **Production Trial Ready**（本地公开文档，OCR 关闭）

**已验证场景**:
- 本地 PDF / HTML / TXT / Markdown 文件抽取
- PDF metadata 和文本提取（PyMuPDF）
- 文档去重（canonical_key + document_hash）
- Source Health 监控
- 失败队列与重试
- 日报生成

## 2. What is ready

### 核心能力
| 能力 | 状态 | 说明 |
|------|------|------|
| 本地 PDF 抽取 | ✅ Ready | 文本 + metadata + page_count |
| 本地 HTML 抽取 | ✅ Ready | beautifulsoup4 提取纯文本 |
| 本地 TXT 抽取 | ✅ Ready | 直接读取 |
| 本地 Markdown 抽取 | ✅ Ready | 直接读取 |
| 文档去重 | ✅ Ready | canonical_key + document_hash |
| Source Health | ✅ Ready | healthy / degraded / failed / disabled |
| 失败队列 | ✅ Ready | failed_queue.jsonl |
| 日报 | ✅ Ready | Markdown 格式日报 |
| CLI | ✅ Ready | 7 个命令 |
| PowerShell 脚本 | ✅ Ready | run / check |

### 输出产物
- `documents.jsonl` - 全量文档索引
- `documents.latest.jsonl` - 最新文档快照
- `source_health.jsonl` - 源健康状态
- `failed_queue.jsonl` - 失败队列
- `run_log.jsonl` - 运行日志
- `reports/` - 日报（Markdown）
- `metadata/` - 文档元数据 sidecar
- `raw/` - 原始文件副本
- `text/` - 纯文本文件
- `markdown/` - Markdown 文件

## 3. Recommended Production Setup

### 配置文件
```yaml
# configs/document_extraction.production.local.yaml
archive_root: "/path/to/data/document_extraction"

defaults:
  max_documents: 100
  save_raw: true
  save_markdown: true
  save_metadata: true
  extract_text: true
  extract_tables: false
  ocr_enabled: false

sources:
  - source_id: "your_local_docs"
    source_name: "Your Local Documents"
    source_type: "local_document"
    input_path: "/path/to/your/documents"
    input_glob: "*.pdf"
    enabled: true
    legal_profile: "user_provided"
    document_type: "unknown"
    max_documents: 50
```

### 运行方式
```powershell
# 验证配置
.\scripts
un_document_extraction.ps1 -Mode validate-config

# 试运行
.\scripts
un_document_extraction.ps1 -Mode dry-run

# 正式运行
.\scripts
un_document_extraction.ps1 -Mode run

# 检查健康状态
.\scripts
un_document_extraction.ps1 -Mode source-health

# 查看日报
.\scripts
un_document_extraction.ps1 -Mode report

# 检查归档产物
.\scripts\check_document_extraction.ps1
```

### 定时运行建议
- 本地文档目录：每天 1 次或按需
- 建议在文件更新后触发
- 每次运行前可先 dry-run 确认

## 4. Downstream Contract

### 核心数据模型
下游消费 `ExtractedDocument`，核心字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| document_id | string | 文档唯一 ID（doc_ 前缀） |
| source_id | string | 来源 ID |
| source_type | string | 来源类型 |
| document_title | string? | 文档标题 |
| file_extension | string? | 文件扩展名 |
| page_count | int? | 页数（PDF） |
| char_count | int? | 字符数 |
| word_count | int? | 词数 |
| content_hash | string | 文本内容 SHA256 |
| document_hash | string | 文件 SHA256 |
| canonical_key | string | 去重 key（source_id::document_hash） |
| extraction_quality | string | high / medium / low / empty / failed |
| extraction_status | string | success / partial / failed / skipped |
| created_at | string | ISO 时间戳 |
| raw_path | string? | 原始文件副本路径 |
| text_path | string? | 纯文本路径 |
| markdown_path | string? | Markdown 路径 |
| metadata_path | string? | metadata sidecar 路径 |

### 消费方式
1. 读取 `documents.latest.jsonl` 获取当前所有有效文档
2. 或读取 `documents.jsonl` 获取全量历史
3. 通过 `canonical_key` 去重
4. 通过 `extraction_status` 过滤成功文档
5. 通过 `source_id` 按来源分组

### 不提供的能力
- ❌ 投资判断（rating / signal / target price 等）
- ❌ LLM 摘要
- ❌ OCR 结果（当前版本）
- ❌ 远程网站抓取
- ❌ 付费内容

## 5. Operating Checklist

### 首次部署
- [ ] 复制 `document_extraction.production.example.yaml` 为 local 版本
- [ ] 配置 archive_root（建议绝对路径）
- [ ] 添加 source 配置
- [ ] 运行 validate-config 验证
- [ ] 运行 dry-run 确认候选数量
- [ ] 运行 run 完成首次抽取
- [ ] 运行 check 脚本验证产物

### 日常运维
- [ ] 定期检查 source-health
- [ ] 关注 failed_queue 增长
- [ ] 定期清理旧数据（如需要）
- [ ] 监控磁盘空间（raw/ 目录可能很大）

### 异常处理
- **source health = degraded**: 检查该 source 是否有失败文档
- **source health = failed**: 检查连接器或路径配置
- **failed_queue 增长**: 运行 retry-failed 或检查文档是否损坏
- **重复抽取**: 检查 canonical_key 生成逻辑

### 不支持的能力 / 明确边界

以下能力 **明确不支持**，请勿在生产环境中尝试：

- ❌ **浏览器自动化 / Playwright / Selenium**：不做任何形式的浏览器自动化，不渲染 JS 页面
- ❌ **远程 PDF 下载**：仅支持本地文件，不下载远程 URL 的 PDF
- ❌ **OCR 文字识别**：扫描版 PDF 无法抽取文本，OCR 不在当前版本范围内
- ❌ **付费内容 / paywall 绕过**：不处理付费研报，不绕过任何 paywall / 登录 / captcha
- ❌ **LLM 摘要**：不做任何 LLM 摘要或分析
- ❌ **投资判断**：不输出任何投资评级、买卖信号、目标价等投研判断字段
- ❌ **批量抓取研报**：不做大规模研报抓取

## 6. Known limitations

1. **仅支持本地文件**: 当前版本仅支持本地文件抽取，不支持远程 URL
2. **OCR 未实现**: 扫描版 PDF 无法抽取文本
3. **retry-failed 为 MVP**: 当前实现是重跑所有 source，而非只重试失败项
4. **无增量抽取**: 每次运行全量扫描，依赖去重避免重复
5. **表格抽取有限**: extract_tables 默认关闭，且未深度实现
6. **Windows 路径兼容**: 已做基本兼容，但大规模部署建议测试
7. **无并发支持**: 单线程顺序处理

## 7. Final decision

**Status: Production Trial Ready for local/public documents with OCR disabled.**

### 可以投入试用的场景
- 本地公开文档的标准化抽取
- 文档归档和索引
- 下游系统的文档数据源
- 健康状态监控

### 不建议的场景
- 扫描版 PDF（需要 OCR）
- 远程网站抓取（需要 connector）
- 实时性要求高的场景
- 大规模并发处理
