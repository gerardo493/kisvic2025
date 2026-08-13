@echo off
cd /d "%~dp0"
title Kisvic - Backup Diario

echo ================================================
echo   KISVIC - BACKUP DIARIO
echo ================================================
echo.

python kisvic.py backup
if %errorlevel% neq 0 (
    echo.
    echo [X] El backup diario fallo.
    pause
    exit /b 1
)

echo.
echo [OK] Backup diario completado.
pause

