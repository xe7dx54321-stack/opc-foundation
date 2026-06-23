# Official Filing Foundation - 生产运行指南

## 一、前言

本文档指导如何在生产环境中运行 Official Filing Foundation。

**重要提醒**：

- MVP 版本仅支持 fixture 注入测试，不包含真实网络抓取
- 生产环境使用前，请确保你了解目标网站的 robots.txt 和使用条款
- 请遵守相关法律法规，尊重数据源的知识产权
- Foundation 不做投资判断，所有投研决策由业务系统负责

---

## 二、本地配置创建

### 2.1 从 example 复制

```bash
# 复制 example 配置为本地配置
cp configs/official_filings.example.yaml configs/official_filings.local.yaml
```

### 2.2 修改配置

编辑 `configs/official_filings.local.yaml`：

| 字段 | 说明 | 示例 |
|------|------|------|
| `archive_root` | 归档根目录 | `./data/official_filings` |
| `defaults.max_items_per_source` | 每个 source 最大抓取数 | `20` |
| `sources[].enabled` | 是否启用该 source | `true` |
| `sources[].endpoint_url` | API/列表页 URL | 见各 source 说明 |
| `sources[].max_items` | 单 source 覆盖默认值 | `10` |
| `sources[].filing_types` | 披露类型过滤（空=全部） | `["10-K", "10-Q"]` |

### 2.3 注意事项

- `configs/official_filings.local.yaml` 已在 `.gitignore` 中，**不会提交到 git**
- 不要在配置中写入密码、token 等敏感信息
- 生产环境建议使用 `official_filings.production.local.yaml`

---

## 三、validate-config

校验配置文件是否合法。

```bash
python -m opc_foundation.official_filings.cli validate-config \
  --config configs/official_filings.local.yaml
```

校验通过的输出：

```
[配置校验通过]
  - archive_root: ./data/official_filings
  - source 总数: 3
  - 已启用 source: 2
  - max_items_per_source: 10
```

校验失败会列出具体错误，比如：

- 缺少 `archive_root`
- `source_id` 重复
- `legal_profile` 不合法
- `source_type` 未实现
- 缺少 `base_url` 或 `endpoint_url`

---

## 四、dry-run

试运行：只发现候选披露，不写入归档。

```bash
python -m opc_foundation.official_filings.cli dry-run \
  --config configs/official_filings.local.yaml
```

用途：

- 验证 connector 能否正常发现候选
- 查看大概会有多少条数据
- 确认 source 配置正确
- 不影响现有归档数据

输出示例：

```
开始试运行（dry-run）...

运行 ID：run_abc123
模式：dry-run
开始：2024-01-15T00:00:00Z
结束：2024-01-15T00:00:05Z
Source 总数：3
启用 Source：2
候选披露：15
新保存：15
重复跳过：0
失败：0
跳过：1
```

---

## 五、run

正式运行：发现候选并写入归档。

```bash
python -m opc_foundation.official_filings.cli run \
  --config configs/official_filings.local.yaml
```

运行后会写入：

- `index/filings.jsonl` — 全量索引
- `index/filings.latest.jsonl` — 最新快照
- `index/source_health.jsonl` — source 健康状态
- `index/run_log.jsonl` — 运行日志
- `reports/daily_filing_YYYY-MM-DD.md` — 日报
- `metadata/*.json` — 每个 filing 的元数据 sidecar
- `raw/<source_type>/*` — 原始响应（如果配置了 save_raw）

### Exit Code

| code | 说明 |
|------|------|
| 0 | 完全成功 |
| 1 | 配置错误 |
| 2 | 部分失败（部分 source/filing 失败） |
| 3 | 严重运行时错误 |

---

## 六、检查输出

### 6.1 查看索引

```bash
# 查看全量索引条数
wc -l data/official_filings/index/filings.jsonl

# 查看最新快照
head -n 5 data/official_filings/index/filings.latest.jsonl
```

### 6.2 查看元数据

```bash
# 查看某个 filing 的详情
cat data/official_filings/metadata/of_xxx.json
```

### 6.3 查看原始数据

```bash
# 列出 SEC 的原始响应
ls data/official_filings/raw/sec/

# 查看某个原始文件
cat data/official_filings/raw/sec/of_xxx.json
```

---

## 七、source-health

查看 source 健康状态。

### 7.1 文本格式

```bash
python -m opc_foundation.official_filings.cli source-health \
  --archive-root data/official_filings
```

输出示例：

```
共 3 个 source：

Source ID                      类型                 状态        候选     保存     失败
------------------------------------------------------------------------------------------
example_sec_edgar               sec_edgar            healthy        5       5       0
example_cninfo                  cninfo_announcement  healthy        5       5       0
example_hkex                    hkex_announcement    disabled       0       0       0
```

### 7.2 JSON 格式

```bash
python -m opc_foundation.official_filings.cli source-health \
  --archive-root data/official_filings \
  --format json
```

方便程序读取和监控。

---

## 八、生成日报

查看指定日期的日报。

```bash
python -m opc_foundation.official_filings.cli report \
  --archive-root data/official_filings \
  --date 2024-01-15
```

日报包含：

1. **总览**：source 数、候选数、新保存数、失败数等
2. **Source 健康概览**：表格形式
3. **新保存披露**：表格形式（前 20 条）
4. **Partial / Failed**：失败详情
5. **Warnings**：警告列表
6. **下游消费入口**：索引文件路径

---

## 九、retry-failed

重试失败队列中的披露。

```bash
python -m opc_foundation.official_filings.cli retry-failed \
  --archive-root data/official_filings
```

> **MVP 版本说明**：当前 MVP 版本的 retry-failed 会列出失败队列。
> 实际重试请重新执行 `run` 命令，connector 会自动跳过已成功的披露。

---

## 十、如何避免提交 data/local config/secrets

### 10.1 已在 .gitignore 中的文件

以下文件/目录已在 `.gitignore` 中，不会被提交：

```
data/official_filings/
configs/official_filings.local.yaml
configs/official_filings.production.local.yaml
```

### 10.2 检查是否有意外提交

```bash
# 查看哪些文件会被提交
git status

# 查看详情
git diff --cached --name-only
```

### 10.3 安全建议

- 永远不要把真实的 feed URL、API key 等写入 example config
- 生产配置单独存放，不要加入 git
- data/ 目录只放本地归档，不要提交
- 定期检查 .gitignore 是否完整

---

## 十一、SEC / CNINFO / HKEX Live Smoke 后续建议

MVP 版本仅支持 fixture 注入，不包含真实网络抓取。后续接入真实数据源时建议：

### 11.1 SEC EDGAR

- SEC 有官方 API，使用 `User-Agent` 头标识自己
- 遵循 rate limit（每秒不超过 10 个请求）
- 使用 `Accept-Encoding: gzip, deflate` 减少流量
- 优先使用 submissions JSON（结构化数据）
- 先从单个公司（如 Apple）测试，再逐步扩展

### 11.2 CNINFO 巨潮资讯

- 巨潮有公开的查询 API
- 注意反爬策略，控制请求频率
- 建议在盘后或非高峰时段抓取
- 先从单只股票测试，确认解析正确

### 11.3 HKEXnews 港交所披露易

- 港交所网站是 HTML 结构，需要解析表格
- 注意中英文版本的差异
- 公告链接可能是相对路径，需要拼接 base_url
- PDF 文件可能需要单独处理

### 11.4 通用建议

1. **先小范围测试**：用 1-2 个 source，少量数据验证
2. **控制频率**：不要对目标网站造成压力
3. **做好 fail-soft**：单个 source 失败不影响全局
4. **监控健康状态**：定期检查 source_health
5. **遵守法律法规**：尊重数据源的知识产权和使用条款
6. **只抓公开数据**：不要尝试绕过登录或 paywall

---

## 十二、常见问题

### Q: 为什么我的 connector 返回空列表？

A: 可能的原因：
- endpoint_url 配置错误
- 网站结构变化，解析规则失效
- 没有匹配的 filing_type
- max_items 设置为 0

### Q: 怎么判断数据有没有重复？

A: 使用 `canonical_key` 去重。同一 source_type + issuer_code + filing_date + filing_type + 唯一标识（accession_number/announcement_id/URL）会生成相同的 canonical_key。

### Q: 怎么只抓特定类型的披露？

A: 在 source 配置的 `filing_types` 字段中列出你关心的类型，比如 `["10-K", "10-Q"]` 只抓 10-K 和 10-Q。

### Q: 数据存在哪里？

A: 默认在 `data/official_filings/` 下，结构见 Foundation 文档的"目录结构"章节。

### Q: 怎么接入到我的业务系统？

A: 读取 `index/filings.latest.jsonl`，按你的业务逻辑过滤和处理。Foundation 不做投资判断，这部分是你业务系统的职责。


---

## 十三、Recommended Production Trial Setup

### 初始生产试运行配置

**建议启用的 Source：**

| Source | 建议 | 原因 |
|--------|------|------|
| SEC EDGAR | ✅ 启用 | 真实 HTTP fetch 正常 |
| CNINFO | ✅ 启用 | 真实 HTTP POST 正常 |
| HKEXnews | ⚠️ 保持 disabled | 客户端渲染限制 |

### 配置规则

```yaml
defaults:
  max_items_per_source: 5      # 试运行阶段限制
  download_pdfs: false         # 默认不下载 PDF
  save_raw: true               # 保存原始响应
  save_html: true              # 保存 HTML
  save_pdf_metadata: true      # 记录 PDF 元数据
  fetch_timeout_seconds: 30    # 超时设置
```

### HKEXnews 限制说明

港交所页面使用 JavaScript 动态加载数据，静态 HTML 解析器当前无法获取公告列表。

**当前状态：** degraded + empty_source

**不要将其标记为 healthy。**

直到确认有公开静态端点可用，否则保持 disabled。

### 操作清单

1. validate-config
2. dry-run
3. run
4. check script
5. source-health
6. source-health --format json
7. report
8. duplicate run
9. retry-failed
10. 确认 local config/data 未被提交
