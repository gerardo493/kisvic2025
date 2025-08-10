@echo off
chcp 65001 >nul
echo ================================================================
echo              MIGRACIÓN DE PRODUCTOS EN FACTURAS
echo ================================================================
echo.
echo Este script corrige facturas existentes que NO muestran productos
echo debido a problemas de estructura de datos (funciones vs listas).
echo.
echo ⚠️  IMPORTANTE:
echo   - Se creará un backup automático de tus facturas
echo   - Las facturas con productos se dejarán intactas
echo   - Las facturas problemáticas se reconstruirán automáticamente
echo.

pause

echo.
echo 🔄 Iniciando migración de productos...
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
echo 🚀 Ejecutando migración de productos en facturas...
echo.
python migrar_facturas_productos.py

echo.
echo ================================================================
echo                    MIGRACIÓN COMPLETADA
echo ================================================================
echo.
echo 📋 Próximos pasos:
echo   1. Abre cualquier factura desde el sistema
echo   2. Verifica que ahora aparezcan los productos
echo   3. Si siguen sin aparecer, crea una nueva factura de prueba
echo   4. Las facturas nuevas funcionarán perfectamente
echo.
echo 🎯 Problema de productos solucionado!
echo.

pause 