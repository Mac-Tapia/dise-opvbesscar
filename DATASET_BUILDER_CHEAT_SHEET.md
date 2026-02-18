# CityLearn v2 Dataset Builder - CHEAT SHEET

## 🚀 USO MÁS RÁPIDO (Copiar & Pegar)

### Build (Construir desde OE2)
```python
from dataset_builder_citylearn import build_citylearn_dataset

dataset = build_citylearn_dataset()
combined_df = dataset['combined']  # 8,760 × 22
print(f"Dataset: {combined_df.shape}")
```

### Save (Guardar a disco)
```python
from dataset_builder_citylearn import save_citylearn_dataset

output_dir = save_citylearn_dataset(dataset)
# Crea: data/processed/citylearn/iquitos_ev_mall/*.csv
```

### Load (Cargar para training)
```python
from dataset_builder_citylearn import load_citylearn_dataset

loaded = load_citylearn_dataset()  # Lee desde data/processed/citylearn/...
combined = loaded['combined']      # Listo para training
```

---

## 📊 DATOS DISPONIBLES

```python
dataset['combined']      # 8,760 × 22 (MAIN)
dataset['solar']         # SolarData (8,760 horas)
dataset['bess']          # BESSData (1,700 kWh)
dataset['chargers']      # ChargerData (38 sockets)
dataset['demand']        # DemandData (mall + EV)
dataset['config']        # Dict with system specs
```

---

## 🔧 CONFIGURACIÓN (v7.0 LOCKED)

```python
config = dataset['config']

# Sistema
pv_kwp = config['system']['pv_capacity_kwp']           # 4,050 kWp
bess_kwh = config['system']['bess_capacity_kwh']       # 1,700 kWh
bess_kw = config['system']['bess_max_power_kw']        # 400 kW
n_sockets = config['system']['n_sockets']              # 38
charger_kw = config['system']['charger_power_kw']      # 7.4 kW

# Demanda
mall_avg_kw = config['demand']['mall_avg_kw']          # 100 kW avg
ev_avg_kw = config['demand']['ev_avg_kw']              # 50 kW

# CO2
grid_co2_kg_per_kwh = config['co2']['grid_factor_kg_per_kwh']  # 0.4521
ev_co2_kg_per_kwh = config['co2']['ev_factor_kg_per_kwh']      # 2.146
```

---

## 📁 ARCHIVOS SALIDA

```
data/processed/citylearn/iquitos_ev_mall/
├── citylearnv2_combined_dataset.csv    8,760 × 22 (MAIN)
├── solar_generation.csv                8,760 × 11
├── bess_timeseries.csv                 8,760 × 27
├── chargers_timeseries.csv             8,760 × 1,060
├── mall_demand.csv                     8,760 × 6
└── dataset_config_v7.json              Metadata
```

---

## 🎯 CASOS COMUNES

### Case 1: Training SAC/PPO/A2C
```python
from dataset_builder_citylearn import build_citylearn_dataset

dataset = build_citylearn_dataset()
combined = dataset['combined']

# Pass to CityLearn environment
env = CityLearnEnv(timeseries_data=combined)
agent.learn(env, ...)
```

### Case 2: Análisis post-training
```python
from dataset_builder_citylearn import load_citylearn_dataset
import pandas as pd

loaded = load_citylearn_dataset()
df = loaded['combined']

# EDA
print(df.describe())
print(df.columns)

# Visualizar
df.plot()
```

### Case 3: Exportar a CSV
```python
dataset = build_citylearn_dataset()
dataset['combined'].to_csv('export.csv', index=False)

# O individual
dataset['solar'].df.to_csv('solar_only.csv', index=False)
```

### Case 4: Override rutas
```python
dataset = build_citylearn_dataset(
    solar_path="datos/mi_solar.csv",
    bess_path="datos/mi_bess.csv"
)
save_citylearn_dataset(dataset, output_dir="datos_custom/")
```

---

## ✅ VALIDACIÓN

```bash
# Quick test
python scripts/test_citylearn_dataset_builder.py

# Output esperado:
# ✅ ALL TESTS PASSED!
# 📂 Dataset saved to: data/processed/citylearn/iquitos_ev_mall/
```

---

## 🔍 DEBUGGING

```python
# Verificar cargas OK
dataset = build_citylearn_dataset()
print(f"Solar: {len(dataset['solar'].df)} rows")
print(f"BESS: {len(dataset['bess'].df)} rows")
# Deben ser 8,760 ambos

# Verificar guardado OK
from pathlib import Path
dir_path = Path('data/processed/citylearn/iquitos_ev_mall')
files = list(dir_path.glob('*.csv'))
print(f"Files saved: {len(files)}")  # Deben ser 5

# Verificar carga OK
loaded = load_citylearn_dataset()
print(f"Combined shape: {loaded['combined'].shape}")
# Debe ser (8760, 22)
```

---

## 🐛 ERRORES COMUNES

| Error | Solución |
|-------|----------|
| `OE2ValidationError: Data not found` | Ejecutar desde root del proyecto, verificar data/oe2/ existe |
| `FileNotFoundError` al load | Ejecutar `save_citylearn_dataset()` primero |
| `KeyError: 'solar'` | Usar `dataset['solar']` (lowercase) |
| Memory error | Reducir batch size, usar `load_citylearn_dataset()` en lugar de build |

---

## 📚 FUNCIONES DISPONIBLES

```python
# Build (desde OE2)
from dataset_builder_citylearn import build_citylearn_dataset
build_citylearn_dataset(solar_path=None, bess_path=None, ...)

# Save (a disco)
from dataset_builder_citylearn import save_citylearn_dataset
save_citylearn_dataset(dataset, output_dir=None)

# Load (desde disco)
from dataset_builder_citylearn import load_citylearn_dataset
load_citylearn_dataset(input_dir=None)

# Validación (bajo nivel)
from dataset_builder_citylearn import (
    load_solar_data,
    load_bess_data,
    load_chargers_data,
    load_mall_demand_data,
    validate_oe2_complete,
)
```

---

## ⏱️ TIEMPOS

| Operación | Tiempo (aprox) |
|-----------|----------------|
| build_citylearn_dataset() | ~2-3 segundos |
| save_citylearn_dataset() | ~1-2 segundos |
| load_citylearn_dataset() | ~0.5 segundos |
| **Total pipeline** | **~3-5 segundos** |

*Números con SSD, datos 8,760 filas × múltiples columnas*

---

## 📞 SOPORTE

**Documentación completa:** `DATASET_BUILDER_v7.0_RESUMEN.md`

**Ejemplo completo:** `examples/quick_start_dataset_builder.py`

**Test script:** `scripts/test_citylearn_dataset_builder.py`

**Branch:** `smartcharger` (GitHub)

**Fecha:** 2026-02-18  
**Versión:** v7.0
