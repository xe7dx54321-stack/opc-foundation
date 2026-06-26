# run_foundation_trial_sources.ps1
# M3C-2D Trial Source Run Script
# Trial-only run for 16 verified sources. NOT final production.

param(
    [string]$Config = "configs/trae_foundation_trial_sources.example.yaml",
    [string]$Allowlist = "configs/foundation_trial_source_allowlist.example.yaml",
    [string]$OutputDir = "data/foundation_trial",
    [string]$Mode = "run",
    [int]$MaxItemsPerSource = 10,
    [int]$TimeoutSeconds = 20,
    [string]$Proxy = $null
)

# ============================================================
# Helpers
# ============================================================

function Get-RepoRoot {
    # Auto-detect RepoRoot by searching for .git upward
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

function Write-TrialHeader {
    param([string]$Mode)
    $cyan = "Cyan"
    Write-Host ""
    Write-Host "===============================================" -ForegroundColor $cyan
    Write-Host " OPC Foundation M3C-2D Trial Source Run" -ForegroundColor $cyan
    Write-Host " Mode: $Mode" -ForegroundColor $cyan
    Write-Host " Config: $Script:Config" -ForegroundColor $cyan
    Write-Host " Output: $Script:OutputDir" -ForegroundColor $cyan
    Write-Host "===============================================" -ForegroundColor $cyan
    Write-Host ""
}

# ============================================================
# Main Logic
# ============================================================

$RepoRoot = Get-RepoRoot
Set-Location $RepoRoot

# Set proxy env vars temporarily (only in current process)
if ($Proxy) {
    $env:HTTP_PROXY = $Proxy
    $env:HTTPS_PROXY = $Proxy
    Write-Host "Proxy enabled (mode=cli)" -ForegroundColor Cyan
    $proxyMode = "cli"
} else {
    # Check if proxy is set via env vars (PS 5.x compatible)
    $envProxy = ""
    if ($env:HTTPS_PROXY) {
        $envProxy = $env:HTTPS_PROXY
    } elseif ($env:HTTP_PROXY) {
        $envProxy = $env:HTTP_PROXY
    }
    if ($envProxy) {
        Write-Host "Proxy enabled (mode=env)" -ForegroundColor Cyan
        $proxyMode = "env"
    } else {
        Write-Host "Proxy disabled (mode=none)" -ForegroundColor Yellow
        $proxyMode = "none"
    }
}

# Set PYTHONPATH
$env:PYTHONPATH = "$RepoRoot\src"

Write-TrialHeader -Mode $Mode

# ---- Mode: validate-config ----
if ($Mode -eq "validate-config") {
    Write-Host "[1/1] Validating trial config..." -ForegroundColor Yellow

    $result = python -m opc_foundation.source_inventory.cli trial-validate `
        --config $Config `
        --allowlist $Allowlist

    if ($LASTEXITCODE -ne 0) {
        Write-Host "validate-config FAILED" -ForegroundColor Red
        exit 1
    }
    Write-Host "validate-config PASSED" -ForegroundColor Green
    exit 0
}

# ---- Mode: dry-run ----
if ($Mode -eq "dry-run") {
    Write-Host "[1/3] Validating trial config..." -ForegroundColor Yellow
    python -m opc_foundation.source_inventory.cli trial-validate `
        --config $Config `
        --allowlist $Allowlist `
        2>&1 | ForEach-Object { Write-Host "  $_" }
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Config validation failed, aborting dry-run" -ForegroundColor Red
        exit 1
    }

    Write-Host "[2/3] Running trial dry-run..." -ForegroundColor Yellow
    python -m opc_foundation.source_inventory.cli trial-run `
        --config $Config `
        --allowlist $Allowlist `
        --output-dir $OutputDir `
        --dry-run `
        --max-items-per-source $MaxItemsPerSource `
        2>&1 | ForEach-Object { Write-Host "  $_" }

    Write-Host "[3/3] Generating trial report..." -ForegroundColor Yellow
    python -m opc_foundation.source_inventory.cli trial-report `
        --archive-root $OutputDir `
        2>&1 | ForEach-Object { Write-Host "  $_" }

    Write-Host ""
    Write-Host "dry-run complete!" -ForegroundColor Green
    Write-Host "Report: $RepoRoot\$OutputDir\reports\" -ForegroundColor Green
    exit $LASTEXITCODE
}

# ---- Mode: run ----
if ($Mode -eq "run") {
    Write-Host "[1/5] Validating trial config..." -ForegroundColor Yellow
    python -m opc_foundation.source_inventory.cli trial-validate `
        --config $Config `
        --allowlist $Allowlist `
        2>&1 | ForEach-Object { Write-Host "  $_" }
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Config validation failed, aborting run" -ForegroundColor Red
        exit 1
    }

    Write-Host "[2/5] Checking allowlist integrity..." -ForegroundColor Yellow
    $allowlistCheck = python -c "
import yaml
with open('configs/foundation_trial_source_allowlist.example.yaml', 'r', encoding='utf-8') as f:
    data = yaml.safe_load(f)
ids = [x['source_id'] for x in data['trial_source_ids']]
excluded = set(data['excluded_source_ids'])
found_bad = [x for x in ids if x in excluded]
if found_bad:
    print('ERROR: Allowlist contains excluded sources: ' + str(found_bad))
    exit(1)
print('Allowlist check: PASSED (' + str(len(ids)) + ' sources, 0 excluded)')
"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Allowlist check FAILED" -ForegroundColor Red
        Write-Host $allowlistCheck -ForegroundColor Red
        exit 1
    }
    Write-Host $allowlistCheck -ForegroundColor Green

    Write-Host "[3/5] Running trial source archiver (real network access)..." -ForegroundColor Yellow
    Write-Host "  max_items_per_source: $MaxItemsPerSource" -ForegroundColor Gray
    Write-Host "  timeout_seconds: $TimeoutSeconds" -ForegroundColor Gray
    Write-Host "  proxy_mode: $proxyMode" -ForegroundColor Gray
    Write-Host ""

    python -m opc_foundation.source_inventory.cli trial-run `
        --config $Config `
        --allowlist $Allowlist `
        --output-dir $OutputDir `
        --max-items-per-source $MaxItemsPerSource `
        --timeout-seconds $TimeoutSeconds `
        2>&1 | ForEach-Object { Write-Host "  $_" }

    $runExitCode = $LASTEXITCODE

    Write-Host "[4/5] Generating trial run report..." -ForegroundColor Yellow
    python -m opc_foundation.source_inventory.cli trial-report `
        --archive-root $OutputDir `
        2>&1 | ForEach-Object { Write-Host "  $_" }

    Write-Host "[5/5] Checking output integrity..." -ForegroundColor Yellow
    python -c "
import os, json
base = 'data/foundation_trial'
index_dir = os.path.join(base, 'index')
health = os.path.join(index_dir, 'source_health.jsonl')
log = os.path.join(index_dir, 'run_log.jsonl')
queue = os.path.join(index_dir, 'failed_queue.jsonl')

for f, label in [(health, 'source_health'), (log, 'run_log')]:
    if os.path.exists(f):
        print('  ' + label + ': EXISTS')
    else:
        print('  ' + label + ': NOT FOUND')

if os.path.exists(queue):
    with open(queue, 'r', encoding='utf-8') as fh:
        lines = [l for l in fh if l.strip()]
    print('  failed_queue: ' + str(len(lines)) + ' entries')
else:
    print('  failed_queue: NOT FOUND (OK if no failures)')

# Verify no blocked sources in health log
if os.path.exists(health):
    blocked = ['telegram_groups', 'cloud_drive_share', 'pdf_download_sites',
               'unknown_wechat_pdf', 'report_download_proxy']
    with open(health, 'r', encoding='utf-8') as fh:
        for line in fh:
            if not line.strip():
                continue
            entry = json.loads(line)
            sid = entry.get('source_id', '')
            if sid in blocked:
                print('  ERROR: Blocked source in health log: ' + sid)
                exit(1)
    print('  Blocked source check: PASSED')
"

    Write-Host ""
    Write-Host "===============================================" -ForegroundColor Green
    Write-Host " M3C-2D Trial Run Complete" -ForegroundColor Green
    Write-Host " Output: $RepoRoot\$OutputDir\" -ForegroundColor Green
    Write-Host " proxy_enabled: $proxyMode" -ForegroundColor Green
    Write-Host "===============================================" -ForegroundColor Green

    exit $runExitCode
}

# ---- Unknown Mode ----
Write-Host "Unknown mode: $Mode" -ForegroundColor Red
Write-Host "Supported modes: validate-config, dry-run, run" -ForegroundColor Red
exit 1
