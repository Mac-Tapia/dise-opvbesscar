@echo off
REM Ejecuta los agentes SAC, PPO y A2C en serie usando configs/default.yaml
setlocal
set PYTHONPATH=src

echo [1/3] Entrenando SAC (10 episodios)...
.\.venv\Scripts\python.exe -m scripts.run_oe3_simulate --config configs/default.yaml --agent SAC
if errorlevel 1 goto :error

echo [2/3] Entrenando PPO (10 episodios)...
.\.venv\Scripts\python.exe -m scripts.run_oe3_simulate --config configs/default.yaml --agent PPO
if errorlevel 1 goto :error

echo [3/3] Entrenando A2C (10 episodios)...
.\.venv\Scripts\python.exe -m scripts.run_oe3_simulate --config configs/default.yaml --agent A2C
if errorlevel 1 goto :error

echo.
echo [OK] Entrenamientos completados.
goto :eof

:error
echo.
echo [ERROR] Alguna corrida fallo. Revisa la consola para detalles.
exit /b 1
