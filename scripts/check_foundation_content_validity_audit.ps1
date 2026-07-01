# check_foundation_content_validity_audit.ps1
# M3C-5A5 Content Validity Audit Check Script
# 20 checks: config, inputs, outputs, coverage, safety, git safety

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

function Get-JsonlRecords {
    param([string]$Path)
    $records = @()
    if (Test-Path $Path) {
        $lines = Get-Content $Path -Encoding UTF8 | Where-Object { $_.Trim() -ne "" }
        foreach ($line in $lines) {
            try {
                $records += ($line | ConvertFrom-Json)
            } catch {
                # Skip malformed lines
            }
        }
    }
    return $records
}

# ============================================================
# Main Logic
# ============================================================

$RepoRoot = Get-RepoRoot
Set-Location $RepoRoot

Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host " OPC Foundation M3C-5A5 Content Validity Check" -ForegroundColor Cyan
Write-Host " 20 checks total" -ForegroundColor Cyan
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

$passed = 0
$failed = 0

# ---- Check 1: Config file exists ----
Write-Host "1/20. Checking config file..." -ForegroundColor Yellow
if (Test-CheckItem "Config file exists" (Test-Path $Config) "Path: $Config") {
    $passed++
} else {
    $failed++
}

# ---- Check 2: trial_v2 allowlist exists ----
Write-Host "2/20. Checking trial_v2 allowlist..." -ForegroundColor Yellow
$allowlistPath = "configs/foundation_trial_v2_allowlist.example.yaml"
if (Test-CheckItem "Trial v2 allowlist exists" (Test-Path $allowlistPath) "Path: $allowlistPath") {
    $passed++
} else {
    $failed++
}

# ---- Check 3: source inventory exists ----
Write-Host "3/20. Checking source inventory..." -ForegroundColor Yellow
$inventoryPath = "configs/foundation_source_inventory.example.yaml"
if (Test-CheckItem "Source inventory exists" (Test-Path $inventoryPath) "Path: $inventoryPath") {
    $passed++
} else {
    $failed++
}

# ---- Check 4: operational source count = 21 ----
Write-Host "4/20. Checking operational source count..." -ForegroundColor Yellow
$yamlContent = ""
if (Test-Path $Config) {
    $yamlContent = Get-Content $Config -Raw -Encoding UTF8
}
$opCountMatch = $yamlContent -match "operational_source_count:\s*(\d+)"
if ($opCountMatch) {
    $opCount = [int]$matches[1]
    if (Test-CheckItem "Operational source count = 21" ($opCount -eq 21) "Found: $opCount") {
        $passed++
    } else {
        $failed++
    }
} else {
    Test-CheckItem "Operational source count = 21" $false "Pattern not found in config"
    $failed++
}

# ---- Check 5: source inventory count = 92 ----
Write-Host "5/20. Checking source inventory count..." -ForegroundColor Yellow
$invCountMatch = $yamlContent -match "source_inventory_count:\s*(\d+)"
if ($invCountMatch) {
    $invCount = [int]$matches[1]
    if (Test-CheckItem "Source inventory count = 92" ($invCount -eq 92) "Found: $invCount") {
        $passed++
    } else {
        $failed++
    }
} else {
    Test-CheckItem "Source inventory count = 92" $false "Pattern not found in config"
    $failed++
}

# ---- Check 6: source_content_audit.jsonl exists ----
Write-Host "6/20. Checking audit JSONL..." -ForegroundColor Yellow
$auditJsonl = "$OutputDir\index\source_content_audit.jsonl"
if (Test-CheckItem "Audit JSONL exists" (Test-Path $auditJsonl) "Path: $auditJsonl") {
    $passed++
} else {
    Test-CheckItem "Audit JSONL exists" $false "Not generated yet (run audit first)"
    $failed++
}

# ---- Check 7: source_content_validity_matrix.jsonl exists ----
Write-Host "7/20. Checking matrix JSONL..." -ForegroundColor Yellow
$matrixJsonl = "$OutputDir\index\source_content_validity_matrix.jsonl"
if (Test-CheckItem "Matrix JSONL exists" (Test-Path $matrixJsonl) "Path: $matrixJsonl") {
    $passed++
} else {
    Test-CheckItem "Matrix JSONL exists" $false "Not generated yet (run audit or matrix mode)"
    $failed++
}

# ---- Check 8: Audit JSONL covers all 21 operational sources ----
Write-Host "8/20. Checking audit JSONL coverage (21 operational sources)..." -ForegroundColor Yellow
$auditRecords = Get-JsonlRecords -Path $auditJsonl
if ($auditRecords.Count -gt 0) {
    # Get unique source IDs from audit JSONL
    $auditedSourceIds = @()
    foreach ($rec in $auditRecords) {
        $sid = $rec.source_id
        if ($sid -and $sid -notin $auditedSourceIds) {
            $auditedSourceIds += $sid
        }
    }
    $auditCoverageOk = ($auditedSourceIds.Count -ge 21)
    if (Test-CheckItem "Audit JSONL covers 21 operational sources" $auditCoverageOk "Unique sources found: $($auditedSourceIds.Count)") {
        $passed++
    } else {
        $failed++
    }
} else {
    Test-CheckItem "Audit JSONL covers 21 operational sources" $false "Audit JSONL not available or empty"
    $failed++
}

# ---- Check 9: Matrix JSONL covers all 92 sources ----
Write-Host "9/20. Checking matrix JSONL coverage (92 sources)..." -ForegroundColor Yellow
$matrixRecords = Get-JsonlRecords -Path $matrixJsonl
if ($matrixRecords.Count -gt 0) {
    $matrixSourceIds = @()
    foreach ($rec in $matrixRecords) {
        $sid = $rec.source_id
        if ($sid -and $sid -notin $matrixSourceIds) {
            $matrixSourceIds += $sid
        }
    }
    $matrixCoverageOk = ($matrixSourceIds.Count -ge 92)
    if (Test-CheckItem "Matrix JSONL covers 92 sources" $matrixCoverageOk "Unique sources found: $($matrixSourceIds.Count)") {
        $passed++
    } else {
        $failed++
    }
} else {
    Test-CheckItem "Matrix JSONL covers 92 sources" $false "Matrix JSONL not available or empty"
    $failed++
}

# ---- Check 10: Every operational source has content_status ----
Write-Host "10/20. Checking content_status for operational sources..." -ForegroundColor Yellow
if ($auditRecords.Count -gt 0) {
    $missingStatus = 0
    foreach ($rec in $auditRecords) {
        if (-not $rec.content_status) {
            $missingStatus++
        }
    }
    if (Test-CheckItem "All operational sources have content_status" ($missingStatus -eq 0) "Missing: $missingStatus") {
        $passed++
    } else {
        $failed++
    }
} else {
    Test-CheckItem "All operational sources have content_status" $false "Audit JSONL not available"
    $failed++
}

# ---- Check 11: Every source has expected_content_goal ----
Write-Host "11/20. Checking expected_content_goal for all sources..." -ForegroundColor Yellow
if ($matrixRecords.Count -gt 0) {
    $missingGoal = 0
    foreach ($rec in $matrixRecords) {
        if (-not $rec.expected_content_goal) {
            $missingGoal++
        }
    }
    if (Test-CheckItem "All sources have expected_content_goal" ($missingGoal -eq 0) "Missing: $missingGoal") {
        $passed++
    } else {
        $failed++
    }
} else {
    Test-CheckItem "All sources have expected_content_goal" $false "Matrix JSONL not available"
    $failed++
}

# ---- Check 12: Every not_audited source has not_audited_reason ----
Write-Host "12/20. Checking not_audited_reason for not_audited sources..." -ForegroundColor Yellow
if ($matrixRecords.Count -gt 0) {
    $notAuditedWithoutReason = 0
    foreach ($rec in $matrixRecords) {
        if ($rec.content_status -eq "not_audited" -and -not $rec.not_audited_reason) {
            $notAuditedWithoutReason++
        }
    }
    if (Test-CheckItem "All not_audited sources have not_audited_reason" ($notAuditedWithoutReason -eq 0) "Missing reasons: $notAuditedWithoutReason") {
        $passed++
    } else {
        $failed++
    }
} else {
    Test-CheckItem "All not_audited sources have not_audited_reason" $false "Matrix JSONL not available"
    $failed++
}

# ---- Check 13: Status statistics exist (content_ready/watch/reject/technical_only/not_audited) ----
Write-Host "13/20. Checking status statistics coverage..." -ForegroundColor Yellow
if ($matrixRecords.Count -gt 0) {
    $hasReady = $false
    $hasWatch = $false
    $hasReject = $false
    $hasTechnical = $false
    $hasNotAudited = $false
    foreach ($rec in $matrixRecords) {
        switch ($rec.content_status) {
            "content_ready" { $hasReady = $true }
            "content_watch" { $hasWatch = $true }
            "content_reject" { $hasReject = $true }
            "technical_only" { $hasTechnical = $true }
            "not_audited" { $hasNotAudited = $true }
        }
    }
    $allStatsPresent = $hasReady -or $hasWatch -or $hasReject -or $hasTechnical -or $hasNotAudited
    $statsSummary = "ready=$hasReady, watch=$hasWatch, reject=$hasReject, tech=$hasTechnical, not_audited=$hasNotAudited"
    if (Test-CheckItem "Status statistics present in matrix" $allStatsPresent $statsSummary) {
        $passed++
    } else {
        $failed++
    }
} else {
    Test-CheckItem "Status statistics present in matrix" $false "Matrix JSONL not available"
    $failed++
}

# ---- Check 14: technical_only not in scheduling recommendation ----
Write-Host "14/20. Checking technical_only exclusion from scheduling..." -ForegroundColor Yellow
if ($matrixRecords.Count -gt 0) {
    $techInScheduling = 0
    foreach ($rec in $matrixRecords) {
        if ($rec.content_status -eq "technical_only" -and $rec.scheduling_recommendation) {
            $techInScheduling++
        }
    }
    if (Test-CheckItem "technical_only excluded from scheduling" ($techInScheduling -eq 0) "Found in scheduling: $techInScheduling") {
        $passed++
    } else {
        $failed++
    }
} else {
    Test-CheckItem "technical_only excluded from scheduling" $false "Matrix JSONL not available"
    $failed++
}

# ---- Check 15: content_reject not in scheduling recommendation ----
Write-Host "15/20. Checking content_reject exclusion from scheduling..." -ForegroundColor Yellow
if ($matrixRecords.Count -gt 0) {
    $rejectInScheduling = 0
    foreach ($rec in $matrixRecords) {
        if ($rec.content_status -eq "content_reject" -and $rec.scheduling_recommendation) {
            $rejectInScheduling++
        }
    }
    if (Test-CheckItem "content_reject excluded from scheduling" ($rejectInScheduling -eq 0) "Found in scheduling: $rejectInScheduling") {
        $passed++
    } else {
        $failed++
    }
} else {
    Test-CheckItem "content_reject excluded from scheduling" $false "Matrix JSONL not available"
    $failed++
}

# ---- Check 16: Report does not contain full proxy URL ----
Write-Host "16/20. Checking report safety (no proxy URL)..." -ForegroundColor Yellow
$reportPath = "$OutputDir\reports\content_validity_audit_latest.md"
if (Test-Path $reportPath) {
    $reportContent = Get-Content $reportPath -Raw -Encoding UTF8
    # Check for common proxy URL patterns (http://, https:// followed by proxy-like patterns)
    $hasProxyUrl = $false
    if ($reportContent -match "https?://[^`"'\s]*:(\d{2,5})") {
        $hasProxyUrl = $true
    }
    if ($reportContent -match "proxy_url\s*[:=]\s*`"?(https?://)") {
        $hasProxyUrl = $true
    }
    if (Test-CheckItem "Report does not contain proxy URL" (-not $hasProxyUrl) "proxy_url found: $hasProxyUrl") {
        $passed++
    } else {
        $failed++
    }
} else {
    Test-CheckItem "Report does not contain proxy URL" $false "Report not generated yet"
    $failed++
}

# ---- Check 17: Report does not contain secrets/cookie/token ----
Write-Host "17/20. Checking report safety (no secrets)..." -ForegroundColor Yellow
if (Test-Path $reportPath) {
    $reportContent = Get-Content $reportPath -Raw -Encoding UTF8
    $hasSecret = $false
    $secretPatterns = @("cookie", "token", "secret", "api_key", "apikey", "password")
    foreach ($pat in $secretPatterns) {
        if ($reportContent -match "(?i)$pat\s*[:=]\s*`"[^`"]{8,}`"") {
            $hasSecret = $true
            break
        }
    }
    if (Test-CheckItem "Report does not contain secrets/cookie/token" (-not $hasSecret) "Secrets found: $hasSecret") {
        $passed++
    } else {
        $failed++
    }
} else {
    Test-CheckItem "Report does not contain secrets/cookie/token" $false "Report not generated yet"
    $failed++
}

# ---- Check 18: Current trial_v1 not modified ----
Write-Host "18/20. Checking trial_v1 safety..." -ForegroundColor Yellow
$trialV1Path = "configs/foundation_trial_v1_sources.yaml"
$trialV1ExamplePath = "configs/foundation_trial_v1_sources.example.yaml"
$gitDirtyV1 = $false

if (Test-Path $trialV1Path) {
    $gitStatus = git diff --name-only -- "configs/foundation_trial_v1_sources.yaml" 2>$null
    if ($gitStatus) {
        $gitDirtyV1 = $true
    }
    $gitStatus2 = git diff --cached --name-only -- "configs/foundation_trial_v1_sources.yaml" 2>$null
    if ($gitStatus2) {
        $gitDirtyV1 = $true
    }
}
if (-not $gitDirtyV1 -and (Test-Path $trialV1ExamplePath)) {
    $gitStatus3 = git diff --name-only -- "configs/foundation_trial_v1_sources.example.yaml" 2>$null
    if ($gitStatus3) {
        $gitDirtyV1 = $true
    }
}

if (Test-CheckItem "Trial v1 not modified" (-not $gitDirtyV1) "Git dirty: $gitDirtyV1") {
    $passed++
} else {
    $failed++
}

# ---- Check 19: TRAE scheduling not modified ----
Write-Host "19/20. Checking TRAE scheduling safety..." -ForegroundColor Yellow
$traeSchedulePath = "configs/foundation_trae_schedule.yaml"
$traeScheduleExamplePath = "configs/foundation_trae_schedule.example.yaml"
$gitDirtyTrae = $false

if (Test-Path $traeSchedulePath) {
    $gitStatus = git diff --name-only -- "configs/foundation_trae_schedule.yaml" 2>$null
    if ($gitStatus) {
        $gitDirtyTrae = $true
    }
}
if (-not $gitDirtyTrae -and (Test-Path $traeScheduleExamplePath)) {
    $gitStatus = git diff --name-only -- "configs/foundation_trae_schedule.example.yaml" 2>$null
    if ($gitStatus) {
        $gitDirtyTrae = $true
    }
}

if (Test-CheckItem "TRAE scheduling not modified" (-not $gitDirtyTrae) "Git dirty: $gitDirtyTrae") {
    $passed++
} else {
    $failed++
}

# ---- Check 20: data/ not committed ----
Write-Host "20/20. Checking data directory safety..." -ForegroundColor Yellow
$dataInGit = $false
$gitLsOutput = git ls-files -- "data/" 2>$null
if ($gitLsOutput) {
    $dataLines = $gitLsOutput -split "`n" | Where-Object { $_.Trim() -ne "" }
    if ($dataLines.Count -gt 0) {
        $dataInGit = $true
    }
}
$gitStatusData = git status --porcelain -- "data/" 2>$null
$dataStaged = $false
if ($gitStatusData) {
    $dataStatusLines = $gitStatusData -split "`n" | Where-Object { $_.Trim() -ne "" -and $_.Trim() -match "^[AM]" }
    if ($dataStatusLines.Count -gt 0) {
        $dataStaged = $true
    }
}

if (Test-CheckItem "Data directory not committed" ((-not $dataInGit) -and (-not $dataStaged)) "Tracked: $dataInGit, Staged: $dataStaged") {
    $passed++
} else {
    $failed++
}

# ---- Summary ----
Write-Host ""
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host " Check Summary: $passed / 20 passed, $failed failed" -ForegroundColor $(if ($failed -eq 0) { "Green" } else { "Yellow" })
Write-Host "===============================================" -ForegroundColor Cyan
Write-Host ""

if ($failed -eq 0) {
    Write-Host "All 20 checks PASSED" -ForegroundColor Green
    Write-Host ""
    Write-Host "NOTE: Run the full audit with:" -ForegroundColor Yellow
    Write-Host "  powershell -ExecutionPolicy Bypass -File scripts/run_foundation_content_validity_audit.ps1 -Mode audit" -ForegroundColor Yellow
    exit 0
} else {
    Write-Host "$failed check(s) FAILED, $passed check(s) PASSED" -ForegroundColor Red
    exit 1
}
