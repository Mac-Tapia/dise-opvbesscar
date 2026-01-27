@echo off
cd /d D:\diseñopvbesscar

echo.
echo ============================================
echo  Reconstruyendo Entorno Virtual
echo ============================================
echo.

if exist .venv (
    echo Eliminando entorno anterior...
    rmdir /s /q .venv
)

echo Creando nuevo entorno...
python -m venv .venv --upgrade-deps

if errorlevel 1 (
    echo ERROR: No se pudo crear el entorno virtual
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Instalando Dependencias
echo ============================================
echo.

echo Instalando requirements base...
.venv\Scripts\pip install -q -r requirements.txt
if errorlevel 1 (
    echo ERROR: No se pudo instalar requirements.txt
    pause
    exit /b 1
)

echo Instalando requirements training...
.venv\Scripts\pip install -q -r requirements-training.txt
if errorlevel 1 (
    echo ERROR: No se pudo instalar requirements-training.txt
    pause
    exit /b 1
)

echo.
echo ✅ Entorno reconstruido exitosamente
echo.
echo ============================================
echo  Verificando Instalación
echo ============================================
echo.

.venv\Scripts\python --version
.venv\Scripts\pip list | findstr /C:"torch" /C:"numpy" /C:"pandas" /C:"stable-baselines3" /C:"citylearn"

echo.
echo ============================================
echo  Iniciando Entrenamiento A2C
echo ============================================
echo.

.venv\Scripts\python -m scripts.run_oe3_simulate --config configs/default.yaml

echo.
echo ✅ Entrenamiento completado
echo.
pause
