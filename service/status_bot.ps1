# ==============================================================================
# Cek Status Bot MikroTik AI Agent (Running / Stopped)
# ==============================================================================
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host " Pengecekan Status MikroTik AI Agent" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

$procs = Get-CimInstance Win32_Process -Filter "name = 'python.exe'" | Where-Object {
    $_.CommandLine -like "*watchdog.py*" -or $_.CommandLine -like "*run_bot.py*"
}

if ($procs) {
    Write-Host "[STATUS: RUNNING] Bot aktif berjalan di background!" -ForegroundColor Green
    foreach ($p in $procs) {
        Write-Host "  - PID: $($p.ProcessId)" -ForegroundColor Cyan
    }
} else {
    Write-Host "[STATUS: STOPPED] Bot TIDAK sedang berjalan." -ForegroundColor Red
}
Write-Host ""
