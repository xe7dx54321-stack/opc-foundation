# Document Extraction Foundation - Production Run Guide

## 前提条件

1. 已完成模块安装
2. 已有 `configs/document_extraction.example.yaml`
3. 有待处理的本地文档

## 步骤

### 1. 创建 local config

```bash
cp configs/document_extraction.example.yaml configs/document_extraction.local.yaml
```

编辑 `configs/document_extraction.local.yaml`：

```yaml
archive_root: "/path/to/your/data/document_extraction"

sources:
  - source_id: "my_documents"
    source_name: "My Documents"
    source_type: "local_document"
    input_path: "/path/to/your/documents"  # 改成你的路径
    input_glob: "*.pdf"  # 根据需要调整
    enabled: true  # 启用
    legal_profile: "user_provided"
    document_type: "unknown"
```

### 2. 验证配置

```bash
python -m opc_foundation.document_extraction.cli validate-config \
  --config configs/document_extraction.local.yaml
```

### 3. 试运行

```bash
python -m opc_foundation.document_extraction.cli dry-run \
  --config configs/document_extraction.local.yaml
```

检查输出，确认没有问题。

### 4. 正式运行

```bash
python -m opc_foundation.document_extraction.cli run \
  --config configs/document_extraction.local.yaml
```

### 5. 检查输出

```bash
# 查看归档目录
ls -la data/document_extraction/

# 查看文档索引
cat data/document_extraction/index/documents.jsonl

# 查看源健康状态
python -m opc_foundation.document_extraction.cli source-health \
  --archive-root data/document_extraction

# 查看日报
python -m opc_foundation.document_extraction.cli report \
  --archive-root data/document_extraction
```

### 6. 重试失败（如有）

```bash
python -m opc_foundation.document_extraction.cli retry-failed \
  --archive-root data/document_extraction
```

## 避免提交敏感文件

### 必须在 .gitignore 中添加

```
# Document Extraction local configs
configs/document_extraction.local.yaml
configs/document_extraction.production.local.yaml

# Document Extraction data
data/document_extraction/
```

### 确认 .gitignore 已更新

运行前检查 `.gitignore` 文件是否包含上述规则。

## OCR 默认关闭

OCR 功能默认关闭（`ocr_enabled: false`），本阶段不实现。

如需启用 OCR，需要：
1. 引入 OCR 依赖（如 pytesseract）
2. 实现 OCR extractor
3. 更新配置

## 故障排除

### 配置文件找不到

```
❌ 配置文件不存在: configs/document_extraction.local.yaml
```

解决：确保文件存在，使用绝对路径或相对于项目根目录。

### input_path 不存在

```
Source [my_documents] input_path 不存在: /path/to/documents
```

解决：检查 input_path 是否正确，确保目录存在。

### 没有 extractor

```
Candidate [/path/to/doc.pdf] 没有对应的 extractor
```

解决：检查 file_extension 是否被支持，当前支持 .pdf/.html/.htm/.txt/.md。

### PDF 读取失败

```
PyMuPDF 读取失败: ...
```

解决：
1. 检查 PDF 文件是否损坏
2. 确认 PDF 文件不是扫描版（需要 OCR）
3. 检查是否有 PDF 库安装

## 下游消费

下游系统应从以下入口读取数据：

```bash
# 所有文档
data/document_extraction/index/documents.jsonl

# 最新文档
data/document_extraction/index/documents.latest.jsonl

# 元数据
data/document_extraction/metadata/
```

## 完整流程示例

```bash
# 1. 创建 local config
cp configs/document_extraction.example.yaml configs/document_extraction.local.yaml

# 2. 编辑配置（设置你的 input_path 和 enabled=true）

# 3. 验证
python -m opc_foundation.document_extraction.cli validate-config \
  --config configs/document_extraction.local.yaml

# 4. 试跑
python -m opc_foundation.document_extraction.cli dry-run \
  --config configs/document_extraction.local.yaml

# 5. 正式跑
python -m opc_foundation.document_extraction.cli run \
  --config configs/document_extraction.local.yaml

# 6. 检查健康
python -m opc_foundation.document_extraction.cli source-health \
  --archive-root data/document_extraction

# 7. 查看报告
python -m opc_foundation.document_extraction.cli report \
  --archive-root data/document_extraction
```
