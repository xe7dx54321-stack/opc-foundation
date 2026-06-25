# Foundation Control Center - 健康检查脚本
#
# 作用：只读检查 Dashboard / Control Center 所需配置是否完整。
#       不启动 Streamlit，不访问网站，不写 data。
#
# 使用方法：
#   .\scripts\check_foundation_control_center.ps1
#
# 小白解读：
#   这个脚本帮你检查 Control Center 需要的配置文件都在不在，
#   就像体检一样，看看各个零件是不是都齐了。
#   它不会启动 Dashboard，只是检查配置。

param()

$ErrorActionPreference = "Stop"

# 自动定位仓库根目录（脚本位于 scripts/ 下，上一级即仓库根）
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
Set-Location $RepoRoot

# 设置 PYTHONPATH，确保能找到 src/ 下的模块
$env:PYTHONPATH = Join-Path $RepoRoot "src"

Write-Host ""
Write-Host "Foundation Control Center - 配置健康检查" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "检查目录：$RepoRoot"
Write-Host ""

# 需要检查的配置文件列表
$configFiles = @(
    @{ Path = "configs/foundation_capabilities.yaml";                Name = "能力台账";                  Required = $true },
    @{ Path = "configs/capability_runbooks.yaml";                    Name = "运行手册";                  Required = $true },
    @{ Path = "configs/capability_runtime_bindings.yaml";            Name = "运行时绑定（example）";     Required = $false },
    @{ Path = "configs/foundation_source_inventory.example.yaml";    Name = "信息源清单（example）";    Required = $true },
    @{ Path = "configs/trae_foundation_schedule.example.yaml";       Name = "TRAE 调度模板（example）";  Required = $false }
)

$missingCritical = 0
$missingOptional = 0
$okCount = 0

Write-Host "配置文件检查：" -ForegroundColor Cyan
Write-Host ""

foreach ($file in $configFiles) {
    if (Test-Path $file.Path) {
        $size = (Get-Item $file.Path).Length
        Write-Host ("  [OK]   " + $file.Name + " (" + $size + " bytes)") -ForegroundColor Green
        $okCount++
    } else {
        if ($file.Required) {
            Write-Host ("  [ERROR] " + $file.Name + " - 缺失（关键）") -ForegroundColor Red
            $missingCritical++
        } else {
            Write-Host ("  [WARN] " + $file.Name + " - 不存在（可选）") -ForegroundColor Yellow
            $missingOptional++
        }
    }
}

Write-Host ""

# 检查 source inventory 是否可加载（通过 Python）
Write-Host "Source Inventory 加载检查：" -ForegroundColor Cyan
Write-Host ""

$sourceInvPath = "configs/foundation_source_inventory.example.yaml"
if (Test-Path $sourceInvPath) {
    try {
        $result = python -c "
import sys
sys.path.insert(0, 'src')
from opc_foundation.dashboard.loaders import load_source_inventory_config, validate_source_inventory
inv = load_source_inventory_config('configs/foundation_source_inventory.example.yaml')
v = validate_source_inventory(inv)
print(f'groups={len(inv.groups)}, sources={len(inv.sources)}, errors={v.error_count}, warnings={v.warning_count}')
" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host ("  [OK]   加载成功 - " + $result) -ForegroundColor Green
        } else {
            Write-Host "  [WARN] 加载失败（可能是依赖问题）" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  [WARN] 加载检查跳过（Python 调用失败）" -ForegroundColor Yellow
    }
}

Write-Host ""

# 汇总
Write-Host "汇总：" -ForegroundColor Cyan
Write-Host ("  正常：" + $okCount)
Write-Host ("  缺失（关键）：" + $missingCritical)
Write-Host ("  缺失（可选）：" + $missingOptional)
Write-Host ""

if ($missingCritical -gt 0) {
    Write-Host "[错误] 有 $missingCritical 个关键配置文件缺失。" -ForegroundColor Red
    Write-Host "     请补全后再启动 Control Center。" -ForegroundColor Red
    exit 1
} else {
    Write-Host "[成功] 所有关键配置文件均存在。" -ForegroundColor Green
    Write-Host "       可以启动 Foundation Control Center。" -ForegroundColor Green
    exit 0
}
