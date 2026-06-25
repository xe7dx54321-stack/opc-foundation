# Foundation Control Center - Config Health Check
#
# Purpose: Read-only check if Dashboard/Control Center required configs exist.
#          Does NOT start Streamlit, does NOT access websites, does NOT write data.
#
# Usage:
#   .\scripts\check_foundation_control_center.ps1

param()

$ErrorActionPreference = "Stop"

# Auto-locate repo root (script is in scripts/, parent is repo root)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

# Set PYTHONPATH to find src/ modules
$env:PYTHONPATH = Join-Path $RepoRoot "src"

Write-Host ""
Write-Host "Foundation Control Center - Config Health Check" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Check Directory: $RepoRoot"
Write-Host ""

# Config files to check
$configFiles = @(
    @{ Path = "configs/foundation_capabilities.yaml";                Name = "Capabilities Registry";              Required = $true },
    @{ Path = "configs/capability_runbooks.yaml";                  Name = "Capability Runbooks";                 Required = $true },
    @{ Path = "configs/capability_runtime_bindings.yaml";          Name = "Runtime Bindings (example)";         Required = $false },
    @{ Path = "configs/foundation_source_inventory.example.yaml";   Name = "Source Inventory (example)";         Required = $true },
    @{ Path = "configs/trae_foundation_schedule.example.yaml";      Name = "TRAE Schedule (example)";            Required = $false }
)

$missingCritical = 0
$missingOptional = 0
$okCount = 0

Write-Host "Config Files Check:" -ForegroundColor Cyan
Write-Host ""

foreach ($file in $configFiles) {
    if (Test-Path $file.Path) {
        $size = (Get-Item $file.Path).Length
        Write-Host ("  [OK]   " + $file.Name + " (" + $size + " bytes)") -ForegroundColor Green
        $okCount++
    } else {
        if ($file.Required) {
            Write-Host ("  [ERROR] " + $file.Name + " - MISSING (critical)") -ForegroundColor Red
            $missingCritical++
        } else {
            Write-Host ("  [WARN] " + $file.Name + " - not present (optional)") -ForegroundColor Yellow
            $missingOptional++
        }
    }
}

Write-Host ""

# Check if source inventory can be loaded
Write-Host "Source Inventory Load Check:" -ForegroundColor Cyan
Write-Host ""

$sourceInvPath = "configs/foundation_source_inventory.example.yaml"
if (Test-Path $sourceInvPath) {
    try {
        $result = python -c "
import sys
sys.path.insert(0, 'src')
from opc_foundation.dashboard.loaders import load_source_inventory_config, validate_source_inventory
inv = load_source_inventory_config('configs/foundation_source_inventory.example.yaml')
v = validate_source_inventory(inv)
print(f'groups={len(inv.groups)}, sources={len(inv.sources)}, errors={v.error_count}, warnings={v.warning_count}')
" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host ("  [OK]   Load success - " + $result) -ForegroundColor Green
        } else {
            Write-Host "  [WARN] Load failed (may be dependency issue)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  [WARN] Load check skipped (Python call failed)" -ForegroundColor Yellow
    }
}

Write-Host ""

# Summary
Write-Host "Summary:" -ForegroundColor Cyan
Write-Host ("  OK: " + $okCount)
Write-Host ("  Missing (critical): " + $missingCritical)
Write-Host ("  Missing (optional): " + $missingOptional)
Write-Host ""

if ($missingCritical -gt 0) {
    Write-Host "[ERROR] $missingCritical critical config file(s) missing." -ForegroundColor Red
    Write-Host "     Please fix before starting Control Center." -ForegroundColor Red
    exit 1
} else {
    Write-Host "[SUCCESS] All critical config files present." -ForegroundColor Green
    Write-Host "          Can start Foundation Control Center." -ForegroundColor Green
    exit 0
}
