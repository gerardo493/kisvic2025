@echo off
echo ========================================
echo    SISTEMA DE NOTAS DE ENTREGA
echo ========================================
echo.
echo Iniciando servidor web...
echo.
echo La aplicacion estara disponible en:
echo http://127.0.0.1:5000
echo.
echo Para acceder a las notas de entrega:
echo http://127.0.0.1:5000/notas-entrega
echo.
echo Presiona CTRL+C para detener el servidor
echo.
echo ========================================
echo.

python app.py

echo.
echo Servidor detenido.
pause
