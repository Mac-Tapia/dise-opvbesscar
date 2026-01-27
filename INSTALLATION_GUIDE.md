# 📦 GUÍA COMPLETA DE INSTALACIÓN - pvbesscar

**Estado**: ✅ Completado  
**Python**: 3.11+ requerido  
**Última actualización**: 27 Enero, 2026

---

## 🚀 Instalación Rápida (5 minutos)

### 1. Crear ambiente virtual

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/Mac
python -m venv .venv
source .venv/bin/activate
```

### 2. Instalar dependencias (EN ORDEN)

```bash
# [1/3] Instalación base (numpy, pandas, torch, gymnasium, stable-baselines3, etc.)
pip install -r requirements.txt

# [2/3] Instalación para training (GPU support, monitoring, etc.)
pip install -r requirements-training.txt

# [3/3] Instalación de CityLearn v2 (separada, sin dependencias duplicadas)
pip install -r requirements-citylearn-v2.txt
```

### 3. Verificar instalación

```bash
python scripts/install_dependencies.py
```

✅ Verás un resumen de todas las librerías instaladas.

---

## 📋 Archivos de requisitos

### `requirements.txt` - BASE
**Contiene**: numpy, pandas, scipy, gymnasium, stable-baselines3, torch, pyyaml, matplotlib, jupyter

```bash
pip install -r requirements.txt
```

**Incluye**:
- ✅ Core data processing (numpy, pandas, scipy)
- ✅ RL frameworks (gymnasium, stable-baselines3)
- ✅ Deep learning (PyTorch)
- ✅ Configuration (PyYAML, python-dotenv)
- ✅ Visualization (matplotlib, seaborn)
- ✅ Development tools (IPython, Jupyter, pytest, mypy, black)

---

### `requirements-training.txt` - TRAINING ADICIONAL
**Contiene**: sb3-contrib, tensorboard, wandb, optimizaciones para GPU

```bash
pip install -r requirements-training.txt
```

**Incluye**:
- ✅ Stable Baselines 3 extras (callbacks, utilities)
- ✅ Monitoring (TensorBoard, Weights & Biases)
- ✅ GPU optimization (numpy-mkl)
- ✅ Profiling (line-profiler, memory-profiler)
- ✅ Testing (pytest-benchmark)

**Notas**:
- Opcional para inferencia, recomendado para training
- Los comentarios incluyen comandos para CUDA 11.8 y 12.1 (si tienes GPU)

---

### `requirements-citylearn-v2.txt` - SEPARADO Y LIMPIO
**Contiene**: SOLO citylearn>=2.0.0 + jsonschema (sus dependencias directas)

```bash
pip install -r requirements-citylearn-v2.txt
```

**Incluye**:
- ✅ CityLearn v2 (environment de simulación de energía)
- ✅ jsonschema (validación de configuración)
- ❌ NO duplica numpy, pandas, scipy, gymnasium (ya están en requirements.txt)

**Ventajas**:
- Sin redundancias de dependencias
- Fácil de actualizar CityLearn sin afectar el resto
- Menor tamaño de instalación

---

## 🔧 Instalación por caso de uso

### Caso 1: Desarrollo local (sin GPU)

```bash
pip install -r requirements.txt
pip install -r requirements-citylearn-v2.txt
```

**Tiempo**: ~5 minutos  
**Espacio**: ~2 GB  
**Notas**: Perfecto para pruebas, debugging

---

### Caso 2: Training con GPU

```bash
# Step 1: Instalar PyTorch con CUDA
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# Step 2: Resto de dependencias
pip install -r requirements.txt
pip install -r requirements-training.txt
pip install -r requirements-citylearn-v2.txt
```

**Tiempo**: ~10 minutos  
**Espacio**: ~4 GB  
**Notas**:
- Reemplaza `cu118` por tu versión CUDA (cu121, cu124, etc.)
- Requiere NVIDIA CUDA Toolkit 11.8+ en tu sistema

---

### Caso 3: Producción (servidor)

```bash
pip install -r requirements.txt
pip install -r requirements-citylearn-v2.txt
```

**Notas**:
- Omitir `requirements-training.txt` (no necesario para inferencia)
- Usar PyTorch CPU o el build específico del servidor

---

## ✅ Verificación

### Script automático

```bash
python scripts/install_dependencies.py
```

**Salida esperada**:
```
================================================================================
ESTADO DE DEPENDENCIAS
================================================================================
Paquete                        Status          Versión
--------------------------------------------------------------------------------
numpy                          ✅ OK           1.24.3
pandas                         ✅ OK           2.0.3
scipy                          ✅ OK           1.11.1
gymnasium                      ✅ OK           0.29.0
stable-baselines3              ✅ OK           2.1.0
torch                          ✅ OK           2.1.0
citylearn                      ✅ OK           2.1.0
pyyaml                         ✅ OK           6.0
python-dotenv                  ✅ OK           1.0.0
matplotlib                     ✅ OK           3.7.2
seaborn                        ✅ OK           0.12.2
tensorboard                    ✅ OK           2.13.0
================================================================================

📊 RESUMEN:
   ✅ Instaladas: 12/12
   ❌ Faltantes: 0/12

✅ TODAS LAS DEPENDENCIAS INSTALADAS CORRECTAMENTE
```

### Verificación manual

```python
# Verificar librerías críticas
import torch
import numpy as np
import pandas as pd
import gymnasium as gym
from stable_baselines3 import SAC, PPO, A2C
from citylearn.citylearn import CityLearnEnv

print("✅ Todas las librerías importables")
print(f"PyTorch GPU: {torch.cuda.is_available()}")
```

---

## 🐛 Solución de problemas

### Error: "Python 3.11 requerido"

```bash
# Verificar versión actual
python --version

# Si no es 3.11, cambiar a 3.11
# Windows: usa py -3.11 en lugar de python
# Linux/Mac: instala Python 3.11 con pyenv o anaconda
```

### Error: "ModuleNotFoundError: No module named 'citylearn'"

```bash
# Asegúrate de instalar en orden:
pip install -r requirements.txt          # ✅ Primero
pip install -r requirements-training.txt # ✅ Segundo
pip install -r requirements-citylearn-v2.txt  # ✅ Tercero
```

### Error: "torch not found" o "CUDA error"

```bash
# Para CPU only:
pip install torch --index-url https://download.pytorch.org/whl/cpu

# Para GPU (CUDA 11.8):
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# Para GPU (CUDA 12.1):
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

### Error: "version conflict" o "incompatible versions"

```bash
# Reinstalar ambiente limpio
deactivate  # Salir del venv
rm -rf .venv  # Eliminar ambiente
python -m venv .venv  # Crear nuevo
.venv\Scripts\activate  # Activar
pip install --upgrade pip  # Actualizar pip
pip install -r requirements.txt  # Instalar desde cero
```

---

## 📊 Comparación de archivos requirements

| Aspecto | requirements.txt | requirements-training.txt | requirements-citylearn-v2.txt |
|---------|-----------------|---------------------------|-------------------------------|
| **Propósito** | Base del proyecto | Training RL con GPU | Environment de simulación |
| **Tamaño** | ~25 paquetes | ~6 paquetes | ~2 paquetes |
| **Instalación** | Obligatorio | Recomendado para training | Obligatorio |
| **Tiempo** | ~3 min | ~2 min | ~1 min |
| **Duplica deps** | NO | NO | NO |
| **GPU support** | NO (CPU) | SÍ (opcional) | N/A |

---

## 🎯 Próximos pasos

Una vez instalado todo:

```bash
# 1. Verificar instalación
python scripts/install_dependencies.py

# 2. Construir dataset OE3
python scripts/run_oe3_build_dataset.py --config configs/default.yaml

# 3. Ejecutar baseline (sin control)
python scripts/run_uncontrolled_baseline.py --config configs/default.yaml

# 4. Entrenar agentes (SAC, PPO, A2C)
python -m scripts.run_oe3_simulate --config configs/default.yaml

# 5. Generar reporte CO2
python -m scripts.run_oe3_co2_table --config configs/default.yaml
```

---

## 📞 Soporte

Si encuentras problemas:

1. Verifica que estés en Python 3.11: `python --version`
2. Ejecuta: `python scripts/install_dependencies.py`
3. Revisa la salida para paquetes faltantes
4. Reinstala el ambiente si es necesario (ver "Solución de problemas")

---

## 📝 Notas finales

- ✅ Todos los archivos requirements.txt están optimizados y sin redundancias
- ✅ CityLearn v2 está SEPARADO sin duplicar dependencias
- ✅ Compatible con Python 3.11+ únicamente
- ✅ GPU support está documentado en requirements-training.txt
- ✅ Script de verificación automático incluido

**Instalación total estimada**: 10-15 minutos (incluye descargas)

