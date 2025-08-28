@echo off
chcp 65001 >nul
echo 🚀 Script de Deploy Automático para Render
echo ===========================================
echo.

REM Verificar si Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Python no está instalado o no está en el PATH
    echo Por favor, instala Python y asegúrate de que esté en el PATH
    pause
    exit /b 1
)

REM Verificar si el archivo de configuración existe
if not exist "render_config.json" (
    echo ⚠️  Advertencia: render_config.json no encontrado
    echo Por favor, configura tu Service ID en render_config.json
    echo.
    echo Ejemplo de configuración:
    echo {
    echo     "service_id": "srv-xxxxxxxxxxxxxxxxx",
    echo     "service_name": "mi_app_web"
    echo }
    echo.
    pause
)

REM Verificar si hay argumentos
if "%1"=="" (
    echo 📝 Ejecutando deploy automático...
    echo Para opciones, ejecuta: deploy_render.bat --help
    echo.
    python deploy_render_automatico.py
) else (
    echo 📝 Ejecutando con argumentos: %*
    echo.
    python deploy_render_automatico.py %*
)

echo.
echo ✅ Script completado
pause
