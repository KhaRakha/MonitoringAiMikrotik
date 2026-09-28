@echo off
rem ==============================================================================
rem Hentikan Bot MikroTik AI Agent yang Berjalan di Background (Klik Ganda)
rem ==============================================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop_bot.ps1"
pause
