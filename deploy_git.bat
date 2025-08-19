@echo off
chcp 65001 >nul
echo 🚀 Deploy Simple - Solo Git
echo ============================
echo.

REM Verificar si Git está instalado
git --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Git no está instalado o no está en el PATH
    echo Por favor, instala Git y asegúrate de que esté en el PATH
    pause
    exit /b 1
)

REM Verificar si estamos en un repositorio Git
git status >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: No estás en un repositorio Git
    echo Por favor, navega al directorio de tu proyecto Git
    pause
    exit /b 1
)

REM Verificar si hay repositorio remoto
git remote get-url origin >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: No hay repositorio remoto configurado
    echo Por favor, configura un repositorio remoto con: git remote add origin URL
    pause
    exit /b 1
)

echo ✅ Repositorio Git verificado correctamente
echo.

REM Verificar estado del repositorio
echo 🔍 Verificando estado del repositorio...
git status --porcelain > temp_status.txt
set /p status_content=<temp_status.txt
del temp_status.txt

if "%status_content%"=="" (
    echo ✅ No hay cambios pendientes
    echo 📝 El repositorio está actualizado
    echo.
    echo ¿Deseas hacer push de todos modos? (s/n)
    set /p choice=
    if /i "%choice%"=="s" (
        goto :push_changes
    ) else (
        echo Deploy cancelado
        pause
        exit /b 0
    )
) else (
    echo 📝 Cambios detectados:
    git status --short
    echo.
)

REM Preguntar por mensaje de commit
if "%1"=="" (
    echo 📝 Ingresa el mensaje del commit (o presiona Enter para mensaje automático):
    set /p commit_msg=
    if "%commit_msg%"=="" (
        for /f "tokens=1-3 delims=/ " %%a in ('date /t') do set today=%%a-%%b-%%c
        for /f "tokens=1-2 delims=: " %%a in ('time /t') do set now=%%a:%%b
        set commit_msg=Actualización automática - %today% %now%
    )
) else (
    set commit_msg=%1
)

echo.
echo 📝 Mensaje del commit: %commit_msg%
echo.

REM Hacer commit
echo 🔄 Realizando commit...
git add .
if errorlevel 1 (
    echo ❌ Error agregando archivos al staging
    pause
    exit /b 1
)

git commit -m "%commit_msg%"
if errorlevel 1 (
    echo ❌ Error realizando commit
    pause
    exit /b 1
)

echo ✅ Commit realizado exitosamente
echo.

:push_changes
REM Hacer push
echo 🚀 Enviando cambios al repositorio remoto...
git push origin main
if errorlevel 1 (
    echo ❌ Error enviando cambios
    echo Intentando con la rama actual...
    for /f "tokens=*" %%i in ('git branch --show-current') do set current_branch=%%i
    git push origin %current_branch%
    if errorlevel 1 (
        echo ❌ Error enviando cambios a la rama %current_branch%
        pause
        exit /b 1
    )
)

echo ✅ Cambios enviados exitosamente
echo.

REM Mostrar información del deploy
echo 📊 Información del Deploy:
echo ==========================
echo 📝 Último commit:
git log -1 --oneline
echo.
echo 🔗 Repositorio remoto:
git remote get-url origin
echo.
echo 🌿 Rama actual:
git branch --show-current
echo ==========================
echo.

echo 🎉 ¡Deploy completado exitosamente!
echo 📝 Render detectará los cambios automáticamente
echo ⏱️  El despliegue puede tomar 2-5 minutos
echo.
echo 🌐 Puedes verificar el estado en:
echo    https://dashboard.render.com/web/srv-d2ckh46r433s73appvug
echo.

pause
