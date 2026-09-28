# ==============================================================================
# Hapus Auto-Start MikroTik AI Agent dari Windows Startup
# ==============================================================================
$StartupFolder = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Startup)
$ShortcutPath = Join-Path $StartupFolder "MikroTik-AI-Agent.lnk"

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host " Menghapus Auto-Start MikroTik AI Agent dari Windows Startup" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

if (Test-Path $ShortcutPath) {
    Remove-Item $ShortcutPath -Force
    Write-Host "[SUKSES] Auto-start berhasil dicopot!" -ForegroundColor Green
    Write-Host "Bot tidak akan berjalan otomatis lagi saat Windows dinyalakan." -ForegroundColor Yellow
} else {
    Write-Host "[INFO] Shortcut auto-start tidak ditemukan di folder Startup." -ForegroundColor Yellow
}
Write-Host ""
