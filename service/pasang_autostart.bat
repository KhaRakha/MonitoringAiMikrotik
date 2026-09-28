@echo off
rem ==============================================================================
rem Pasang Auto-Start MikroTik AI Agent ke Windows Startup (Klik Ganda)
rem ==============================================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_startup.ps1"
pause
