# check_foundation_content_validity_audit.ps1
# M3C-5A4 Content Validity Audit Check Script
# Checks audit results and report generation

param(
    [string]$Config = "configs/foundation_content_validity_audit.example.yaml",
    [string]$OutputDir = "data/foundation_content_validity"
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
Write-Host " OPC Foundation M3C-5A4 Content Validity Check" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

$passed = 0
$failed = 0

# ---- 1. Check config exists ----
Write-Host "1. Checking config..." -ForegroundColor Yellow
if (Test-CheckItem "Config exists" (Test-Path $Config) "Path: $Config") {
    $passed++
} else {
    $failed++
}

# ---- 2. Check input trial_v2 allowlist exists ----
Write-Host "2. Checking input trial_v2 allowlist..." -ForegroundColor Yellow
$allowlistPath = "configs/foundation_trial_v2_allowlist.example.yaml"
if (Test-CheckItem "Trial v2 allowlist exists" (Test-Path $allowlistPath) "Path: $allowlistPath") {
    $passed++
} else {
    $failed++
}

# ---- 3. Check operational source count ----
Write-Host "3. Checking operational source count..." -ForegroundColor Yellow
if (Test-Path $Config) {
    $yamlContent = Get-Content $Config -Raw -Encoding UTF8
    if ($yamlContent -match "operational_source_count:\s*(\d+)") {
        $count = $matches[1]
        if (Test-CheckItem "Operational source count is 21" ($count -eq 21) "Found: $count") {
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

# ---- 4. Check audit script exists ----
Write-Host "4. Checking audit script..." -ForegroundColor Yellow
$auditScript = "scripts/run_foundation_content_validity_audit.ps1"
if (Test-CheckItem "Audit script exists" (Test-Path $auditScript) "Path: $auditScript") {
    $passed++
} else {
    $failed++
}

# ---- 5. Check output directory ----
Write-Host "5. Checking output directory..." -ForegroundColor Yellow
if (Test-Path $OutputDir) {
    if (Test-CheckItem "Output directory exists" $true "Path: $OutputDir") {
        $passed++
    } else {
        $failed++
    }
} else {
    Test-CheckItem "Output directory exists" $false "Not created yet (audit required)"
    $passed++
}

# ---- 6. Check audit JSONL exists ----
Write-Host "6. Checking audit JSONL..." -ForegroundColor Yellow
$auditJsonl = "$OutputDir\index\source_content_audit.jsonl"
if (Test-Path $auditJsonl) {
    # Check if file has content
    $jsonlContent = Get-Content $auditJsonl -Raw -Encoding UTF8
    $lineCount = ($jsonlContent -split "`n" | Where-Object { $_.Trim() -ne "" }).Count

    if (Test-CheckItem "Audit JSONL has content" ($lineCount -gt 0) "Lines: $lineCount") {
        $passed++
    } else {
        $failed++
    }
} else {
    Test-CheckItem "Audit JSONL exists" $false "Not generated yet (audit required)"
    $passed++
}

# ---- 7. Check report exists ----
Write-Host "7. Checking report..." -ForegroundColor Yellow
$reportDir = "$OutputDir\reports"
if (Test-Path $reportDir) {
    $reports = Get-ChildItem "$reportDir\*.md" -ErrorAction SilentlyContinue
    if (Test-CheckItem "Report exists" ($reports.Count -gt 0) "Count: $($reports.Count)") {
        $passed++
    } else {
        Test-CheckItem "Report exists" $false "No reports found"
        $failed++
    }
} else {
    Test-CheckItem "Report exists" $false "Not generated yet (audit required)"
    $passed++
}

# ---- 8. Check run script supports modes ----
Write-Host "8. Checking run script modes..." -ForegroundColor Yellow
if (Test-Path $auditScript) {
    $scriptContent = Get-Content $auditScript -Raw -Encoding UTF8
    $hasValidate = $scriptContent -match "validate-config"
    $hasSample = $scriptContent -match "sample"
    $hasAudit = $scriptContent -match "audit"

    if (Test-CheckItem "Supports validate-config" $hasValidate) {
        $passed++
    } else {
        $failed++
    }
    if (Test-CheckItem "Supports sample" $hasSample) {
        $passed++
    } else {
        $failed++
    }
    if (Test-CheckItem "Supports audit" $hasAudit) {
        $passed++
    } else {
        $failed++
    }
} else {
    $failed += 3
}

# ---- 9. Check run script supports proxy ----
Write-Host "9. Checking proxy support..." -ForegroundColor Yellow
if (Test-Path $auditScript) {
    $scriptContent = Get-Content $auditScript -Raw -Encoding UTF8
    $hasProxy = $scriptContent -match "\$Proxy" -or $scriptContent -match "-Proxy"
    if (Test-CheckItem "Supports -Proxy parameter" $hasProxy) {
        $passed++
    } else {
        $failed++
    }
} else {
    $failed++
}

# ---- 10. Check gitignore coverage ----
Write-Host "10. Checking gitignore coverage..." -ForegroundColor Yellow
$gitignorePath = ".gitignore"
if (Test-Path $gitignorePath) {
    $gitignoreContent = Get-Content $gitignorePath -Raw -Encoding UTF8
    $hasCoverage = $gitignoreContent -match "data/foundation_content_validity" -or $gitignoreContent -match "data/foundation_trial"
    if (Test-CheckItem "Gitignore covers data/foundation_content_validity" $hasCoverage) {
        $passed++
    } else {
        $failed++
    }
} else {
    Test-CheckItem "Gitignore exists" $false
    $failed++
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
    Write-Host "NOTE: Run the full audit with:" -ForegroundColor Yellow
    Write-Host "  powershell -ExecutionPolicy Bypass -File scripts/run_foundation_content_validity_audit.ps1 -Mode audit" -ForegroundColor Yellow
    exit 0
} else {
    Write-Host "Some checks FAILED" -ForegroundColor Red
    exit 1
}
