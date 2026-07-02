# OPC Foundation Trial V2 Content-Ready Check Script
# M3C-5A8
# Performs 14-item verification of content-ready scheduling setup

$ErrorActionPreference = "Continue"

# Auto-locate RepoRoot
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path "$ScriptDir\..").Path

Write-Host "=== OPC Foundation Trial V2 Content-Ready Check ===" -ForegroundColor Cyan
Write-Host "RepoRoot: $RepoRoot"

$AllowlistPath = Join-Path $RepoRoot "configs\foundation_trial_v2_content_ready_allowlist.example.yaml"
$TraeConfigPath = Join-Path $RepoRoot "configs\trae_foundation_trial_v2_content_ready.example.yaml"
$RunScript = Join-Path $RepoRoot "scripts\run_foundation_trial_v2_content_ready.ps1"
$CheckScript = $RepoRoot + "\" + $MyInvocation.MyCommand.Name
$OutputDir = Join-Path $RepoRoot "data\foundation_trial_v2_content_ready"
$IndexDir = Join-Path $OutputDir "index"
$ReportDir = Join-Path $OutputDir "reports"

$passCount = 0
$failCount = 0
$totalChecks = 14

function Check-Item {
    param([string]$Name, [bool]$Passed, [string]$Detail)
    if ($Passed) {
        Write-Host "  [PASS] $Name" -ForegroundColor Green
        $script:passCount++
    } else {
        Write-Host "  [FAIL] $Name - $Detail" -ForegroundColor Red
        $script:failCount++
    }
}

# Check 1: Content-ready allowlist exists
Check-Item "Allowlist exists" (Test-Path $AllowlistPath) ""

# Check 2: Source count
if (Test-Path $AllowlistPath) {
    $config = Get-Content $AllowlistPath -Raw | ConvertFrom-Yaml
    $count = $config.sources.Count
    Check-Item "Source count >= 9" ($count -ge 9) "Got $count"
} else {
    Check-Item "Source count" $false "Allowlist not found"
}

# Check 3: All sources content_ready
if (Test-Path $AllowlistPath) {
    $allReady = $true
    $nonReady = @()
    foreach ($src in $config.sources) {
        if ($src.content_status -ne "content_ready") {
            $allReady = $false
            $nonReady += $src.source_id
        }
    }
    Check-Item "All sources content_ready" $allReady ($nonReady -join ", ")
} else {
    Check-Item "All sources content_ready" $false "Allowlist not found"
}

# Check 4: No content_watch
if (Test-Path $AllowlistPath) {
    $hasWatch = $false
    foreach ($src in $config.sources) {
        if ($src.content_status -eq "content_watch") { $hasWatch = $true; break }
    }
    Check-Item "No content_watch in allowlist" (-not $hasWatch) ""
} else {
    Check-Item "No content_watch" $false "Allowlist not found"
}

# Check 5: No content_reject
if (Test-Path $AllowlistPath) {
    $hasReject = $false
    foreach ($src in $config.sources) {
        if ($src.content_status -eq "content_reject") { $hasReject = $true; break }
    }
    Check-Item "No content_reject in allowlist" (-not $hasReject) ""
} else {
    Check-Item "No content_reject" $false "Allowlist not found"
}

# Check 6: No technical_only
if (Test-Path $AllowlistPath) {
    $hasTech = $false
    foreach ($src in $config.sources) {
        if ($src.content_status -eq "technical_only") { $hasTech = $true; break }
    }
    Check-Item "No technical_only in allowlist" (-not $hasTech) ""
} else {
    Check-Item "No technical_only" $false "Allowlist not found"
}

# Check 7: production_enabled=false
if (Test-Path $AllowlistPath) {
    Check-Item "production_enabled=false" ($config.scope.production_enabled -eq $false) ""
} else {
    Check-Item "production_enabled=false" $false "Allowlist not found"
}

# Check 8: trae_scheduling_enabled=false
if (Test-Path $AllowlistPath) {
    Check-Item "trae_scheduling_enabled=false" ($config.scope.trae_scheduling_enabled -eq $false) ""
} else {
    Check-Item "trae_scheduling_enabled=false" $false "Allowlist not found"
}

# Check 9: TRAE example config exists
Check-Item "TRAE example config exists" (Test-Path $TraeConfigPath) ""

# Check 10: TRAE example enabled=false
if (Test-Path $TraeConfigPath) {
    $traeConfig = Get-Content $TraeConfigPath -Raw | ConvertFrom-Yaml
    $allDisabled = $true
    foreach ($job in $traeConfig.jobs) {
        if ($job.enabled -ne $false) { $allDisabled = $false; break }
    }
    Check-Item "All TRAE jobs enabled=false" $allDisabled ""
} else {
    Check-Item "TRAE jobs disabled" $false "Config not found"
}

# Check 11: Run script exists
Check-Item "Run script exists" (Test-Path $RunScript) ""

# Check 12: Check script exists
Check-Item "Check script exists" (Test-Path $CheckScript) ""

# Check 13: Output directory exists
Check-Item "Output directory exists" (Test-Path $IndexDir) ""

# Check 14: Reports directory exists
Check-Item "Reports directory exists" (Test-Path $ReportDir) ""

Write-Host ""
Write-Host "=== Check Results ===" -ForegroundColor Cyan
Write-Host "PASS: $passCount / $totalChecks"
Write-Host "FAIL: $failCount / $totalChecks"
if ($failCount -eq 0) {
    Write-Host "OVERALL: PASS" -ForegroundColor Green
} else {
    Write-Host "OVERALL: FAIL ($failCount items)" -ForegroundColor Red
}
