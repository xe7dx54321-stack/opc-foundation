# Official Filing Foundation Live Smoke Registry

更新时间：2026-06-23
状态：Production Trial Ready with Caveats

## 1. 总览

| Source | Source Type | Market | Result | Health | Production Trial |
|--------|-------------|--------|--------|--------|------------------|
| SEC EDGAR | sec_edgar | US | 5/5 saved | healthy | ready |
| CNINFO | cninfo_announcement | CN | 5/5 saved | healthy | ready |
| HKEXnews | hkex_announcement | HK | 0 candidates | degraded + empty_source | limited |

---

## 2. SEC EDGAR

### 测试结果

- **Live Source**: Apple CIK0000320193
- **Real HTTP Fetch**: success
- **Candidates**: 5
- **Saved**: 5
- **Health**: healthy
- **Notes**: SEC source requires proper User-Agent and public endpoint usage.

### Readiness

**SEC EDGAR is ready for production trial.**

### Boundary

Foundation records filing metadata and raw source references only.
It does not extract financial metrics, compare expectations, or generate investment judgment.

### 支持的字段

| 字段 | 状态 | 说明 |
|------|------|------|
| filing_type | ✅ | 10-K, 10-Q, 8-K 等 |
| filing_date | ✅ | YYYY-MM-DD |
| accession_number | ✅ | SEC 唯一标识 |
| document_url | ✅ | 文档相对路径 |
| issuer_name | ⚠️ | 部分为空 |
| issuer_code | ✅ | CIK 格式 |

---

## 3. CNINFO（巨潮资讯）

### 测试结果

- **Live Source**: CNINFO announcement API
- **Real HTTP POST**: success
- **Candidates**: 5
- **Saved**: 5
- **Health**: healthy

### Readiness

**CNINFO is ready for production trial with small batch limits.**

### Boundary

No captcha bypass, no browser automation, no OCR, no investment interpretation.

### 支持的字段

| 字段 | 状态 | 说明 |
|------|------|------|
| 证券代码 | ✅ | A 股代码 |
| 证券简称 | ✅ | 公司简称 |
| 公告标题 | ✅ | 完整标题 |
| 公告类型 | ✅ | 年报、季报等 |
| 公告日期 | ✅ | YYYY-MM-DD |
| announcement_id | ✅ | 巨潮唯一标识 |
| pdf_url | ✅ | PDF 下载链接 |

---

## 4. HKEXnews（港交所披露易）

### 测试结果

- **HTTP GET**: success
- **Static HTML Candidates**: 0
- **Health**: degraded
- **Error Type**: empty_source
- **Reason**: client-side rendering / JavaScript-loaded announcement list

### Readiness

**HKEXnews is not fully ready for static production collection.**

**Current status: degraded, not healthy.**

### Future Options

- Find official static endpoint if available
- Use official downloadable metadata if available
- Keep as degraded until non-browser public endpoint is found
- Do not add browser automation in foundation without separate approval

### 重要说明

港交所页面使用 JavaScript 动态加载数据，静态 HTML 解析无法获取公告列表。
当前 HTTP fetch 正常，但 `candidate_count=0`，根据 health 语义规则应标记为 `degraded`。

---

## 5. Source Health 语义规则

### 重要规则

```text
enabled + candidate_count = 0
→ degraded + empty_source
```

这确保了不会对可达但无数据的 source 误标为 healthy。

### 完整状态映射

| 场景 | 状态 | last_error |
|------|------|------------|
| enabled + candidates > 0 + no errors | healthy | null |
| enabled + candidates > 0 + has errors | degraded | error message |
| enabled + candidates = 0 | degraded | empty_source |
| connector failed | failed | error message |
| disabled | disabled | null |

---

## 6. Production 建议

### 初始生产试运行

**建议启用的 Source：**

| Source | 建议 |
|--------|------|
| SEC EDGAR | ✅ 启用 |
| CNINFO | ✅ 启用 |
| HKEXnews | ⚠️ 保持 disabled 或监控 |

### 配置建议

```yaml
defaults:
  max_items_per_source: 5  # 试运行阶段限制
  download_pdfs: false       # 默认不下载 PDF
  save_raw: true             # 保存原始响应
  save_html: true            # 保存 HTML
  save_pdf_metadata: true     # 记录 PDF 元数据

sources:
  - source_id: "your_sec_source"
    enabled: true            # SEC 启用
    max_items: 5

  - source_id: "your_cninfo_source"
    enabled: true            # CNINFO 启用
    max_items: 5

  - source_id: "your_hkex_source"
    enabled: false            # HKEX 暂时禁用
```

---

## 7. 不支持的功能

以下功能在 Official Filing Foundation 中**不支持**：

- ❌ 浏览器自动化
- ❌ 验证码绕过
- ❌ Paywall 绕过
- ❌ Cookie/Token 认证
- ❌ OCR
- ❌ 批量 PDF 下载（默认禁用）
- ❌ 投资判断（利好/利空/超预期）
- ❌ 交易信号生成

---

## 8. 相关文档

- [Official Filing Foundation 主文档](./official_filing_foundation.md)
- [生产运行指南](./official_filing_production_run.md)
- [Production Readiness Summary](./official_filing_production_readiness.md)
