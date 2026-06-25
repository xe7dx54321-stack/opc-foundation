# Foundation Daily Status - 每日状态收口报告
#
# 作用：生成每日 foundation 状态收口报告。
#
# 使用方法：
#   .\scripts\check_foundation_daily_status.ps1
#   .\scripts\check_foundation_daily_status.ps1 -OutputDir ./data/foundation_control_center/reports
#
# 注意：
#   data/ 不提交 Git。
#   本脚本可以写报告，但测试中使用临时目录。

param(
    [string]$OutputDir = "./data/foundation_control_center/reports"
)

$ErrorActionPreference = "Stop"

# 自动定位仓库根目录（脚本位于 scripts/ 下，上一级即仓库根）
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

# 设置 PYTHONPATH，确保能找到 src/ 下的模块
$env:PYTHONPATH = Join-Path $RepoRoot "src"

$Today = Get-Date -Format "yyyy-MM-dd"
$ReportPath = Join-Path $OutputDir "daily_status_$Today.md"

Write-Host ""
Write-Host "Foundation Daily Status - 每日状态收口" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "日期：$Today"
Write-Host "输出目录：$OutputDir"
Write-Host ""

# 确保输出目录存在
if (!(Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

# 尝试通过 Python 生成更详细的报告
try {
    $reportContent = python -c "
import sys
sys.path.insert(0, 'src')
from datetime import date

from opc_foundation.dashboard.loaders import (
    load_capabilities_config,
    load_source_inventory_config,
    summarize_source_inventory,
)

today = date.today().strftime('%Y-%m-%d')

# 加载配置
cap_path = 'configs/foundation_capabilities.yaml'
inv_path = 'configs/foundation_source_inventory.example.yaml'

registry = load_capabilities_config(cap_path)
inventory = load_source_inventory_config(inv_path)
summary = summarize_source_inventory(inventory)

# 生成报告
lines = []
lines.append(f'# Foundation 每日状态报告 - {today}')
lines.append('')
lines.append('## 1. 能力状态摘要')
lines.append('')
lines.append(f'- 能力总数：{len(registry.capabilities)}')
lines.append(f'- 运行时绑定：待 runtime 数据接入')
lines.append('')
lines.append('## 2. Source Inventory 摘要')
lines.append('')
lines.append(f'- source group 数量：{summary.group_count}')
lines.append(f'- source 总数：{summary.source_count}')
lines.append(f'- 默认启用：{summary.enabled_count}')
lines.append(f'- 高风险/禁止源：{summary.high_risk_count}')
lines.append(f'- 搜索源：{summary.search_provider_count}')
lines.append(f'- 社区源：{summary.community_count}')
lines.append('')
lines.append('### 优先级分布')
lines.append('')
for priority, count in sorted(summary.priority_counts.items()):
    lines.append(f'- {priority}：{count}')
lines.append('')
lines.append('### 自动化模式分布')
lines.append('')
for mode, count in sorted(summary.automation_counts.items()):
    lines.append(f'- {mode}：{count}')
lines.append('')
lines.append('## 3. Runtime Binding 摘要')
lines.append('')
lines.append('- 待 runtime 数据接入后补充')
lines.append('')
lines.append('## 4. 异常能力摘要')
lines.append('')
lines.append('- 待 runtime 数据接入后补充')
lines.append('')
lines.append('## 5. Known Limited 摘要')
lines.append('')
lines.append('- 待 runtime 数据接入后补充')
lines.append('')
lines.append('## 6. Blocked / High Risk 源摘要')
lines.append('')
lines.append(f'- 高风险/禁止源总数：{summary.high_risk_count}')
lines.append('- 不进入定时任务')
lines.append('')
lines.append('## 7. TRAE 调度模板摘要')
lines.append('')
lines.append('- 参考 configs/trae_foundation_schedule.example.yaml')
lines.append('- 默认启用 scheduled 任务')
lines.append('- Search Provider / Community / Dev 保持 on_demand')
lines.append('')
lines.append('---')
lines.append(f'*报告生成时间：{today}*')

print('\n'.join(lines))
" 2>&1

    if ($LASTEXITCODE -eq 0) {
        # 写入报告文件
        $reportContent | Out-File -FilePath $ReportPath -Encoding UTF8
        Write-Host "[成功] 报告已生成：$ReportPath" -ForegroundColor Green
    } else {
        Write-Host "[警告] Python 报告生成失败，生成基础报告。" -ForegroundColor Yellow

        # 生成基础报告
        $basicReport = @"
# Foundation 每日状态报告 - $Today

## 1. 能力状态摘要

- 待 runtime 数据接入后补充

## 2. Source Inventory 摘要

- 待 source inventory 加载后补充

## 3. Runtime Binding 摘要

- 待 runtime 数据接入后补充

## 4. 异常能力摘要

- 待 runtime 数据接入后补充

## 5. Known Limited 摘要

- 待 runtime 数据接入后补充

## 6. Blocked / High Risk 源摘要

- 待 source inventory 加载后补充

## 7. TRAE 调度模板摘要

- 参考 configs/trae_foundation_schedule.example.yaml

---
*报告生成时间：$Today*
"@
        $basicReport | Out-File -FilePath $ReportPath -Encoding UTF8
        Write-Host "[信息] 基础报告已生成：$ReportPath" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[警告] 报告生成过程出错：$_" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "完成。" -ForegroundColor Green
exit 0
