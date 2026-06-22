<#
.SYNOPSIS
    微信公众号归档生产运行脚本。

.DESCRIPTION
    本脚本用于手动或被 TRAE 调度调用，执行一次完整的微信公众号归档流程。
    会自动切换到仓库根目录，读取生产 local config，执行 wechat archive run。

    本脚本不包含真实 feed_url、cookie、token。
    本脚本不调用 LLM、不判断文章价值、不接业务线。

.PARAMETER Config
    可选。生产配置文件路径，默认 configs/wechat_archive.production.local.yaml。

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts/run_wechat_archive.ps1

.NOTES
    退出码：
      0 - 成功
      1 - 配置错误或脚本错误
      2 - 部分失败（非阻塞，请查看日报和 failed_queue）
      3 - 严重错误
#>

param(
    [string]$Config = "configs/wechat_archive.production.local.yaml"
)

$ErrorActionPreference = "Stop"

# 切换到仓库根目录（脚本位于 scripts/ 下，上一级即仓库根）
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

# 设置 PYTHONPATH，确保能找到 src/ 下的模块
$env:PYTHONPATH = Join-Path $RepoRoot "src"

# 检查配置文件是否存在
if (-not (Test-Path $Config)) {
    Write-Host "缺少生产配置文件：$Config" -ForegroundColor Red
    Write-Host "请先执行：" -ForegroundColor Yellow
    Write-Host "  Copy-Item configs/wechat_archive.production.example.yaml configs/wechat_archive.production.local.yaml" -ForegroundColor Yellow
    Write-Host "然后编辑 wechat_archive.production.local.yaml，填入真实 feed_url。" -ForegroundColor Yellow
    exit 1
}

$StartTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  微信公众号归档任务（生产）" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "仓库根目录：$RepoRoot" -ForegroundColor Gray
Write-Host "配置文件：  $Config" -ForegroundColor Gray
Write-Host "开始时间：  $StartTime" -ForegroundColor Gray
Write-Host ""

# 执行归档
python -m opc_foundation.wechat.cli run --config $Config
$ExitCode = $LASTEXITCODE

$EndTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Write-Host ""
Write-Host "结束时间：  $EndTime" -ForegroundColor Gray

# 根据退出码输出摘要（使用 if/elseif/else 避免 switch 兼容性问题）
if ($ExitCode -eq 0) {
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  微信公众号归档任务完成" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
} elseif ($ExitCode -eq 2) {
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host "  归档任务部分完成（存在非阻塞失败）" -ForegroundColor Yellow
    Write-Host "  请查看日报和 failed_queue.jsonl" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Yellow
} else {
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "  归档任务失败，exit_code=$ExitCode" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
}

exit $ExitCode
