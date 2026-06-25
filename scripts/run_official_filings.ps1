# Official Filings Foundation - 生产运行脚本
#
# 作用：读取 production local config，运行 SEC / CNINFO / HKEX 官方披露归档。
#
# 使用方法：
#   .\scripts\run_official_filings.ps1                              # 默认 run
#   .\scripts\run_official_filings.ps1 -Mode dry-run                # 试运行
#   .\scripts\run_official_filings.ps1 -Mode run                    # 完整运行
#   .\scripts\run_official_filings.ps1 -Mode source-health          # 查看 source health
#   .\scripts\run_official_filings.ps1 -Mode report                 # 查看日报
#   .\scripts\run_official_filings.ps1 -Config path/to/config.yaml  # 自定义配置
#
# 小白解读：
#   这个脚本就是帮你省去记长命令的麻烦。
#   你只要告诉它"我要 run"或"我要 dry-run"，它就会帮你调用正确的 CLI 命令。

param(
    [string]$Config = "configs/official_filings.production.local.yaml",
    [string]$Mode = "run"
)

$ErrorActionPreference = "Stop"

# 自动定位仓库根目录（脚本位于 scripts/ 下，上一级即仓库根）
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

# 设置 PYTHONPATH，确保能找到 src/ 下的模块
$env:PYTHONPATH = Join-Path $RepoRoot "src"

# 检查配置文件是否存在
if (!(Test-Path $Config)) {
    Write-Host ""
    Write-Host "配置文件不存在：$Config" -ForegroundColor Red
    Write-Host ""
    Write-Host "当前能力尚未配置 production local 文件，请先复制 example 配置并填写本地配置。" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "操作步骤：" -ForegroundColor Yellow
    Write-Host "  1. 复制 configs/official_filings.production.example.yaml 到 $Config"
    Write-Host "  2. 编辑 $Config，填入真实配置"
    Write-Host "  3. 重新运行本脚本"
    exit 1
}

$StartTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Official Filings Archive - $Mode" -ForegroundColor Cyan
Write-Host "开始时间：$StartTime" -ForegroundColor Cyan
Write-Host "配置文件：$Config"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 根据 Mode 调用对应 CLI 命令
switch ($Mode) {
    "dry-run" {
        Write-Host "开始官方披露归档试运行..." -ForegroundColor Cyan
        python -m opc_foundation.official_filings.cli dry-run --config $Config
    }
    "run" {
        Write-Host "开始官方披露归档运行..." -ForegroundColor Cyan
        python -m opc_foundation.official_filings.cli run --config $Config
    }
    "source-health" {
        Write-Host "检查 source health..." -ForegroundColor Cyan
        python -m opc_foundation.official_filings.cli source-health --archive-root ./data/official_filings
    }
    "report" {
        Write-Host "生成日报..." -ForegroundColor Cyan
        python -m opc_foundation.official_filings.cli report --archive-root ./data/official_filings
    }
    default {
        Write-Host "不支持的模式：$Mode" -ForegroundColor Red
        Write-Host ""
        Write-Host "支持的模式：dry-run, run, source-health, report" -ForegroundColor Yellow
        exit 1
    }
}

$exitCode = $LASTEXITCODE
$EndTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "结束时间：$EndTime" -ForegroundColor Cyan

if ($exitCode -eq 0) {
    Write-Host "状态：成功 ✅" -ForegroundColor Green
} elseif ($exitCode -eq 2) {
    Write-Host "状态：部分完成（非阻塞）⚠️" -ForegroundColor Yellow
    Write-Host "请查看日报和 failed_queue 了解详情。" -ForegroundColor Yellow
} else {
    Write-Host "状态：失败 ❌（退出码：$exitCode）" -ForegroundColor Red
}

Write-Host "========================================" -ForegroundColor Cyan
exit $exitCode
