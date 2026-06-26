# Source Inventory Live Smoke - Run Script
#
# Purpose: Run source inventory live smoke for all 92 sources.
#
# Usage:
#   .\scripts\run_source_inventory_live_smoke.ps1 -Mode validate-config
#   .\scripts\run_source_inventory_live_smoke.ps1 -Mode dry-run
#   .\scripts\run_source_inventory_live_smoke.ps1 -Mode run
#   .\scripts\run_source_inventory_live_smoke.ps1 -Mode report
#   .\scripts\run_source_inventory_live_smoke.ps1 -Config path/to/config.yaml
#   .\scripts\run_source_inventory_live_smoke.ps1 -Mode run -Proxy "http://127.0.0.1:7890"

param(
    [string]$Config = "configs/foundation_source_inventory.example.yaml",
    [string]$OutputDir = "data/source_inventory_live_smoke",
    [string]$Mode = "run",
    [int]$MaxCandidatesPerSource = 5,
    [int]$TimeoutSeconds = 20,
    [string]$Proxy = ""
)

$ErrorActionPreference = "Stop"

# Auto-locate repo root (script is in scripts/, parent is repo root)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

# Set PYTHONPATH to find src/ modules
$env:PYTHONPATH = Join-Path $RepoRoot "src"

# Proxy configuration
# Priority: -Proxy param > existing env vars > none
$ProxyEnabled = $false
$ProxyMode = "none"
if ($Proxy) {
    $env:HTTP_PROXY = $Proxy
    $env:HTTPS_PROXY = $Proxy
    $ProxyEnabled = $true
    $ProxyMode = "cli"
} elseif ($env:HTTPS_PROXY -or $env:HTTP_PROXY) {
    $ProxyEnabled = $true
    $ProxyMode = "env"
}

# Check if config exists
if (!(Test-Path $Config)) {
    Write-Host ""
    Write-Host "Config file not found: $Config" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please ensure source inventory config exists." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Expected path: configs/foundation_source_inventory.example.yaml" -ForegroundColor Yellow
    exit 1
}

$StartTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Source Inventory Live Smoke - $Mode" -ForegroundColor Cyan
Write-Host "Start time: $StartTime" -ForegroundColor Cyan
Write-Host "Config: $Config"
Write-Host "Output: $OutputDir"
Write-Host "Proxy enabled: $ProxyEnabled (mode: $ProxyMode)"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Call corresponding CLI command based on Mode
switch ($Mode) {
    "validate-config" {
        Write-Host "Validating source inventory config..." -ForegroundColor Yellow
        python -m opc_foundation.source_inventory.cli validate-config --config $Config
        if ($LASTEXITCODE -ne 0) {
            Write-Host ""
            Write-Host "Config validation FAILED." -ForegroundColor Red
            exit 1
        }
        Write-Host ""
        Write-Host "Config validation PASSED." -ForegroundColor Green
    }

    "dry-run" {
        Write-Host "Running live smoke dry-run (no network access)..." -ForegroundColor Yellow
        python -m opc_foundation.source_inventory.cli dry-run --config $Config --output-dir $OutputDir
        if ($LASTEXITCODE -ne 0) {
            Write-Host ""
            Write-Host "Dry-run FAILED." -ForegroundColor Red
            exit 1
        }
        Write-Host ""
        Write-Host "Dry-run complete." -ForegroundColor Green
    }

    "run" {
        Write-Host "Running live smoke (real network access)..." -ForegroundColor Yellow
        Write-Host "  Max candidates per source: $MaxCandidatesPerSource"
        Write-Host "  Timeout per request: ${TimeoutSeconds}s"
        Write-Host ""

        python -m opc_foundation.source_inventory.cli run `
            --config $Config `
            --max-candidates-per-source $MaxCandidatesPerSource `
            --timeout-seconds $TimeoutSeconds `
            --output-dir $OutputDir

        if ($LASTEXITCODE -ne 0) {
            Write-Host ""
            Write-Host "Live smoke run FAILED." -ForegroundColor Red
            exit 1
        }
        Write-Host ""
        Write-Host "Live smoke run complete." -ForegroundColor Green
    }

    "report" {
        Write-Host "Generating live smoke report..." -ForegroundColor Yellow
        python -m opc_foundation.source_inventory.cli report --archive-root $OutputDir
        if ($LASTEXITCODE -ne 0) {
            Write-Host ""
            Write-Host "Report generation FAILED." -ForegroundColor Red
            exit 1
        }
        Write-Host ""
        Write-Host "Report generated." -ForegroundColor Green
    }

    default {
        Write-Host "Unknown mode: $Mode" -ForegroundColor Red
        Write-Host "Supported modes: validate-config, dry-run, run, report" -ForegroundColor Yellow
        exit 1
    }
}

$EndTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "End time: $EndTime" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
