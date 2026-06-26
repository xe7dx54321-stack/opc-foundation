# Source Inventory Live Smoke - Check Script
#
# Purpose: Check live smoke results and report health status.
#
# Usage:
#   .\scripts\check_source_inventory_live_smoke.ps1
#   .\scripts\check_source_inventory_live_smoke.ps1 -ArchiveRoot data/source_inventory_live_smoke

param(
    [string]$ArchiveRoot = "data/source_inventory_live_smoke"
)

$ErrorActionPreference = "Stop"

# Auto-locate repo root (script is in scripts/, parent is repo root)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

# Set PYTHONPATH to find src/ modules
$env:PYTHONPATH = Join-Path $RepoRoot "src"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Source Inventory Live Smoke - Check" -ForegroundColor Cyan
Write-Host "Archive root: $ArchiveRoot"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if index directory exists
$IndexDir = Join-Path $ArchiveRoot "index"
$LatestFile = Join-Path $IndexDir "source_live_status.latest.json"

if (!(Test-Path $LatestFile)) {
    Write-Host "No live smoke results found at: $LatestFile" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please run live smoke first:" -ForegroundColor Yellow
    Write-Host "  .\scripts\run_source_inventory_live_smoke.ps1 -Mode run" -ForegroundColor Yellow
    exit 1
}

Write-Host "Latest results found at: $LatestFile" -ForegroundColor Green
Write-Host ""

# Use Python to read and summarize results
$pythonScript = @"
import json
import sys
from pathlib import Path

latest_path = Path(r"$LatestFile")
try:
    data = json.loads(latest_path.read_text(encoding='utf-8'))
except Exception as e:
    print(f"Error reading results: {e}")
    sys.exit(1)

total = data.get('total_sources', 0)
status_counts = data.get('status_counts', {})
results = data.get('results', [])

print(f"Total sources: {total}")
print(f"Run started: {data.get('run_started_at', 'N/A')}")
print(f"Run finished: {data.get('run_finished_at', 'N/A')}")
duration_ms = data.get('total_duration_ms', 0)
print(f"Duration: {duration_ms / 1000:.1f}s")
print()

print("Status breakdown:")
for status, count in sorted(status_counts.items()):
    print(f"  {status}: {count}")
print()

# Check blocked sources
blocked = [r for r in results if r.get('status') == 'blocked_by_policy']
print(f"Blocked by policy: {len(blocked)} sources (all should have visited=false)")
blocked_visited = [r for r in blocked if r.get('visited')]
if blocked_visited:
    print(f"  WARNING: {len(blocked_visited)} blocked sources were visited!")
    for r in blocked_visited[:5]:
        print(f"    - {r.get('source_id')}")
else:
    print(f"  OK: all blocked sources have visited=false")
print()

# Check on-demand sources
on_demand = [r for r in results if r.get('status') == 'on_demand_not_run']
print(f"On-demand not run: {len(on_demand)} sources")
on_demand_visited = [r for r in on_demand if r.get('visited')]
if on_demand_visited:
    print(f"  WARNING: {len(on_demand_visited)} on-demand sources were visited!")
else:
    print(f"  OK: all on-demand sources have visited=false")
print()

# Check failures
failure_statuses = {'http_error', 'timeout', 'failed'}
failures = [r for r in results if r.get('status') in failure_statuses]
print(f"Failures: {len(failures)} sources")
if failures:
    for r in failures[:10]:
        print(f"  - {r.get('source_id')}: {r.get('status')} - {r.get('error_message', '')[:80]}")
    if len(failures) > 10:
        print(f"  ... and {len(failures) - 10} more")
print()

# Needs connector
needs_connector = [r for r in results if r.get('status') == 'needs_connector']
print(f"Needs connector: {len(needs_connector)} sources")
if needs_connector:
    for r in needs_connector[:10]:
        print(f"  - {r.get('source_id')}: {r.get('access_mode', 'unknown')}")
    if len(needs_connector) > 10:
        print(f"  ... and {len(needs_connector) - 10} more")
print()

# Success count
success_statuses = {'live_ok', 'live_ok_empty', 'live_ok_candidates_found', 'live_ok_saved'}
successes = [r for r in results if r.get('status') in success_statuses]
print(f"Live OK: {len(successes)} sources")
if successes:
    for r in successes[:10]:
        print(f"  - {r.get('source_id')}: {r.get('status')} ({r.get('candidates_found', 0)} candidates)")
    if len(successes) > 10:
        print(f"  ... and {len(successes) - 10} more")
print()

print("Summary:")
print(f"  Total: {total}")
print(f"  Success: {len(successes)}")
print(f"  Needs connector: {len(needs_connector)}")
print(f"  Failed: {len(failures)}")
print(f"  Blocked: {len(blocked)}")
print(f"  On-demand: {len(on_demand)}")
"@

$tempPy = Join-Path $env:TEMP "check_live_smoke_$(Get-Random).py"
$pythonScript | Out-File -FilePath $tempPy -Encoding utf8

try {
    python $tempPy
    $exitCode = $LASTEXITCODE
} finally {
    if (Test-Path $tempPy) {
        Remove-Item $tempPy -Force
    }
}

if ($exitCode -ne 0) {
    Write-Host ""
    Write-Host "Check FAILED." -ForegroundColor Red
    exit $exitCode
}

Write-Host ""
Write-Host "Check complete." -ForegroundColor Green
