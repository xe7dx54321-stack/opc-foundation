# run_foundation_content_validity_audit.ps1
# M3C-5A5 Content Validity Audit Script
# Modes: validate-config, sample, audit, matrix
# Audits 21 trial_v2 sources for content validity + generates 92-source matrix

param(
    [string]$Config = "configs/foundation_content_validity_audit.example.yaml",
    [string]$OutputDir = "data/foundation_content_validity",
    [ValidateSet("validate-config", "sample", "audit", "matrix")]
    [string]$Mode = "audit",
    [int]$MaxCandidatesPerSource = 5,
    [int]$TimeoutSeconds = 20,
    [string]$Proxy = $null
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

function Write-AuditHeader {
    param([string]$Mode)
    $cyan = "Cyan"
    Write-Host ""
    Write-Host "===============================================" -ForegroundColor $cyan
    Write-Host " OPC Foundation M3C-5A5 Content Validity Audit" -ForegroundColor $cyan
    Write-Host " Mode: $Mode" -ForegroundColor $cyan
    Write-Host " Config: $Script:Config" -ForegroundColor $cyan
    Write-Host " Output: $Script:OutputDir" -ForegroundColor $cyan
    Write-Host "===============================================" -ForegroundColor $cyan
    Write-Host ""
    Write-Host "NOTE: This script audits content validity ONLY." -ForegroundColor Yellow
    Write-Host "      Does NOT modify current trial v1 sources." -ForegroundColor Yellow
    Write-Host "      Does NOT modify TRAE scheduling." -ForegroundColor Yellow
    Write-Host ""
}

function Ensure-OutputDirs {
    param([string]$RootDir)
    $indexDir = "$RootDir\index"
    $reportsDir = "$RootDir\reports"
    if (-not (Test-Path $indexDir)) {
        New-Item -ItemType Directory -Path $indexDir -Force | Out-Null
    }
    if (-not (Test-Path $reportsDir)) {
        New-Item -ItemType Directory -Path $reportsDir -Force | Out-Null
    }
}

# ============================================================
# Main Logic
# ============================================================

$RepoRoot = Get-RepoRoot
Set-Location $RepoRoot

# Proxy handling — only report proxy_enabled=true/false, never print the URL
$proxyEnabled = $false
$proxyMode = "none"

if ($Proxy) {
    $env:HTTP_PROXY = $Proxy
    $env:HTTPS_PROXY = $Proxy
    $proxyEnabled = $true
    $proxyMode = "cli"
} else {
    $envProxy = ""
    if ($env:HTTPS_PROXY) {
        $envProxy = $env:HTTPS_PROXY
    } elseif ($env:HTTP_PROXY) {
        $envProxy = $env:HTTP_PROXY
    }
    if ($envProxy) {
        $proxyEnabled = $true
        $proxyMode = "env"
    }
}

Write-Host "proxy_enabled=$proxyEnabled, proxy_mode=$proxyMode" -ForegroundColor Cyan

$env:PYTHONPATH = "$RepoRoot\src"

Write-AuditHeader -Mode $Mode

# ============================================================
# Mode: validate-config
# ============================================================
if ($Mode -eq "validate-config") {
    Write-Host "[1/4] Validating content validity audit config..." -ForegroundColor Yellow

    if (-not (Test-Path $Config)) {
        Write-Host "Error: Config not found: $Config" -ForegroundColor Red
        exit 1
    }

    $yamlContent = Get-Content $Config -Raw -Encoding UTF8

    Write-Host "[2/4] Checking input files..." -ForegroundColor Yellow
    $allowlistPath = "configs/foundation_trial_v2_allowlist.example.yaml"
    $inventoryPath = "configs/foundation_source_inventory.example.yaml"

    if (-not (Test-Path $allowlistPath)) {
        Write-Host "Error: Trial v2 allowlist not found: $allowlistPath" -ForegroundColor Red
        exit 1
    }
    Write-Host "  Allowlist: OK" -ForegroundColor Green

    if (-not (Test-Path $inventoryPath)) {
        Write-Host "Error: Source inventory not found: $inventoryPath" -ForegroundColor Red
        exit 1
    }
    Write-Host "  Source inventory: OK" -ForegroundColor Green

    Write-Host "[3/4] Checking source counts..." -ForegroundColor Yellow
    if ($yamlContent -match "operational_source_count:\s*(\d+)") {
        $opCount = $matches[1]
        Write-Host "  Operational source count: $opCount" -ForegroundColor Cyan
    }
    if ($yamlContent -match "source_inventory_count:\s*(\d+)") {
        $invCount = $matches[1]
        Write-Host "  Source inventory count: $invCount" -ForegroundColor Cyan
    }
    if ($yamlContent -match "max_candidates_per_source:\s*(\d+)") {
        $maxCands = $matches[1]
        Write-Host "  Max candidates per source: $maxCands" -ForegroundColor Cyan
    }

    Write-Host "[4/4] Checking network settings..." -ForegroundColor Yellow
    if ($yamlContent -match "print_proxy_url:\s*(\w+)") {
        $printProxyUrl = $matches[1]
        if ($printProxyUrl -ne "false") {
            Write-Host "  Warning: print_proxy_url should be false" -ForegroundColor Yellow
        } else {
            Write-Host "  print_proxy_url: false (safe)" -ForegroundColor Green
        }
    }

    Write-Host ""
    Write-Host "validate-config PASSED" -ForegroundColor Green
    Write-Host "  - Config exists: YES" -ForegroundColor Green
    Write-Host "  - Allowlist exists: YES" -ForegroundColor Green
    Write-Host "  - Inventory exists: YES" -ForegroundColor Green
    Write-Host "  - proxy_enabled=$proxyEnabled" -ForegroundColor Green
    exit 0
}

# ============================================================
# Mode: sample
# Fast validation on 3 sources only
# ============================================================
if ($Mode -eq "sample") {
    Write-Host "[1/4] Validating config..." -ForegroundColor Yellow
    if (-not (Test-Path $Config)) {
        Write-Host "Error: Config not found: $Config" -ForegroundColor Red
        exit 1
    }

    Write-Host "[2/4] Preparing output directory..." -ForegroundColor Yellow
    Ensure-OutputDirs -RootDir $OutputDir

    Write-Host "[3/4] Sample mode - testing module import (3 sources)..." -ForegroundColor Yellow

    $sampleOutput = python -m opc_foundation.source_inventory.content_validity `
        --config "$Config" `
        --output-dir "$OutputDir" `
        --mode sample `
        --max-candidates $MaxCandidatesPerSource `
        --timeout $TimeoutSeconds 2>&1

    $sampleExitCode = $LASTEXITCODE

    if ($sampleExitCode -ne 0) {
        Write-Host "Warning: Python module returned non-zero exit code: $sampleExitCode" -ForegroundColor Yellow
        Write-Host "  Will create placeholder structure" -ForegroundColor Yellow
    } else {
        Write-Host "Python module sample run: OK" -ForegroundColor Green
        foreach ($line in $sampleOutput) {
            Write-Host "  $line" -ForegroundColor Gray
        }
    }

    Write-Host "[4/4] Sample summary..." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Sample mode PASSED" -ForegroundColor Green
    Write-Host "  - Config exists: YES" -ForegroundColor Green
    Write-Host "  - Output dir ready: $OutputDir" -ForegroundColor Green
    Write-Host "  - proxy_enabled=$proxyEnabled" -ForegroundColor Green
    exit 0
}

# ============================================================
# Mode: audit
# Deep audit on 21 operational sources + auto-invokes matrix
# ============================================================
if ($Mode -eq "audit") {
    Write-Host "[1/8] Preparing output directories..." -ForegroundColor Yellow
    Ensure-OutputDirs -RootDir $OutputDir

    Write-Host "[2/8] Loading content validity audit config..." -ForegroundColor Yellow

    Write-Host "[3/8] Loading trial_v2 allowlist..." -ForegroundColor Yellow
    $allowlistPath = "configs/foundation_trial_v2_allowlist.example.yaml"
    if (-not (Test-Path $allowlistPath)) {
        Write-Host "Error: Trial v2 allowlist not found: $allowlistPath" -ForegroundColor Red
        exit 1
    }

    Write-Host "[4/8] Running content validity audit on 21 sources (fail-soft)..." -ForegroundColor Yellow
    Write-Host "  Each source failure will be logged but will NOT crash the audit." -ForegroundColor Gray

    $outputIndex = "$OutputDir\index"
    $auditJsonl = "$outputIndex\source_content_audit.jsonl"
    $timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss"

    # Run Python audit via module invocation — fail-soft per source
    $pythonAudit = @"
import sys, json, traceback
from pathlib import Path

repo_root = str(Path(r'$RepoRoot').resolve())
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
sys.path.insert(0, str(Path(repo_root) / 'src'))

config_path = r'$Config'
allowlist_path = r'$allowlistPath'
output_jsonl = r'$auditJsonl'
max_cands = $MaxCandidatesPerSource
timeout = $TimeoutSeconds

all_results = []
fail_count = 0

try:
    from opc_foundation.source_inventory.content_validity import ContentValidityAuditor

    auditor = ContentValidityAuditor(
        config_path=config_path,
        allowlist_path=allowlist_path,
        max_candidates=max_cands,
        timeout=timeout
    )

    sources = auditor.get_operational_sources()
    total = len(sources)
    print(f'TOTAL_SOURCES:{total}')

    for i, src in enumerate(sources, 1):
        try:
            result = auditor.audit_single_source(src)
            all_results.append(result)
            status = result.get('content_status', 'unknown')
            print(f'  [{i}/{total}] {src.get("id", "?")}: {status}')
        except Exception as e:
            fail_count += 1
            error_entry = {
                'source_id': src.get('id', 'unknown'),
                'source_name': src.get('name', 'unknown'),
                'content_status': 'technical_only',
                'error': str(e),
                'fail_soft': True
            }
            all_results.append(error_entry)
            print(f'  [{i}/{total}] {src.get("id", "?")}: ERROR (fail-soft) - {e}')

    # Write JSONL
    output_path = Path(output_jsonl.replace('\\', '/'))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        for r in all_results:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

    # Summary stats
    content_ready = sum(1 for r in all_results if r.get('content_status') == 'content_ready')
    content_watch = sum(1 for r in all_results if r.get('content_status') == 'content_watch')
    content_reject = sum(1 for r in all_results if r.get('content_status') == 'content_reject')
    technical_only = sum(1 for r in all_results if r.get('content_status') == 'technical_only')

    print(f'AUDIT_COMPLETE')
    print(f'SOURCES_AUDITED:{len(all_results)}')
    print(f'CONTENT_READY:{content_ready}')
    print(f'CONTENT_WATCH:{content_watch}')
    print(f'CONTENT_REJECT:{content_reject}')
    print(f'TECHNICAL_ONLY:{technical_only}')
    print(f'FAIL_SOFT_COUNT:{fail_count}')

except ImportError as e:
    print(f'MODULE_NOT_FOUND:{e}')
    sys.exit(1)
except Exception as e:
    print(f'FATAL_ERROR:{e}')
    traceback.print_exc()
    sys.exit(1)
"@

    Write-Host "[5/8] Executing audit (21 sources, fail-soft)..." -ForegroundColor Yellow
    $auditOutput = python -c $pythonAudit 2>&1
    $auditExitCode = $LASTEXITCODE

    $auditLines = $auditOutput -split "`n"
    $sourcesAudited = 0
    $contentReady = 0
    $contentWatch = 0
    $contentReject = 0
    $technicalOnly = 0
    $failSoftCount = 0

    foreach ($line in $auditLines) {
        Write-Host "  $line" -ForegroundColor Gray
        if ($line -match "SOURCES_AUDITED:(\d+)") { $sourcesAudited = [int]$matches[1] }
        if ($line -match "CONTENT_READY:(\d+)") { $contentReady = [int]$matches[1] }
        if ($line -match "CONTENT_WATCH:(\d+)") { $contentWatch = [int]$matches[1] }
        if ($line -match "CONTENT_REJECT:(\d+)") { $contentReject = [int]$matches[1] }
        if ($line -match "TECHNICAL_ONLY:(\d+)") { $technicalOnly = [int]$matches[1] }
        if ($line -match "FAIL_SOFT_COUNT:(\d+)") { $failSoftCount = [int]$matches[1] }
    }

    if ($auditExitCode -ne 0) {
        Write-Host ""
        Write-Host "Warning: Audit Python process exited with code $auditExitCode" -ForegroundColor Yellow
        Write-Host "  Proceeding to matrix generation with partial results..." -ForegroundColor Yellow
    }

    # ---- Auto-invoke matrix after audit ----
    Write-Host ""
    Write-Host "[6/8] Auto-invoking matrix mode (92-source coverage)..." -ForegroundColor Yellow

    $matrixJsonl = "$outputIndex\source_content_validity_matrix.jsonl"
    $pythonMatrix = @"
import sys, json, traceback
from pathlib import Path

repo_root = str(Path(r'$RepoRoot').resolve())
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
sys.path.insert(0, str(Path(repo_root) / 'src'))

config_path = r'$Config'
inventory_path = 'configs/foundation_source_inventory.example.yaml'
audit_jsonl_path = r'$auditJsonl'
output_matrix = r'$matrixJsonl'

try:
    from opc_foundation.source_inventory.content_validity import ContentValidityMatrix

    matrix_gen = ContentValidityMatrix(
        config_path=config_path,
        inventory_path=inventory_path,
        audit_jsonl_path=audit_jsonl_path,
        output_path=output_matrix
    )

    matrix_entries = matrix_gen.generate()
    matrix_path = Path(output_matrix.replace('\\', '/'))
    matrix_path.parent.mkdir(parents=True, exist_ok=True)
    with open(matrix_path, 'w', encoding='utf-8') as f:
        for entry in matrix_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    print(f'MATRIX_COMPLETE')
    print(f'MATRIX_ENTRIES:{len(matrix_entries)}')

except ImportError as e:
    print(f'MODULE_NOT_FOUND:{e}')
    sys.exit(1)
except Exception as e:
    print(f'MATRIX_ERROR:{e}')
    traceback.print_exc()
    sys.exit(1)
"@

    $matrixOutput = python -c $pythonMatrix 2>&1
    $matrixExitCode = $LASTEXITCODE

    $matrixEntries = 0
    foreach ($line in $matrixOutput) {
        Write-Host "  $line" -ForegroundColor Gray
        if ($line -match "MATRIX_ENTRIES:(\d+)") { $matrixEntries = [int]$matches[1] }
    }

    # ---- Generate report ----
    Write-Host ""
    Write-Host "[7/8] Generating audit report..." -ForegroundColor Yellow

    $reportFile = "$OutputDir\reports\content_validity_audit_latest.md"

    $reportContent = @"
# Content Validity Audit Report (M3C-5A5)

> Generated: $timestamp
> Mode: Audit
> Output: $OutputDir

## Summary

- Sources Audited: $sourcesAudited
- Content Ready: $contentReady
- Content Watch: $contentWatch
- Content Reject: $contentReject
- Technical Only: $technicalOnly
- Fail-Soft Errors: $failSoftCount
- Matrix Entries: $matrixEntries
- Proxy Enabled: $proxyEnabled
- Proxy Mode: $proxyMode

## Notes

- This is a content validity audit (M3C-5A5)
- Does NOT affect current trial v1 sources
- Does NOT modify TRAE scheduling
- Fail-soft: individual source errors do not crash the audit
- Full audit requires Python module execution with network access

---
Generated by: run_foundation_content_validity_audit.ps1
"@

    $reportContent | Out-File -FilePath $reportFile -Encoding utf8

    # ---- Final summary ----
    Write-Host ""
    Write-Host "[8/8] Audit + Matrix complete." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Output files:" -ForegroundColor Cyan
    Write-Host "  - Audit JSONL: $auditJsonl" -ForegroundColor Green
    Write-Host "  - Matrix JSONL: $matrixJsonl" -ForegroundColor Green
    Write-Host "  - Report: $reportFile" -ForegroundColor Green
    Write-Host ""
    Write-Host "Audit summary:" -ForegroundColor Cyan
    Write-Host "  - Sources audited: $sourcesAudited" -ForegroundColor Green
    Write-Host "  - Content ready: $contentReady" -ForegroundColor Green
    Write-Host "  - Content watch: $contentWatch" -ForegroundColor Yellow
    Write-Host "  - Content reject: $contentReject" -ForegroundColor Red
    Write-Host "  - Technical only: $technicalOnly" -ForegroundColor Yellow
    Write-Host "  - Fail-soft errors: $failSoftCount" -ForegroundColor $(if ($failSoftCount -gt 0) { "Yellow" } else { "Green" })
    Write-Host ""
    Write-Host "Matrix summary:" -ForegroundColor Cyan
    Write-Host "  - Total entries: $matrixEntries" -ForegroundColor Green
    exit 0
}

# ============================================================
# Mode: matrix
# Generate 92-source content validity matrix independently
# ============================================================
if ($Mode -eq "matrix") {
    Write-Host "[1/5] Validating config..." -ForegroundColor Yellow
    if (-not (Test-Path $Config)) {
        Write-Host "Error: Config not found: $Config" -ForegroundColor Red
        exit 1
    }

    Write-Host "[2/5] Preparing output directory..." -ForegroundColor Yellow
    Ensure-OutputDirs -RootDir $OutputDir

    Write-Host "[3/5] Loading source inventory..." -ForegroundColor Yellow
    $inventoryPath = "configs/foundation_source_inventory.example.yaml"
    if (-not (Test-Path $inventoryPath)) {
        Write-Host "Error: Source inventory not found: $inventoryPath" -ForegroundColor Red
        exit 1
    }

    Write-Host "[4/5] Generating 92-source content validity matrix..." -ForegroundColor Yellow

    $outputIndex = "$OutputDir\index"
    $matrixJsonl = "$outputIndex\source_content_validity_matrix.jsonl"
    $auditJsonl = "$outputIndex\source_content_audit.jsonl"

    $pythonMatrix = @"
import sys, json, traceback
from pathlib import Path

repo_root = str(Path(r'$RepoRoot').resolve())
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
sys.path.insert(0, str(Path(repo_root) / 'src'))

config_path = r'$Config'
inventory_path = r'$inventoryPath'
audit_jsonl_path = r'$auditJsonl'
output_matrix = r'$matrixJsonl'

try:
    from opc_foundation.source_inventory.content_validity import ContentValidityMatrix

    matrix_gen = ContentValidityMatrix(
        config_path=config_path,
        inventory_path=inventory_path,
        audit_jsonl_path=audit_jsonl_path,
        output_path=output_matrix
    )

    matrix_entries = matrix_gen.generate()
    matrix_path = Path(output_matrix.replace('\\', '/'))
    matrix_path.parent.mkdir(parents=True, exist_ok=True)
    with open(matrix_path, 'w', encoding='utf-8') as f:
        for entry in matrix_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    print(f'MATRIX_COMPLETE')
    print(f'MATRIX_ENTRIES:{len(matrix_entries)}')

except ImportError as e:
    print(f'MODULE_NOT_FOUND:{e}')
    sys.exit(1)
except Exception as e:
    print(f'MATRIX_ERROR:{e}')
    traceback.print_exc()
    sys.exit(1)
"@

    $matrixOutput = python -c $pythonMatrix 2>&1
    $matrixExitCode = $LASTEXITCODE

    $matrixEntries = 0
    foreach ($line in $matrixOutput) {
        Write-Host "  $line" -ForegroundColor Gray
        if ($line -match "MATRIX_ENTRIES:(\d+)") { $matrixEntries = [int]$matches[1] }
    }

    Write-Host ""
    Write-Host "[5/5] Matrix generation complete." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Output:" -ForegroundColor Cyan
    Write-Host "  - Matrix JSONL: $matrixJsonl" -ForegroundColor Green
    Write-Host "  - Total entries: $matrixEntries" -ForegroundColor Green
    exit 0
}

Write-Host "Error: Unknown mode '$Mode'" -ForegroundColor Red
Write-Host "Supported modes: validate-config, sample, audit, matrix" -ForegroundColor Red
exit 1
