@echo off
chcp 65001 >nul
echo ================================================================
echo                MIGRACIÓN DE CLIENTES A FORMATO SENIAT
echo ================================================================
echo.
echo Este script migra tus clientes existentes al formato SENIAT
echo para que cumplan con las validaciones requeridas por la
echo Providencia 00102.
echo.
echo ⚠️  IMPORTANTE:
echo   - Se creará un backup automático de tus clientes
echo   - Solo ejecutar UNA VEZ antes de usar el sistema SENIAT
echo   - Los clientes con problemas requerirán edición manual
echo.

pause

echo.
echo 🔄 Iniciando migración...
echo.

REM Activar entorno virtual
if exist "venv\Scripts\activate.bat" (
    echo 📦 Activando entorno virtual...
    call venv\Scripts\activate.bat
) else (
    echo ⚠️  Entorno virtual no encontrado, usando Python del sistema...
)

REM Ejecutar migración
echo.
echo 🚀 Ejecutando migración SENIAT...
echo.
python migrar_clientes_seniat.py

echo.
echo ================================================================
echo                    MIGRACIÓN COMPLETADA
echo ================================================================
echo.
echo 📋 Próximos pasos:
echo   1. Revisa los clientes marcados con problemas
echo   2. Edítalos desde: http://localhost:5000/clientes
echo   3. Completa los campos obligatorios faltantes
echo   4. Crea facturas sin errores de RIF
echo.
echo 🎯 Tu sistema ahora es compatible con SENIAT!
echo.

pause 