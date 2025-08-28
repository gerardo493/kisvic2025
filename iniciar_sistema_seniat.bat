@echo off
echo ================================================
echo   SISTEMA FISCAL HOMOLOGADO SENIAT v1.0
echo ================================================
echo.

echo [1/3] Activando entorno virtual...
call .\venv\Scripts\activate.bat

echo [2/3] Verificando dependencias SENIAT...
python -c "import psutil; import cryptography; from seguridad_fiscal import seguridad_fiscal; print('✅ Modulos SENIAT cargados correctamente')" 2>nul

if %errorlevel% neq 0 (
    echo.
    echo ❌ ERROR: Faltan dependencias SENIAT
    echo.
    echo Ejecuta primero: instalar_dependencias.bat
    echo.
    pause
    exit /b 1
)

echo [3/3] Iniciando sistema fiscal...
echo.
echo ================================================
echo   ✅ SISTEMA SENIAT ACTIVO
echo ================================================
echo.
echo Funcionalidades disponibles:
echo   • Facturas inmutables con hash SHA-256
echo   • Numeracion consecutiva automatica
echo   • Logs de auditoria completos
echo   • Validacion campos obligatorios
echo   • Exportacion CSV/XML/JSON
echo   • Interface de consulta SENIAT
echo.
echo Accede al sistema en: http://localhost:5000
echo Endpoints SENIAT: http://localhost:5000/seniat/sistema/estado
echo.
echo Presiona Ctrl+C para detener el servidor
echo.

python app.py 