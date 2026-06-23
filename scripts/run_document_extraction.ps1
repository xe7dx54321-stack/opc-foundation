# Document Extraction Foundation - 生产运行脚本
#
# 作用：读取 production local config，运行 document extraction archive。
#
# 使用方法：
#   .\scripts\run_document_extraction.ps1                              # 默认 run
#   .\scripts\run_document_extraction.ps1 -Mode validate-config       # 验证配置
#   .\scripts\run_document_extraction.ps1 -Mode dry-run               # 试运行
#   .\scripts\run_document_extraction.ps1 -Mode run                   # 完整运行
#   .\scripts\run_document_extraction.ps1 -Mode source-health         # 查看 source health
#   .\scripts\run_document_extraction.ps1 -Mode report                # 查看日报
#   .\scripts\run_document_extraction.ps1 -Mode retry-failed          # 重试失败队列
#   .\scripts\run_document_extraction.ps1 -Config path/to/config.yaml # 自定义配置
#
# 小白解读：
#   这个脚本就是帮你省去记长命令的麻烦。
#   你只要告诉它"我要 run"或"我要 dry-run"，它就会帮你调用正确的 CLI 命令。

param(
    [string]$Config = "configs/document_extraction.production.local.yaml",
    [string]$Mode = "run",
    [string]$ArchiveRoot = "./data/document_extraction",
    [string]$Date = ""
)

$ErrorActionPreference = "Stop"

# 设置 PYTHONPATH 优先使用项目 src
$env:PYTHONPATH = "src;$env:PYTHONPATH"

# 根据 Mode 判断是否需要配置文件
$needsConfig = @("validate-config", "dry-run", "run", "retry-failed") -contains $Mode

if ($needsConfig) {
    # 检查配置文件是否存在
    if (!(Test-Path $Config)) {
        Write-Host "Missing config: $Config" -ForegroundColor Red
        Write-Host ""
        Write-Host "请按以下步骤操作：" -ForegroundColor Yellow
        Write-Host "  1. 复制 configs/document_extraction.production.example.yaml 到 $Config"
        Write-Host "  2. 编辑 $Config，填入真实 source 路径"
        Write-Host "  3. 重新运行本脚本"
        exit 1
    }
}

# 根据 Mode 调用对应 CLI 命令
switch ($Mode) {
    "validate-config" {
        Write-Host "Validating document extraction config..." -ForegroundColor Cyan
        python -m opc_foundation.document_extraction.cli validate-config --config $Config
    }
    "dry-run" {
        Write-Host "Starting document extraction dry-run..." -ForegroundColor Cyan
        python -m opc_foundation.document_extraction.cli dry-run --config $Config
    }
    "run" {
        Write-Host "Starting document extraction run..." -ForegroundColor Cyan
        python -m opc_foundation.document_extraction.cli run --config $Config
    }
    "source-health" {
        Write-Host "Checking source health..." -ForegroundColor Cyan
        python -m opc_foundation.document_extraction.cli source-health --archive-root $ArchiveRoot
    }
    "report" {
        Write-Host "Viewing daily report..." -ForegroundColor Cyan
        if ($Date) {
            python -m opc_foundation.document_extraction.cli report --archive-root $ArchiveRoot --date $Date
        } else {
            python -m opc_foundation.document_extraction.cli report --archive-root $ArchiveRoot
        }
    }
    "retry-failed" {
        Write-Host "Retrying failed documents..." -ForegroundColor Cyan
        python -m opc_foundation.document_extraction.cli retry-failed --archive-root $ArchiveRoot --config $Config
    }
    default {
        Write-Host "Unsupported mode: $Mode" -ForegroundColor Red
        Write-Host ""
        Write-Host "Supported modes: validate-config, dry-run, run, source-health, report, retry-failed" -ForegroundColor Yellow
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
