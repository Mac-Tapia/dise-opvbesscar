@echo off
REM Docker Quick Commands for PVBESSCAR - Windows Batch

setlocal enabledelayedexpansion

if "%~1"=="" (
    echo.
    echo PVBESSCAR Docker Commands
    echo ========================
    echo.
    echo Usage: docker_quick.bat [command] [options]
    echo.
    echo Commands:
    echo   build-cpu          Build CPU image
    echo   build-gpu          Build GPU image
    echo   build-dev          Build dev image
    echo   build-clean        Build without cache
    echo.
    echo   up-cpu             Start CPU services
    echo   up-gpu             Start GPU services
    echo   up-dev             Start dev services
    echo.
    echo   down               Stop all services
    echo   down-volumes       Stop and remove volumes
    echo.
    echo   logs               View all logs
    echo   logs-pipeline      View pipeline logs
    echo   logs-monitor       View monitor logs
    echo.
    echo   stats              Show resource usage
    echo   health             Check container health
    echo.
    echo   clean              Clean Docker cache
    echo   shell              Open container shell
    echo.
    goto :eof
)

if /i "%~1"=="build-cpu" (
    docker build --build-arg BUILDKIT_INLINE_CACHE=1 -t pvbesscar:latest .
    goto :eof
)

if /i "%~1"=="build-gpu" (
    docker build --build-arg BUILDKIT_INLINE_CACHE=1 -t pvbesscar:latest-gpu .
    goto :eof
)

if /i "%~1"=="build-dev" (
    docker build --build-arg BUILDKIT_INLINE_CACHE=1 -t pvbesscar:dev .
    goto :eof
)

if /i "%~1"=="build-clean" (
    docker build --no-cache -t pvbesscar:latest .
    goto :eof
)

if /i "%~1"=="up-cpu" (
    docker-compose -f docker-compose.yml up -d
    timeout /t 5
    docker ps
    goto :eof
)

if /i "%~1"=="up-gpu" (
    docker-compose -f docker-compose.gpu.yml up -d
    timeout /t 5
    docker ps
    goto :eof
)

if /i "%~1"=="up-dev" (
    docker-compose -f docker-compose.dev.yml up -d
    timeout /t 5
    docker ps
    goto :eof
)

if /i "%~1"=="down" (
    docker-compose down
    goto :eof
)

if /i "%~1"=="down-volumes" (
    docker-compose down -v
    goto :eof
)

if /i "%~1"=="logs" (
    docker-compose logs -f --tail=100
    goto :eof
)

if /i "%~1"=="logs-pipeline" (
    docker logs -f pvbesscar-pipeline --tail=100
    goto :eof
)

if /i "%~1"=="logs-monitor" (
    docker logs -f pvbesscar-monitor --tail=100
    goto :eof
)

if /i "%~1"=="stats" (
    docker stats
    goto :eof
)

if /i "%~1"=="health" (
    docker inspect --format="{{json .State.Health}}" pvbesscar-pipeline
    goto :eof
)

if /i "%~1"=="clean" (
    docker builder prune --all -f
    goto :eof
)

if /i "%~1"=="shell" (
    docker exec -it pvbesscar-pipeline bash
    goto :eof
)

echo Unknown command: %~1
goto :eof
