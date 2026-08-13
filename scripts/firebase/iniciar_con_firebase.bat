@echo off
cd /d "%~dp0"
title Kisvic - Firebase + Flask (solo local)
color 0B

echo.
echo  Kisvic solo en esta PC (sin tunel publico)
echo.

if not exist .env.server (
    python kisvic.py setup
)

python kisvic.py run --solo-local
pause
