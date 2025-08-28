@echo off
chcp 65001 >nul

REM Activar entorno virtual y ejecutar script
call venv\Scripts\activate.bat

if "%1"=="" (
    python deploy_auto.py
) else (
    python deploy_auto.py %*
)
