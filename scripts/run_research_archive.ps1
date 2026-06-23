# Research Source Foundation - 生产运行脚本
#
# 作用：读取 production local config，运行 research archive。
#
# 使用方法：
#   .\scripts\run_research_archive.ps1                              # 默认 run
#   .\scripts\run_research_archive.ps1 -Mode dry-run                # 试运行
#   .\scripts\run_research_archive.ps1 -Mode run                    # 完整运行
#   .\scripts\run_research_archive.ps1 -Mode source-health          # 查看 source health
#   .\scripts\run_research_archive.ps1 -Config path/to/config.yaml  # 自定义配置
#
# 小白解读：
#   这个脚本就是帮你省去记长命令的麻烦。
#   你只要告诉它"我要 run"或"我要 dry-run"，它就会帮你调用正确的 CLI 命令。

param(
    [string]$Config = "configs/research_sources.production.local.yaml",
    [string]$Mode = "run"
)

$ErrorActionPreference = "Stop"

# 检查配置文件是否存在
if (!(Test-Path $Config)) {
    Write-Host "Missing config: $Config" -ForegroundColor Red
    Write-Host ""
    Write-Host "请按以下步骤操作：" -ForegroundColor Yellow
    Write-Host "  1. 复制 configs/research_sources.production.example.yaml 到 $Config"
    Write-Host "  2. 编辑 $Config，填入真实 source URL"
    Write-Host "  3. 重新运行本脚本"
    exit 1
}

# 根据 Mode 调用对应 CLI 命令
switch ($Mode) {
    "dry-run" {
        Write-Host "Starting research archive dry-run..." -ForegroundColor Cyan
        python -m opc_foundation.research.cli dry-run --config $Config
    }
    "run" {
        Write-Host "Starting research archive run..." -ForegroundColor Cyan
        python -m opc_foundation.research.cli run --config $Config
    }
    "source-health" {
        Write-Host "Checking source health..." -ForegroundColor Cyan
        python -m opc_foundation.research.cli source-health --archive-root ./data/research_archive
    }
    default {
        Write-Host "Unsupported mode: $Mode" -ForegroundColor Red
        Write-Host ""
        Write-Host "Supported modes: dry-run, run, source-health" -ForegroundColor Yellow
        exit 1
    }
}

$exitCode = $LASTEXITCODE
if ($exitCode -eq 0) {
    Write-Host ""
    Write-Host "Done." -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "Failed with exit code: $exitCode" -ForegroundColor Red
}
exit $exitCode
