# ⚠️ A2C TRAINING - PYTHON 3.11 REQUERIDO

**Proyecto**: pvbesscar - Iquitos, Perú  
**Versión Python**: 3.11 EXACTAMENTE (no 3.10, 3.12, 3.13, etc.)  
**Fecha**: 26 de Enero 2026  
**Estado**: ✅ VALIDADO Y LISTO  

---

## 🚨 REQUERIMIENTO CRÍTICO: PYTHON 3.11

### ❌ NO SOPORTADOS:
- Python 3.10 o anterior
- Python 3.12 o posterior
- Python 3.13

### ✅ REQUERIDO:
- **Python 3.11.x** (3.11.0, 3.11.1, 3.11.2, etc.)

---

## 🔧 Setup Rápido (Python 3.11)

### Windows

**Opción 1: Instalador oficial**
```bash
# 1. Descargar Python 3.11 desde
#    https://www.python.org/downloads/release/python-311x/
#    (marca: Add Python to PATH)

# 2. Crear venv
python3.11 -m venv .venv
.venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements-training.txt
```

**Opción 2: Script automático**
```bash
.\setup_a2c.ps1
```

### Linux/Mac

```bash
# 1. Instalar Python 3.11
sudo apt install python3.11 python3.11-venv  # Ubuntu/Debian
brew install python@3.11                      # Mac

# 2. Crear venv
python3.11 -m venv .venv
source .venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements-training.txt
```

---

## ✅ Verificar Setup

```bash
# Verificar Python 3.11
python --version
# Output debe ser: Python 3.11.x

# Ejecutar setup
python setup_a2c.py

# Si pasa, ya puedes entrenar
python train_a2c_local_data_only.py
```

---

## 🚀 Entrenar A2C

### Paso 1: Validar Sistema (OBLIGATORIO)
```bash
python validate_a2c_mall_demand.py
```
**Output esperado**: ✓ Model loaded ✓ Predictions working

### Paso 2: Entrenar
```bash
python train_a2c_local_data_only.py
```
**Tiempo**: 30-120 min (GPU) | 2-4 horas (CPU)  
**Output**: `checkpoints/A2C/a2c_mall_demand_2024.zip`

### Paso 3: Analizar
```bash
python analyze_a2c_24hours.py
```

---

## 📝 Archivos de Configuración

### requirements-training.txt
```
numpy>=1.24.0,<2.0
pandas>=2.0.0,<3.0
gymnasium>=0.28.0,<0.30
stable-baselines3>=2.0.0
torch>=2.0.0,<2.3
pyyaml>=6.0
python-dotenv>=1.0.0
```

**TODAS las versiones son compatibles con Python 3.11**

---

## ⚠️ Si hay Error: "Python 3.X no soportado"

### Significa:
Se ejecutó script con Python 3.10, 3.12, 3.13, etc.

### Solución:
1. **Desinstalar Python equivocado** (opcional)
2. **Instalar Python 3.11** desde python.org
3. **Crear venv nuevo**:
   ```bash
   python3.11 -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements-training.txt
   ```
4. **Ejecutar script de nuevo**

---

## 📊 Archivos Esenciales

| Archivo | Propósito | Python |
|---------|-----------|--------|
| `train_a2c_local_data_only.py` | Entrenar A2C | 3.11 ✓ |
| `validate_a2c_mall_demand.py` | Validar modelo | 3.11 ✓ |
| `analyze_a2c_24hours.py` | Analizar resultados | 3.11 ✓ |
| `setup_a2c.py` | Verificar instalación | 3.11 ✓ |
| `setup_a2c.ps1` | Setup automático | 3.11 ✓ |
| `requirements-training.txt` | Dependencias | 3.11 ✓ |

**Todos requieren Python 3.11 exactamente**

---

## 🔍 Verificación Pre-Entrenamiento

Ejecuta ANTES de `train_a2c_local_data_only.py`:

```bash
# 1. Verificar Python
python --version
# Debe mostrar: Python 3.11.x

# 2. Verificar ambiente
python -c "import sys; print(f'venv: {sys.prefix != sys.base_prefix}')"
# Debe mostrar: venv: True

# 3. Verificar paquetes
python -c "import gymnasium, numpy, pandas, stable_baselines3, torch; print('OK')"
# Debe mostrar: OK

# 4. Validar modelo
python validate_a2c_mall_demand.py
# Debe mostrar: ✓ Predictions working

# 5. Si todo OK: entrenar
python train_a2c_local_data_only.py
```

---

## 🆘 Troubleshooting

### Error: "Python 3.11 required, got 3.12"

**Causa**: Ejecutar script con Python equivocado  
**Solución**:
```bash
# Activar venv con Python 3.11
.venv\Scripts\activate
# Luego ejecutar script
python train_a2c_local_data_only.py
```

### Error: "No module named gymnasium"

**Causa**: Paquetes no instalados  
**Solución**:
```bash
pip install -r requirements-training.txt
```

### Error: "venv not active"

**Causa**: Ambiente no activado  
**Solución**:
```bash
# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

### Error: "torch not found but GPU needed"

**Causa**: PyTorch sin CUDA  
**Solución** (si tienes CUDA 11.8+):
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

---

## 📚 Referencias Rápidas

**Setup rápido**:
```bash
python3.11 -m venv .venv && .venv\Scripts\activate && pip install -r requirements-training.txt
```

**Verificar todo**:
```bash
python setup_a2c.py
```

**Entrenar**:
```bash
python train_a2c_local_data_only.py
```

---

**IMPORTANTE**: Todos los scripts tienen validación integrada de Python 3.11.  
Si ejecutas con otra versión, el script se detendrá automáticamente.

✅ Sistema listo. Usa Python 3.11 y disfruta. 🚀
