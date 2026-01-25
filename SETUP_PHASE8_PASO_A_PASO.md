# 🚀 SETUP PHASE 8 - STEP BY STEP GUIDE

## PASO 1: Instalar Python 3.11.9

#### Antes de nada, instalar Python 3.11.9 (versión EXACTA)

<!-- markdownlint-disable MD013 -->
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
<!-- markdownlint-enable MD013 -->

---

## PASO 2: Verificar Python 3.11.9...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

**Si NO es 3.11.9, DETENER y reinstalar.**

---

## PASO 3: Crear/Activar Virtual Environment

<!-- markdownlint-disable MD013 -->
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
<!-- markdownlint-enable MD013 -->

#### Verificar que está activado:

<!-- markdownlint-disable MD013 -->
```bash
# Debe mostrar algo como: (.venv) D:\dise...
```

[Ver código completo en GitHub]bash
pip install --upgrade pip setuptools wheel
pip install -r requirements-phase7.txt
```bash
<!-- markdownlint-enable MD013 -->

**Esperar a que terminen todas las instalaciones.**

---

## PASO 5: Verificar Phase 7 Installation

#### Ejecutar test de validación

<!-- markdownlint-disable MD013 -->
```bash
python phase7_validation_complete.py
```bash
<!-- markdownlint-enable MD013 -->

#### Esperado: TODOS los tests deben pasar ✅

<!-- markdownlint-disable MD013 -->
```bash
✓ STEP 1: OE2 ...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

---

## PASO 6: Instalar CityLearn (PHASE 8 ONLY)

#### SOLO DESPUÉS de verificar Phase 7

<!-- markdownlint-disable MD013 -->
```bash
# Instalar CityLearn específicamente
pip install -r requirements-phase8.txt

# O manualmente
pip install citylearn>=2.5.0
```bash
<!-- markdownlint-enable MD013 -->

#### Verificar instalación:

<!-- markdownlint-disable MD013 -->
```bash
python -c "import citylearn; print(f'CityLearn {citylearn.__version__} ✅')"
```bash
<!-- markdownlint-enable MD013 -->

---

## PASO 7: Construir Dataset

#### D...
```

[Ver código completo en GitHub]bash
<!-- markdownlint-enable MD013 -->

#### Esperado: Schema y 128 charger CSV files generados

<!-- markdownlint-disable MD013 -->
```bash
✅ Loading OE2 artifacts...
✅ Building schema...
✅ Generating 128 charger_simulation_*.csv files...
✅ Complete dataset generated
```bash
<!-- markdownlint-enable MD013 -->

---

## PASO 8: Entrenar Agentes (Phase 8)

#### Después de dataset construido

<!-- markdownlint-disable MD013 -->
```bash
python scripts/train_agents_serial.py --device cuda --episodes 50
```bash
<!-- markdownlint-enable MD013...
```

[Ver código completo en GitHub]bash
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
<!-- markdownlint-enable MD013 -->

---

**Status**: ✅ Phase 7 → Phase 8 Setup Ready
**Python Version**: 3.11.9 REQUIRED
**CityLearn**: Phase 8 Only (NO Phase 7)
