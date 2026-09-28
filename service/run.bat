@echo off
rem ==============================================================================
rem MikroTik AI Agent Automation - Windows Launcher
rem ==============================================================================
title MikroTik AI Agent Automation

set "PROJECT_DIR=%~dp0.."
cd /d "%PROJECT_DIR%"

set "PYTHON_EXE=C:\Users\LENOVO\AppData\Local\Programs\Python\Python314\python.exe"
if not exist "%PYTHON_EXE%" (
    set "PYTHON_EXE=py"
)

echo [STARTUP] Menjalankan MikroTik AI Agent Supervisor...
"%PYTHON_EXE%" service\watchdog.py

if "%~1"=="" (
    pause
)
