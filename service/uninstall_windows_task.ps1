# ==============================================================================
# Windows Scheduled Task Uninstaller for MikroTik AI Agent
# ==============================================================================

$TaskName = "MikroTik-AI-Agent-Bot"

$ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($ExistingTask) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "[SUKSES] Scheduled Task '$TaskName' berhasil dihapus." -ForegroundColor Green
} else {
    Write-Host "[INFO] Task '$TaskName' tidak ditemukan." -ForegroundColor Yellow
}
