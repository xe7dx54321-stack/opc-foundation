# Official Filing Foundation - 归档检查脚本
#
# 作用：检查 official filings 归档目录的状态，包括索引文件、报表、source health 等。
#
# 使用方法：
#     .\scripts\check_official_filings_archive.ps1                    # 默认检查
#     .\scripts\check_official_filings_archive.ps1 -ArchiveRoot ./data/official_filings
#
# 小白解读：
#     这个脚本帮你检查归档目录里有什么东西。
#     如果你跑完 run 之后想看看结果，就运行这个脚本。

param(
    [string]$ArchiveRoot = "./data/official_filings"
)

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Official Filing Archive 检查" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "归档根目录: $ArchiveRoot"
Write-Host ""

# 检查归档目录是否存在
if (!(Test-Path $ArchiveRoot)) {
    Write-Host "归档目录不存在: $ArchiveRoot" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "请先运行归档脚本：" -ForegroundColor Yellow
    Write-Host "  .\scripts\run_official_filings_archive.ps1 -Mode run"
    exit 0
}

# 检查 index 目录
$indexDir = Join-Path $ArchiveRoot "index"
$indexFiles = @(
    "filings.jsonl",
    "filings.latest.jsonl",
    "source_health.jsonl",
    "failed_queue.jsonl",
    "run_log.jsonl"
)

Write-Host "----------------------------------------" -ForegroundColor Gray
Write-Host "索引文件" -ForegroundColor White
Write-Host "----------------------------------------" -ForegroundColor Gray

if (!(Test-Path $indexDir)) {
    Write-Host "索引目录不存在: $indexDir" -ForegroundColor Yellow
} else {
    foreach ($file in $indexFiles) {
        $filePath = Join-Path $indexDir $file
        if (Test-Path $filePath) {
            $lineCount = (Get-Content $filePath | Measure-Object -Line).Lines
            $size = (Get-Item $filePath).Length
            $sizeStr = if ($size -gt 1MB) { "{0:N2} MB" -f ($size / 1MB) } elseif ($size -gt 1KB) { "{0:N2} KB" -f ($size / 1KB) } else { "$size bytes" }
            Write-Host "  $file : $lineCount 条记录 ($sizeStr)" -ForegroundColor Green
        } else {
            Write-Host "  $file : 不存在" -ForegroundColor Yellow
        }
    }
}

# 检查 reports 目录
Write-Host ""
Write-Host "----------------------------------------" -ForegroundColor Gray
Write-Host "日报" -ForegroundColor White
Write-Host "----------------------------------------" -ForegroundColor Gray

$reportsDir = Join-Path $ArchiveRoot "reports"
if (!(Test-Path $reportsDir)) {
    Write-Host "报表目录不存在: $reportsDir" -ForegroundColor Yellow
} else {
    $reportFiles = Get-ChildItem -Path $reportsDir -Filter "daily_filing_*.md" | Sort-Object LastWriteTime -Descending | Select-Object -First 5
    if ($reportFiles.Count -eq 0) {
        Write-Host "没有找到日报文件" -ForegroundColor Yellow
    } else {
        foreach ($report in $reportFiles) {
            Write-Host "  $($report.Name) - $($report.LastWriteTime.ToString('yyyy-MM-dd HH:mm:ss'))" -ForegroundColor Green
        }
    }
}

# 检查 metadata 目录
Write-Host ""
Write-Host "----------------------------------------" -ForegroundColor Gray
Write-Host "元数据文件" -ForegroundColor White
Write-Host "----------------------------------------" -ForegroundColor Gray

$metadataDir = Join-Path $ArchiveRoot "metadata"
if (!(Test-Path $metadataDir)) {
    Write-Host "元数据目录不存在: $metadataDir" -ForegroundColor Yellow
} else {
    $metadataCount = (Get-ChildItem -Path $metadataDir -Filter "*.json" -ErrorAction SilentlyContinue | Measure-Object).Count
    if ($metadataCount -eq 0) {
        Write-Host "没有找到元数据文件" -ForegroundColor Yellow
    } else {
        Write-Host "  共 $metadataCount 个元数据文件" -ForegroundColor Green
    }
}

# 检查 raw 目录
Write-Host ""
Write-Host "----------------------------------------" -ForegroundColor Gray
Write-Host "原始数据" -ForegroundColor White
Write-Host "----------------------------------------" -ForegroundColor Gray

$rawDir = Join-Path $ArchiveRoot "raw"
if (!(Test-Path $rawDir)) {
    Write-Host "原始数据目录不存在（可能是 save_raw=false）" -ForegroundColor Gray
} else {
    $sources = @("sec", "cninfo", "hkex")
    $hasAnyRaw = $false
    foreach ($source in $sources) {
        $sourceDir = Join-Path $rawDir $source
        if (Test-Path $sourceDir) {
            $fileCount = (Get-ChildItem -Path $sourceDir -File -ErrorAction SilentlyContinue | Measure-Object).Count
            if ($fileCount -gt 0) {
                Write-Host "  raw/$source : $fileCount 个文件" -ForegroundColor Green
                $hasAnyRaw = $true
            }
        }
    }
    if (-not $hasAnyRaw) {
        Write-Host "原始数据目录为空（可能是 save_raw=false 或没有启用 source）" -ForegroundColor Gray
    }
}

# 输出 Source Health 摘要
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Source Health 摘要" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$healthFile = Join-Path $indexDir "source_health.jsonl"
if (Test-Path $healthFile) {
    $healthContent = Get-Content $healthFile -Tail 10 -ErrorAction SilentlyContinue
    Write-Host $healthContent -ForegroundColor White
} else {
    Write-Host "没有找到 source health 记录" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "检查完成。" -ForegroundColor Cyan
