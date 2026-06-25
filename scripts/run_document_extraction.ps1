# Document Extraction Foundation - Production Run Script
#
# Purpose: Read production local config, run document extraction archive.
#
# Usage:
#   .\scripts\run_document_extraction.ps1                              # Default run
#   .\scripts\run_document_extraction.ps1 -Mode validate-config       # Validate config
#   .\scripts\run_document_extraction.ps1 -Mode dry-run               # Dry-run
#   .\scripts\run_document_extraction.ps1 -Mode run                   # Full run
#   .\scripts\run_document_extraction.ps1 -Mode source-health         # Source health
#   .\scripts\run_document_extraction.ps1 -Mode report                # Daily report
#   .\scripts\run_document_extraction.ps1 -Mode retry-failed         # Retry failed
#   .\scripts\run_document_extraction.ps1 -Config path/to/config.yaml # Custom config

param(
    [string]$Config = "configs/document_extraction.production.local.yaml",
    [string]$Mode = "run",
    [string]$ArchiveRoot = "./data/document_extraction",
    [string]$Date = ""
)

$ErrorActionPreference = "Stop"

# Auto-locate repo root (script is in scripts/, parent is repo root)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

# Set PYTHONPATH to find src/ modules
$env:PYTHONPATH = Join-Path $RepoRoot "src"

# Determine if config is needed based on Mode
$needsConfig = @("validate-config", "dry-run", "run", "retry-failed") -contains $Mode

if ($needsConfig) {
    # Check if config file exists
    if (!(Test-Path $Config)) {
        Write-Host "Missing config: $Config" -ForegroundColor Red
        Write-Host ""
        Write-Host "Production config not set up yet. Please follow these steps:" -ForegroundColor Yellow
        Write-Host "  1. Copy configs/document_extraction.production.example.yaml to $Config" -ForegroundColor Yellow
        Write-Host "  2. Edit $Config with real source paths" -ForegroundColor Yellow
        Write-Host "  3. Run this script again" -ForegroundColor Yellow
        exit 1
    }
}

$StartTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Document Extraction - $Mode" -ForegroundColor Cyan
Write-Host "Start time: $StartTime" -ForegroundColor Cyan
Write-Host "Config: $Config" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Call corresponding CLI command based on Mode
switch ($Mode) {
    "validate-config" {
        Write-Host "Validating document extraction config..." -ForegroundColor Cyan
        python -m opc_foundation.document_extraction.cli validate-config --config $Config
    }
    "dry-run" {
        Write-Host "Starting document extraction dry-run..." -ForegroundColor Cyan
        python -m opc_foundation.document_extraction.cli dry-run --config $Config
    }
    "run" {
        Write-Host "Starting document extraction run..." -ForegroundColor Cyan
        python -m opc_foundation.document_extraction.cli run --config $Config
    }
    "source-health" {
        Write-Host "Checking source health..." -ForegroundColor Cyan
        python -m opc_foundation.document_extraction.cli source-health --archive-root $ArchiveRoot
    }
    "report" {
        Write-Host "Viewing daily report..." -ForegroundColor Cyan
        if ($Date) {
            python -m opc_foundation.document_extraction.cli report --archive-root $ArchiveRoot --date $Date
        } else {
            python -m opc_foundation.document_extraction.cli report --archive-root $ArchiveRoot
        }
    }
    "retry-failed" {
        Write-Host "Retrying failed documents..." -ForegroundColor Cyan
        python -m opc_foundation.document_extraction.cli retry-failed --archive-root $ArchiveRoot --config $Config
    }
    default {
        Write-Host "Unsupported mode: $Mode" -ForegroundColor Red
        Write-Host ""
        Write-Host "Supported modes: validate-config, dry-run, run, source-health, report, retry-failed" -ForegroundColor Yellow
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
