@echo off
REM Monitor SAC Training - Estado sin interrupciones (Batch)
REM Uso: sat_check_status.bat

setlocal enabledelayedexpansion

echo.
echo ========================================
echo     SAC TRAINING - VERIFICACION RAPIDA
echo ========================================
echo.

REM Verificar checkpoints
echo [1] Checkpoints disponibles:
for /f %%A in ('dir /b analyses\oe3\training\checkpoints\sac\*.zip 2^>nul ^| find /c /v ""') do (
    echo     Total: %%A archivos
)

REM Mostrar ultimos 3 checkpoints
echo     Ultimos 3:
for /f "tokens=1" %%A in ('dir /b /o-d analyses\oe3\training\checkpoints\sac\sac_step_*.zip 2^>nul ^| findstr /v /b "" ^| (for /l %%N in (1 1 3) do pause ^| find /v "^C" ^| findstr /v "^$"^)') do (
    echo       - %%A
)

echo.
echo [2] Baseline data:
if exist analyses\oe3\simulations\uncontrolled_pv_bess.json (
    echo     ✓ Baseline file found
) else (
    echo     ✗ Baseline file NOT found
)

echo.
echo [3] Espacio disponible:
dir analyses\oe3\training\checkpoints\sac\ 2^>nul | find "archivo" 

echo.
echo ========================================
echo Entrenamiento SAC esta en progreso.
echo Usa: .\monitor_sac_vivo.ps1 para ver detalles en vivo
echo ========================================
echo.

pause
