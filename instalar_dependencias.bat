@echo off
echo ================================================
echo   INSTALACION DE DEPENDENCIAS SENIAT
echo ================================================
echo.

echo [1/4] Activando entorno virtual...
call .\venv\Scripts\activate.bat

echo [2/4] Actualizando pip...
python -m pip install --upgrade pip

echo [3/4] Instalando dependencias SENIAT...
pip install -r requirements.txt

echo [4/4] Verificando instalacion...
python -c "import psutil; import cryptography; import requests; print('✅ Todas las dependencias SENIAT instaladas correctamente')" 2>nul

if %errorlevel% equ 0 (
    echo.
    echo ================================================
    echo   ✅ INSTALACION COMPLETADA EXITOSAMENTE
    echo ================================================
    echo.
    echo Ahora puedes ejecutar el sistema:
    echo   python app.py
    echo.
) else (
    echo.
    echo ================================================
    echo   ❌ ERROR EN LA INSTALACION
    echo ================================================
    echo.
    echo Intenta instalar manualmente:
    echo   1. .\venv\Scripts\activate
    echo   2. pip install -r requirements.txt
    echo.
)

pause 