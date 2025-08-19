@echo off
chcp 65001 >nul
echo 🚀 Script de Deploy Simple - Solo Git
echo ======================================
echo.

REM Verificar si Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Python no está instalado o no está en el PATH
    echo Por favor, instala Python y asegúrate de que esté en el PATH
    pause
    exit /b 1
)

REM Verificar si Git está configurado
git --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Git no está instalado o no está en el PATH
    echo Por favor, instala Git y asegúrate de que esté en el PATH
    pause
    exit /b 1
)

REM Verificar si hay argumentos
if "%1"=="" (
    echo 📝 Ejecutando deploy automático...
    echo Para opciones, ejecuta: deploy_simple.bat --help
    echo.
    python deploy_simple.py
) else (
    echo 📝 Ejecutando con argumentos: %*
    echo.
    python deploy_simple.py %*
)

echo.
echo ✅ Script completado
echo 📝 Render detectará los cambios automáticamente
echo ⏱️  El despliegue puede tomar 2-5 minutos
pause
