# run_foundation_trial_v2_candidates.ps1
# M3C-5A2 Trial v2 Candidate Validation Script
# Validates 8 URL-recovered candidates before merging into trial scheduling
# Does NOT modify current 15 trial v1 sources or TRAE scheduling

param(
    [string]$Config = "configs/trae_foundation_trial_v2_candidates.example.yaml",
    [string]$Allowlist = "configs/foundation_trial_v2_candidate_allowlist.example.yaml",
    [string]$OutputDir = "data/foundation_trial_v2",
    [string]$Mode = "run",
    [int]$MaxItemsPerSource = 10,
    [int]$TimeoutSeconds = 20,
    [string]$Proxy = $null
)

# ============================================================
# Helpers
# ============================================================

function Get-RepoRoot {
    # Auto-detect RepoRoot by searching for .git upward
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
    Write-Host " OPC Foundation M3C-5A2 Trial v2 Candidate" -ForegroundColor $cyan
    Write-Host " Validation Mode: $Mode" -ForegroundColor $cyan
    Write-Host " Config: $Script:Config" -ForegroundColor $cyan
    Write-Host " Allowlist: $Script:Allowlist" -ForegroundColor $cyan
    Write-Host " Output: $Script:OutputDir" -ForegroundColor $cyan
    Write-Host "===============================================" -ForegroundColor $cyan
    Write-Host ""
    Write-Host "NOTE: This script validates trial_v2 candidates ONLY." -ForegroundColor Yellow
    Write-Host "      Does NOT modify current 15 trial v1 sources." -ForegroundColor Yellow
    Write-Host "      Does NOT modify TRAE scheduling." -ForegroundColor Yellow
    Write-Host ""
}

# ============================================================
# Main Logic
# ============================================================

$RepoRoot = Get-RepoRoot
Set-Location $RepoRoot

# Set proxy env vars temporarily (only in current process)
if ($Proxy) {
    $env:HTTP_PROXY = $Proxy
    $env:HTTPS_PROXY = $Proxy
    Write-Host "Proxy enabled (mode=cli)" -ForegroundColor Cyan
    $proxyMode = "cli"
} else {
    # Check if proxy is set via env vars (PS 5.x compatible)
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

# Set PYTHONPATH
$env:PYTHONPATH = "$RepoRoot\src"

Write-TrialV2Header -Mode $Mode

# ---- Mode: validate-config ----
if ($Mode -eq "validate-config") {
    Write-Host "[1/1] Validating trial_v2 candidate allowlist..." -ForegroundColor Yellow

    # Check allowlist exists
    if (-not (Test-Path $Allowlist)) {
        Write-Host "Error: Allowlist not found: $Allowlist" -ForegroundColor Red
        exit 1
    }

    # Parse YAML to count candidates
    $yamlContent = Get-Content $Allowlist -Raw -Encoding UTF8

    # Basic validation
    if ($yamlContent -match "candidate_count:\s*(\d+)") {
        $expectedCount = $matches[1]
        Write-Host "Expected candidate count: $expectedCount" -ForegroundColor Cyan
    }

    # Extract trial_v2_candidates section only (between "trial_v2_candidates:" and next top-level key)
    $candidatesSection = ""
    if ($yamlContent -match '(?s)trial_v2_candidates:\s*\n((?:  - .+\n?)+)') {
        $candidatesSection = $matches[1]
    }

    # Check no trial v1 sources are included in candidates section
    $trialV1Ids = @(
        "goldman_sachs_research", "goldman_sachs_reports", "goldman_sachs_top_of_mind",
        "goldman_sachs_insights", "barclays_our_insights", "microsoft_ir",
        "yahoo_finance", "business_insider", "markets_insider", "the_fly",
        "briefing_com_upgrades", "wallstreet_cn", "cls_cn", "wind_public",
        "gelonghui", "zhitong_caijing"
    )

    $conflictFound = $false
    foreach ($id in $trialV1Ids) {
        if ($candidatesSection -match $id) {
            Write-Host "Error: Trial v1 source '$id' found in candidates" -ForegroundColor Red
            $conflictFound = $true
        }
    }

    if ($conflictFound) {
        Write-Host "validate-config FAILED: Trial v1 sources conflict" -ForegroundColor Red
        exit 1
    }

    Write-Host "validate-config PASSED" -ForegroundColor Green
    Write-Host "  - Allowlist exists: YES" -ForegroundColor Green
    Write-Host "  - Trial v1 conflict: NONE" -ForegroundColor Green
    Write-Host "  - Proxy mode: $proxyMode" -ForegroundColor Green
    exit 0
}

# ---- Mode: dry-run ----
if ($Mode -eq "dry-run") {
    Write-Host "[1/3] Validating allowlist..." -ForegroundColor Yellow

    # Basic allowlist check
    if (-not (Test-Path $Allowlist)) {
        Write-Host "Error: Allowlist not found: $Allowlist" -ForegroundColor Red
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
    Write-Host "  - Allowlist exists: YES" -ForegroundColor Green
    Write-Host "  - Source inventory exists: YES" -ForegroundColor Green
    Write-Host "  - Output directory will be: $OutputDir" -ForegroundColor Green
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

    Write-Host "[2/5] Running trial_v2 candidate validation..." -ForegroundColor Yellow

    # Run the actual validation (simulated for now - in production would call Python)
    # This is a local-only run for validation purposes

    $timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss"
    $reportFile = "$outputReports\trial_v2_candidate_validation_$(Get-Date -Format 'yyyy-MM-dd').md"

    Write-Host "[3/5] Executing smoke test on 8 candidates..." -ForegroundColor Yellow

    # Create output files
    $healthFile = "$outputIndex\source_health.jsonl"
    $logFile = "$outputIndex\run_log.jsonl"
    $failedFile = "$outputIndex\failed_queue.jsonl"

    # Initialize files
    "" | Out-File -FilePath $healthFile -Encoding utf8
    "" | Out-File -FilePath $logFile -Encoding utf8
    "" | Out-File -FilePath $failedFile -Encoding utf8

    Write-Host "[4/5] Generating validation report..." -ForegroundColor Yellow

    # Generate report
    $reportContent = @"
# Trial v2 Candidate Validation Report (M3C-5A2)

> Generated: $timestamp
> Mode: Validation Run
> Output: $OutputDir

## Summary

- Total Candidates: 8
- Validate Mode: Trial v2 Candidate Validation
- Proxy Enabled: $(if ($proxyMode -ne "none") { "YES" } else { "NO" })
- Proxy Mode: $proxyMode

## Candidates

| source_id | status | notes |
|---|---|---|
| bofa_global_research | PENDING | Awaiting smoke test |
| texas_instruments_ir | PENDING | Awaiting smoke test |
| merck_ir | PENDING | Awaiting smoke test |
| benzinga_analyst_ratings | PENDING | Awaiting smoke test |
| china_fund_news | PENDING | Awaiting smoke test |
| goldman_sachs_exchanges | PENDING | Awaiting smoke test |
| goldman_sachs_the_markets | PENDING | Awaiting smoke test |
| goldman_sachs_top_of_mind_podcast | PENDING | Awaiting smoke test |

## Notes

- This is a validation-only run
- Does NOT affect current 15 trial v1 sources
- Does NOT modify TRAE scheduling
- Full validation requires actual Python execution with network access

---
Generated by: run_foundation_trial_v2_candidates.ps1
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
    Write-Host "  python -m opc_foundation.source_inventory.cli trial-v2-validate" -ForegroundColor Yellow
    exit 0
}

# Fallback
Write-Host "Error: Unknown mode '$Mode'" -ForegroundColor Red
Write-Host "Supported modes: validate-config, dry-run, run" -ForegroundColor Red
exit 1
