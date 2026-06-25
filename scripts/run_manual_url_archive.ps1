# Manual URL Archive - 人工 URL 归档脚本
#
# 作用：检查并处理 manual_url 待处理队列。
#
# 使用方法：
#   .\scripts\run_manual_url_archive.ps1
#   .\scripts\run_manual_url_archive.ps1 -Mode check
#   .\scripts\run_manual_url_archive.ps1 -Mode process
#
# 小白解读：
#   这个脚本用于处理人工收集的 URL 归档队列。
#   没有待处理 URL 时会正常退出，不会报错。
#   manual_url 以人工触发为主，不建议高频调度。

param(
    [string]$Mode = "check"
)

$ErrorActionPreference = "Stop"

# 自动定位仓库根目录（脚本位于 scripts/ 下，上一级即仓库根）
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

# 设置 PYTHONPATH，确保能找到 src/ 下的模块
$env:PYTHONPATH = Join-Path $RepoRoot "src"

Write-Host ""
Write-Host "Manual URL Archive - $Mode" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# manual_url 队列路径（示例路径，实际路径可能不同）
$manualQueuePath = "data/manual_url/pending.jsonl"

switch ($Mode) {
    "check" {
        Write-Host "检查 manual_url 待处理队列..." -ForegroundColor Cyan
        Write-Host ""

        if (!(Test-Path $manualQueuePath)) {
            Write-Host "[信息] 无待处理 URL，等待人工触发。" -ForegroundColor Green
            Write-Host "       队列文件不存在：$manualQueuePath" -ForegroundColor Gray
            exit 0
        }

        $pendingCount = (Get-Content $manualQueuePath | Where-Object { $_.Trim() -ne "" } | Measure-Object).Count

        if ($pendingCount -eq 0) {
            Write-Host "[信息] 无待处理 URL，等待人工触发。" -ForegroundColor Green
            exit 0
        } else {
            Write-Host "[信息] 待处理 URL 数量：$pendingCount" -ForegroundColor Yellow
            Write-Host "       可手动执行 process 模式进行处理。" -ForegroundColor Yellow
            exit 0
        }
    }
    "process" {
        Write-Host "处理 manual_url 待处理队列..." -ForegroundColor Cyan
        Write-Host ""

        if (!(Test-Path $manualQueuePath)) {
            Write-Host "[信息] 无待处理 URL，无需处理。" -ForegroundColor Green
            exit 0
        }

        $pendingCount = (Get-Content $manualQueuePath | Where-Object { $_.Trim() -ne "" } | Measure-Object).Count

        if ($pendingCount -eq 0) {
            Write-Host "[信息] 无待处理 URL，无需处理。" -ForegroundColor Green
            exit 0
        }

        Write-Host "[提示] 检测到 $pendingCount 条待处理 URL。" -ForegroundColor Yellow
        Write-Host "       manual_url 归档功能尚未完全实现，" -ForegroundColor Yellow
        Write-Host "       请等待后续版本支持。" -ForegroundColor Yellow
        exit 0
    }
    default {
        Write-Host "不支持的模式：$Mode" -ForegroundColor Red
        Write-Host ""
        Write-Host "支持的模式：check, process" -ForegroundColor Yellow
        exit 1
    }
}
