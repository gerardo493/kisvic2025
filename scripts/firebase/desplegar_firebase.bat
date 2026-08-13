@echo off
cd /d "%~dp0"
title Kisvic - Desplegar a Firebase (como Excursiones ZJ)

echo ================================================
echo   DESPLIEGUE FIREBASE - Igual que tus otros proyectos
echo   npm run build  +  firebase deploy
echo ================================================
echo.

where firebase >nul 2>nul
if %errorlevel% neq 0 (
    echo [X] Instala: npm install -g firebase-tools
    echo     Luego: firebase login
    pause
    exit /b 1
)

where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo [X] Instala Node.js desde https://nodejs.org/
    pause
    exit /b 1
)

if not exist .env.production (
    echo [AVISO] Falta .env.production con las claves Web de Firebase.
    echo.
    echo 1. Abre: https://console.firebase.google.com/project/kisvic-facturacion/settings/general
    echo 2. Tus apps - Agregar app - Web
    echo 3. Copia .env.production.example a .env.production y pega apiKey, appId, etc.
    echo.
    if exist .env.production.example copy /Y .env.production.example .env.production
    echo Se creo .env.production vacio. Completalo y vuelve a ejecutar este archivo.
    pause
    exit /b 1
)

echo [1/3] Instalando dependencias npm...
call npm install
if %errorlevel% neq 0 pause & exit /b 1

echo.
echo [2/3] Compilando frontend (carpeta dist/)...
call npm run build
if %errorlevel% neq 0 (
    echo [X] Error en npm run build
    pause
    exit /b 1
)

echo.
echo [3/3] Subiendo a Firebase Hosting + reglas Firestore...
call npm run deploy:all
if %errorlevel% neq 0 (
    echo [X] Error en firebase deploy
    pause
    exit /b 1
)

echo.
echo ================================================
echo   LISTO - Kisvic en Firebase
echo ================================================
echo   Web:     https://kisvic-facturacion.web.app
echo   Datos:   Firestore - coleccion kisvic_datos
echo   Flask:   iniciar_con_firebase.bat (facturacion completa en PC)
echo ================================================
pause
