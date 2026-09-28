# ==============================================================================
# Pasang Auto-Start MikroTik AI Agent ke Windows Startup (Tanpa Hak Administrator)
# ==============================================================================
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VbsPath = Join-Path $ScriptDir "start_background.vbs"
$StartupFolder = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Startup)
$ShortcutPath = Join-Path $StartupFolder "MikroTik-AI-Agent.lnk"

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host " Memasang Auto-Start MikroTik AI Agent ke Windows Startup" -ForegroundColor Cyan
Write-Host " Target VBS : $VbsPath" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "wscript.exe"
$Shortcut.Arguments = "`"$VbsPath`""
$Shortcut.WorkingDirectory = $ScriptDir
$Shortcut.Description = "Auto-start MikroTik AI Agent Telegram Bot"
$Shortcut.Save()

if (Test-Path $ShortcutPath) {
    Write-Host "[SUKSES] Auto-start berhasil dipasang!" -ForegroundColor Green
    Write-Host "Bot akan otomatis berjalan di background setiap kali Windows dinyalakan." -ForegroundColor Green
    Write-Host "Lokasi shortcut: $ShortcutPath" -ForegroundColor Gray
} else {
    Write-Host "[GAGAL] Gagal membuat shortcut auto-start." -ForegroundColor Red
}
Write-Host ""
