@echo off
REM Script para iniciar Docker daemon y ejecutar el pipeline
REM Requiere Docker Desktop instalado en Windows

echo.
echo ========================================
echo Iquitos CityLearn - Docker Pipeline
echo ========================================
echo.

REM Verificar si Docker Desktop está corriendo
echo [*] Verificando Docker Desktop...
docker --version >nul 2>&1
if errorlevel 1 (
    echo [*] Docker Desktop no está corriendo
    echo [!] Iniciando Docker Desktop...
    
    REM Intentar iniciar Docker Desktop
    if exist "C:\Program Files\Docker\Docker\Docker.exe" (
        start "" "C:\Program Files\Docker\Docker\Docker.exe"
        echo [*] Esperando a que Docker Desktop se inicie (30 segundos)...
        timeout /t 30 /nobreak
    ) else if exist "C:\Program Files (x86)\Docker\Docker\Docker.exe" (
        start "" "C:\Program Files (x86)\Docker\Docker\Docker.exe"
        echo [*] Esperando a que Docker Desktop se inicie (30 segundos)...
        timeout /t 30 /nobreak
    ) else (
        echo [ERROR] Docker Desktop no encontrado. Instalar desde https://www.docker.com/products/docker-desktop
        exit /b 1
    )
)

REM Esperar a que Docker daemon esté listo
echo [*] Esperando a que Docker daemon esté listo...
for /l %%i in (1,1,60) do (
    docker ps >nul 2>&1
    if errorlevel 0 goto docker_ready
    timeout /t 1 /nobreak >nul
)

echo [ERROR] Docker daemon no respondió
exit /b 1

:docker_ready
echo [OK] Docker está listo
echo.

REM Ejecutar el pipeline
cd /d %~dp0

REM Mostrar opciones
echo ¿Qué deseas ejecutar?
echo 1. Pipeline completo (OE2 + OE3)
echo 2. Solo OE3 (asume OE2 completado)
echo 3. Con GPU (OE2 + OE3, más rápido)
echo 4. Monitorear logs en vivo
echo 5. Salir
echo.

set /p choice="Selecciona una opción (1-5): "

if "%choice%"=="1" (
    echo [*] Ejecutando pipeline completo...
    powershell -ExecutionPolicy Bypass -Command ".\docker-run.ps1 -Action run"
) else if "%choice%"=="2" (
    echo [*] Ejecutando solo OE3...
    powershell -ExecutionPolicy Bypass -Command ".\docker-run.ps1 -Action run -SkipOE2"
) else if "%choice%"=="3" (
    echo [*] Ejecutando con GPU...
    powershell -ExecutionPolicy Bypass -Command ".\docker-run.ps1 -Action run -GPU"
) else if "%choice%"=="4" (
    echo [*] Mostrando logs en vivo...
    docker logs -f iquitos-pipeline
) else if "%choice%"=="5" (
    exit /b 0
) else (
    echo [ERROR] Opción inválida
    exit /b 1
)

pause
