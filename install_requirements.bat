@echo off
REM Script de instalación individual de requisitos
REM Python 3.11 - Iquitos PV-BESS-CAR Project

setlocal enabledelayedexpansion

echo.
echo ================================================================================
echo  INSTALACIÓN DE REQUISITOS - PYTHON 3.11
echo  Proyecto: diseñopvbesscar
echo ================================================================================
echo.

python --version

set "logfile=installation_log.txt"
echo Iniciando instalación en %date% %time% > %logfile%

echo.
echo ================================================================================
echo  CORE DATA PROCESSING
echo ================================================================================
echo.

echo [1/3] Instalando numpy...
pip install numpy==1.26.4
if %errorlevel% equ 0 (echo ✓ numpy instalado) else (echo ✗ Error en numpy) >> %logfile%
echo.

echo [2/3] Instalando pandas...
pip install pandas==2.3.3
if %errorlevel% equ 0 (echo ✓ pandas instalado) else (echo ✗ Error en pandas) >> %logfile%
echo.

echo [3/3] Instalando scipy...
pip install scipy==1.17.0
if %errorlevel% equ 0 (echo ✓ scipy instalado) else (echo ✗ Error en scipy) >> %logfile%
echo.

echo ================================================================================
echo  REINFORCEMENT LEARNING
echo ================================================================================
echo.

echo [1/2] Instalando gymnasium...
pip install gymnasium==0.29.1
if %errorlevel% equ 0 (echo ✓ gymnasium instalado) else (echo ✗ Error en gymnasium) >> %logfile%
echo.

echo [2/2] Instalando Farama-Notifications...
pip install Farama-Notifications==0.0.4
if %errorlevel% equ 0 (echo ✓ Farama-Notifications instalado) else (echo ✗ Error en Farama-Notifications) >> %logfile%
echo.

echo ================================================================================
echo  DEEP LEARNING - PYTORCH
echo ================================================================================
echo.

echo [1/2] Instalando torch (ESTO TARDA VARIOS MINUTOS)...
pip install torch==2.10.0
if %errorlevel% equ 0 (echo ✓ torch instalado) else (echo ✗ Error en torch) >> %logfile%
echo.

echo [2/2] Instalando torchvision...
pip install torchvision==0.15.2
if %errorlevel% equ 0 (echo ✓ torchvision instalado) else (echo ✗ Error en torchvision) >> %logfile%
echo.

echo ================================================================================
echo  STABLE BASELINES 3 (FRAMEWORK DE RL)
echo ================================================================================
echo.

echo Instalando stable_baselines3...
pip install stable_baselines3==2.7.1
if %errorlevel% equ 0 (echo ✓ stable_baselines3 instalado) else (echo ✗ Error en stable_baselines3) >> %logfile%
echo.

echo ================================================================================
echo  CONFIGURATION & UTILITIES
echo ================================================================================
echo.

echo [1/4] Instalando PyYAML...
pip install PyYAML==6.0.3
if %errorlevel% equ 0 (echo ✓ PyYAML instalado) else (echo ✗ Error en PyYAML) >> %logfile%
echo.

echo [2/4] Instalando python_dotenv...
pip install python_dotenv==1.2.1
if %errorlevel% equ 0 (echo ✓ python_dotenv instalado) else (echo ✗ Error en python_dotenv) >> %logfile%
echo.

echo [3/4] Instalando pydantic...
pip install pydantic==2.12.5
if %errorlevel% equ 0 (echo ✓ pydantic instalado) else (echo ✗ Error en pydantic) >> %logfile%
echo.

echo [4/4] Instalando pydantic_core...
pip install pydantic_core==2.41.5
if %errorlevel% equ 0 (echo ✓ pydantic_core instalado) else (echo ✗ Error en pydantic_core) >> %logfile%
echo.

echo ================================================================================
echo  VISUALIZATION & ANALYSIS
echo ================================================================================
echo.

echo [1/7] Instalando matplotlib...
pip install matplotlib==3.10.8
if %errorlevel% equ 0 (echo ✓ matplotlib instalado) else (echo ✗ Error en matplotlib) >> %logfile%
echo.

echo [2/7] Instalando seaborn...
pip install seaborn==0.13.2
if %errorlevel% equ 0 (echo ✓ seaborn instalado) else (echo ✗ Error en seaborn) >> %logfile%
echo.

echo [3/7] Instalando pillow...
pip install pillow==12.1.0
if %errorlevel% equ 0 (echo ✓ pillow instalado) else (echo ✗ Error en pillow) >> %logfile%
echo.

echo [4/7] Instalando contourpy...
pip install contourpy==1.3.3
if %errorlevel% equ 0 (echo ✓ contourpy instalado) else (echo ✗ Error en contourpy) >> %logfile%
echo.

echo [5/7] Instalando cycler...
pip install cycler==0.12.1
if %errorlevel% equ 0 (echo ✓ cycler instalado) else (echo ✗ Error en cycler) >> %logfile%
echo.

echo [6/7] Instalando fonttools...
pip install fonttools==4.61.1
if %errorlevel% equ 0 (echo ✓ fonttools instalado) else (echo ✗ Error en fonttools) >> %logfile%
echo.

echo [7/7] Instalando kiwisolver...
pip install kiwisolver==1.4.9
if %errorlevel% equ 0 (echo ✓ kiwisolver instalado) else (echo ✗ Error en kiwisolver) >> %logfile%
echo.

echo ================================================================================
echo  TESTING & LINTING
echo ================================================================================
echo.

echo [1/2] Instalando pytest...
pip install pytest==8.3.4
if %errorlevel% equ 0 (echo ✓ pytest instalado) else (echo ✗ Error en pytest) >> %logfile%
echo.

echo [2/2] Instalando black...
pip install black==24.10.0
if %errorlevel% equ 0 (echo ✓ black instalado) else (echo ✗ Error en black) >> %logfile%
echo.

echo ================================================================================
echo  SOLAR & CITYLEARN
echo ================================================================================
echo.

echo [1/2] Instalando pvlib...
pip install pvlib==0.10.4
if %errorlevel% equ 0 (echo ✓ pvlib instalado) else (echo ✗ Error en pvlib) >> %logfile%
echo.

echo [2/2] Instalando requests...
pip install requests==2.32.3
if %errorlevel% equ 0 (echo ✓ requests instalado) else (echo ✗ Error en requests) >> %logfile%
echo.

echo ================================================================================
echo  VERIFICACIÓN FINAL
echo ================================================================================
echo.

echo Listando todos los paquetes instalados...
pip list
echo.

echo ================================================================================
echo  INSTALACIÓN COMPLETADA
echo ================================================================================
echo.

echo Próximos pasos:
echo 1. Verificar que todos los paquetes se instalaron
echo 2. Ejecutar: python -c "import torch; print(torch.__version__)"
echo 3. Ejecutar: python -c "import stable_baselines3; print(stable_baselines3.__version__)"
echo 4. Ejecutar: python run_solar_generation_hourly.py
echo.

pause
