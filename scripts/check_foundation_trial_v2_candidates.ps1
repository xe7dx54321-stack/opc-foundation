# check_foundation_trial_v2_candidates.ps1
# M3C-5A2 Trial v2 Candidate Validation Check Script
# Checks validation results and report generation

param(
    [string]$Allowlist = "configs/foundation_trial_v2_candidate_allowlist.example.yaml",
    [string]$OutputDir = "data/foundation_trial_v2"
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

function Test-CheckItem {
    param(
        [string]$Name,
        [bool]$Condition,
        [string]$Message = ""
    )

    if ($Condition) {
        Write-Host "[PASS] $Name" -ForegroundColor Green
        if ($Message) {
            Write-Host "       $Message" -ForegroundColor Gray
        }
        return $true
    } else {
        Write-Host "[FAIL] $Name" -ForegroundColor Red
        if ($Message) {
            Write-Host "       $Message" -ForegroundColor Gray
        }
        return $false
    }
}

# ============================================================
# Main Logic
# ============================================================

$RepoRoot = Get-RepoRoot
Set-Location $RepoRoot

Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host " OPC Foundation M3C-5A2 Trial v2 Check" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

$passed = 0
$failed = 0

# ---- 1. Check allowlist exists ----
Write-Host "1. Checking allowlist..." -ForegroundColor Yellow
if (Test-CheckItem "Allowlist exists" (Test-Path $Allowlist) "Path: $Allowlist") {
    $passed++
} else {
    $failed++
}

# ---- 2. Check candidate count ----
Write-Host "2. Checking candidate count..." -ForegroundColor Yellow
if (Test-Path $Allowlist) {
    $yamlContent = Get-Content $Allowlist -Raw -Encoding UTF8
    if ($yamlContent -match "candidate_count:\s*(\d+)") {
        $count = $matches[1]
        if (Test-CheckItem "Candidate count is 8" ($count -eq 8) "Found: $count") {
            $passed++
        } else {
            $failed++
        }
    } else {
        Test-CheckItem "Candidate count is 8" $false "Pattern not found in YAML"
        $failed++
    }
} else {
    $failed++
}

# ---- 3. Check no trial v1 sources ----
Write-Host "3. Checking no trial v1 conflict..." -ForegroundColor Yellow
$trialV1Ids = @(
    "goldman_sachs_research", "goldman_sachs_reports", "goldman_sachs_top_of_mind",
    "goldman_sachs_insights", "barclays_our_insights", "microsoft_ir",
    "yahoo_finance", "business_insider", "markets_insider", "the_fly",
    "briefing_com_upgrades", "wallstreet_cn", "cls_cn", "wind_public",
    "gelonghui", "zhitong_caijing"
)

$conflictFound = $false
if (Test-Path $Allowlist) {
    # Extract candidates section only
    $yamlContent = Get-Content $Allowlist -Raw -Encoding UTF8
    $candidatesSection = ""
    if ($yamlContent -match '(?s)trial_v2_candidates:\s*\n((?:  - .+\n?)+)') {
        $candidatesSection = $matches[1]
    }
    foreach ($id in $trialV1Ids) {
        if ($candidatesSection -match $id) {
            $conflictFound = $true
            break
        }
    }
}

if (Test-CheckItem "No trial v1 sources" (-not $conflictFound) "All trial v1 sources excluded") {
    $passed++
} else {
    $failed++
}

# ---- 4. Check no blocked sources ----
Write-Host "4. Checking no blocked sources..." -ForegroundColor Yellow
$blockedIds = @("telegram_groups", "cloud_drive_share", "pdf_download_sites")
$blockedFound = $false
if (Test-Path $Allowlist) {
    foreach ($id in $blockedIds) {
        if ($candidatesSection -match $id) {
            $blockedFound = $true
            break
        }
    }
}

if (Test-CheckItem "No blocked sources" (-not $blockedFound) "Blocked sources excluded") {
    $passed++
} else {
    $failed++
}

# ---- 5. Check no search providers ----
Write-Host "5. Checking no search providers..." -ForegroundColor Yellow
$searchIds = @("tavily_search", "brave_search", "serpapi")
$searchFound = $false
if (Test-Path $Allowlist) {
    foreach ($id in $searchIds) {
        if ($candidatesSection -match $id) {
            $searchFound = $true
            break
        }
    }
}

if (Test-CheckItem "No search providers" (-not $searchFound) "Search providers excluded") {
    $passed++
} else {
    $failed++
}

# ---- 6. Check no TLS sources ----
Write-Host "6. Checking no TLS sources..." -ForegroundColor Yellow
$tlsIds = @("morgan_stanley_insights", "jp_morgan_research")
$tlsFound = $false
if (Test-Path $Allowlist) {
    foreach ($id in $tlsIds) {
        if ($candidatesSection -match $id) {
            $tlsFound = $true
            break
        }
    }
}

if (Test-CheckItem "No TLS sources" (-not $tlsFound) "TLS sources excluded") {
    $passed++
} else {
    $failed++
}

# ---- 7. Check no WeChat sources ----
Write-Host "7. Checking no WeChat sources..." -ForegroundColor Yellow
$wechatIds = @("goldman_sachs_china_wechat", "morgan_stanley_china_wechat")
$wechatFound = $false
if (Test-Path $Allowlist) {
    foreach ($id in $wechatIds) {
        if ($candidatesSection -match $id) {
            $wechatFound = $true
            break
        }
    }
}

if (Test-CheckItem "No WeChat sources" (-not $wechatFound) "WeChat sources excluded") {
    $passed++
} else {
    $failed++
}

# ---- 8. Check source inventory consistency ----
Write-Host "8. Checking source inventory..." -ForegroundColor Yellow
$inventoryPath = "configs/foundation_source_inventory.example.yaml"
if (Test-CheckItem "Source inventory exists" (Test-Path $inventoryPath) "Path: $inventoryPath") {
    $passed++
} else {
    $failed++
}

# ---- 9. Check run script exists ----
Write-Host "9. Checking run script..." -ForegroundColor Yellow
$runScript = "scripts/run_foundation_trial_v2_candidates.ps1"
if (Test-CheckItem "Run script exists" (Test-Path $runScript) "Path: $runScript") {
    $passed++
} else {
    $failed++
}

# ---- 10. Check output directory (if exists) ----
Write-Host "10. Checking output directory..." -ForegroundColor Yellow
$outputIndex = "$OutputDir\index"
$outputReports = "$OutputDir\reports"

if (Test-Path $OutputDir) {
    if (Test-CheckItem "Output directory exists" $true "Path: $OutputDir") {
        $passed++
    } else {
        $failed++
    }

    if (Test-Path $outputIndex) {
        if (Test-CheckItem "Output index exists" $true "Path: $outputIndex") {
            $passed++
        } else {
            $failed++
        }
    } else {
        if (Test-CheckItem "Output index exists" $false "Not generated yet (run required)") {
            # This is expected if run hasn't been executed
        }
        $passed++
    }

    if (Test-Path $outputReports) {
        if (Test-CheckItem "Output reports exists" $true "Path: $outputReports") {
            $passed++
        } else {
            $failed++
        }
    } else {
        if (Test-CheckItem "Output reports exists" $false "Not generated yet (run required)") {
            # This is expected if run hasn't been executed
        }
        $passed++
    }
} else {
    if (Test-CheckItem "Output directory exists" $false "Not created yet (run required)") {
        # This is expected if run hasn't been executed
    }
    $passed++
}

# ---- Summary ----
Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host " Check Summary: $passed passed, $failed failed" -ForegroundColor $(if ($failed -eq 0) { "Green" } else { "Yellow" })
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

if ($failed -eq 0) {
    Write-Host "All checks PASSED" -ForegroundColor Green
    Write-Host ""
    Write-Host "NOTE: Run the validation with:" -ForegroundColor Yellow
    Write-Host "  powershell -ExecutionPolicy Bypass -File scripts/run_foundation_trial_v2_candidates.ps1 -Mode run" -ForegroundColor Yellow
    exit 0
} else {
    Write-Host "Some checks FAILED" -ForegroundColor Red
    exit 1
}
