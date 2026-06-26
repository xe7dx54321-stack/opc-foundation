# OPC Foundation M3C-2D-URLFix Report

> **版本**：1.0
> **执行时间**：2026-06-26
> **处理范围**：M3C-2D 试运行中 3 个 HTTP 404 源

## 1. 处理范围

- **目标源数**：3
- **source_id**：goldman_sachs_research, goldman_sachs_reports, microsoft_ir

## 2. URL Verification 结果

### goldman_sachs_research

| 项目 | 内容 |
|---|---|
| 原 trial URL | `https://www.goldmansachs.com/insights/research/index.html` |
| 原始错误 | HTTP 404 Not Found |
| URL verification 方法 | curl.exe -I -L |
| 是否找到修复 URL | 是 |
| 修复后 URL | `https://www.goldmansachs.com/insights` |
| 修复后验证结果 | HTTP 200 OK，内容有效（包含真实文章如 "Why Oil Prices Could Grind Lower"） |
| 最终状态 | **url_fixed_and_trial_ready** |
| 是否保留在 trial | 是（feed_url 已更新） |

### goldman_sachs_reports

| 项目 | 内容 |
|---|---|
| 原 trial URL | `https://www.goldmansachs.com/insights/research/reports/index.html` |
| 原始错误 | HTTP 404 Not Found |
| URL verification 方法 | curl.exe -I -L |
| 是否找到修复 URL | 是 |
| 修复后 URL | `https://www.goldmansachs.com/insights/reports` |
| 修复后验证结果 | HTTP 200 OK |
| 最终状态 | **url_fixed_and_trial_ready** |
| 是否保留在 trial | 是（feed_url 已更新） |

### microsoft_ir

| 项目 | 内容 |
|---|---|
| 原 trial URL | `https://www.microsoft.com/en-us/Investor/events-events-presentations.aspx` |
| 原始错误 | HTTP 301 Moved Permanently → HTTP 403 Forbidden (Akamai bot protection) |
| URL verification 方法 | curl.exe -I -L，多个 MS IR URL 变体测试 |
| 是否找到修复 URL | 否 |
| 尝试的 URL | `https://www.microsoft.com/investor` (403), `https://www.microsoft.com/en-us/Investor/earnings` (403) |
| 最终状态 | **still_403_move_to_backlog** |
| 是否保留在 trial | 否（已移出 trial allowlist，进入 url_backlog） |

## 3. Trial Allowlist 变化

| 项目 | 内容 |
|---|---|
| 修复前 trial source 数 | 16 |
| 修复后 trial source 数 | **15** |
| 移出 trial 的源 | microsoft_ir（403，Akamai bot 保护） |
| 修复的源 | goldman_sachs_research（404→200），goldman_sachs_reports（404→200） |

## 4. 重跑 Trial 结果

### validate-config

- 结果：**PASSED**

### dry-run

- 结果：**PASSED**
- 15 sources skipped（dry-run 模式）

### run

- 结果：**PASSED**
- Total: 15, Success: 14, Failed: 1, Skipped: 0
- 注意：cls_cn 出现 1 次 url_error（疑似临时网络 timeout，单独 curl 验证 cls.cn 本身返回 200 OK）

### check

- 结果：**ALL CHECKS PASSED**

## 5. 配置更新

| 文件 | 更新内容 |
|---|---|
| configs/trae_foundation_trial_sources.example.yaml | GS Research feed_url: insights → insights; GS Reports feed_url: insights/research/reports → insights/reports; 移除 microsoft_ir（注释掉） |
| configs/foundation_trial_source_allowlist.example.yaml | trial_source_count: 16 → 15; 移除 microsoft_ir 条目，移入 url_backlog excluded_sources |
| scripts/check_foundation_trial_sources.ps1 | 硬编码 16 → 动态读取配置文件的 source_count |

## 6. M3C-3 建议

1. **可进入 TRAE trial scheduling 的源数**：15 个
2. **暂缓源**：microsoft_ir（需 M3C-2D-MSIR-Fix，探索替代入口或 connector）
3. **后续工作**：
   - M3C-2D-MSIR-Fix：探索 Microsoft IR 替代公开入口（如 SEC EDGAR、第三方财经平台）
   - M3C-3：基于 15 个验证通过源，配置正式 TRAE production 调度
   - 持续监控 cls_cn 的稳定性
