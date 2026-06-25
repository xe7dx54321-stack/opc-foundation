# Research Archive Foundation - Archive Check Script
#
# Purpose: Check if research archive products exist, output basic health info.
#
# Usage:
#   .\scripts\check_research_archive.ps1
#   .\scripts\check_research_archive.ps1 -ArchiveRoot ./data/research_archive

param(
    [string]$ArchiveRoot = "./data/research_archive"
)

$ErrorActionPreference = "Stop"

# Auto-locate repo root (script is in scripts/, parent is repo root)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

# Set PYTHONPATH to find src/ modules
$env:PYTHONPATH = Join-Path $RepoRoot "src"

Write-Host ""
Write-Host "Research Archive - Archive Check" -ForegroundColor Cyan
Write-Host "Archive Root: $ArchiveRoot"
Write-Host ""

# Check if root directory exists
if (!(Test-Path $ArchiveRoot)) {
    Write-Host "[WARNING] Archive root does not exist: $ArchiveRoot" -ForegroundColor Yellow
    Write-Host "         May not have run research archive yet." -ForegroundColor Yellow
    exit 0
}

# Key files to check
$indexDir = Join-Path $ArchiveRoot "index"
$stateDir = Join-Path $ArchiveRoot "state"
$reportsDir = Join-Path $ArchiveRoot "reports"

$criticalFiles = @(
    @{ Path = (Join-Path $indexDir "documents.jsonl");         Name = "documents.jsonl";         Required = $true },
    @{ Path = (Join-Path $indexDir "documents.latest.jsonl");  Name = "documents.latest.jsonl";  Required = $false },
    @{ Path = (Join-Path $stateDir "run_log.jsonl");           Name = "run_log.jsonl";           Required = $true },
    @{ Path = (Join-Path $stateDir "source_health.jsonl");     Name = "source_health.jsonl";     Required = $true },
    @{ Path = (Join-Path $stateDir "failed_queue.jsonl");      Name = "failed_queue.jsonl";      Required = $false }
)

$missingCritical = 0
$missingOptional = 0

foreach ($file in $criticalFiles) {
    if (Test-Path $file.Path) {
        $size = (Get-Item $file.Path).Length
        Write-Host ("  [OK]   " + $file.Name + " (" + $size + " bytes)") -ForegroundColor Green
    } else {
        if ($file.Required) {
            Write-Host ("  [WARN] " + $file.Name + " - MISSING (critical)") -ForegroundColor Yellow
            $missingCritical++
        } else {
            Write-Host ("  [-]    " + $file.Name + " - not present (optional)") -ForegroundColor Gray
            $missingOptional++
        }
    }
}

# Check reports directory
Write-Host ""
if (Test-Path $reportsDir) {
    $reportCount = (Get-ChildItem -Path $reportsDir -Filter "*.md" -ErrorAction SilentlyContinue | Measure-Object).Count
    Write-Host ("  [OK]   reports/ (" + $reportCount + " markdown reports)") -ForegroundColor Green
} else {
    Write-Host "  [WARN] reports/ - MISSING" -ForegroundColor Yellow
    $missingCritical++
}

# Check failed_queue (count only, not treated as script failure)
$failedCount = 0
$failedQueuePath = Join-Path $stateDir "failed_queue.jsonl"
if (Test-Path $failedQueuePath) {
    $failedCount = (Get-Content $failedQueuePath | Where-Object { $_.Trim() -ne "" } | Measure-Object).Count
}

Write-Host ""
Write-Host "Summary:" -ForegroundColor Cyan
Write-Host ("  Missing critical files: " + $missingCritical)
Write-Host ("  Missing optional files: " + $missingOptional)
Write-Host ("  Failed queue entries:   " + $failedCount)
Write-Host ""

if ($failedCount -gt 0) {
    Write-Host ("[INFO] failed_queue has " + $failedCount + " entries.") -ForegroundColor Yellow
    Write-Host "       This does not mean script failure, some docs may have failed to archive." -ForegroundColor Yellow
    Write-Host ""
}

# Call source-health CLI if source_health.jsonl exists
if (Test-Path (Join-Path $stateDir "source_health.jsonl")) {
    Write-Host "Calling source-health CLI..." -ForegroundColor Cyan
    Write-Host ""
    python -m opc_foundation.research.cli source-health --archive-root $ArchiveRoot
}

if ($missingCritical -gt 0) {
    Write-Host ""
    Write-Host ("[WARNING] " + $missingCritical + " critical file(s) missing.") -ForegroundColor Yellow
    exit 0  # Don't exit with failure, just output warning
}

Write-Host "All critical files present." -ForegroundColor Green
exit 0
