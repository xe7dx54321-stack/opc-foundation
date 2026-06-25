# Manual URL Archive - Manual URL Queue Handler
#
# Purpose: Check and process manual_url pending queue.
#
# Usage:
#   .\scripts\run_manual_url_archive.ps1
#   .\scripts\run_manual_url_archive.ps1 -Mode check
#   .\scripts\run_manual_url_archive.ps1 -Mode process
#
# Note: manual_url is primarily human-triggered. No frequent scheduling recommended.

param(
    [string]$Mode = "check"
)

$ErrorActionPreference = "Stop"

# Auto-locate repo root (script is in scripts/, parent is repo root)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

# Set PYTHONPATH to find src/ modules
$env:PYTHONPATH = Join-Path $RepoRoot "src"

Write-Host ""
Write-Host "Manual URL Archive - $Mode" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Manual URL queue path (example path, actual path may differ)
$manualQueuePath = "data/manual_url/pending.jsonl"

switch ($Mode) {
    "check" {
        Write-Host "Checking manual_url pending queue..." -ForegroundColor Cyan
        Write-Host ""

        if (!(Test-Path $manualQueuePath)) {
            Write-Host "[INFO] No pending URLs, waiting for human trigger." -ForegroundColor Green
            Write-Host "       Queue file does not exist: $manualQueuePath" -ForegroundColor Gray
            exit 0
        }

        $pendingCount = (Get-Content $manualQueuePath | Where-Object { $_.Trim() -ne "" } | Measure-Object).Count

        if ($pendingCount -eq 0) {
            Write-Host "[INFO] No pending URLs, waiting for human trigger." -ForegroundColor Green
            exit 0
        } else {
            Write-Host "[INFO] Pending URLs count: $pendingCount" -ForegroundColor Yellow
            Write-Host "       Can manually run process mode to handle." -ForegroundColor Yellow
            exit 0
        }
    }
    "process" {
        Write-Host "Processing manual_url pending queue..." -ForegroundColor Cyan
        Write-Host ""

        if (!(Test-Path $manualQueuePath)) {
            Write-Host "[INFO] No pending URLs, nothing to process." -ForegroundColor Green
            exit 0
        }

        $pendingCount = (Get-Content $manualQueuePath | Where-Object { $_.Trim() -ne "" } | Measure-Object).Count

        if ($pendingCount -eq 0) {
            Write-Host "[INFO] No pending URLs, nothing to process." -ForegroundColor Green
            exit 0
        }

        Write-Host "[INFO] Detected $pendingCount pending URLs." -ForegroundColor Yellow
        Write-Host "       Manual URL archive feature not fully implemented yet," -ForegroundColor Yellow
        Write-Host "       please wait for future version." -ForegroundColor Yellow
        exit 0
    }
    default {
        Write-Host "Unsupported mode: $Mode" -ForegroundColor Red
        Write-Host ""
        Write-Host "Supported modes: check, process" -ForegroundColor Yellow
        exit 1
    }
}
