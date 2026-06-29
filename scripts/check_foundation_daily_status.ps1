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
    $ReportScript = Join-Path $ScriptDir "generate_daily_status_report.py"
    $reportContent = python $ReportScript 2>&1

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
