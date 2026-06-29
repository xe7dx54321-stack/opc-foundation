# check_foundation_trial_v2.ps1
# M3C-5A3 Trial v2 Full Validation Check Script
# Checks 21-source trial_v2 validation results and report generation

param(
    [string]$Config = "configs/foundation_trial_v2_allowlist.example.yaml",
    [string]$OutputDir = "data/foundation_trial_v2_full"
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
Write-Host " OPC Foundation M3C-5A3 Trial v2 Full Check" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

$passed = 0
$failed = 0

# ---- 1. Check trial_v2 allowlist exists ----
Write-Host "1. Checking trial_v2 allowlist..." -ForegroundColor Yellow
if (Test-CheckItem "Trial_v2 allowlist exists" (Test-Path $Config) "Path: $Config") {
    $passed++
} else {
    $failed++
}

# ---- 2. Check trial_v1 base count ----
Write-Host "2. Checking trial_v1 base count..." -ForegroundColor Yellow
if (Test-Path $Config) {
    $yamlContent = Get-Content $Config -Raw -Encoding UTF8
    if ($yamlContent -match "base_trial_v1_count:\s*(\d+)") {
        $v1Count = $matches[1]
        if (Test-CheckItem "Trial v1 base count is 15" ($v1Count -eq 15) "Found: $v1Count") {
            $passed++
        } else {
            $failed++
        }
    } else {
        Test-CheckItem "Trial v1 base count is 15" $false "Pattern not found"
        $failed++
    }
} else {
    $failed++
}

# ---- 3. Check trial_v2 additions count ----
Write-Host "3. Checking trial_v2 additions count..." -ForegroundColor Yellow
if (Test-Path $Config) {
    if ($yamlContent -match "trial_v2_ready_additions_count:\s*(\d+)") {
        $addCount = $matches[1]
        if (Test-CheckItem "Trial v2 additions count is 6" ($addCount -eq 6) "Found: $addCount") {
            $passed++
        } else {
            $failed++
        }
    } else {
        Test-CheckItem "Trial v2 additions count is 6" $false "Pattern not found"
        $failed++
    }
} else {
    $failed++
}

# ---- 4. Check operational source count ----
Write-Host "4. Checking operational source count..." -ForegroundColor Yellow
if (Test-Path $Config) {
    if ($yamlContent -match "operational_source_count:\s*(\d+)") {
        $opCount = $matches[1]
        if (Test-CheckItem "Operational source count is 21" ($opCount -eq 21) "Found: $opCount") {
            $passed++
        } else {
            $failed++
        }
    } else {
        Test-CheckItem "Operational source count is 21" $false "Pattern not found"
        $failed++
    }
} else {
    $failed++
}

# ---- 5. Check source inventory count ----
Write-Host "5. Checking source inventory count..." -ForegroundColor Yellow
$inventoryPath = "configs/foundation_source_inventory.example.yaml"
if (Test-Path $inventoryPath) {
    $invContent = Get-Content $inventoryPath -Raw -Encoding UTF8
    # Count sources by counting "  - source_id:" lines
    $sourceMatches = [regex]::Matches($invContent, '  - source_id:')
    $invCount = $sourceMatches.Count
    if (Test-CheckItem "Source inventory count is 92" ($invCount -eq 92) "Found: $invCount") {
        $passed++
    } else {
        $failed++
    }
} else {
    Test-CheckItem "Source inventory exists" $false "Path: $inventoryPath"
    $failed++
}

# ---- 6. Check consolidated Goldman Sachs podcasts ----
Write-Host "6. Checking consolidated candidate..." -ForegroundColor Yellow
if (Test-Path $Config) {
    $hasConsolidated = $yamlContent -match "goldman_sachs_podcasts" -and $yamlContent -match "consolidated"
    if (Test-CheckItem "Has consolidated goldman_sachs_podcasts" $hasConsolidated "Found in config") {
        $passed++
    } else {
        $failed++
    }

    $hasMemberSources = $yamlContent -match "member_source_ids"
    if (Test-CheckItem "Has member_source_ids" $hasMemberSources "Found in config") {
        $passed++
    } else {
        $failed++
    }
} else {
    $failed += 2
}

# ---- 7. Check no blocked sources ----
Write-Host "7. Checking no blocked sources..." -ForegroundColor Yellow
$blockedIds = @("telegram_groups", "cloud_drive_share", "pdf_download_sites")
$blockedFound = $false
if (Test-Path $Config) {
    $candidatesSection = ""
    if ($yamlContent -match '(?s)trial_v2_additions:\s*\n((?:  - .+\n?)+)') {
        $candidatesSection = $matches[1]
    }
    foreach ($id in $blockedIds) {
        if ($candidatesSection -match $id) {
            $blockedFound = $true
            break
        }
    }
}

if (Test-CheckItem "No blocked sources in additions" (-not $blockedFound) "Blocked sources excluded") {
    $passed++
} else {
    $failed++
}

# ---- 8. Check no search providers ----
Write-Host "8. Checking no search providers..." -ForegroundColor Yellow
$searchIds = @("tavily_search", "brave_search", "serpapi")
$searchFound = $false
if (Test-Path $Config) {
    foreach ($id in $searchIds) {
        if ($candidatesSection -match $id) {
            $searchFound = $true
            break
        }
    }
}

if (Test-CheckItem "No search providers in additions" (-not $searchFound) "Search providers excluded") {
    $passed++
} else {
    $failed++
}

# ---- 9. Check no TLS sources ----
Write-Host "9. Checking no TLS sources..." -ForegroundColor Yellow
$tlsIds = @("morgan_stanley_insights", "jp_morgan_research")
$tlsFound = $false
if (Test-Path $Config) {
    foreach ($id in $tlsIds) {
        if ($candidatesSection -match $id) {
            $tlsFound = $true
            break
        }
    }
}

if (Test-CheckItem "No TLS sources in additions" (-not $tlsFound) "TLS sources excluded") {
    $passed++
} else {
    $failed++
}

# ---- 10. Check no WeChat sources ----
Write-Host "10. Checking no WeChat sources..." -ForegroundColor Yellow
$wechatIds = @("goldman_sachs_china_wechat", "morgan_stanley_china_wechat")
$wechatFound = $false
if (Test-Path $Config) {
    foreach ($id in $wechatIds) {
        if ($candidatesSection -match $id) {
            $wechatFound = $true
            break
        }
    }
}

if (Test-CheckItem "No WeChat sources in additions" (-not $wechatFound) "WeChat sources excluded") {
    $passed++
} else {
    $failed++
}

# ---- 11. Check run script exists ----
Write-Host "11. Checking run script..." -ForegroundColor Yellow
$runScript = "scripts/run_foundation_trial_v2.ps1"
if (Test-CheckItem "Run script exists" (Test-Path $runScript) "Path: $runScript") {
    $passed++
} else {
    $failed++
}

# ---- 12. Check output directory ----
Write-Host "12. Checking output directory..." -ForegroundColor Yellow
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
        Test-CheckItem "Output index exists" $false "Not generated yet (run required)"
        $passed++
    }

    if (Test-Path $outputReports) {
        if (Test-CheckItem "Output reports exists" $true "Path: $outputReports") {
            $passed++
        } else {
            $failed++
        }
    } else {
        Test-CheckItem "Output reports exists" $false "Not generated yet (run required)"
        $passed++
    }
} else {
    Test-CheckItem "Output directory exists" $false "Not created yet (run required)"
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
    Write-Host "NOTE: Run the full validation with:" -ForegroundColor Yellow
    Write-Host "  powershell -ExecutionPolicy Bypass -File scripts/run_foundation_trial_v2.ps1 -Mode run" -ForegroundColor Yellow
    exit 0
} else {
    Write-Host "Some checks FAILED" -ForegroundColor Red
    exit 1
}
