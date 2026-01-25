# 🚀 SETUP PHASE 8 - STEP BY STEP GUIDE

## PASO 1: Instalar Python 3.11.9

#### Antes de nada, instalar Python 3.11.9 (versión EXACTA)

```bash
# Opción 1: Descargar de python.org
# https://www.python.org/downloads/release/python-3119/

# Opción 2: Usando pyenv (Windows)
pyenv install 3.11.9
pyenv local 3.11.9

# Opción 3: Usando Conda
conda create -n phase8 python=3.11.9
conda activate phase8

# Opción 4: Usando Scoop (Windows)
scoop install python@3.11.9
```bash

---

## PASO 2: Verificar Python 3.11.9

#### Asegúrate que Python es 3.11.9

```bash
python --version
# DEBE mostrar: Python 3.11.9

python -c "import sys; print(sys.executable)"
# DEBE ser la ruta de Python 3.11.9
```bash

**Si NO es 3.11.9, DETENER y reinstalar.**

---

## PASO 3: Crear/Activar Virtual Environment

```bash
# Crear nuevo .venv (si no existe)
python -m venv .venv

# Activar .venv (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Activar .venv (Windows CMD)
.venv\Scripts\activate.bat

# Activar .venv (Linux/Mac)
source .venv/bin/activate
```bash

#### Verificar que está activado:

```bash
# Debe mostrar algo como: (.venv) D:\diseñopvbesscar>
```bash

---

## PASO 4: Instalar Dependencias Phase 7

#### SOLO dependencias básicas (sin CityLearn)

```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements-phase7.txt
```bash

**Esperar a que terminen todas las instalaciones.**

---

## PASO 5: Verificar Phase 7 Installation

#### Ejecutar test de validación

```bash
python phase7_validation_complete.py
```bash

#### Esperado: TODOS los tests deben pasar ✅

```bash
✓ STEP 1: OE2 Data Integrity Check ✅
✓ STEP 2: Key Data Metrics ✅
✓ STEP 3: Charger Profile Expansion ✅
✓ STEP 4: Schema File Status ✅
```bash

---

## PASO 6: Instalar CityLearn (PHASE 8 ONLY)

#### SOLO DESPUÉS de verificar Phase 7

```bash
# Instalar CityLearn específicamente
pip install -r requirements-phase8.txt

# O manualmente
pip install citylearn>=2.5.0
```bash

#### Verificar instalación:

```bash
python -c "import citylearn; print(f'CityLearn {citylearn.__version__} ✅')"
```bash

---

## PASO 7: Construir Dataset

#### Después de CityLearn instalado

```bash
python -m scripts.run_oe3_build_dataset --config configs/default.yaml
```bash

#### Esperado: Schema y 128 charger CSV files generados

```bash
✅ Loading OE2 artifacts...
✅ Building schema...
✅ Generating 128 charger_simulation_*.csv files...
✅ Complete dataset generated
```bash

---

## PASO 8: Entrenar Agentes (Phase 8)

#### Después de dataset construido

```bash
python scripts/train_agents_serial.py --device cuda --episodes 50
```bash

---

## ⚠️ ERRORES COMUNES

### Error 1: "python --version → Python 3.13"

**PROBLEMA**: Installed Python 3.13 (wrong version)

**SOLUCIÓN**:

1. Uninstall Python 3.13
2. Install Python 3.11.9 exactly
3. Verify: `python --version` → Python 3.11.9

---

### Error 2: "ImportError: No module named 'citylearn'"

**PROBLEMA**: CityLearn no instalado (esperado en Phase 7)

**SOLUCIÓN**:

- Phase 7: Ignorar (normal)
- Phase 8: Ejecutar `pip install -r requirements-phase8.txt`

---

### Error 3: "Cython errors during citylearn install"

**PROBLEMA**: Python version incorrecto cuando instalar CityLearn

**SOLUCIÓN**:

1. Verify Python version: `python --version` → DEBE ser 3.11.9
2. Instalar CityLearn: `pip install -r requirements-phase8.txt`

---

## ✅ CHECKLIST

- [ ] Python 3.11.9 instalado
- [ ] `python --version` → Python 3.11.9
- [ ] `.venv` creado y activado
- [ ] `pip install -r requirements-phase7.txt` completado
- [ ] `python phase7_validation_complete.py` - ✅ TODOS PASAN
- [ ] `pip install -r requirements-phase8.txt` completado
- [ ] `python -c "import citylearn"` → ✅ OK
- [ ] Dataset construido (128 charger CSVs)
- [ ] Listo para entrenar agentes

---

## 🎯 VERSIONES EXACTAS

#### REQUERIDAS:

- Python: **3.11.9** (exactamente)
- CityLearn: **>=2.5.0** (solo Phase 8)
- gymnasium: **<=0.28.1** (especificar versión máxima)
- PyYAML: **>=6.0**

---

## 📋 ARCHIVOS DE DEPENDENCIAS

1. **requirements.txt** - Todas las dependencias (ACTUALIZADO - sin CityLearn)
2. **requirements-phase7.txt** - Phase 7 core (sin CityLearn)
3. **requirements-phase8.txt** - Phase 8 only (CityLearn)

---

## 🚀 QUICK START COMMAND

```bash
# 1. Verificar Python
python --version

# 2. Activar .venv
.\.venv\Scripts\Activate.ps1

# 3. Instalar Phase 7
pip install -r requirements-phase7.txt

# 4. Validar Phase 7
python phase7_validation_complete.py

# 5. Instalar Phase 8
pip install -r requirements-phase8.txt

# 6. Entrenar
python scripts/train_agents_serial.py --device cuda --episodes 50
```bash

---

**Status**: ✅ Phase 7 → Phase 8 Setup Ready
**Python Version**: 3.11.9 REQUIRED
**CityLearn**: Phase 8 Only (NO Phase 7)
