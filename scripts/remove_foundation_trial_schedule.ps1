# ============================================================
# Remove Foundation Trial Schedule - Windows Task Scheduler Cleanup
# ============================================================
#
# Purpose: Remove or disable Windows Task Scheduler jobs for M3C-3 trial scheduling.
#
# Usage:
#   - Disable all trial jobs:  powershell -ExecutionPolicy Bypass -File scripts/remove_foundation_trial_schedule.ps1 -Action disable
#   - Delete all trial jobs:    powershell -ExecutionPolicy Bypass -File scripts/remove_foundation_trial_schedule.ps1 -Action delete
#   - Dry run (preview):        powershell -ExecutionPolicy Bypass -File scripts/remove_foundation_trial_schedule.ps1 -Action dry-run
#
# ============================================================

param(
    [string]$Action = "dry-run"
)

$trialTaskNames = @(
    "OPC_Foundation_Trial_Morning_Run",
    "OPC_Foundation_Trial_Morning_Check",
    "OPC_Foundation_Trial_Afternoon_Run",
    "OPC_Foundation_Trial_Evening_Run",
    "OPC_Foundation_Trial_Evening_Check",
    "OPC_Foundation_Trial_Daily_Status"
)

if ($Action -eq "dry-run") {
    Write-Host "=== Dry Run: What Would Be Removed/Disabled ==="
    Write-Host ""
    foreach ($name in $trialTaskNames) {
        $existing = schtasks /query /tn $name 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [FOUND] $name (would be deleted)"
        }
        else {
            Write-Host "  [NOT FOUND] $name"
        }
    }
    Write-Host ""
    Write-Host "This will NOT affect: source inventory, production jobs, blocked source policy."
    exit 0
}

if ($Action -eq "disable") {
    Write-Host "=== Disabling OPC Foundation Trial Scheduled Tasks ==="
    $disabled = 0
    $notFound = 0
    foreach ($name in $trialTaskNames) {
        $existing = schtasks /query /tn $name 2>$null
        if ($LASTEXITCODE -eq 0) {
            $result = schtasks /change /tn $name /disable 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  [DISABLED] $name"
                $disabled++
            }
            else {
                Write-Host "  [ERROR] $name : $result"
            }
        }
        else {
            Write-Host "  [NOT FOUND] $name"
            $notFound++
        }
    }
    Write-Host ""
    Write-Host "Disabled: $disabled, Not found: $notFound"
    exit 0
}

if ($Action -eq "delete") {
    Write-Host "=== Deleting OPC Foundation Trial Scheduled Tasks ==="
    $deleted = 0
    $notFound = 0
    foreach ($name in $trialTaskNames) {
        $existing = schtasks /query /tn $name 2>$null
        if ($LASTEXITCODE -eq 0) {
            $result = schtasks /delete /tn $name /f 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "  [DELETED] $name"
                $deleted++
            }
            else {
                Write-Host "  [ERROR] $name : $result"
            }
        }
        else {
            Write-Host "  [NOT FOUND] $name"
            $notFound++
        }
    }
    Write-Host ""
    Write-Host "Deleted: $deleted, Not found: $notFound"
    Write-Host ""
    Write-Host "NOTE: data/foundation_trial/ is preserved (not deleted by this script)."
    Write-Host "This will NOT affect: source inventory, production jobs, blocked source policy."
    exit 0
}

Write-Host "[ERROR] Unknown action: $Action"
Write-Host "Supported actions: dry-run, disable, delete"
exit 1
