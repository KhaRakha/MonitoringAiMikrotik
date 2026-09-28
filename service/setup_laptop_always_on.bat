@echo off
rem ==============================================================================
rem MikroTik AI Agent - 1-Click Setup Laptop Always-On Mode
rem Jalankan file ini (Klik Kanan -> Run as Administrator)
rem ==============================================================================
title Setup Laptop Always-On 24/7 - MikroTik AI

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_laptop_always_on.ps1"

echo.
pause
