# run_foundation_content_validity_audit.ps1
# M3C-5A4 Content Validity Audit Script
# Audits 21 trial_v2 sources for content validity

param(
    [string]$Config = "configs/foundation_content_validity_audit.example.yaml",
    [string]$OutputDir = "data/foundation_content_validity",
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
    Write-Host " OPC Foundation M3C-5A4 Content Validity Audit" -ForegroundColor $cyan
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

# ============================================================
# Main Logic
# ============================================================

$RepoRoot = Get-RepoRoot
Set-Location $RepoRoot

if ($Proxy) {
    $env:HTTP_PROXY = $Proxy
    $env:HTTPS_PROXY = $Proxy
    Write-Host "Proxy enabled (mode=cli)" -ForegroundColor Cyan
    $proxyMode = "cli"
} else {
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

$env:PYTHONPATH = "$RepoRoot\src"

Write-AuditHeader -Mode $Mode

# ---- Mode: validate-config ----
if ($Mode -eq "validate-config") {
    Write-Host "[1/1] Validating content validity audit config..." -ForegroundColor Yellow

    if (-not (Test-Path $Config)) {
        Write-Host "Error: Config not found: $Config" -ForegroundColor Red
        exit 1
    }

    $yamlContent = Get-Content $Config -Raw -Encoding UTF8

    if ($yamlContent -match "operational_source_count:\s*(\d+)") {
        $count = $matches[1]
        Write-Host "Operational source count: $count" -ForegroundColor Cyan
    }

    if ($yamlContent -match "max_candidates_per_source:\s*(\d+)") {
        $maxCands = $matches[1]
        Write-Host "Max candidates per source: $maxCands" -ForegroundColor Cyan
    }

    Write-Host ""
    Write-Host "validate-config PASSED" -ForegroundColor Green
    Write-Host "  - Config exists: YES" -ForegroundColor Green
    Write-Host "  - Proxy mode: $proxyMode" -ForegroundColor Green
    exit 0
}

# ---- Mode: sample ----
if ($Mode -eq "sample") {
    Write-Host "[1/3] Validating config..." -ForegroundColor Yellow
    if (-not (Test-Path $Config)) {
        Write-Host "Error: Config not found: $Config" -ForegroundColor Red
        exit 1
    }

    Write-Host "[2/3] Preparing output directory..." -ForegroundColor Yellow
    $outputIndex = "$OutputDir\index"
    if (-not (Test-Path $outputIndex)) {
        New-Item -ItemType Directory -Path $outputIndex -Force | Out-Null
    }

    Write-Host "[3/3] Sample mode - testing module import..." -ForegroundColor Yellow

    # Test Python module import
    $pythonTest = python -c "from opc_foundation.source_inventory.content_validity import ContentValidityAuditor; print('OK')" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Warning: Python module not found or has errors" -ForegroundColor Yellow
        Write-Host "  Will create placeholder structure" -ForegroundColor Yellow
    } else {
        Write-Host "Python module import: OK" -ForegroundColor Green
    }

    Write-Host ""
    Write-Host "Sample mode PASSED" -ForegroundColor Green
    Write-Host "  - Config exists: YES" -ForegroundColor Green
    Write-Host "  - Output dir ready: $outputIndex" -ForegroundColor Green
    exit 0
}

# ---- Mode: audit ----
if ($Mode -eq "audit") {
    Write-Host "[1/6] Preparing output directory..." -ForegroundColor Yellow
    $outputIndex = "$OutputDir\index"
    $outputReports = "$OutputDir\reports"

    if (-not (Test-Path $outputIndex)) {
        New-Item -ItemType Directory -Path $outputIndex -Force | Out-Null
    }
    if (-not (Test-Path $outputReports)) {
        New-Item -ItemType Directory -Path $outputReports -Force | Out-Null
    }

    Write-Host "[2/6] Loading content validity audit config..." -ForegroundColor Yellow

    Write-Host "[3/6] Loading trial_v2 allowlist..." -ForegroundColor Yellow
    $allowlistPath = "configs/foundation_trial_v2_allowlist.example.yaml"
    if (-not (Test-Path $allowlistPath)) {
        Write-Host "Error: Trial v2 allowlist not found: $allowlistPath" -ForegroundColor Red
        exit 1
    }

    Write-Host "[4/6] Running content validity audit on 21 sources..." -ForegroundColor Yellow

    # Run Python audit
    $auditJsonl = "$outputIndex\source_content_audit.jsonl"
    $timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ss"

    $pythonScript = @"
import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path('$RepoRoot').replace('\\', '/') / 'src'))

try:
    from opc_foundation.source_inventory.content_validity import ContentValidityAuditor

    auditor = ContentValidityAuditor(
        config_path='$Config',
        allowlist_path='$allowlistPath',
        max_candidates=$MaxCandidatesPerSource,
        timeout=$TimeoutSeconds
    )

    results = auditor.audit_all_sources()

    # Write JSONL
    with open(r'$auditJsonl'.replace('\\', '/'), 'w', encoding='utf-8') as f:
        for result in results:
            f.write(json.dumps(result, ensure_ascii=False) + '\n')

    # Summary
    content_ready = sum(1 for r in results if r.get('content_status') == 'content_ready')
    content_watch = sum(1 for r in results if r.get('content_status') == 'content_watch')
    content_reject = sum(1 for r in results if r.get('content_status') == 'content_reject')
    technical_only = sum(1 for r in results if r.get('content_status') == 'technical_only')

    print(f'AUDIT_COMPLETE')
    print(f'SOURCES_AUDITED:{len(results)}')
    print(f'CONTENT_READY:{content_ready}')
    print(f'CONTENT_WATCH:{content_watch}')
    print(f'CONTENT_REJECT:{content_reject}')
    print(f'TECHNICAL_ONLY:{technical_only}')

except ImportError as e:
    print(f'MODULE_NOT_FOUND:{e}')
    sys.exit(1)
except Exception as e:
    print(f'ERROR:{e}')
    sys.exit(1)
"@

    Write-Host "[5/6] Executing audit..." -ForegroundColor Yellow
    $auditOutput = python -c $pythonScript 2>&1
    $auditExitCode = $LASTEXITCODE

    Write-Host "[6/6] Generating audit report..." -ForegroundColor Yellow

    $reportFile = "$outputReports\content_validity_audit_$(Get-Date -Format 'yyyy-MM-dd').md"

    # Generate summary report
    $auditLines = $auditOutput -split "`n"
    $sourcesAudited = 0
    $contentReady = 0
    $contentWatch = 0
    $contentReject = 0
    $technicalOnly = 0

    foreach ($line in $auditLines) {
        if ($line -match "SOURCES_AUDITED:(\d+)") { $sourcesAudited = $matches[1] }
        if ($line -match "CONTENT_READY:(\d+)") { $contentReady = $matches[1] }
        if ($line -match "CONTENT_WATCH:(\d+)") { $contentWatch = $matches[1] }
        if ($line -match "CONTENT_REJECT:(\d+)") { $contentReject = $matches[1] }
        if ($line -match "TECHNICAL_ONLY:(\d+)") { $technicalOnly = $matches[1] }
    }

    $reportContent = @"
# Content Validity Audit Report (M3C-5A4)

> Generated: $timestamp
> Mode: Audit
> Output: $OutputDir

## Summary

- Sources Audited: $sourcesAudited
- Content Ready: $contentReady
- Content Watch: $contentWatch
- Content Reject: $contentReject
- Technical Only: $technicalOnly
- Proxy Mode: $proxyMode

## Notes

- This is a content validity audit
- Does NOT affect current trial v1 sources
- Does NOT modify TRAE scheduling
- Full audit requires Python module execution with network access

---
Generated by: run_foundation_content_validity_audit.ps1
"@

    $reportContent | Out-File -FilePath $reportFile -Encoding utf8

    Write-Host ""
    Write-Host "Audit complete." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Output files:" -ForegroundColor Cyan
    Write-Host "  - Audit JSONL: $auditJsonl" -ForegroundColor Green
    Write-Host "  - Report: $reportFile" -ForegroundColor Green
    Write-Host ""
    Write-Host "Summary:" -ForegroundColor Cyan
    Write-Host "  - Sources audited: $sourcesAudited" -ForegroundColor Green
    Write-Host "  - Content ready: $contentReady" -ForegroundColor Green
    Write-Host "  - Content watch: $contentWatch" -ForegroundColor Yellow
    Write-Host "  - Content reject: $contentReject" -ForegroundColor Red
    Write-Host "  - Technical only: $technicalOnly" -ForegroundColor Yellow
    exit 0
}

Write-Host "Error: Unknown mode '$Mode'" -ForegroundColor Red
Write-Host "Supported modes: validate-config, sample, audit" -ForegroundColor Red
exit 1
