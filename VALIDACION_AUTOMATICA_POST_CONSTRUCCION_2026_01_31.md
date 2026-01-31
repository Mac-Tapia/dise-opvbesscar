# VALIDACIÓN AUTOMÁTICA POST-CONSTRUCCIÓN: CityLearn v2 Dataset

**Fecha**: 2026-01-31  
**Propósito**: Garantizar que cada vez que se construya un dataset para CityLearn v2, se validen automáticamente los datos generados.

---

## 🎯 Objetivo

Implementar un sistema que:
1. ✅ Construya dataset CityLearn v2 desde OE2 artifacts
2. ✅ **Valide automáticamente** los datos después de construcción
3. ✅ **Falle si hay errores críticos** (previene entrenamiento con datos incorrectos)
4. ✅ **Advierte sobre inconsistencias** sin bloquear construcción

---

## 📦 Componentes

### 1. Validador: `src/iquitos_citylearn/oe3/validate_citylearn_build.py`

**Clase**: `CityLearnDataValidator`

Ejecuta 7 checks automáticos POST-construcción:

| Check | Valida | Falla Si |
|-------|--------|----------|
| **Schema Structure** | schema.json existe + estructura correcta | No hay buildings o schema vacío |
| **Baseline CSV** | 8,760 filas + columnas requeridas | Longitud ≠ 8,760 o datos negativos |
| **Energy Simulation** | energy_simulation.csv existe + datos | NaN/Infinity en datos |
| **Charger Files** | 128 × charger_simulation_*.csv | < 128 archivos o datos inválidos |
| **BESS Configuration** | BESS en schema + capacidad 4,520 kWh | Capacidad ≠ 4,520 kWh |
| **Solar Sync** | Solar baseline vs OE2 sincronizado | Diferencia > 5% |
| **Data Integrity** | Sin NaN, Infinity, valores inválidos | Cualquier anomalía |

### 2. Integración: `scripts/run_oe3_build_dataset.py`

**Cambio**: Agregar validación POST-BUILD automática

```python
# ANTES
build_citylearn_dataset(...)  # Build solo

# DESPUÉS
build_citylearn_dataset(...)  # Build
validate_citylearn_dataset(...)  # Validación automática
```

---

## 🚀 Uso

### Construcción CON Validación (Recomendado)

```bash
python -m scripts.run_oe3_build_dataset --config configs/default.yaml
```

**Output esperado**:
```
================================================================================
STEP 1: BUILD CITYLEARN DATASET
================================================================================
✓ Dataset construction completed

================================================================================
STEP 2: POST-BUILD VALIDATION
================================================================================
[Schema structure] ✓ PASS
[Baseline CSV] ✓ PASS
[Energy simulation CSV] ✓ PASS
[Charger simulation files] ✓ PASS
[BESS configuration] ✓ PASS
[Solar data sync] ✓ PASS
[Data integrity] ✓ PASS

VALIDATION SUMMARY
Total: 7 PASS, 0 WARN, 0 FAIL

✅ POST-BUILD VALIDATION: ALL CHECKS PASSED - Dataset ready for training
```

### Construcción SIN Validación (Solo si es necesario)

```bash
python -m scripts.run_oe3_build_dataset --config configs/default.yaml --skip-validation
```

⚠️ **No recomendado** - Validación automática es mejor.

---

## 📊 Escenarios de Validación

### Escenario 1: TODO OK ✅

```
7 PASS, 0 WARN, 0 FAIL
→ Script termina con exit code 0
→ Dataset listo para entrenamiento
```

### Escenario 2: Advertencias Menores ⚠️

```
6 PASS, 1 WARN, 0 FAIL
→ Script termina normalmente
→ Dataset usable con caución
Ejemplo: BESS capacity 4,500 vs 4,520 (diferencia pequeña)
```

### Escenario 3: Errores Críticos ❌

```
5 PASS, 0 WARN, 2 FAIL
→ Script termina con RuntimeError
→ Dataset NO es usable
→ Requiere fix de dataset_builder.py o OE2 artifacts
Ejemplo: baseline.csv tiene 8,000 filas en lugar de 8,760
```

---

## 🔍 Detalles de Cada Check

### Check 1: Schema Structure
```python
Valida:
  ✓ schema.json existe
  ✓ Tiene clave 'buildings'
  ✓ Building tiene PV, BESS, Chargers
  ✓ episode_time_steps = 8760

Falla si:
  ✗ schema.json no existe
  ✗ 'buildings' vacío
  ✗ Ninguno de PV/BESS/Chargers configurado
```

### Check 2: Baseline CSV
```python
Valida:
  ✓ baseline_full_year_hourly.csv existe
  ✓ Exactamente 8,760 filas
  ✓ Columnas: pv_generation, ev_demand, mall_load, bess_soc, co2_emissions
  ✓ Todos valores ≥ 0 (no negativos)
  ✓ bess_soc ∈ [0, 100]%

Falla si:
  ✗ Archivo no existe
  ✗ Longitud ≠ 8,760
  ✗ Columnas requeridas falta
  ✗ Valores negativos en demanda
  ✗ bess_soc fuera de rango
```

### Check 3: Energy Simulation
```python
Valida:
  ✓ energy_simulation.csv existe
  ✓ 8,760 filas
  ✓ Columnas de generación solar
  ✓ Columnas de carga de demanda

Falla si:
  ✗ Longitud ≠ 8,760
  ✗ NaN valores
  ✗ Infinity valores
```

### Check 4: Charger Files
```python
Valida:
  ✓ 128 × charger_simulation_*.csv existen
  ✓ Cada archivo tiene 8,760 filas
  ✓ Datos válidos (no negativos)

Advierte si:
  ⚠ < 128 chargers encontrados
```

### Check 5: BESS Configuration
```python
Valida:
  ✓ electrical_storage en schema
  ✓ capacity = 4,520 kWh
  ✓ nominal_power = 2,712 kW

Advierte si:
  ⚠ Capacidad ligeramente diferente
  ⚠ Potencia diferente
```

### Check 6: Solar Sync
```python
Compara:
  OE2: data/interim/oe2/solar/pv_generation_timeseries.csv
  vs
  Baseline: outputs/oe3/baseline_full_year_hourly.csv

Advierte si:
  ⚠ Diferencia > 5% en suma anual
```

### Check 7: Data Integrity
```python
Valida:
  ✓ Sin NaN valores
  ✓ Sin Infinity valores
  ✓ hour ∈ [0, 23]
  ✓ month ∈ [1, 12]

Falla si:
  ✗ NaN encontrados
  ✗ Infinity encontrados
```

---

## 📋 Integración en Pipeline Completo

```bash
# 1. Construcción de dataset CON validación automática
python -m scripts.run_oe3_build_dataset --config configs/default.yaml
   ↓
   BUILD DATASET (dataset_builder.py)
   ↓
   VALIDAR DATOS (validate_citylearn_build.py) ← NUEVO
   ↓
   ✅ Si OK: listo para entrenamiento
   ❌ Si falla: abortar antes de entrenar

# 2. Entrenamiento (solo si validación pasó)
python -m scripts.run_oe3_simulate --config configs/default.yaml
```

---

## 🛠️ Usar Validador Manualmente

### Validar dataset existente

```python
from pathlib import Path
from iquitos_citylearn.oe3.validate_citylearn_build import validate_citylearn_dataset

processed_dir = Path("outputs/processed")
success = validate_citylearn_dataset(processed_dir)

if success:
    print("✅ Dataset is valid")
else:
    print("❌ Dataset has errors")
```

### Usar como script independiente

```bash
python src/iquitos_citylearn/oe3/validate_citylearn_build.py
```

---

## 🎯 Casos de Uso

### Caso 1: Desarrollo Normal
```bash
# 1. Cambias OE2 datos (solar, BESS, EV)
# 2. Reconstruyes dataset
python -m scripts.run_oe3_build_dataset

# Si validación FALLA → No entrenar
# Si validación PASA → Puedes entrenar
```

### Caso 2: Debugging de Dataset
```bash
# Si entrenamiento falla, quieres saber si dataset es culpable
python -m scripts.run_oe3_build_dataset --skip-validation  # Fuerza reconstrucción

# Luego valida
python src/iquitos_citylearn/oe3/validate_citylearn_build.py
```

### Caso 3: CI/CD Pipeline
```bash
#!/bin/bash
# Script de deployment

python -m scripts.run_oe3_build_dataset --config configs/default.yaml

if [ $? -ne 0 ]; then
    echo "❌ Dataset validation failed - NOT training"
    exit 1
fi

echo "✅ Dataset valid - Starting training"
python -m scripts.run_oe3_simulate --config configs/default.yaml
```

---

## 📊 Ejemplo de Output Detallado

```
================================================================================
STEP 1: BUILD CITYLEARN DATASET
================================================================================
Loading CityLearn template: citylearn_v2_mixed_use_commercial...
Building schema...
Generating 128 charger files...
✓ Dataset construction completed

================================================================================
STEP 2: POST-BUILD VALIDATION
================================================================================
[Schema structure] Running...
[Schema structure] ✓ PASS
  ✓ 1 building found (Mall_Iquitos)
  ✓ PV: 4,050 kWp
  ✓ BESS: 4,520 kWh, 2,712 kW
  ✓ 128 chargers
  ✓ episode_time_steps: 8760

[Baseline CSV] Running...
[Baseline CSV] ✓ PASS
  ✓ 8,760 rows (correct)
  ✓ pv_generation sum: 8,030,119 kWh
  ✓ ev_demand sum: 843,880 kWh
  ✓ mall_load sum: 12,368,025 kWh
  ✓ bess_soc range: 10% - 95% (valid)

[Energy simulation CSV] Running...
[Energy simulation CSV] ✓ PASS
  ✓ 8,760 rows
  ✓ Solar generation: 8,030,119 kWh
  ✓ Mall load: 12,368,025 kWh

[Charger simulation files] Running...
[Charger simulation files] ✓ PASS
  ✓ 128 charger files found
  ✓ Each file: 8,760 rows
  ✓ All data valid

[BESS configuration] Running...
[BESS configuration] ✓ PASS
  ✓ Capacity: 4,520 kWh
  ✓ Power: 2,712 kW
  ✓ Efficiency: 0.95

[Solar data sync] Running...
[Solar data sync] ✓ PASS
  ✓ OE2 solar: 8,030,119 kWh
  ✓ Baseline solar: 8,030,119 kWh
  ✓ Difference: 0.0% (perfect sync)

[Data integrity] Running...
[Data integrity] ✓ PASS
  ✓ No NaN values
  ✓ No Infinity values
  ✓ All value ranges valid

VALIDATION SUMMARY
--------
  ✓ Schema structure: OK
  ✓ Baseline CSV: OK
  ✓ Energy simulation CSV: OK
  ✓ Charger simulation files: OK
  ✓ BESS configuration: OK
  ✓ Solar data sync: OK
  ✓ Data integrity: OK

  Total: 7 PASS, 0 WARN, 0 FAIL

✅ POST-BUILD VALIDATION: ALL CHECKS PASSED

Dataset ready for training!
```

---

## 🔗 Archivos Modificados

| Archivo | Cambio |
|---------|--------|
| `src/iquitos_citylearn/oe3/validate_citylearn_build.py` | NUEVO (250+ líneas) |
| `scripts/run_oe3_build_dataset.py` | Integración de validación POST-BUILD |

---

## ✅ Resumen

**Antes (Sin validación automática)**:
```
python -m scripts.run_oe3_build_dataset
→ Construye dataset
→ ¿Datos correctos? 🤷 No se sabe
→ Inicia entrenamiento
→ ❌ Falla a mitad de entrenamiento (desperdicio de tiempo)
```

**Después (Con validación automática)**:
```
python -m scripts.run_oe3_build_dataset
→ Construye dataset
→ Valida datos automáticamente
→ ✅ Si OK: Dataset listo
→ ❌ Si falla: Aborta ANTES de entrenar (ahorra tiempo)
```

---

**Status**: ✅ IMPLEMENTADO | **Fecha**: 2026-01-31 | **Integración**: Automática en pipeline
