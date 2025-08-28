@echo off
echo ================================================
echo   SISTEMA FISCAL HOMOLOGADO SENIAT v1.0
echo ================================================
echo.

echo Cambiando al directorio correcto...
cd /d "%~dp0"

echo Activando entorno virtual...
call .\venv\Scripts\activate

echo Verificando dependencias SENIAT...
python -c "import psutil; import cryptography; print('✅ Dependencias OK')" 2>nul
if %errorlevel% neq 0 (
    echo ❌ Faltan dependencias. Ejecuta: instalar_dependencias.bat
    pause
    exit /b 1
)

echo Iniciando sistema fiscal...
echo.
echo ✅ Sistema disponible en: http://localhost:5000
echo ✅ SENIAT endpoints: /seniat/sistema/estado
echo.
python app.py
pause 