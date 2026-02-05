@echo off
REM Instalación de dependencias de CityLearn v2.5.0
REM Ajustar versiones y dependencias

echo.
echo ================================================================================
echo  AJUSTE DE DEPENDENCIAS DE CITYLEARN v2.5.0
echo ================================================================================
echo.

REM Downgrade de gymnasium a versión compatible
echo [1/4] Ajustando gymnasium a versión 0.28.1 (requerida por CityLearn)...
pip install gymnasium==0.28.1 --force-reinstall --no-deps
echo.

REM Instalar dependencias de CityLearn
echo [2/4] Instalando doe-xstock...
pip install doe-xstock>=1.1.0
echo.

echo [3/4] Instalando nrel-pysam...
pip install nrel-pysam
echo.

echo [4/4] Instalando openstudio...
pip install openstudio<=3.3.0
echo.

echo ================================================================================
echo  VERIFICACIÓN DE CITYLEARN
echo ================================================================================
echo.

echo Verificando instalación de CityLearn...
python -c "import citylearn; print('✓ CityLearn version:', citylearn.__version__)"
echo.

echo Verificando PyTorch...
python -c "import torch; print('✓ PyTorch version:', torch.__version__)"
echo.

echo Verificando Stable Baselines 3...
python -c "import stable_baselines3; print('✓ Stable Baselines 3 version:', stable_baselines3.__version__)"
echo.

echo Verificando Gymnasium...
python -c "import gymnasium; print('✓ Gymnasium version:', gymnasium.__version__)"
echo.

echo ================================================================================
echo  CONFIGURACIÓN COMPLETADA
echo ================================================================================
echo.

pause
