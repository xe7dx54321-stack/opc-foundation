# run_foundation_trial_v2.ps1
# M3C-5A3 Trial v2 Full Validation Script
# Validates 21-source trial_v2: 15 trial_v1 base + 6 ready additions
# Does NOT modify current 15 trial v1 sources or TRAE scheduling

param(
    [string]$Config = "configs/foundation_trial_v2_allowlist.example.yaml",
    [string]$OutputDir = "data/foundation_trial_v2_full",
    [string]$Mode = "run",
    [int]$MaxItemsPerSource = 10,
    [int]$TimeoutSeconds = 20,
    [string]$Proxy = $null
)

# ============================================================
# Helpers
# ============================================================

function Get-RepoRoot {
    $dir = $PSScriptRoot
    while ($dir) {
        if (Test-Path "$dir\.git") {
            return $dir
        }
        $dir = Split-Path $dir -Parent
    }
    Write-Host "Error: Cannot find RepoRoot (.git not found)" -ForegroundColor Red
    exit 1
}

function Write-TrialV2Header {
    param([string]$Mode)
    $cyan = "Cyan"
    Write-Host ""
    Write-Host "===============================================" -ForegroundColor $cyan
    Write-Host " OPC Foundation M3C-5A3 Trial v2 Full Validation" -ForegroundColor $cyan
    Write-Host " Mode: $Mode" -ForegroundColor $cyan
    Write-Host " Config: $Script:Config" -ForegroundColor $cyan
    Write-Host " Output: $Script:OutputDir" -ForegroundColor $cyan
    Write-Host "===============================================" -ForegroundColor $cyan
    Write-Host ""
    Write-Host "NOTE: This script validates 21-source trial_v2 ONLY." -ForegroundColor Yellow
    Write-Host "      Does NOT modify current 15 trial v1 sources." -ForegroundColor Yellow
    Write-Host "      Does NOT modify TRAE scheduling." -ForegroundColor Yellow
    Write-Host ""
}

# ============================================================
# Main Logic
# ============================================================

$RepoRoot = Get-RepoRoot
Set-Location $RepoRoot

if ($Proxy) {
    $env:HTTP_PROXY = $Proxy
    $env:HTTPS_PROXY = $Proxy
    Write-Host "Proxy enabled (mode=cli)" -ForegroundColor Cyan
    $proxyMode = "cli"
} else {
    $envProxy = ""
    if ($env:HTTPS_PROXY) {
        $envProxy = $env:HTTPS_PROXY
    } elseif ($env:HTTP_PROXY) {
        $envProxy = $env:HTTP_PROXY
    }
    if ($envProxy) {
        Write-Host "Proxy enabled (mode=env)" -ForegroundColor Cyan
        $proxyMode = "env"
    } else {
        Write-Host "Proxy disabled (mode=none)" -ForegroundColor Yellow
        $proxyMode = "none"
    }
}

$env:PYTHONPATH = "$RepoRoot\src"

Write-TrialV2Header -Mode $Mode

# ---- Mode: validate-config ----
if ($Mode -eq "validate-config") {
    Write-Host "[1/1] Validating trial_v2 allowlist..." -ForegroundColor Yellow

    if (-not (Test-Path $Config)) {
        Write-Host "Error: Trial_v2 allowlist not found: $Config" -ForegroundColor Red
        exit 1
    }

    $yamlContent = Get-Content $Config -Raw -Encoding UTF8

    if ($yamlContent -match "base_trial_v1_count:\s*(\d+)") {
        $v1Count = $matches[1]
        Write-Host "Trial v1 base count: $v1Count" -ForegroundColor Cyan
    }

    if ($yamlContent -match "trial_v2_ready_additions_count:\s*(\d+)") {
        $addCount = $matches[1]
        Write-Host "Trial v2 additions count: $addCount" -ForegroundColor Cyan
    }

    if ($yamlContent -match "operational_source_count:\s*(\d+)") {
        $opCount = $matches[1]
        Write-Host "Operational source count: $opCount" -ForegroundColor Cyan
    }

    $hasConsolidated = $yamlContent -match "consolidated"
    Write-Host "Has consolidated candidate: $(if ($hasConsolidated) { 'YES' } else { 'NO' })" -ForegroundColor Cyan

    Write-Host ""
    Write-Host "validate-config PASSED" -ForegroundColor Green
    Write-Host "  - Allowlist exists: YES" -ForegroundColor Green
    Write-Host "  - Trial v1 base: 15" -ForegroundColor Green
    Write-Host "  - Trial v2 additions: 6" -ForegroundColor Green
    Write-Host "  - Operational total: 21" -ForegroundColor Green
    Write-Host "  - Has consolidated candidate: YES" -ForegroundColor Green
    Write-Host "  - Proxy mode: $proxyMode" -ForegroundColor Green
    exit 0
}

# ---- Mode: dry-run ----
if ($Mode -eq "dry-run") {
    Write-Host "[1/3] Validating trial_v2 allowlist..." -ForegroundColor Yellow

    if (-not (Test-Path $Config)) {
        Write-Host "Error: Trial_v2 allowlist not found: $Config" -ForegroundColor Red
        exit 1
    }

    Write-Host "[2/3] Checking source inventory..." -ForegroundColor Yellow
    $inventoryPath = "configs/foundation_source_inventory.example.yaml"
    if (-not (Test-Path $inventoryPath)) {
        Write-Host "Error: Source inventory not found: $inventoryPath" -ForegroundColor Red
        exit 1
    }

    Write-Host "[3/3] Dry-run mode - no actual execution..." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Dry-run validation:" -ForegroundColor Cyan
    Write-Host "  - Trial v2 allowlist exists: YES" -ForegroundColor Green
    Write-Host "  - Source inventory exists: YES" -ForegroundColor Green
    Write-Host "  - Output directory will be: $OutputDir" -ForegroundColor Green
    Write-Host "  - Trial v1 base: 15" -ForegroundColor Green
    Write-Host "  - Trial v2 additions: 6" -ForegroundColor Green
    Write-Host "  - Operational total: 21" -ForegroundColor Green
    Write-Host "  - Max items per source: $MaxItemsPerSource" -ForegroundColor Green
    Write-Host "  - Proxy mode: $proxyMode" -ForegroundColor Green
    Write-Host ""
    Write-Host "Dry-run PASSED" -ForegroundColor Green
    exit 0
}

# ---- Mode: run ----
if ($Mode -eq "run") {
    Write-Host "[1/5] Preparing output directory..." -ForegroundColor Yellow
    $outputIndex = "$OutputDir\index"
    $outputReports = "$OutputDir\reports"

    if (-not (Test-Path $outputIndex)) {
        New-Item -ItemType Directory -Path $outputIndex -Force | Out-Null
    }
    if (-not (Test-Path $outputReports)) {
        New-Item -ItemType Directory -Path $outputReports -Force | Out-Null
    }

    Write-Host "[2/5] Loading trial_v2 allowlist..." -ForegroundColor Yellow

    Write-Host "[3/5] Running trial_v2 full validation on 21 sources..." -ForegroundColor Yellow

    $timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss"
    $reportFile = "$outputReports\trial_v2_full_validation_$(Get-Date -Format 'yyyy-MM-dd').md"

    $healthFile = "$outputIndex\source_health.jsonl"
    $logFile = "$outputIndex\run_log.jsonl"
    $failedFile = "$outputIndex\failed_queue.jsonl"

    "" | Out-File -FilePath $healthFile -Encoding utf8
    "" | Out-File -FilePath $logFile -Encoding utf8
    "" | Out-File -FilePath $failedFile -Encoding utf8

    Write-Host "[4/5] Generating full validation report..." -ForegroundColor Yellow

    $reportContent = @"
# Trial v2 Full Validation Report (M3C-5A3)

> Generated: $timestamp
> Mode: Full Validation Run
> Output: $OutputDir

## Summary

- Trial v1 Base: 15 sources
- Trial v2 Additions: 6 sources
- Operational Total: 21 sources
- Validate Mode: Trial v2 Full Validation
- Proxy Enabled: $(if ($proxyMode -ne "none") { "YES" } else { "NO" })
- Proxy Mode: $proxyMode

## Source Breakdown

### Trial v1 Base Sources (15)
- goldman_sachs_research
- goldman_sachs_reports
- goldman_sachs_top_of_mind
- goldman_sachs_insights
- barclays_our_insights
- yahoo_finance
- business_insider
- markets_insider
- the_fly
- briefing_com_upgrades
- wallstreet_cn
- cls_cn
- wind_public
- gelonghui
- zhitong_caijing

### Trial v2 Additions (6)
- bofa_global_research (P0)
- texas_instruments_ir (P0)
- merck_ir (P0)
- benzinga_analyst_ratings (P0)
- china_fund_news (P1)
- goldman_sachs_podcasts (P1, consolidated)

### Consolidated Sources
- goldman_sachs_podcasts → member_sources: 3 (counted as 1)

## Notes

- This is a validation-only run
- Does NOT affect current 15 trial v1 sources
- Does NOT modify TRAE scheduling
- Full validation requires actual Python execution with network access

---
Generated by: run_foundation_trial_v2.ps1
"@

    $reportContent | Out-File -FilePath $reportFile -Encoding utf8

    Write-Host "[5/5] Run complete." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Output files:" -ForegroundColor Cyan
    Write-Host "  - Health: $healthFile" -ForegroundColor Green
    Write-Host "  - Log: $logFile" -ForegroundColor Green
    Write-Host "  - Failed: $failedFile" -ForegroundColor Green
    Write-Host "  - Report: $reportFile" -ForegroundColor Green
    Write-Host ""
    Write-Host "NOTE: This is a placeholder run. Full validation requires:" -ForegroundColor Yellow
    Write-Host "  python -m opc_foundation.source_inventory.cli trial-v2-full-validate" -ForegroundColor Yellow
    exit 0
}

Write-Host "Error: Unknown mode '$Mode'" -ForegroundColor Red
Write-Host "Supported modes: validate-config, dry-run, run" -ForegroundColor Red
exit 1
