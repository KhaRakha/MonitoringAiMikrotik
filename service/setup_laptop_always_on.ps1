# ==============================================================================
# Konfigurasi Laptop Always-On Mode (Server Mini) - MikroTik AI Agent
# ==============================================================================
# Skrip ini mengonfigurasi laptop Windows agar:
# 1. Tidak sleep/mati saat layar laptop ditutup (khususnya saat dicolok charger)
# 2. Tidak otomatis sleep (Never sleep) saat terhubung ke listrik
# 3. Mendaftarkan bot ke Windows Task Scheduler agar auto-start saat komputer dinyalakan
# ==============================================================================

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host " MENGATUR LAPTOP AGAR TETAP RUNNING 24/7 (SERVER MODE)" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan

# 1. Konfigurasi Aksi Tutup Layar (Lid Close Action) saat dicolok charger -> Do Nothing (0)
# Subgroup: SUB_BUTTONS (4f971e89-eebd-4455-a8de-9e59040e7347)
# Setting : LIDACTION   (5ca83367-6e45-459f-a27b-476b1d01c936)
try {
    Write-Host "[1/3] Mengatur aksi saat layar laptop ditutup..." -ForegroundColor Yellow
    powercfg /setacvalueindex SCHEME_CURRENT 4f971e89-eebd-4455-a8de-9e59040e7347 5ca83367-6e45-459f-a27b-476b1d01c936 0
    Write-Host "      -> Berhasil: Saat dicolok charger, layar ditutup TIDAK akan membuat laptop tidur/sleep." -ForegroundColor Green
} catch {
    Write-Warning "Gagal mengatur LID Action via GUID: $_"
}

# 2. Nonaktifkan Sleep & Hibernate Timeout saat terhubung ke charger (0 = Never)
try {
    Write-Host "[2/3] Menonaktifkan batas waktu sleep (Never Sleep)..." -ForegroundColor Yellow
    powercfg /change standby-timeout-ac 0
    powercfg /change hibernate-timeout-ac 0
    powercfg /setactive SCHEME_CURRENT
    Write-Host "      -> Berhasil: Laptop tidak akan pernah sleep otomatis saat charger terpasang." -ForegroundColor Green
} catch {
    Write-Warning "Gagal mengatur timeout sleep: $_"
}

# 3. Pasang Auto-Start (Windows Startup & Scheduled Task)
Write-Host "[3/3] Memasang Auto-Start saat Windows dinyalakan..." -ForegroundColor Yellow
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$StartupScript = Join-Path $ScriptDir "install_startup.ps1"
$TaskScript = Join-Path $ScriptDir "install_windows_task.ps1"

if (Test-Path $StartupScript) {
    & powershell.exe -ExecutionPolicy Bypass -File "$StartupScript"
}

# Coba pasang scheduled task juga jika memiliki hak admin
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if ($isAdmin -and (Test-Path $TaskScript)) {
    & powershell.exe -ExecutionPolicy Bypass -File "$TaskScript"
}

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host " [SELESAI] Konfigurasi 24/7 Berhasil Diterapkan!" -ForegroundColor Green
Write-Host " Sekarang Anda bisa:" -ForegroundColor White
Write-Host " 1. Biarkan laptop dicolok charger." -ForegroundColor White
Write-Host " 2. Tutup layar laptop Anda (layar mati hemat listrik, bot tetap aktif)." -ForegroundColor White
Write-Host " 3. Bot Telegram MikroTik AI akan terus berjalan memantau jaringan!" -ForegroundColor White
Write-Host "================================================================" -ForegroundColor Cyan
