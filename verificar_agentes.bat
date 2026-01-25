@echo off
REM ===============================================
REM VERIFICAR AGENTES ANTES DE ENTRENAR
REM ===============================================
REM Autor: Proyecto Iquitos PV BESS EV
REM Fecha: 2026-01-24
REM ===============================================

echo.
echo ================================================================================
echo  VERIFICACION DE AGENTES - CONFIGURACIONES DE ENTRENAMIENTO
echo ================================================================================
echo.

REM Activar entorno virtual
if exist ".venv\Scripts\activate.bat" (
    echo [OK] Activando entorno virtual...
    call .venv\Scripts\activate.bat
) else (
    echo [ERROR] No se encontro entorno virtual en .venv
    pause
    exit /b 1
)

REM Ejecutar verificacion
echo.
echo [OK] Ejecutando verificacion...
python scripts\verificar_agentes.py

REM Pausar para ver resultado
echo.
pause
