# ============================================================
# Setup Foundation Trial Schedule - Windows Task Scheduler Setup
# ============================================================
#
# Purpose: Create Windows Task Scheduler jobs for M3C-3 trial scheduling.
#          Based on configs/trae_foundation_trial_schedule.example.yaml.
#
# Usage:
#   - Dry run (preview only): powershell -ExecutionPolicy Bypass -File scripts/setup_foundation_trial_schedule.ps1 -Mode dry-run
#   - Real setup:              powershell -ExecutionPolicy Bypass -File scripts/setup_foundation_trial_schedule.ps1 -Mode setup
#   - List current jobs:       powershell -ExecutionPolicy Bypass -File scripts/setup_foundation_trial_schedule.ps1 -Mode list
#
# This script is TRIAL-ONLY. It only creates jobs for 15 verified trial sources.
# It does NOT create production jobs or 92-source jobs.
#
# ============================================================

param(
    [string]$Mode = "dry-run",
    [string]$RepoRoot = ""
)

# Auto-detect RepoRoot
if (-not $RepoRoot) {
    $currentDir = (Get-Location).Path
    $currentDirFull = [System.IO.Path]::GetFullPath($currentDir)
    if ($currentDirFull -match "opc-foundation") {
        $RepoRoot = $currentDirFull
    }
    else {
        # Try default path
        $defaultRoot = "d:\李少博的文件\一人公司项目开发\opc-foundation"
        if (Test-Path "$defaultRoot\scripts\run_foundation_trial_sources.ps1") {
            $RepoRoot = $defaultRoot
        }
    }
}

if (-not $RepoRoot -or -not (Test-Path "$RepoRoot\scripts\run_foundation_trial_sources.ps1")) {
    Write-Host "[ERROR] Cannot locate opc-foundation repo root."
    Write-Host "Please run this script from the opc-foundation directory or specify -RepoRoot."
    exit 1
}

Set-Location $RepoRoot
Write-Host "RepoRoot: $RepoRoot"
Write-Host "Mode: $Mode"
Write-Host ""

# Trial schedule jobs to create
$trialJobs = @(
    @{
        taskName = "OPC_Foundation_Trial_Morning_Run"
        description = "[Trial] OPC Foundation Trial Sources Morning Run - M3C-3"
        command = "powershell"
        arguments = "-ExecutionPolicy Bypass -File `"$RepoRoot\scripts\run_foundation_trial_sources.ps1`" -Mode run"
        scheduleTime = "08:10"
        scheduleDay = "MON,TUE,WED,THU,FRI,SAT,SUN"
    },
    @{
        taskName = "OPC_Foundation_Trial_Morning_Check"
        description = "[Trial] OPC Foundation Trial Sources Morning Check - M3C-3"
        command = "powershell"
        arguments = "-ExecutionPolicy Bypass -File `"$RepoRoot\scripts\check_foundation_trial_sources.ps1`""
        scheduleTime = "08:25"
        scheduleDay = "MON,TUE,WED,THU,FRI,SAT,SUN"
    },
    @{
        taskName = "OPC_Foundation_Trial_Afternoon_Run"
        description = "[Trial] OPC Foundation Trial Sources Afternoon Run - M3C-3"
        command = "powershell"
        arguments = "-ExecutionPolicy Bypass -File `"$RepoRoot\scripts\run_foundation_trial_sources.ps1`" -Mode run"
        scheduleTime = "13:10"
        scheduleDay = "MON,TUE,WED,THU,FRI,SAT,SUN"
    },
    @{
        taskName = "OPC_Foundation_Trial_Evening_Run"
        description = "[Trial] OPC Foundation Trial Sources Evening Run - M3C-3"
        command = "powershell"
        arguments = "-ExecutionPolicy Bypass -File `"$RepoRoot\scripts\run_foundation_trial_sources.ps1`" -Mode run"
        scheduleTime = "20:10"
        scheduleDay = "MON,TUE,WED,THU,FRI,SAT,SUN"
    },
    @{
        taskName = "OPC_Foundation_Trial_Evening_Check"
        description = "[Trial] OPC Foundation Trial Sources Evening Check - M3C-3"
        command = "powershell"
        arguments = "-ExecutionPolicy Bypass -File `"$RepoRoot\scripts\check_foundation_trial_sources.ps1`""
        scheduleTime = "20:25"
        scheduleDay = "MON,TUE,WED,THU,FRI,SAT,SUN"
    },
    @{
        taskName = "OPC_Foundation_Trial_Daily_Status"
        description = "[Trial] OPC Foundation Trial Daily Status (dry-run) - M3C-3"
        command = "powershell"
        arguments = "-ExecutionPolicy Bypass -File `"$RepoRoot\scripts\run_foundation_trial_sources.ps1`" -Mode dry-run"
        scheduleTime = "23:50"
        scheduleDay = "MON,TUE,WED,THU,FRI,SAT,SUN"
    }
)

if ($Mode -eq "list") {
    Write-Host "=== Current OPC Foundation Trial Scheduled Tasks ==="
    $allTasks = schtasks /query /fo CSV /v 2>$null | ConvertFrom-Csv
    $trialTasks = $allTasks | Where-Object { $_.TaskName -like "*OPC_Foundation_Trial*" }
    if ($trialTasks) {
        $trialTasks | ForEach-Object {
            Write-Host "  [$($_.TaskName)] Next run: $($_.'Next Run Time') Status: $($_.Status)"
        }
    }
    else {
        Write-Host "  No OPC_Foundation_Trial tasks found."
    }
    exit 0
}

if ($Mode -eq "dry-run") {
    Write-Host "=== Dry Run: What Would Be Created ==="
    Write-Host ""
    Write-Host "Trial source count: 15"
    Write-Host "Trial jobs to create: $($trialJobs.Count)"
    Write-Host ""
    $trialJobs | ForEach-Object {
        Write-Host "  [CREATE] $($_.taskName)"
        Write-Host "    Time: $($_.scheduleTime) daily"
        Write-Host "    Command: $($_.command) $($_.arguments)"
        Write-Host "    Description: $($_.description)"
        Write-Host ""
    }
    Write-Host "Trial-only: YES (only 15 sources, NOT 92 sources)"
    Write-Host "Production mode: NO"
    Write-Host "Microsoft IR included: NO (url_backlog)"
    Write-Host ""
    exit 0
}

if ($Mode -eq "setup") {
    Write-Host "=== Setting Up OPC Foundation Trial Scheduled Tasks ==="
    Write-Host ""

    $created = 0
    $skipped = 0
    $failed = 0

    foreach ($job in $trialJobs) {
        # Check if task already exists
        $existing = schtasks /query /tn $job.taskName 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [SKIP] $($job.taskName) already exists. Use -Mode delete-first to replace."
            $skipped++
            continue
        }

        # Create the scheduled task
        # schtasks /create /tn TaskName /tr "command" /sc daily /st HH:MM /ru SYSTEM
        $createCmd = "schtasks /create /tn `"$($job.taskName)`" /tr `"$($job.command) $($job.arguments)`" /sc daily /st $($job.scheduleTime) /ru SYSTEM /f"
        Write-Host "  [CREATE] $($job.taskName) at $($job.scheduleTime)..."
        Write-Host "    Command: $createCmd"

        $result = Invoke-Expression $createCmd 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "    SUCCESS"
            $created++
        }
        else {
            Write-Host "    FAILED: $result"
            $failed++
        }
    }

    Write-Host ""
    Write-Host "=== Setup Complete ==="
    Write-Host "  Created: $created"
    Write-Host "  Skipped: $skipped"
    Write-Host "  Failed: $failed"
    Write-Host ""
    Write-Host "To list tasks:      scripts\setup_foundation_trial_schedule.ps1 -Mode list"
    Write-Host "To delete all:      scripts\remove_foundation_trial_schedule.ps1 -Action delete"
    Write-Host "Trial-only: YES (only 15 sources, NOT 92 sources)"
    exit 0
}

Write-Host "[ERROR] Unknown mode: $Mode"
Write-Host "Supported modes: dry-run, setup, list"
exit 1
