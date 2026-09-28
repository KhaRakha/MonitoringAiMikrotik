# ==============================================================================
# Hentikan Bot MikroTik AI Agent yang Berjalan di Background
# ==============================================================================
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host " Menghentikan MikroTik AI Agent Background Process" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

$pythonExe = "C:\Users\LENOVO\AppData\Local\Programs\Python\Python314\python.exe"
if (Test-Path $pythonExe) {
    & $pythonExe -c "import psutil, os, time; cur=os.getpid(); [p.kill() for p in psutil.process_iter(['pid','cmdline']) if p.info['pid']!=cur and 'watchdog.py' in ' '.join(p.info['cmdline'] or [])]; time.sleep(0.5); [p.kill() for p in psutil.process_iter(['pid','cmdline']) if p.info['pid']!=cur and any(x in ' '.join(p.info['cmdline'] or []) for x in ('run_bot.py', 'telegram_bot'))]"
}

$procs = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match "python" -and ($_.CommandLine -like "*watchdog.py*" -or $_.CommandLine -like "*run_bot.py*")
}

if ($procs) {
    foreach ($p in $procs) {
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
        Write-Host "[STOPPED] Proses Python PID $($p.ProcessId) berhasil dihentikan." -ForegroundColor Green
    }
} else {
    Write-Host "[INFO] Semua proses bot MikroTik AI telah dihentikan." -ForegroundColor Green
}
Write-Host ""
