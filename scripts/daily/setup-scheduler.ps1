# AgentNexLiFy — Schedule Automated Morning/Evening Routines
# Run this script once in PowerShell (as Administrator) to set up Task Scheduler jobs
# Prerequisites: Claude Code CLI installed, Git Bash available
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\daily\setup-scheduler.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\daily\setup-scheduler.ps1 -MorningTime "09:00" -EveningTime "21:00"

param(
    [string]$RepoPath = (Get-Location).Path,
    [string]$MorningTime = "08:00",
    [string]$EveningTime = "20:00"
)

Write-Host "AgentNexLiFy Scheduler Setup" -ForegroundColor Cyan
Write-Host "============================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Repo path: $RepoPath"
Write-Host "Morning time: $MorningTime"
Write-Host "Evening time: $EveningTime"
Write-Host ""

# Verify prerequisites
$claudePath = Get-Command claude -ErrorAction SilentlyContinue
if (-not $claudePath) {
    Write-Host "ERROR: Claude Code CLI not found. Install it first:" -ForegroundColor Red
    Write-Host "  npm install -g @anthropic-ai/claude-code" -ForegroundColor Yellow
    exit 1
}
Write-Host "Claude Code found: $($claudePath.Source)" -ForegroundColor Green

$gitBashPath = ""
$possiblePaths = @(
    "C:\Program Files\Git\bin\bash.exe",
    "C:\Program Files (x86)\Git\bin\bash.exe",
    "$env:LOCALAPPDATA\Programs\Git\bin\bash.exe"
)
foreach ($path in $possiblePaths) {
    if (Test-Path $path) {
        $gitBashPath = $path
        break
    }
}
if (-not $gitBashPath) {
    Write-Host "ERROR: Git Bash not found. Install Git for Windows first." -ForegroundColor Red
    exit 1
}
Write-Host "Git Bash found: $gitBashPath" -ForegroundColor Green
Write-Host ""

# Create wrapper batch files that Task Scheduler will call
$morningBat = Join-Path $RepoPath "scripts\daily\run-morning.bat"
$eveningBat = Join-Path $RepoPath "scripts\daily\run-evening.bat"

# Morning batch file
@"
@echo off
REM AgentNexLiFy Automated Morning Routine
REM Called by Windows Task Scheduler

cd /d "$RepoPath"
"$gitBashPath" -c "cd '$($RepoPath -replace '\\','/')' && bash scripts/daily/morning-auto.sh"
"@ | Set-Content -Path $morningBat -Encoding ASCII

# Evening batch file
@"
@echo off
REM AgentNexLiFy Automated Evening Review
REM Called by Windows Task Scheduler

cd /d "$RepoPath"
"$gitBashPath" -c "cd '$($RepoPath -replace '\\','/')' && bash scripts/daily/evening-auto.sh"
"@ | Set-Content -Path $eveningBat -Encoding ASCII

Write-Host "Created wrapper scripts:" -ForegroundColor Green
Write-Host "  $morningBat"
Write-Host "  $eveningBat"
Write-Host ""

# Register Morning Task
$morningTaskName = "AgentNexLiFy-Morning"
$existingMorning = Get-ScheduledTask -TaskName $morningTaskName -ErrorAction SilentlyContinue
if ($existingMorning) {
    Unregister-ScheduledTask -TaskName $morningTaskName -Confirm:$false
    Write-Host "Removed existing morning task" -ForegroundColor Yellow
}

$morningAction = New-ScheduledTaskAction -Execute $morningBat
$morningTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At $MorningTime
$morningSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

Register-ScheduledTask -TaskName $morningTaskName -Action $morningAction -Trigger $morningTrigger -Settings $morningSettings -Description "AgentNexLiFy automated morning startup — runs Claude Code to analyze repo and generate task plan" | Out-Null

Write-Host "Registered: $morningTaskName at $MorningTime (weekdays)" -ForegroundColor Green

# Register Evening Task
$eveningTaskName = "AgentNexLiFy-Evening"
$existingEvening = Get-ScheduledTask -TaskName $eveningTaskName -ErrorAction SilentlyContinue
if ($existingEvening) {
    Unregister-ScheduledTask -TaskName $eveningTaskName -Confirm:$false
    Write-Host "Removed existing evening task" -ForegroundColor Yellow
}

$eveningAction = New-ScheduledTaskAction -Execute $eveningBat
$eveningTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At $EveningTime
$eveningSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

Register-ScheduledTask -TaskName $eveningTaskName -Action $eveningAction -Trigger $eveningTrigger -Settings $eveningSettings -Description "AgentNexLiFy automated evening review — runs Claude Code to review work and update knowledge base" | Out-Null

Write-Host "Registered: $eveningTaskName at $EveningTime (weekdays)" -ForegroundColor Green

Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Cyan
Write-Host ""
Write-Host "To verify:" -ForegroundColor White
Write-Host "  Get-ScheduledTask -TaskName 'AgentNexLiFy-*' | Format-Table TaskName, State"
Write-Host ""
Write-Host "To test immediately:" -ForegroundColor White
Write-Host "  Start-ScheduledTask -TaskName '$morningTaskName'"
Write-Host ""
Write-Host "To remove:" -ForegroundColor White
Write-Host "  powershell -ExecutionPolicy Bypass -File scripts\daily\remove-scheduler.ps1"
Write-Host ""
Write-Host "Logs: docs/daily-logs/auto-morning-*.log and auto-evening-*.log" -ForegroundColor White
Write-Host ""
Write-Host "IMPORTANT: Your computer must be ON at the scheduled times." -ForegroundColor Yellow
Write-Host "If missed, -StartWhenAvailable will run it when the machine next wakes up." -ForegroundColor Yellow
