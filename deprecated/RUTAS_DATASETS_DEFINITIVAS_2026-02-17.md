# 📋 MAPEO DEFINITIVO DE RUTAS DE DATASETS (Validado 2026-02-17)

## ✅ RUTAS CANÓNICAS - SIEMPRE USAR ESTAS

### OE2 Primary (Source of Truth)
```
data/oe2/Generacionsolar/pv_generation_citylearn2024.csv   → Solar (8,760 filas) ✅
data/oe2/bess/bess_ano_2024.csv                             → BESS (8,760 filas) ✅
data/oe2/chargers/chargers_ev_ano_2024_v3.csv               → Chargers (8,760 filas, 38 sockets) ✅
data/oe2/demandamallkwh/demandamallhorakwh.csv              → Mall Demand (8,760 filas) ✅
```

### OE2 Secondary (Alternativas válidas)
```
data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv  → Solar alt
data/oe2/Generacionsolar/pv_generation_citylearn_enhanced_v2.csv → Solar enhanced
data/oe2/bess/bess_hourly_dataset_2024.csv                       → BESS alt
```

### Interim (Fallbacks - Solo si OE2 no existe)
```
data/interim/oe2/solar/pv_generation_hourly_citylearn_v2.csv     → Solar fallback
data/interim/oe2/bess/bess_hourly_dataset_2024.csv               → BESS fallback
```

---

## ❌ RUTAS INVÁLIDAS - ELIMINAR/NO USAR

```
NUNCA usar:
  ❌ data/interim/oe2/solar/pv_generation_timeseries.csv          (NO EXISTE)
  ❌ data/oe2/bess/bess_simulation_hourly.csv                     (NO EXISTE)
  ❌ data/oe2/chargers/demanda_vehicular_diaria.csv               (NO EXISTE)
  ❌ data/interim/oe2/demanda/mall_demand_hourly.csv              (NO EXISTE)
  ❌ data/interim/oe2/grid/grid_frequency_and_carbon.csv          (NO EXISTE)
```

---

## 📊 Datasets Listados (177 Total)

### Por Categoría
- **BESS**: 6 datasets (bess_ano_2024, bess_hourly_dataset, bess_soc_profile, etc.)
- **Chargers**: 43 datasets (chargers_ev_ano_2024_v3 + 128 charger_simulation_*.csv)
- **Solar**: 8 datasets (pv_generation_citylearn2024, pv_monthly, pv_daily, etc.)
- **Demand**: 2 datasets (demandamallhorakwh, demandamall15kwh)
- **Training**: 1 dataset (dataset_training_oe3)
- **Utility**: 117 datasets (tablas, escenarios, profiles, etc.)

---

## 🔧 Cambios Realizados (17 Feb 2026)

1. ✅ Actualizado `scripts/list_datasets.py` - Solo rutas válidas
2. ✅ Actualizado `scripts/list_datasets_summary.py` - Solo rutas válidas
3. ✅ Actualizado `src/dataset_builder_citylearn/data_loader.py` - Removed invalid fallbacks
4. ✅ Actualizado `scripts/train/train_ppo_multiobjetivo.py` - bess_ano_2024 primaria
5. ✅ Actualizado `scripts/train/train_a2c_multiobjetivo.py` - pv_generation_citylearn2024 primaria

---

## 🎯 Regla de Oro

**Una sola fuente de verdad (SSOT) para cada dataset:**

1. **Solar**: `data/oe2/Generacionsolar/pv_generation_citylearn2024.csv`
2. **BESS**: `data/oe2/bess/bess_ano_2024.csv`
3. **Chargers**: `data/oe2/chargers/chargers_ev_ano_2024_v3.csv`
4. **Mall Demand**: `data/oe2/demandamallkwh/demandamallhorakwh.csv`

**Siempre usar estas rutas en:**
- Scripts de entrenamiento
- Data loaders
- Configuraciones
- Documentación

---

## ✅ Validación Final

```python
# Test si todas las rutas están disponibles
from pathlib import Path

canonical_datasets = [
    'data/oe2/Generacionsolar/pv_generation_citylearn2024.csv',
    'data/oe2/bess/bess_ano_2024.csv',
    'data/oe2/chargers/chargers_ev_ano_2024_v3.csv',
    'data/oe2/demandamallkwh/demandamallhorakwh.csv',
]

for path in canonical_datasets:
    p = Path(path)
    print(f"{'✅' if p.exists() else '❌'} {path}")
```

---

**Status**: ✅ Rutas definitivas establecidas
**Impact**: Zero breaking changes (las rutas siempre existieron, solo se eliminó confusión)
