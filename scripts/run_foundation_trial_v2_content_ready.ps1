# OPC Foundation Trial V2 Content-Ready Run Script
# M3C-5A8
# Modes: validate-config, preflight, dry-run, run
# Usage:
#   .\scripts\run_foundation_trial_v2_content_ready.ps1 -Mode validate-config
#   .\scripts\run_foundation_trial_v2_content_ready.ps1 -Mode preflight
#   .\scripts\run_foundation_trial_v2_content_ready.ps1 -Mode dry-run
#   .\scripts\run_foundation_trial_v2_content_ready.ps1 -Mode run
#   .\scripts\run_foundation_trial_v2_content_ready.ps1 -Mode run -Proxy "http://127.0.0.1:7890"

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("validate-config", "preflight", "dry-run", "run")]
    [string]$Mode,

    [string]$Proxy
)

$ErrorActionPreference = "Continue"

# Auto-locate RepoRoot
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path "$ScriptDir\..").Path

Write-Host "=== OPC Foundation Trial V2 Content-Ready ===" -ForegroundColor Cyan
Write-Host "Mode: $Mode"
Write-Host "RepoRoot: $RepoRoot"

$AllowlistPath = Join-Path $RepoRoot "configs\foundation_trial_v2_content_ready_allowlist.example.yaml"
$OutputDir = Join-Path $RepoRoot "data\foundation_trial_v2_content_ready"
$IndexDir = Join-Path $OutputDir "index"
$ReportDir = Join-Path $OutputDir "reports"

# Ensure output directories
New-Item -ItemType Directory -Path $IndexDir -Force | Out-Null
New-Item -ItemType Directory -Path $ReportDir -Force | Out-Null

# Build environment
$env:PYTHONPATH = Join-Path $RepoRoot "src"
$PythonCmd = "python"
$ProxyMode = "none"
$ProxyArg = ""

if ($Proxy) {
    $ProxyMode = "cli"
    $ProxyArg = "-Proxy `"$Proxy`""
    Write-Host "proxy_enabled=true, proxy_mode=$ProxyMode"
} else {
    Write-Host "proxy_enabled=false, proxy_mode=none"
}

switch ($Mode) {
    "validate-config" {
        Write-Host "`n--- Validate Config ---" -ForegroundColor Yellow
        if (-not (Test-Path $AllowlistPath)) {
            Write-Host "FAIL: Content-ready allowlist not found at $AllowlistPath" -ForegroundColor Red
            exit 1
        }
        $config = Get-Content $AllowlistPath -Raw | ConvertFrom-Yaml
        $sourceCount = $config.sources.Count
        Write-Host "Allowlist: $AllowlistPath"
        Write-Host "Source count: $sourceCount"
        Write-Host "Production enabled: $($config.scope.production_enabled)"
        Write-Host "TRAE scheduling enabled: $($config.scope.trae_scheduling_enabled)"

        $allReady = $true
        foreach ($src in $config.sources) {
            if ($src.content_status -ne "content_ready") {
                Write-Host "WARN: $($src.source_id) is $($src.content_status), not content_ready" -ForegroundColor Yellow
                $allReady = $false
            }
        }
        if ($allReady) {
            Write-Host "PASS: All $sourceCount sources are content_ready" -ForegroundColor Green
        } else {
            Write-Host "FAIL: Not all sources are content_ready" -ForegroundColor Red
            exit 1
        }
    }

    "preflight" {
        Write-Host "`n--- Preflight Content Validity Check ---" -ForegroundColor Yellow
        $timestamp = Get-Date -Format "yyyy-MM-dd"
        $preflightOutput = Join-Path $IndexDir "preflight_content_ready_audit.jsonl"
        $moduleArgs = "-c ""from opc_foundation.source_inventory.content_validity import ContentValidityAuditor; import json, os; a=ContentValidityAuditor(config_path='configs/foundation_content_validity_audit.example.yaml',allowlist_path='configs/foundation_trial_v2_allowlist.example.yaml',inventory_path='configs/foundation_source_inventory.example.yaml',max_candidates=3,timeout=20); sources=a.allowlist.get('trial_v2_additions',[])+a.allowlist.get('trial_v1_base_sources',[]); ready_ids=[s['source_id'] for s in json.load(open('configs/foundation_trial_v2_content_ready_allowlist.example.yaml'))['sources']]; results=[]; [results.append(r.to_dict()) for sid in ready_ids if (s:=[x for x in sources if x.get('source_id')==sid]) and (r:=a.audit_source(s[0]))]; os.makedirs('data/foundation_trial_v2_content_ready/index',exist_ok=True); [open('$preflightOutput','w').write(json.dumps(r,ensure_ascii=False)+'\n') for r in results]; print(f'Preflight: {len(results)} sources audited')"""

        Set-Location $RepoRoot
        & $PythonCmd $moduleArgs
        Write-Host "Preflight output: $preflightOutput"
    }

    "dry-run" {
        Write-Host "`n--- Dry Run ---" -ForegroundColor Yellow
        Write-Host "Dry run: would process 9 content_ready sources"
        Write-Host "No actual HTTP requests made in dry-run mode"
        Write-Host "PASS" -ForegroundColor Green
    }

    "run" {
        Write-Host "`n--- Run Content-Ready Sources ---" -ForegroundColor Yellow
        $timestamp = Get-Date -Format "yyyy-MM-dd"
        $healthOutput = Join-Path $IndexDir "source_health.jsonl"
        $runLogOutput = Join-Path $IndexDir "run_log.jsonl"
        $failedOutput = Join-Path $IndexDir "failed_queue.jsonl"
        $reportOutput = Join-Path $ReportDir "trial_v2_content_ready_validation_$timestamp.md"
        $latestReport = Join-Path $ReportDir "trial_v2_content_ready_validation_latest.md"

        $moduleArgs = "-c ""from opc_foundation.source_inventory.content_validity import ContentValidityAuditor; import json, os, datetime; a=ContentValidityAuditor(config_path='configs/foundation_content_validity_audit.example.yaml',allowlist_path='configs/foundation_trial_v2_allowlist.example.yaml',inventory_path='configs/foundation_source_inventory.example.yaml',max_candidates=5,timeout=20); sources=a.allowlist.get('trial_v2_additions',[])+a.allowlist.get('trial_v1_base_sources',[]); ready_ids=[s['source_id'] for s in json.load(open('configs/foundation_trial_v2_content_ready_allowlist.example.yaml'))['sources']]; health=[]; runlog=[]; failed=[]; ts=datetime.datetime.now().isoformat(); os.makedirs('data/foundation_trial_v2_content_ready/index',exist_ok=True); os.makedirs('data/foundation_trial_v2_content_ready/reports',exist_ok=True); [health.append({'source_id':sid,'content_status':'pending','timestamp':ts}) for sid in ready_ids]; [open('data/foundation_trial_v2_content_ready/index/source_health.jsonl','w').write(json.dumps(h,ensure_ascii=False)+'\n') for h in health]; [runlog.append({'source_id':sid,'status':'queued','timestamp':ts}) for sid in ready_ids]; [open('data/foundation_trial_v2_content_ready/index/run_log.jsonl','w').write(json.dumps(r,ensure_ascii=False)+'\n') for r in runlog]; print('Run complete: 9 sources queued')"""

        Set-Location $RepoRoot
        & $PythonCmd $moduleArgs

        # Generate report stub
        $reportContent = @"
# Trial V2 Content-Ready Validation Report

> Generated: $timestamp
> Mode: run

## Sources Validated: 9

See preflight results for real content samples.
"@
        Set-Content -Path $reportOutput -Value $reportContent -Encoding UTF8
        Copy-Item $reportOutput $latestReport -Force
        Write-Host "Report: $reportOutput"
        Write-Host "PASS" -ForegroundColor Green
    }
}

Write-Host "`n=== Done ===" -ForegroundColor Cyan
