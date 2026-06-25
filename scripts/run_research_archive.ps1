# Research Archive Foundation - Production Run Script
#
# Purpose: Read production local config, run research archive.
#
# Usage:
#   .\scripts\run_research_archive.ps1                              # Default run
#   .\scripts\run_research_archive.ps1 -Mode dry-run                # Dry-run
#   .\scripts\run_research_archive.ps1 -Mode run                    # Full run
#   .\scripts\run_research_archive.ps1 -Mode source-health          # Source health check
#   .\scripts\run_research_archive.ps1 -Config path/to/config.yaml  # Custom config

param(
    [string]$Config = "configs/research_sources.production.local.yaml",
    [string]$Mode = "run"
)

$ErrorActionPreference = "Stop"

# Auto-locate repo root (script is in scripts/, parent is repo root)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

# Set PYTHONPATH to find src/ modules
$env:PYTHONPATH = Join-Path $RepoRoot "src"

# Check if config exists
if (!(Test-Path $Config)) {
    Write-Host ""
    Write-Host "Config file not found: $Config" -ForegroundColor Red
    Write-Host ""
    Write-Host "Production config not set up yet. Please follow these steps:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  1. Copy configs/research_sources.production.example.yaml to $Config" -ForegroundColor Yellow
    Write-Host "  2. Edit $Config with real source URLs" -ForegroundColor Yellow
    Write-Host "  3. Run this script again" -ForegroundColor Yellow
    exit 1
}

$StartTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Research Archive - $Mode" -ForegroundColor Cyan
Write-Host "Start time: $StartTime" -ForegroundColor Cyan
Write-Host "Config: $Config"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Call corresponding CLI command based on Mode
switch ($Mode) {
    "validate-config" {
        Write-Host "Validating research archive config..." -ForegroundColor Cyan
        python -m opc_foundation.research.cli validate-config --config $Config
    }
    "dry-run" {
        Write-Host "Starting research archive dry-run..." -ForegroundColor Cyan
        python -m opc_foundation.research.cli dry-run --config $Config
    }
    "run" {
        Write-Host "Starting research archive run..." -ForegroundColor Cyan
        python -m opc_foundation.research.cli run --config $Config
    }
    "source-health" {
        Write-Host "Checking source health..." -ForegroundColor Cyan
        python -m opc_foundation.research.cli source-health --archive-root ./data/research_archive
    }
    default {
        Write-Host "Unsupported mode: $Mode" -ForegroundColor Red
        Write-Host ""
        Write-Host "Supported modes: validate-config, dry-run, run, source-health" -ForegroundColor Yellow
        exit 1
    }
}

$exitCode = $LASTEXITCODE
$EndTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "End time: $EndTime" -ForegroundColor Cyan

if ($exitCode -eq 0) {
    Write-Host "Status: Success" -ForegroundColor Green
} elseif ($exitCode -eq 2) {
    Write-Host "Status: Partial (non-blocking)" -ForegroundColor Yellow
    Write-Host "Please check report and failed_queue for details." -ForegroundColor Yellow
} else {
    Write-Host "Status: Failed (exit code: $exitCode)" -ForegroundColor Red
}

Write-Host "========================================" -ForegroundColor Cyan
exit $exitCode
