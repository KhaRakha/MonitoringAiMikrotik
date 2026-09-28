# ==============================================================================
# Windows Scheduled Task Installer for MikroTik AI Agent (PRD Section 18)
# Automatically registers the background service on boot/logon.
# ==============================================================================

$TaskName = "MikroTik-AI-Agent-Bot"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VbsPath = Join-Path $ScriptDir "start_background.vbs"

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host " Memasang Windows Scheduled Task: $TaskName" -ForegroundColor Cyan
Write-Host " Target VBS : $VbsPath" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan

# Check existing task
$ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($ExistingTask) {
    Write-Host "[INFO] Menghapus task lama..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Define Action: wscript.exe executing start_background.vbs
$Action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument "`"$VbsPath`"" -WorkingDirectory $ScriptDir

# Define Trigger: At logon of any user
$Trigger = New-ScheduledTaskTrigger -AtLogOn

# Define Settings: Restart on failure, do not stop on idle, run indefinitely
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Days 0)

# Register Task
Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Hermes AI Agent Telegram Bot untuk Otomatisasi MikroTik (Background Service)"

Write-Host "`n[SUKSES] Scheduled Task '$TaskName' berhasil didaftarkan!" -ForegroundColor Green
Write-Host "Bot akan otomatis berjalan di latar belakang setiap kali Windows menyala." -ForegroundColor Green
Write-Host "Untuk menjalankan task sekarang, jalankan: Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Green
