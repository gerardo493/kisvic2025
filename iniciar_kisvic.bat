@echo off
cd /d "%~dp0"
title Kisvic - Inicio automatico
color 0A

echo.
echo  Kisvic: setup + Firebase + Flask + tunel Cloudflare
echo  Primera vez: crea .env.server si no existe
echo.

if not exist .env.server (
    echo [INFO] Ejecutando setup inicial...
    python kisvic.py setup
    echo.
)

python kisvic.py run
pause
