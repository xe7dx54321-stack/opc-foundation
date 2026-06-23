# Document Extraction Foundation - 归档产物检查脚本
#
# 作用：检查 document extraction archive 产物是否存在，输出基本健康信息。
#
# 使用方法：
#   .\scripts\check_document_extraction.ps1
#   .\scripts\check_document_extraction.ps1 -ArchiveRoot ./data/document_extraction

param(
    [string]$ArchiveRoot = "./data/document_extraction"
)

$ErrorActionPreference = "Stop"

# 设置 PYTHONPATH 优先使用项目 src
$env:PYTHONPATH = "src;$env:PYTHONPATH"

Write-Host ""
Write-Host "Document Extraction Foundation - Archive Check" -ForegroundColor Cyan
Write-Host "Archive Root: $ArchiveRoot"
Write-Host ""

# 检查根目录是否存在
if (!(Test-Path $ArchiveRoot)) {
    Write-Host "[WARNING] Archive root does not exist: $ArchiveRoot" -ForegroundColor Yellow
    Write-Host "         可能还没有运行过 document extraction。" -ForegroundColor Yellow
    exit 0
}

# 定义需要检查的关键文件
$indexDir = Join-Path $ArchiveRoot "index"
$reportsDir = Join-Path $ArchiveRoot "reports"
$metadataDir = Join-Path $ArchiveRoot "metadata"
$markdownDir = Join-Path $ArchiveRoot "markdown"
$textDir = Join-Path $ArchiveRoot "text"
$rawDir = Join-Path $ArchiveRoot "raw"

$criticalFiles = @(
    @{ Path = (Join-Path $indexDir "documents.jsonl");         Name = "documents.jsonl";         Required = $true },
    @{ Path = (Join-Path $indexDir "documents.latest.jsonl");  Name = "documents.latest.jsonl";  Required = $false },
    @{ Path = (Join-Path $indexDir "source_health.jsonl");     Name = "source_health.jsonl";     Required = $true },
    @{ Path = (Join-Path $indexDir "failed_queue.jsonl");      Name = "failed_queue.jsonl";      Required = $false },
    @{ Path = (Join-Path $indexDir "run_log.jsonl");           Name = "run_log.jsonl";           Required = $true }
)

$missingCritical = 0
$missingOptional = 0

foreach ($file in $criticalFiles) {
    if (Test-Path $file.Path) {
        $size = (Get-Item $file.Path).Length
        Write-Host ("  [OK]   " + $file.Name + " (" + $size + " bytes)") -ForegroundColor Green
    } else {
        if ($file.Required) {
            Write-Host ("  [WARN] " + $file.Name + " - MISSING (critical)") -ForegroundColor Yellow
            $missingCritical++
        } else {
            Write-Host ("  [-]    " + $file.Name + " - not present (optional)") -ForegroundColor Gray
            $missingOptional++
        }
    }
}

# 检查各输出目录
Write-Host ""
$outputDirs = @(
    @{ Path = $reportsDir;  Name = "reports/";  Filter = "*.md" },
    @{ Path = $metadataDir; Name = "metadata/"; Filter = "*.json" },
    @{ Path = $markdownDir; Name = "markdown/"; Filter = "*.md" },
    @{ Path = $textDir;     Name = "text/";     Filter = "*.txt" },
    @{ Path = $rawDir;      Name = "raw/";      Filter = "*" }
)

foreach ($dir in $outputDirs) {
    if (Test-Path $dir.Path) {
        $count = (Get-ChildItem -Path $dir.Path -Filter $dir.Filter -ErrorAction SilentlyContinue | Measure-Object).Count
        Write-Host ("  [OK]   " + $dir.Name + " (" + $count + " files)") -ForegroundColor Green
    } else {
        Write-Host ("  [-]    " + $dir.Name + " - not present") -ForegroundColor Gray
    }
}

# 检查 failed_queue 是否有失败项（只计数，不视为脚本失败）
$failedCount = 0
$failedQueuePath = Join-Path $indexDir "failed_queue.jsonl"
if (Test-Path $failedQueuePath) {
    $failedCount = (Get-Content $failedQueuePath | Where-Object { $_.Trim() -ne "" } | Measure-Object).Count
}

Write-Host ""
Write-Host "Summary:" -ForegroundColor Cyan
Write-Host ("  Missing critical files: " + $missingCritical)
Write-Host ("  Missing optional files: " + $missingOptional)
Write-Host ("  Failed queue entries:   " + $failedCount)
Write-Host ""

if ($failedCount -gt 0) {
    Write-Host ("[INFO] failed_queue has " + $failedCount + " entries.") -ForegroundColor Yellow
    Write-Host "       这不代表脚本失败，只代表有部分文档抽取失败，可以 retry-failed。" -ForegroundColor Yellow
    Write-Host ""
}

# 调用 source-health CLI（如果存在 source_health.jsonl）
if (Test-Path (Join-Path $indexDir "source_health.jsonl")) {
    Write-Host "Calling source-health CLI..." -ForegroundColor Cyan
    Write-Host ""
    python -m opc_foundation.document_extraction.cli source-health --archive-root $ArchiveRoot
}

if ($missingCritical -gt 0) {
    Write-Host ""
    Write-Host ("[WARNING] " + $missingCritical + " critical file(s) missing.") -ForegroundColor Yellow
    exit 0  # 不以失败退出，只输出 warning
}

Write-Host "All critical files present." -ForegroundColor Green
exit 0
