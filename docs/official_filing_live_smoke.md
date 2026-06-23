# Official Filing Foundation M1 Live Smoke Report

> **状态**：✅ 已完成
>
> 本文档记录 Official Filing Foundation 的 Live Smoke 测试结果。

## 一、Live Smoke 概述

| 项目 | 说明 |
|------|------|
| 开始日期 | 2026-06-23 |
| 结束日期 | 2026-06-23 |
| 分支 | master |
| 测试环境 | Windows 11 / Python 3.11 |
| 测试人员 | OPC Foundation Agent |

---

## 二、测试源概览

| Source | Type | Status | 结果 |
|--------|------|--------|------|
| SEC EDGAR (Apple) | sec_edgar | ✅ 成功 | 5 条披露 |
| CNINFO | cninfo_announcement | ✅ 成功 | 5 条披露 |
| HKEXnews | hkex_announcement | ⚠️ degraded | 0 条（empty_source） |

---

## 三、SEC EDGAR Live Smoke

### 3.1 测试配置

```yaml
source_id: "smoke_sec_apple"
source_name: "SEC EDGAR Apple Live Smoke"
source_type: "sec_edgar"
endpoint_url: "https://data.sec.gov/submissions/CIK0000320193.json"
enabled: true
max_items: 5
```

### 3.2 执行结果

| 指标 | 值 |
|------|-----|
| validate-config | ✅ 通过 |
| dry-run | ✅ 候选 5 条 |
| run | ✅ 保存 5 条，失败 0 条 |
| duplicate run | ✅ 重复跳过 5 条 |
| source_health | healthy |
| report | ✅ 正常生成 |

### 3.3 字段提取验证

| 字段 | 是否提取 | 示例值 |
|------|---------|--------|
| filing_type | ✅ | 4,10-K, 8-K 等 |
| filing_date | ✅ | 2024-01-01 |
| accession_number | ✅ | 0000320193-24-000001 |
| document_url | ✅ | /Archives/... |
| issuer_name | ⚠️ | 部分为空（见限制） |
| issuer_code | ✅ | CIK0000320193 |

### 3.4 限制与问题

1. **issuer_name 部分为空**：SEC 返回的 `entityName` 字段有时为空，这不影响核心功能
2. **html_url/pdf_url 为 null**：SEC 的部分披露是 XML 格式，不是 HTML
3. **真实 HTTP 支持已添加**：MVP 版本现在支持真实 HTTP fetch（使用 urllib）

---

## 四、CNINFO Live Smoke

### 4.1 测试配置

```yaml
source_id: "smoke_cninfo"
source_name: "CNINFO Live Smoke"
source_type: "cninfo_announcement"
endpoint_url: "https://www.cninfo.com.cn/new/hisAnnouncement/query"
enabled: true
max_items: 5
```

### 4.2 执行结果

| 指标 | 值 |
|------|-----|
| validate-config | ✅ 通过 |
| dry-run | ✅ 候选 5 条 |
| run | ✅ 保存 5 条，失败 0 条 |
| duplicate run | ✅ 重复跳过 5 条 |
| source_health | healthy |

### 4.3 字段提取验证

| 字段 | 是否提取 | 示例值 |
|------|---------|--------|
| 证券代码 | ✅ | 000001 |
| 证券简称 | ✅ | 平安银行 |
| 公告标题 | ✅ | 2024年半年度报告 |
| 公告类型 | ✅ | 半年报 |
| 公告日期 | ✅ | 2024-08-15 |
| announcement_id | ✅ | 121... |
| pdf_url | ✅ | https://... |

### 4.4 限制与问题

1. **真实 HTTP POST 已实现**：CNINFO API 需要 POST 请求，已添加支持
2. **API 参数可能需要调整**：不同查询条件可能需要不同的 POST 参数

---

## 五、HKEXnews Live Smoke

### 5.1 测试配置

```yaml
source_id: "smoke_hkex"
source_name: "HKEX Live Smoke"
source_type: "hkex_announcement"
endpoint_url: "https://www.hkexnews.hk/listedco/listconews/advancedsearch/search_active_main_c.aspx"
enabled: true
max_items: 5
```

### 5.2 执行结果

| 指标 | 值 |
|------|-----|
| validate-config | ✅ 通过 |
| dry-run | ⚠️ 候选 0 条 |
| run | ⚠️ 保存 0 条 |
| source_health | **degraded (empty_source)** |

### 5.3 观察到的现象

- HTTP GET 成功执行（无异常）
- 返回的 HTML 不包含公告数据
- 解析器无法从静态 HTML 中提取数据
- **状态标记为 degraded + last_error="empty_source"**

### 5.4 Health 状态说明

**重要更新**：根据 health 逻辑规则：
- `enabled=True` 但 `candidate_count=0` → **degraded**
- `last_error="empty_source"` 表示启用但未发现候选

这是统一的行为，适用于所有 enabled source。

### 5.5 限制与问题

1. **客户端渲染问题**：港交所页面使用 JavaScript 动态加载数据，静态 HTML 解析无法获取
2. **建议**：后续可以考虑使用官方 API（如果有）或接受当前限制

---

## 六、CLI 命令验证

| 命令 | 结果 | 说明 |
|------|------|------|
| validate-config | ✅ | 配置校验正常 |
| dry-run | ✅ | 试运行正常 |
| run | ✅ | 正式运行正常 |
| source-health | ✅ | 文本格式正常，HKEX → degraded |
| source-health --format json | ✅ | JSON 格式正常，last_error="empty_source" |
| report --date YYYY-MM-DD | ✅ | 日报生成正常 |
| retry-failed | ✅ | 失败重试正常 |
| duplicate run | ✅ | 去重正常 |

---

## 七、Hardening 记录

### 7.1 代码修改

| 文件 | 修改内容 | 原因 |
|------|---------|------|
| connectors/sec.py | 添加真实 HTTP fetch | 支持生产环境真实网络抓取 |
| connectors/cninfo.py | 添加真实 HTTP POST fetch | 支持巨潮 API |
| connectors/hkex.py | 添加真实 HTTP GET fetch | 支持港交所页面 |
| archiver.py | Health 逻辑：enabled+0 candidates → degraded | 统一处理 empty_source |
| tests/official_filings/test_production_config.py | 新增 | 验证 production 配置和脚本 |

### 7.2 Health 逻辑规则

| 场景 | 状态 | last_error |
|------|------|------------|
| enabled + candidates > 0 + no errors | healthy | null |
| enabled + candidates > 0 + has errors | degraded | error message |
| enabled + candidates = 0 | **degraded** | **empty_source** |
| connector failed | failed | error message |
| disabled | disabled | null |

### 7.3 Fixture 回归测试

| 测试文件 | 测试场景 |
|---------|---------|
| test_sec_connector.py | fixture 解析正常 |
| test_cninfo_connector.py | fixture 解析正常 |
| test_hkex_connector.py | fixture 解析正常 |
| test_production_config.py | production 配置和脚本正常 |

---

## 八、Production Trial Ready 判断

### 8.1 整体评估

| 维度 | 状态 | 说明 |
|------|------|------|
| SEC EDGAR | ✅ Production Ready | 真实 HTTP 抓取正常 |
| CNINFO | ✅ Production Ready | 真实 HTTP POST 正常 |
| HKEXnews | ⚠️ Limited | 客户端渲染限制，health=**degraded** |
| Storage/Index | ✅ Production Ready | JSONL 写入正常 |
| Source Health | ✅ Production Ready | **degraded 逻辑正常** |
| Failed Queue | ✅ Production Ready | 失败队列正常 |
| Report | ✅ Production Ready | 中文日报正常 |
| CLI | ✅ Production Ready | 所有命令正常 |

### 8.2 仍需后续处理的问题

1. **HKEX 客户端渲染**：港交所页面使用 JavaScript 动态加载，当前静态 HTML 解析无法获取数据
   - 可能的解决方案：使用官方 API（如果有）、或接受当前限制
2. **SEC issuer_name 部分为空**：不影响核心功能，但可考虑增强字段提取
3. **PDF 下载**：当前 download_pdfs=false，后续可根据需要启用

### 8.3 适合当前 foundation 的模式

- ✅ SEC EDGAR API（最规范、公开、无需认证）
- ✅ CNINFO API（有公开查询接口）
- ✅ JSONL 归档存储（结构化、易于下游消费）
- ✅ Source Health 监控（**含 empty_source degraded**）

### 8.4 不适合当前 foundation 的模式

- ❌ 客户端渲染页面（需要 JavaScript 执行）
- ❌ 需要登录/paywall 的数据源
- ❌ 验证码保护的数据源
- ❌ 投资判断/利好利空（违反 foundation 边界）

### 8.5 最终结论

> **是否达到 Production Trial Ready**：
>
> **✅ 是，但有 HKEX 限制。**
>
> - SEC 和 CNINFO 已完全可用，health=healthy
> - HKEX 受客户端渲染限制，health=degraded（符合预期）
> - Health 逻辑已统一：enabled+0 candidates → degraded + empty_source
> - 所有 CLI 命令、去重、存储、监控均正常
> - Foundation 边界清晰，无投资判断字段

---

## 九、后续建议

1. **HKEX 优化**：探索港交所是否有 API 端点，或使用其他方式获取数据
2. **字段增强**：提升 issuer_name 等字段的提取准确率
3. **增量同步**：基于 date_from/date_to 实现增量抓取
4. **PDF 下载**：可选择性下载 PDF 正文（需权衡存储空间）
5. **更多 Source**：上交所、深交所、新加坡交易所等
