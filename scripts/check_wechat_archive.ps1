<#
.SYNOPSIS
    微信公众号归档目录检查脚本。

.DESCRIPTION
    本脚本用于手动或被 TRAE 调度调用前后，检查归档目录结构是否正常。
    会自动切换到仓库根目录，检查 ./data/wechat_archive 目录。

    本脚本不访问网络，不修改数据，只读检查并输出中文摘要。

.PARAMETER ArchiveRoot
    可选。归档根目录路径，默认 ./data/wechat_archive。

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts/check_wechat_archive.ps1

.NOTES
    退出码：
      0 - 检查通过，归档目录正常
      1 - 检查失败（目录不存在或结构不完整）
#>

param(
    [string]$ArchiveRoot = "./data/wechat_archive"
)

$ErrorActionPreference = "Stop"

# 切换到仓库根目录
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

# 设置 PYTHONPATH，确保能找到 src/ 下的模块
$env:PYTHONPATH = Join-Path $RepoRoot "src"

# 解析为绝对路径
$ArchivePath = Resolve-Path -LiteralPath $ArchiveRoot -ErrorAction SilentlyContinue
if ($null -eq $ArchivePath) {
    Write-Host "归档目录不存在：$ArchiveRoot" -ForegroundColor Red
    Write-Host "请先运行 scripts/run_wechat_archive.ps1 生成归档数据。" -ForegroundColor Yellow
    exit 1
}

$ArchivePath = $ArchivePath.Path

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  微信公众号归档目录检查" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "归档根目录：$ArchivePath" -ForegroundColor Gray
Write-Host ""

# 调用 Python 检查脚本（复用 scripts/wechat_live_smoke.py 的 check 命令）
python scripts/wechat_live_smoke.py check --archive-root $ArchivePath
$ExitCode = $LASTEXITCODE

Write-Host ""
if ($ExitCode -eq 0) {
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  归档目录检查通过" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
} else {
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "  归档目录检查未通过，exit_code=$ExitCode" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
}

exit $ExitCode
