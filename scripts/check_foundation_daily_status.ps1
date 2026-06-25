# Foundation Daily Status - Daily Status Report Generator
#
# Purpose: Generate daily foundation status summary report.
#
# Usage:
#   .\scripts\check_foundation_daily_status.ps1
#   .\scripts\check_foundation_daily_status.ps1 -OutputDir ./data/foundation_control_center/reports
#
# Note: data/ should NOT be committed to Git.

param(
    [string]$OutputDir = "./data/foundation_control_center/reports"
)

$ErrorActionPreference = "Stop"

# Auto-locate repo root (script is in scripts/, parent is repo root)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

# Set PYTHONPATH to find src/ modules
$env:PYTHONPATH = Join-Path $RepoRoot "src"

$Today = Get-Date -Format "yyyy-MM-dd"
$ReportPath = Join-Path $OutputDir "daily_status_$Today.md"

Write-Host ""
Write-Host "Foundation Daily Status - Daily Status Report" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Date: $Today"
Write-Host "Output: $OutputDir"
Write-Host ""

# Ensure output directory exists
if (!(Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

# Try to generate detailed report via Python
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

# Load configs
cap_path = 'configs/foundation_capabilities.yaml'
inv_path = 'configs/foundation_source_inventory.example.yaml'

registry = load_capabilities_config(cap_path)
inventory = load_source_inventory_config(inv_path)
summary = summarize_source_inventory(inventory)

# Generate report
lines = []
lines.append(f'# Foundation Daily Status Report - {today}')
lines.append('')
lines.append('## 1. Capability Status Summary')
lines.append('')
lines.append(f'- Total capabilities: {len(registry.capabilities)}')
lines.append(f'- Runtime bindings: Awaiting runtime data integration')
lines.append('')
lines.append('## 2. Source Inventory Summary')
lines.append('')
lines.append(f'- Source groups: {summary.group_count}')
lines.append(f'- Total sources: {summary.source_count}')
lines.append(f'- Default enabled: {summary.enabled_count}')
lines.append(f'- High risk/blocked: {summary.high_risk_count}')
lines.append(f'- Search providers: {summary.search_provider_count}')
lines.append(f'- Community sources: {summary.community_count}')
lines.append('')
lines.append('### Priority Distribution')
lines.append('')
for priority, count in sorted(summary.priority_counts.items()):
    lines.append(f'- {priority}: {count}')
lines.append('')
lines.append('### Automation Mode Distribution')
lines.append('')
for mode, count in sorted(summary.automation_counts.items()):
    lines.append(f'- {mode}: {count}')
lines.append('')
lines.append('## 3. Runtime Binding Summary')
lines.append('')
lines.append('- Awaiting runtime data integration')
lines.append('')
lines.append('## 4. Known Limited Summary')
lines.append('')
lines.append('- Awaiting runtime data integration')
lines.append('')
lines.append('## 5. Blocked / High Risk Sources')
lines.append('')
lines.append(f'- Total blocked/high risk: {summary.high_risk_count}')
lines.append('- Not in scheduled tasks')
lines.append('')
lines.append('## 6. TRAE Schedule Template Summary')
lines.append('')
lines.append('- See configs/trae_foundation_schedule.example.yaml')
lines.append('- Default enabled: scheduled tasks')
lines.append('- Search/Community/Dev: on_demand')
lines.append('')
lines.append('---')
lines.append(f'*Report generated: {today}*')

print('\n'.join(lines))
" 2>&1

    if ($LASTEXITCODE -eq 0) {
        # Write report file
        $reportContent | Out-File -FilePath $ReportPath -Encoding UTF8
        Write-Host "[SUCCESS] Report generated: $ReportPath" -ForegroundColor Green
    } else {
        Write-Host "[WARNING] Python report generation failed, generating basic report." -ForegroundColor Yellow

        # Generate basic report
        $basicReport = @"
# Foundation Daily Status Report - $Today

## 1. Capability Status Summary

- Awaiting runtime data integration

## 2. Source Inventory Summary

- Awaiting source inventory load

## 3. Runtime Binding Summary

- Awaiting runtime data integration

## 4. Known Limited Summary

- Awaiting runtime data integration

## 5. Blocked / High Risk Sources

- Awaiting source inventory load

## 6. TRAE Schedule Template Summary

- See configs/trae_foundation_schedule.example.yaml

---
*Report generated: $Today*
"@
        $basicReport | Out-File -FilePath $ReportPath -Encoding UTF8
        Write-Host "[INFO] Basic report generated: $ReportPath" -ForegroundColor Yellow
    }
} catch {
    Write-Host "[WARNING] Report generation error: $_" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Done." -ForegroundColor Green
exit 0
