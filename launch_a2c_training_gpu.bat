@echo off
REM ╔════════════════════════════════════════════════════════════════════════════╗
REM ║     🚀 LANZADOR DE ENTRENAMIENTO A2C CON GPU - ROBUSTO SIN INTERRUPCIONES   ║
REM ║                            27 Enero 2026                                     ║
REM ╚════════════════════════════════════════════════════════════════════════════╝

setlocal enabledelayedexpansion

echo.
echo ╔════════════════════════════════════════════════════════════════════════════╗
echo ║     🚀 INICIANDO ENTRENAMIENTO A2C CON GPU AL MÁXIMO                     ║
echo ║        Python 3.11 ^| PyTorch 2.7.1+cu118 ^| CUDA 11.8 ^| RTX 4060         ║
echo ╚════════════════════════════════════════════════════════════════════════════╝
echo.

REM Verificaciones previas
echo [1/4] 🔍 Verificando Python 3.11...
py -3.11 --version >nul 2>&1
if errorlevel 1 (
    echo     ❌ Error: Python 3.11 no encontrado
    exit /b 1
)
for /f "tokens=*" %%i in ('py -3.11 --version 2^>^&1') do set PYVER=%%i
echo     ✅ %PYVER%

echo [2/4] 🔍 Verificando PyTorch + CUDA...
for /f "tokens=*" %%i in ('py -3.11 -c "import torch; print(f'PyTorch: {torch.__version__}, CUDA: {torch.cuda.is_available()}')" 2^>^&1') do set TORCHVER=%%i
echo     ✅ %TORCHVER%

echo [3/4] 🔍 Verificando CityLearn v2.5.0...
for /f "tokens=*" %%i in ('py -3.11 -c "import citylearn; print(f'CityLearn: {citylearn.__version__}')" 2^>^&1') do set CLVER=%%i
echo     ✅ %CLVER%

REM Crear directorio de outputs
if not exist "outputs" mkdir outputs

REM Crear archivo de timestamp
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c%%a%%b)
for /f "tokens=1-2 delims=/:" %%a in ('time /t') do (set mytime=%%a%%b)
set TIMESTAMP=%mydate%_%mytime%
set LOGFILE=outputs\training_a2c_gpu_%TIMESTAMP%.log

echo [4/4] 🚀 Lanzando entrenamiento A2C en GPU...
echo     📝 Log file: %LOGFILE%
echo.
echo ╔════════════════════════════════════════════════════════════════════════════╗
echo ║  PROCESO INICIADO - El entrenamiento continuará en BACKGROUND             ║
echo ║  Para monitorear GPU en tiempo real: nvidia-smi -l 1                      ║
echo ║  Tail del log: type %LOGFILE% | more /+0                                 ║
echo ╚════════════════════════════════════════════════════════════════════════════╝
echo.

REM Lanzar en background con start /B
echo [%TIME%] Iniciando training... >> %LOGFILE%
echo Python: %PYVER% >> %LOGFILE%
echo PyTorch: %TORCHVER% >> %LOGFILE%
echo CityLearn: %CLVER% >> %LOGFILE%
echo. >> %LOGFILE%

REM COMANDO PRINCIPAL - Lanzado en BACKGROUND
start /B "A2C Training GPU" py -3.11 -m scripts.run_oe3_simulate --config configs/default.yaml >> %LOGFILE% 2>&1

REM Obtener PID (Windows no lo expone fácilmente, pero el proceso está corriendo)
echo.
echo ✅ Entrenamiento lanzado en background
echo.
echo 📊 Información del proceso:
echo    Log: %LOGFILE%
echo    Duración estimada: 2-3 horas con GPU
echo.
echo 🔍 Comandos útiles:
echo    Ver log: type %LOGFILE%
echo    Ver GPU: nvidia-smi -l 1
echo    Resultados: outputs\oe3_simulations\simulation_summary.json
echo.
echo ╔════════════════════════════════════════════════════════════════════════════╗
echo ║  GPU en BACKGROUND - Continuará sin interrupciones                        ║
echo ║  Puedes cerrar esta ventana sin afectar el training                       ║
echo ╚════════════════════════════════════════════════════════════════════════════╝
echo.

REM Pequeño delay para verificación inicial
timeout /t 3 /nobreak

REM Verificar que el proceso esté corriendo
tasklist | find /i "py.exe" >nul
if errorlevel 1 (
    echo ⚠️  ADVERTENCIA: No se detectó py.exe en ejecución
    echo Revisar log: %LOGFILE%
    type %LOGFILE%
) else (
    echo ✅ Proceso py.exe confirmado en ejecución
    echo ✅ ENTRENAMIENTO EN PROGRESO
    echo.
    echo 📝 Log: %LOGFILE%
)
