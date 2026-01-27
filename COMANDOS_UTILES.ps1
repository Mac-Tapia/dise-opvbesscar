#!/usr/bin/env powershell
# =============================================================================
# COMANDOS ÚTILES PARA REQUIREMENTS INTEGRADOS
# =============================================================================
# Este archivo contiene comandos listos para copiar/pegar
# Uso: Copiar el comando deseado y pegar en PowerShell

# =============================================================================
# 🚀 INSTALACIÓN RÁPIDA (RECOMENDADO)
# =============================================================================

# Crear entorno virtual
python -m venv .venv

# Activar entorno (PowerShell)
.venv\Scripts\Activate.ps1

# Activar entorno (CMD)
.venv\Scripts\activate.bat

# Instalar requirements base
pip install -r requirements.txt

# Instalar requirements training
pip install -r requirements-training.txt

# Verificar instalación
pip check

# Validar integración
python validate_requirements_integration.py


# =============================================================================
# ✅ VERIFICACIÓN
# =============================================================================

# Verificar versiones críticas
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
python -c "import pandas; print(f'Pandas: {pandas.__version__}')"
python -c "import numpy; print(f'NumPy: {numpy.__version__}')"
python -c "from stable_baselines3 import PPO; print('SB3: OK')"
python -c "import citylearn; print('CityLearn: OK')"

# Verificar GPU
python -c "import torch; print(f'GPU disponible: {torch.cuda.is_available()}')"

# Listar todas las librerías instaladas
pip list

# Contar librerías
pip list --format=json | python -c "import json, sys; pkgs=json.load(sys.stdin); print(f'Total: {len(pkgs)} librerías')"


# =============================================================================
# 🔧 MANTENIMIENTO
# =============================================================================

# Actualizar pip
python -m pip install --upgrade pip

# Reinstalar un paquete específico
pip install --force-reinstall package_name

# Instalar una nueva libería
pip install new_package

# Desinstalar paquete
pip uninstall package_name -y

# Actualizar todos los paquetes
pip install -U -r requirements.txt

# Generar reporte de diferencias
pip freeze | findstr /v "^-e " > current_packages.txt


# =============================================================================
# 🐛 TROUBLESHOOTING
# =============================================================================

# Limpiar caché pip
pip cache purge

# Reinstalar requirements limpio
pip install --force-reinstall -r requirements.txt

# Ver dependencias de un paquete
pip show package_name

# Ver árbol de dependencias
pip install pipdeptree
pipdeptree

# Verificar conflictos
pip check

# Ver logs de instalación
pip install -r requirements.txt --verbose


# =============================================================================
# 🐳 DOCKER RELATED
# =============================================================================

# Generar requirements desde entorno actual
pip freeze > requirements.txt

# Crear imagen Docker
docker build -t pvbesscar:latest .

# Ejecutar contenedor
docker run -it pvbesscar:latest python -c "import torch; print(torch.__version__)"


# =============================================================================
# 🔬 DESARROLLO
# =============================================================================

# Instalar en modo development (editable)
pip install -e .

# Ejecutar tests
python -m pytest tests/

# Ejecutar linter
flake8 src/

# Ejecutar type checking
mypy src/

# Format código
black src/

# Sort imports
isort src/


# =============================================================================
# 📊 ANÁLISIS
# =============================================================================

# Ver tamaño de paquetes
pip install pip-tools
pip-compile requirements.txt

# Buscar paquetes obsoletos
pip list --outdated

# Ver cambios entre requirements
diff requirements.txt requirements-training.txt


# =============================================================================
# ⚡ GPU SETUP (Si tienes CUDA 11.8)
# =============================================================================

# Desinstalar torch CPU
pip uninstall torch torchvision -y

# Instalar torch con CUDA 11.8
pip install torch==2.10.0 torchvision==0.15.2 `
    --index-url https://download.pytorch.org/whl/cu118

# Instalar torch con CUDA 12.1
pip install torch==2.10.0 torchvision==0.15.2 `
    --index-url https://download.pytorch.org/whl/cu121

# Verificar GPU
python -c "import torch; print(f'GPU: {torch.cuda.is_available()}'); print(f'Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"CPU\"}')"


# =============================================================================
# 🔄 GIT & VERSIONADO
# =============================================================================

# Commit cambios de requirements
git add requirements.txt requirements-training.txt
git commit -m "feat: update requirements with pinned versions"
git push

# Ver cambios en requirements
git diff requirements.txt

# Ver historial de cambios
git log --oneline -- requirements.txt


# =============================================================================
# 📝 DOCUMENTACIÓN ÚTIL
# =============================================================================

# Ver este archivo
code COMANDOS_UTILES.ps1

# Ver guía rápida
code QUICK_START.md

# Ver integración completa
code INTEGRACION_FINAL_REQUIREMENTS.md

# Ver validador
code validate_requirements_integration.py


# =============================================================================
# 🎯 WORKFLOW TÍPICO
# =============================================================================

# 1. Crear entorno
python -m venv .venv
.venv\Scripts\Activate.ps1

# 2. Instalar
pip install -r requirements.txt
pip install -r requirements-training.txt

# 3. Validar
python validate_requirements_integration.py

# 4. Verificar
pip check

# 5. Estar listo
echo "✅ Entorno listo para usar"

# 6. Ejecutar training (ejemplo)
python -m scripts.run_oe3_simulate --config configs/default.yaml


# =============================================================================
# 🚨 EMERGENCY
# =============================================================================

# Si todo falla, empezar de cero
Remove-Item -Recurse -Force .venv
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install -r requirements-training.txt
pip check


# =============================================================================
# 📞 SOPORTE RÁPIDO
# =============================================================================

# Si encuentras error: copiar este comando completo
python -c "
import sys;
print(f'Python: {sys.version}');
import torch;
print(f'PyTorch: {torch.__version__}');
print(f'GPU: {torch.cuda.is_available()}');
from stable_baselines3 import PPO;
print('✅ SB3 OK')
"

# Si necesitas reportar un bug: ejecuta esto
pip list > current_env.txt
python validate_requirements_integration.py > validation.log
# Adjunta ambos archivos al reporte


# =============================================================================
# EOF
# =============================================================================
