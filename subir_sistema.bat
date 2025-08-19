@echo off
chcp 65001 >nul
title 🚀 Subir Sistema - KISVIC 2025

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                    🚀 SUBIR SISTEMA COMPLETO                 ║
echo ║                     Sistema de Recordatorios                 ║
echo ║                           KISVIC 2025                       ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

REM Verificar si Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Python no está instalado o no está en el PATH
    echo.
    echo 💡 Soluciones:
    echo    1. Instala Python desde: https://python.org
    echo    2. Asegúrate de que Python esté en el PATH del sistema
    echo    3. Reinicia la consola después de instalar Python
    echo.
    pause
    exit /b 1
)

echo ✅ Python detectado correctamente
echo.

REM Verificar si el script existe
if not exist "subir_sistema.py" (
    echo ❌ Error: subir_sistema.py no encontrado
    echo.
    echo 💡 Asegúrate de que estés en el directorio correcto del proyecto
    echo.
    pause
    exit /b 1
)

echo ✅ Script subir_sistema.py encontrado
echo.

REM Verificar si Git está configurado
git --version >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Advertencia: Git no está instalado o no está en el PATH
    echo    El script puede no funcionar correctamente
    echo.
) else (
    echo ✅ Git detectado correctamente
)

echo.
echo 🚀 Iniciando Sistema de Deploy...
echo ═══════════════════════════════════════════════════════════════
echo.

REM Ejecutar el script de Python
python subir_sistema.py

echo.
echo ═══════════════════════════════════════════════════════════════
echo ✅ Script completado
echo.
echo 💡 Recuerda verificar tu aplicación en:
echo    https://kisvic2025.onrender.com
echo.
pause
