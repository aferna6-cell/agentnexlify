# Remove AgentNexLiFy scheduled tasks
Write-Host "Removing AgentNexLiFy scheduled tasks..." -ForegroundColor Cyan

$tasks = @("AgentNexLiFy-Morning", "AgentNexLiFy-Evening")
foreach ($task in $tasks) {
    $existing = Get-ScheduledTask -TaskName $task -ErrorAction SilentlyContinue
    if ($existing) {
        Unregister-ScheduledTask -TaskName $task -Confirm:$false
        Write-Host "Removed: $task" -ForegroundColor Green
    } else {
        Write-Host "Not found: $task" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Done. To reinstall:" -ForegroundColor White
Write-Host "  powershell -ExecutionPolicy Bypass -File scripts\daily\setup-scheduler.ps1" -ForegroundColor White
