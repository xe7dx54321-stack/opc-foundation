# Official Filings Foundation - 归档产物检查脚本
#
# 作用：检查 official filings 归档产物是否存在，输出基本健康信息。
#
# 使用方法：
#   .\scripts\check_official_filings.ps1
#   .\scripts\check_official_filings.ps1 -ArchiveRoot ./data/official_filings

param(
    [string]$ArchiveRoot = "./data/official_filings"
)

$ErrorActionPreference = "Stop"

# 自动定位仓库根目录（脚本位于 scripts/ 下，上一级即仓库根）
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

# 设置 PYTHONPATH，确保能找到 src/ 下的模块
$env:PYTHONPATH = Join-Path $RepoRoot "src"

Write-Host ""
Write-Host "Official Filings Foundation - 归档检查" -ForegroundColor Cyan
Write-Host "归档目录：$ArchiveRoot"
Write-Host ""

# 检查根目录是否存在
if (!(Test-Path $ArchiveRoot)) {
    Write-Host "[警告] 归档目录不存在：$ArchiveRoot" -ForegroundColor Yellow
    Write-Host "       可能还没有运行过 official filings 归档。" -ForegroundColor Yellow
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
        Write-Host ("  [OK]   " + $file.Name + " (" + $size + " bytes)") -ForegroundColor Green
    } else {
        if ($file.Required) {
            Write-Host ("  [WARN] " + $file.Name + " - 缺失（关键）") -ForegroundColor Yellow
            $missingCritical++
        } else {
            Write-Host ("  [-]    " + $file.Name + " - 不存在（可选）") -ForegroundColor Gray
            $missingOptional++
        }
    }
}

# 检查 reports 目录
Write-Host ""
if (Test-Path $reportsDir) {
    $reportCount = (Get-ChildItem -Path $reportsDir -Filter "*.md" -ErrorAction SilentlyContinue | Measure-Object).Count
    Write-Host ("  [OK]   reports/ (" + $reportCount + " 份 markdown 报告)") -ForegroundColor Green
} else {
    Write-Host "  [WARN] reports/ - 缺失" -ForegroundColor Yellow
    $missingCritical++
}

# 检查 failed_queue 是否有失败项（只计数，不视为脚本失败）
$failedCount = 0
$failedQueuePath = Join-Path $stateDir "failed_queue.jsonl"
if (Test-Path $failedQueuePath) {
    $failedCount = (Get-Content $failedQueuePath | Where-Object { $_.Trim() -ne "" } | Measure-Object).Count
}

Write-Host ""
Write-Host "汇总：" -ForegroundColor Cyan
Write-Host ("  缺失关键文件：" + $missingCritical)
Write-Host ("  缺失可选文件：" + $missingOptional)
Write-Host ("  失败队列条目：" + $failedCount)
Write-Host ""

if ($failedCount -gt 0) {
    Write-Host ("[信息] failed_queue 有 " + $failedCount + " 条记录。") -ForegroundColor Yellow
    Write-Host "       这不代表脚本失败，只代表有部分归档失败，可以重试。" -ForegroundColor Yellow
    Write-Host ""
}

# 调用 source-health CLI（如果存在 source_health.jsonl）
if (Test-Path (Join-Path $stateDir "source_health.jsonl")) {
    Write-Host "调用 source-health CLI..." -ForegroundColor Cyan
    Write-Host ""
    python -m opc_foundation.official_filings.cli source-health --archive-root $ArchiveRoot
}

if ($missingCritical -gt 0) {
    Write-Host ""
    Write-Host ("[警告] " + $missingCritical + " 个关键文件缺失。") -ForegroundColor Yellow
    exit 0  # 不以失败退出，只输出 warning
}

Write-Host "所有关键文件均存在。" -ForegroundColor Green
exit 0
