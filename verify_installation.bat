@echo off
REM Script de verificación de instalación
REM Verifica que todos los paquetes críticos estén correctamente instalados

echo.
echo ================================================================================
echo  VERIFICACIÓN DE INSTALACIÓN - PYTHON 3.11
echo  diseñopvbesscar Project
echo ================================================================================
echo.

setlocal enabledelayedexpansion

set "failed=0"

REM Función para verificar cada paquete
:check_package
set "package=%1"
set "name=%2"

python -c "import %package%" 2>nul
if %errorlevel% equ 0 (
    echo ✓ %name% - INSTALADO
) else (
    echo ✗ %name% - NO ENCONTRADO
    set /a failed=!failed!+1
)
exit /b

echo.
echo VERIFICANDO DEPENDENCIAS CORE...
echo ================================================================================
echo.

python -c "import numpy; print('✓ NumPy version:', numpy.__version__)" 2>nul || echo ✗ NumPy no encontrado && set /a failed=%failed%+1
python -c "import pandas; print('✓ Pandas version:', pandas.__version__)" 2>nul || echo ✗ Pandas no encontrado && set /a failed=%failed%+1
python -c "import scipy; print('✓ SciPy version:', scipy.__version__)" 2>nul || echo ✗ SciPy no encontrado && set /a failed=%failed%+1

echo.
echo VERIFICANDO REINFORCEMENT LEARNING...
echo ================================================================================
echo.

python -c "import gymnasium; print('✓ Gymnasium version:', gymnasium.__version__)" 2>nul || echo ✗ Gymnasium no encontrado && set /a failed=%failed%+1

echo.
echo VERIFICANDO DEEP LEARNING...
echo ================================================================================
echo.

python -c "import torch; print('✓ PyTorch version:', torch.__version__); print('✓ CUDA disponible:', torch.cuda.is_available())" 2>nul || echo ✗ PyTorch no encontrado && set /a failed=%failed%+1

echo.
echo VERIFICANDO STABLE BASELINES 3...
echo ================================================================================
echo.

python -c "import stable_baselines3; print('✓ Stable Baselines 3 version:', stable_baselines3.__version__)" 2>nul || echo ✗ Stable Baselines 3 no encontrado && set /a failed=%failed%+1

echo.
echo VERIFICANDO UTILITIES...
echo ================================================================================
echo.

python -c "import yaml; print('✓ PyYAML instalado')" 2>nul || echo ✗ PyYAML no encontrado && set /a failed=%failed%+1
python -c "import pydantic; print('✓ Pydantic version:', pydantic.__version__)" 2>nul || echo ✗ Pydantic no encontrado && set /a failed=%failed%+1
python -c "import dotenv; print('✓ python-dotenv instalado')" 2>nul || echo ✗ python-dotenv no encontrado && set /a failed=%failed%+1

echo.
echo VERIFICANDO VISUALIZATION...
echo ================================================================================
echo.

python -c "import matplotlib; print('✓ Matplotlib version:', matplotlib.__version__)" 2>nul || echo ✗ Matplotlib no encontrado && set /a failed=%failed%+1
python -c "import seaborn; print('✓ Seaborn instalado')" 2>nul || echo ✗ Seaborn no encontrado && set /a failed=%failed%+1
python -c "import PIL; print('✓ Pillow instalado')" 2>nul || echo ✗ Pillow no encontrado && set /a failed=%failed%+1

echo.
echo VERIFICANDO SOLAR & ENERGY...
echo ================================================================================
echo.

python -c "import pvlib; print('✓ pvlib version:', pvlib.__version__)" 2>nul || echo ✗ pvlib no encontrado && set /a failed=%failed%+1

echo.
echo VERIFICANDO TESTING...
echo ================================================================================
echo.

python -c "import pytest; print('✓ pytest version:', pytest.__version__)" 2>nul || echo ✗ pytest no encontrado && set /a failed=%failed%+1

echo.
echo ================================================================================
echo  RESUMEN DE VERIFICACIÓN
echo ================================================================================
echo.

pip list > installed_packages.txt

if %failed% equ 0 (
    echo ✅ TODAS LAS DEPENDENCIAS INSTALADAS CORRECTAMENTE
    echo.
    echo El entorno está listo para:
    echo  - Entrenamiento de agentes RL (SAC, PPO, A2C)
    echo  - Simulación de CityLearn v2.5.0
    echo  - Análisis de datos con pandas/numpy
    echo  - Visualización con matplotlib
    echo.
) else (
    echo ⚠️  ADVERTENCIA: %failed% paquetes no encontrados
    echo Por favor revisa el log anterior
    echo.
)

echo Packages instalados guardados en: installed_packages.txt
echo.

pause
