@echo off
rem ==============================================================================
rem Hapus Auto-Start MikroTik AI Agent dari Windows Startup (Klik Ganda)
rem ==============================================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0uninstall_startup.ps1"
pause
