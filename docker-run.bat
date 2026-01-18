@echo off
REM docker-run.bat - Windows batch script for Iquitos CityLearn Docker

setlocal enabledelayedexpansion

set "ACTION=run"
set "GPU=false"
set "SKIP_OE2=false"
set "DETACH=false"
set "IMAGE_TAG=iquitos-citylearn:latest"
set "CONFIG=configs/default.yaml"

REM Parse arguments
:parse_args
if "%~1"=="" goto run_action
if "%~1"=="build" (
    set "ACTION=build"
) else if "%~1"=="run" (
    set "ACTION=run"
) else if "%~1"=="compose" (
    set "ACTION=compose"
) else if "%~1"=="logs" (
    set "ACTION=logs"
) else if "%~1"=="stop" (
    set "ACTION=stop"
) else if "%~1"=="clean" (
    set "ACTION=clean"
) else if "%~1"=="-gpu" (
    set "GPU=true"
) else if "%~1"=="-skipoe2" (
    set "SKIP_OE2=true"
) else if "%~1"=="-detach" (
    set "DETACH=true"
) else if "%~1"=="-config" (
    set "CONFIG=%~2"
    shift
)
shift
goto parse_args

:run_action
echo.
echo ==========================================
echo Iquitos CityLearn Docker Pipeline
echo ==========================================
echo Action: %ACTION%
echo GPU Support: %GPU%
echo Skip OE2: %SKIP_OE2%
echo.

REM Check Docker
docker --version > nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not installed or not in PATH
    exit /b 1
)

if "%ACTION%"=="build" (
    goto build_image
) else if "%ACTION%"=="run" (
    goto build_image
    goto run_pipeline
) else if "%ACTION%"=="compose" (
    goto run_compose
) else if "%ACTION%"=="logs" (
    goto show_logs
) else if "%ACTION%"=="stop" (
    goto stop_pipeline
) else if "%ACTION%"=="clean" (
    goto clean_resources
) else (
    goto usage
)

:build_image
echo [*] Building Docker image...
if "%GPU%"=="true" (
    docker build -t %IMAGE_TAG% --build-arg BUILDKIT_INLINE_CACHE=1 .
) else (
    docker build -t %IMAGE_TAG% --build-arg BUILDKIT_INLINE_CACHE=1 .
)
if errorlevel 1 (
    echo [ERROR] Build failed
    exit /b 1
)
echo [OK] Image built successfully
exit /b 0

:run_pipeline
echo [*] Running OE2-OE3 Pipeline...
set "run_args=-v %CD%\data:/app/data -v %CD%\outputs:/app/outputs -v %CD%\configs:/app/configs:ro"

if "%GPU%"=="true" (
    set "run_args=!run_args! --gpus all"
    echo [*] GPU support enabled
)

if "%DETACH%"=="true" (
    set "run_args=!run_args! -d"
    echo [*] Running in detached mode
) else (
    set "run_args=!run_args! -it"
)

if "%SKIP_OE2%"=="true" (
    docker run --rm !run_args! %IMAGE_TAG% python -m scripts.run_oe3_simulate --config %CONFIG%
    echo [*] Running OE3 only (OE2 skipped)
) else (
    docker run --rm !run_args! %IMAGE_TAG% python -m scripts.run_pipeline --config %CONFIG%
    echo [*] Running full OE2-OE3 pipeline
)
exit /b 0

:run_compose
echo [*] Starting Docker Compose stack...
if "%GPU%"=="true" (
    docker-compose -f docker-compose.gpu.yml up %if "%DETACH%"=="true" (-d) else ()%
) else (
    docker-compose up %if "%DETACH%"=="true" (-d) else ()%
)
exit /b 0

:show_logs
echo [*] Showing pipeline logs...
for /f "delims=" %%A in ('docker ps --filter "name=iquitos-pipeline" --format "{{.ID}}"') do (
    docker logs -f %%A
)
exit /b 0

:stop_pipeline
echo [*] Stopping pipeline...
docker-compose down
echo [OK] Pipeline stopped
exit /b 0

:clean_resources
echo [*] Cleaning Docker resources...
docker container prune -f
docker image prune -f
echo [OK] Cleanup completed
exit /b 0

:usage
echo Usage: %~nx0 [ACTION] [OPTIONS]
echo.
echo Actions:
echo   build      - Build Docker image only
echo   run        - Build and run pipeline (default)
echo   compose    - Use Docker Compose
echo   logs       - Show live logs
echo   stop       - Stop running pipeline
echo   clean      - Clean Docker resources
echo.
echo Options:
echo   -gpu       - Enable GPU support
echo   -skipoe2   - Skip OE2, run OE3 only
echo   -detach    - Run in background
echo   -config    - Config file path (default: configs/default.yaml)
echo.
echo Examples:
echo   %~nx0 run -gpu
echo   %~nx0 run -skipoe2 -detach
echo   %~nx0 compose -gpu
echo.
exit /b 0
