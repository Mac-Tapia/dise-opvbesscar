@echo off
REM ============================================================================
REM MOSTRAR DATOS REALES QUE CARGA dataset_builder
REM ============================================================================

cd /d "d:\diseñopvbesscar"

echo.
echo ============================================================================
echo 📊 MOSTRAR DATOS REALES QUE CARGA dataset_builder
echo ============================================================================
echo.

.venv\Scripts\python.exe mostrar_datos_reales.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ MOSTRADA INFORMACIÓN DE DATOS REALES
    echo.
) else (
    echo.
    echo ❌ ERROR
    echo.
)

pause
