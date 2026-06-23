# Research Source Foundation - 归档产物检查脚本
#
# 作用：检查 research archive 产物是否存在，输出基本健康信息。
#
# 使用方法：
#   .\scripts\check_research_archive.ps1
#   .\scripts\check_research_archive.ps1 -ArchiveRoot ./data/research_archive
#
# 检查内容：
#   - data/research_archive/index/documents.jsonl
#   - data/research_archive/index/documents.latest.jsonl
#   - data/research_archive/state/run_log.jsonl
#   - data/research_archive/state/source_health.jsonl
#   - data/research_archive/state/failed_queue.jsonl
#   - data/research_archive/reports/
#
# 小白解读：
#   这个脚本帮你快速看一眼"采集产物齐不齐"。
#   缺少关键文件会输出 warning，但不会因为 failed_queue 存在就失败。

param(
    [string]$ArchiveRoot = "./data/research_archive"
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "Research Source Foundation - Archive Check" -ForegroundColor Cyan
Write-Host "Archive Root: $ArchiveRoot"
Write-Host ""

# 检查根目录是否存在
if (!(Test-Path $ArchiveRoot)) {
    Write-Host "[WARNING] Archive root does not exist: $ArchiveRoot" -ForegroundColor Yellow
    Write-Host "         可能还没有运行过 research archive。" -ForegroundColor Yellow
    exit 0
}

# 定义需要检查的关键文件
$indexDir = Join-Path $ArchiveRoot "index"
$stateDir = Join-Path $ArchiveRoot "state"
$reportsDir = Join-Path $ArchiveRoot "reports"

$criticalFiles = @(
    @{ Path = (Join-Path $indexDir "documents.jsonl");         Name = "documents.jsonl";         Required = $true },
    @{ Path = (Join-Path $indexDir "documents.latest.jsonl");  Name = "documents.latest.jsonl";  Required = $false },
    @{ Path = (Join-Path $stateDir "run_log.jsonl");           Name = "run_log.jsonl";           Required = $true },
    @{ Path = (Join-Path $stateDir "source_health.jsonl");     Name = "source_health.jsonl";     Required = $true },
    @{ Path = (Join-Path $stateDir "failed_queue.jsonl");      Name = "failed_queue.jsonl";      Required = $false }
)

$missingCritical = 0
$missingOptional = 0

foreach ($file in $criticalFiles) {
    if (Test-Path $file.Path) {
        $size = (Get-Item $file.Path).Length
        Write-Host "  [OK]   $($file.Name) ($size bytes)" -ForegroundColor Green
    } else {
        if ($file.Required) {
            Write-Host "  [WARN] $($file.Name) - MISSING (critical)" -ForegroundColor Yellow
            $missingCritical++
        } else {
            Write-Host "  [-]    $($file.Name) - not present (optional)" -ForegroundColor Gray
            $missingOptional++
        }
    }
}

# 检查 reports 目录
Write-Host ""
if (Test-Path $reportsDir) {
    $reportCount = (Get-ChildItem -Path $reportsDir -Filter "*.md" -ErrorAction SilentlyContinue | Measure-Object).Count
    Write-Host "  [OK]   reports/ ($reportCount markdown reports)" -ForegroundColor Green
} else {
    Write-Host "  [WARN] reports/ - MISSING" -ForegroundColor Yellow
    $missingCritical++
}

# 检查 failed_queue 是否有失败项（只计数，不视为脚本失败）
$failedCount = 0
$failedQueuePath = Join-Path $stateDir "failed_queue.jsonl"
if (Test-Path $failedQueuePath) {
    $failedCount = (Get-Content $failedQueuePath | Where-Object { $_.Trim() -ne "" } | Measure-Object).Count
}

Write-Host ""
Write-Host "Summary:" -ForegroundColor Cyan
Write-Host "  Missing critical files: $missingCritical"
Write-Host "  Missing optional files: $missingOptional"
Write-Host "  Failed queue entries:   $failedCount"
Write-Host ""

if ($failedCount -gt 0) {
    Write-Host "[INFO] failed_queue has $failedCount entries." -ForegroundColor Yellow
    Write-Host "       这不代表脚本失败，只代表有部分文档归档失败，可以 retry-failed。" -ForegroundColor Yellow
    Write-Host ""
}

# 调用 source-health CLI（如果存在 source_health.jsonl）
if (Test-Path (Join-Path $stateDir "source_health.jsonl")) {
    Write-Host "Calling source-health CLI..." -ForegroundColor Cyan
    Write-Host ""
    python -m opc_foundation.research.cli source-health --archive-root $ArchiveRoot
}

if ($missingCritical -gt 0) {
    Write-Host ""
    Write-Host "[WARNING] $missingCritical critical file(s) missing." -ForegroundColor Yellow
    exit 0  # 不以失败退出，只输出 warning
}

Write-Host "All critical files present." -ForegroundColor Green
exit 0
