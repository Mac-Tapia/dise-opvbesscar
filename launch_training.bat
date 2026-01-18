@echo off
REM Lanzador de entrenamiento serial para Command Prompt
REM Uso: launch_training.bat

setlocal enabledelayedexpansion

echo.
echo ====================================================================
echo LANZADOR DE ENTRENAMIENTO SERIAL
echo ====================================================================
echo.

REM Check virtual environment
if not defined VIRTUAL_ENV (
    echo.
    echo ^ Activando virtual environment...
    call .venv\Scripts\activate.bat
)

echo.
echo  Python: 
python --version

echo.
echo  CUDA: 
python -c "import torch; print(f'CUDA Available: {torch.cuda.is_available()}')" 2>nul || echo CUDA check failed

echo.
echo ====================================================================
echo INICIANDO ENTRENAMIENTO SERIAL
echo ====================================================================
echo.
echo  Tiempo estimado: 4-7 horas
echo  Mantener ventana abierta durante entrenamiento
echo.
echo ====================================================================
echo.

python train_agents_serial_auto.py

echo.
echo ====================================================================
if errorlevel 1 (
    echo  ENTRENAMIENTO CON ERRORES
) else (
    echo  ENTRENAMIENTO COMPLETADO EXITOSAMENTE
)
echo ====================================================================
echo.
echo Resultados:
echo   - outputs\oe3\simulations\simulation_summary.json
echo   - outputs\oe3\simulations\co2_comparison.md
echo.
pause
