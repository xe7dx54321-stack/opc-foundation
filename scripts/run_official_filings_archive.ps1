# Official Filing Foundation - 生产运行脚本
#
# 作用：读取 production local config，运行 official filings archive。
#
# 使用方法：
#     .\scripts\run_official_filings_archive.ps1                              # 默认 run
#     .\scripts\run_official_filings_archive.ps1 -Mode dry-run                # 试运行
#     .\scripts\run_official_filings_archive.ps1 -Mode run                   # 完整运行
#     .\scripts\run_official_filings_archive.ps1 -Mode source-health         # 查看 source health
#     .\scripts\run_official_filings_archive.ps1 -Mode report                # 查看日报
#     .\scripts\run_official_filings_archive.ps1 -Config path/to/config.yaml # 自定义配置
#
# 小白解读：
#     这个脚本就是帮你省去记长命令的麻烦。
#     你只要告诉它"我要 run"或"我要 dry-run"，它就会帮你调用正确的 CLI 命令。

param(
    [string]$Config = "configs/official_filings.production.local.yaml",
    [string]$Mode = "run"
)

$ErrorActionPreference = "Stop"

# 设置 PYTHONPATH 优先使用项目 src
$env:PYTHONPATH = "src;$env:PYTHONPATH"

# 检查配置文件是否存在
if (!(Test-Path $Config)) {
    Write-Host ""
    Write-Host "配置文件不存在: $Config" -ForegroundColor Red
    Write-Host ""
    Write-Host "请按以下步骤操作：" -ForegroundColor Yellow
    Write-Host "  1. 复制 configs/official_filings.production.example.yaml 到 $Config"
    Write-Host "  2. 编辑 $Config，启用需要的 source（设置 enabled: true）"
    Write-Host "  3. 如果需要，修改 endpoint_url 为真实的查询地址"
    Write-Host "  4. 重新运行本脚本"
    Write-Host ""
    Write-Host "或者先用 dry-run 模式测试配置：" -ForegroundColor Cyan
    Write-Host "  .\scripts\run_official_filings_archive.ps1 -Mode dry-run"
    exit 1
}

# 根据 Mode 调用对应 CLI 命令
switch ($Mode) {
    "dry-run" {
        Write-Host ""
        Write-Host "开始 official filings dry-run（只发现候选，不写归档）..." -ForegroundColor Cyan
        python -m opc_foundation.official_filings.cli dry-run --config $Config
    }
    "run" {
        Write-Host ""
        Write-Host "开始 official filings run（发现候选并写入归档）..." -ForegroundColor Cyan
        python -m opc_foundation.official_filings.cli run --config $Config
    }
    "source-health" {
        Write-Host ""
        Write-Host "查看 source health 状态..." -ForegroundColor Cyan
        python -m opc_foundation.official_filings.cli source-health --archive-root ./data/official_filings
    }
    "source-health-json" {
        Write-Host ""
        Write-Host "查看 source health 状态（JSON 格式）..." -ForegroundColor Cyan
        python -m opc_foundation.official_filings.cli source-health --archive-root ./data/official_filings --format json
    }
    "report" {
        Write-Host ""
        Write-Host "查看今日日报..." -ForegroundColor Cyan
        $today = Get-Date -Format "yyyy-MM-dd"
        python -m opc_foundation.official_filings.cli report --archive-root ./data/official_filings --date $today
    }
    "retry-failed" {
        Write-Host ""
        Write-Host "重试失败队列..." -ForegroundColor Cyan
        python -m opc_foundation.official_filings.cli retry-failed --archive-root ./data/official_filings
    }
    "validate-config" {
        Write-Host ""
        Write-Host "校验配置文件..." -ForegroundColor Cyan
        python -m opc_foundation.official_filings.cli validate-config --config $Config
    }
    default {
        Write-Host ""
        Write-Host "不支持的模式: $Mode" -ForegroundColor Red
        Write-Host ""
        Write-Host "支持的模式：" -ForegroundColor Yellow
        Write-Host "  dry-run          - 试运行（只发现候选，不写归档）"
        Write-Host "  run              - 完整运行（发现候选并写入归档）"
        Write-Host "  source-health    - 查看 source health 状态"
        Write-Host "  source-health-json - 查看 source health 状态（JSON 格式）"
        Write-Host "  report           - 查看今日日报"
        Write-Host "  retry-failed     - 重试失败队列"
        Write-Host "  validate-config  - 校验配置文件"
        exit 1
    }
}

$exitCode = $LASTEXITCODE
Write-Host ""
if ($exitCode -eq 0) {
    Write-Host "执行完成。" -ForegroundColor Green
} else {
    Write-Host "执行失败，退出码: $exitCode" -ForegroundColor Red
}
exit $exitCode
