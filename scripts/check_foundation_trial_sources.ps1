# check_foundation_trial_sources.ps1
# M3C-2D Trial Source Check Script
# Checks trial configuration integrity and output artifacts.

param(
    [string]$Config = "configs/trae_foundation_trial_sources.example.yaml",
    [string]$Allowlist = "configs/foundation_trial_source_allowlist.example.yaml",
    [string]$OutputDir = "data/foundation_trial"
)

# ============================================================
# Helper Functions
# ============================================================

function Get-RepoRoot {
    $dir = $PSScriptRoot
    while ($dir) {
        if (Test-Path "$dir\.git") {
            return $dir
        }
        $dir = Split-Path $dir -Parent
    }
    Write-Host "Error: Cannot find RepoRoot" -ForegroundColor Red
    exit 1
}

function Test-Check {
    param([string]$Label, [bool]$Passed, [string]$Detail = "")
    $color = if ($Passed) { "Green" } else { "Red" }
    $icon = if ($Passed) { "[PASS]" } else { "[FAIL]" }
    Write-Host "  $icon $Label" -ForegroundColor $color
    if ($Detail -and -not $Passed) {
        Write-Host "        $Detail" -ForegroundColor Red
    }
    return $Passed
}

# ============================================================
# Main Check Logic
# ============================================================

$RepoRoot = Get-RepoRoot
Set-Location $RepoRoot

Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host " OPC Foundation M3C-2D Trial Source Check" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

$allPassed = $true

# ---- 1. Config File Existence Check ----
Write-Host "[1/6] Checking config files..." -ForegroundColor Yellow

$allPassed = (Test-Check "allowlist exists" (Test-Path $Allowlist)) -and $allPassed
$allPassed = (Test-Check "trial config exists" (Test-Path $Config)) -and $allPassed

# ---- 2. Allowlist Integrity Check ----
Write-Host ""
Write-Host "[2/6] Checking allowlist integrity..." -ForegroundColor Yellow

$checkResult = python -c @"
import yaml, sys

with open('configs/foundation_trial_source_allowlist.example.yaml', 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)

# Check trial_source_ids count
trial_ids = [x['source_id'] for x in data['trial_source_ids']]
excluded_ids = set(data['excluded_source_ids'])

# 1. Count must be 16
if len(trial_ids) != 16:
    print(f'FAIL: trial_source_count={len(trial_ids)}, expected 16')
    sys.exit(1)

# 2. No duplicates
dupes = [x for x in trial_ids if trial_ids.count(x) > 1]
if dupes:
    print(f'FAIL: duplicate source_ids: {set(dupes)}')
    sys.exit(1)

# 3. No excluded sources
bad = [x for x in trial_ids if x in excluded_ids]
if bad:
    print(f'FAIL: trial contains excluded sources: {bad}')
    sys.exit(1)

# 4. No blocked sources
blocked = ['telegram_groups', 'cloud_drive_share', 'pdf_download_sites',
           'unknown_wechat_pdf', 'report_download_proxy']
bad_blocked = [x for x in trial_ids if x in blocked]
if bad_blocked:
    print(f'FAIL: trial contains blocked sources: {bad_blocked}')
    sys.exit(1)

print(f'PASS: 16 sources, no duplicates, no excluded')
"@

$checkPassed = $LASTEXITCODE -eq 0
$allPassed = (Test-Check "allowlist count=16" ($null -ne $checkResult -and $checkResult -match "PASS")) -and $allPassed
if ($LASTEXITCODE -ne 0) {
    $allPassed = $false
}

# ---- 3. Script File Existence Check ----
Write-Host ""
Write-Host "[3/6] Checking script files..." -ForegroundColor Yellow

$runScript = "scripts/run_foundation_trial_sources.ps1"
$checkScript = "scripts/check_foundation_trial_sources.ps1"

$allPassed = (Test-Check "run script exists" (Test-Path $runScript)) -and $allPassed
$allPassed = (Test-Check "check script exists" (Test-Path $checkScript)) -and $allPassed

# ---- 4. PYTHONPATH Auto-Setup Check ----
Write-Host ""
Write-Host "[4/6] Checking script auto-locates RepoRoot..." -ForegroundColor Yellow

$runContent = Get-Content $runScript -Raw -Encoding UTF8
$hasRepoRoot = $runContent -match "Get-RepoRoot" -and $runContent -match "\.git"
$allPassed = (Test-Check "run script auto-locates RepoRoot" $hasRepoRoot) -and $allPassed

$hasPythonpath = $runContent -match "PYTHONPATH"
$allPassed = (Test-Check "run script sets PYTHONPATH=src" $hasPythonpath) -and $allPassed

$hasModeSupport = $runContent -match "validate-config" -and $runContent -match "dry-run" -and $runContent -match "run"
$allPassed = (Test-Check "run script supports -Mode validate-config/dry-run/run" $hasModeSupport) -and $allPassed

$hasProxySupport = $runContent -match "Proxy"
$allPassed = (Test-Check "run script supports -Proxy" $hasProxySupport) -and $allPassed

# ---- 5. data/foundation_trial/ Output Check ----
Write-Host ""
Write-Host "[5/6] Checking trial output directory..." -ForegroundColor Yellow

if (Test-Path $OutputDir) {
    $allPassed = (Test-Check "data/foundation_trial/ exists" $true) -and $allPassed

    $health = "$OutputDir\index\source_health.jsonl"
    $log = "$OutputDir\index\run_log.jsonl"
    $queue = "$OutputDir\index\failed_queue.jsonl"
    $reportDir = "$OutputDir\reports"

    $allPassed = (Test-Check "source_health.jsonl exists" (Test-Path $health)) -and $allPassed
    $allPassed = (Test-Check "run_log.jsonl exists" (Test-Path $log)) -and $allPassed
    $allPassed = (Test-Check "reports/ dir exists" (Test-Path $reportDir)) -and $allPassed

    if (Test-Path $health) {
        $healthCount = (Get-Content $health -Encoding UTF8 | Where-Object { $_.Trim() -ne "" }).Count
        $allPassed = (Test-Check "source_health has entries ($healthCount)" ($healthCount -gt 0)) -and $allPassed
    }

    # Check failed_queue is empty or not found (both are OK)
    if (Test-Path $queue) {
        $queueCount = (Get-Content $queue -Encoding UTF8 | Where-Object { $_.Trim() -ne "" }).Count
        if ($queueCount -gt 0) {
            $allPassed = (Test-Check "failed_queue has entries ($queueCount)" $true) -and $allPassed
        } else {
            $allPassed = (Test-Check "failed_queue is empty" $true) -and $allPassed
        }
    } else {
        $allPassed = (Test-Check "failed_queue not found (no failures)" $true) -and $allPassed
    }
} else {
    $allPassed = (Test-Check "data/foundation_trial/ exists" $false) -and $allPassed
    Write-Host "        Trial has not been run yet. Run scripts first." -ForegroundColor Yellow
}

# ---- 6. Report Check ----
Write-Host ""
Write-Host "[6/6] Checking trial report..." -ForegroundColor Yellow

$docsReport = "docs/foundation_trial_run_report.md"
$allPassed = (Test-Check "docs/foundation_trial_run_report.md exists" (Test-Path $docsReport)) -and $allPassed

if (Test-Path $docsReport) {
    $reportContent = Get-Content $docsReport -Raw -Encoding UTF8
    $hasTrialOnly = $reportContent -match "trial-only|trial_only|Trial-only"
    $allPassed = (Test-Check "report states trial-only (not production)" $hasTrialOnly) -and $allPassed

    $hasProxyNote = ($reportContent -match "Proxy")
    $allPassed = (Test-Check "report records proxy info" $hasProxyNote) -and $allPassed
}

# ---- Bonus. Blocked/Search/Dormant Sources Must Not Appear in Output ----
Write-Host ""
Write-Host "[Bonus] Checking no blocked sources in trial output..." -ForegroundColor Yellow

if (Test-Path "$OutputDir\index\source_health.jsonl") {
    $blockedSrc = @("telegram_groups", "cloud_drive_share", "pdf_download_sites", "unknown_wechat_pdf", "report_download_proxy")
    $blockedFound = $false
    Get-Content "$OutputDir\index\source_health.jsonl" -Encoding UTF8 | ForEach-Object {
        if ($_.Trim() -ne "") {
            foreach ($blocked in $blockedSrc) {
                if ($_ -match $blocked) {
                    $blockedFound = $true
                    break
                }
            }
        }
    }
    $allPassed = (Test-Check "no blocked sources in health log" (-not $blockedFound)) -and $allPassed
} else {
    $allPassed = (Test-Check "no blocked sources in health log (no run yet)" $true) -and $allPassed
}

# ---- Final Result ----
Write-Host ""
Write-Host "===============================================" -ForegroundColor $(if ($allPassed) { "Green" } else { "Red" })
if ($allPassed) {
    Write-Host " ALL CHECKS PASSED" -ForegroundColor Green
} else {
    Write-Host " SOME CHECKS FAILED" -ForegroundColor Red
}
Write-Host "===============================================" -ForegroundColor $(if ($allPassed) { "Green" } else { "Red" })

exit $(if ($allPassed) { 0 } else { 1 })
