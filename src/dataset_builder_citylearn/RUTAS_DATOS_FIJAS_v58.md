# 📋 RUTAS DEFINITORIAS DE DATASETS v5.8

**Actualizado:** 17 Feb 2026  
**Versión anterior:** v5.7  
**Status:** ✅ SINGLE SOURCE OF TRUTH (SSOT)

---

## 🎯 REGLA DE ORO

**Una sola fuente de verdad para cada dataset:**

| Dataset | Ruta Canónica | Validación |
|---------|---------------|-----------|
| **Solar PV** | `data/oe2/Generacionsolar/pv_generation_citylearn2024.csv` | 8,760 filas ✅ |
| **BESS** | `data/oe2/bess/bess_ano_2024.csv` | 8,760 filas ✅ |
| **Chargers EV** | `data/oe2/chargers/chargers_ev_ano_2024_v3.csv` | 8,760 filas, 38 sockets ✅ |
| **Mall Demand** | `data/oe2/demandamallkwh/demandamallhorakwh.csv` | 8,760 filas ✅ |

---

## ✅ RUTAS VÁLIDAS (USAR SOLO ESTAS)

### OE2 Primary (Source of Truth)
```
data/oe2/Generacionsolar/pv_generation_citylearn2024.csv   → Solar (8,760 filas) ✅
data/oe2/bess/bess_ano_2024.csv                             → BESS (8,760 filas) ✅
data/oe2/chargers/chargers_ev_ano_2024_v3.csv               → Chargers (8,760 filas, 38 sockets) ✅
data/oe2/demandamallkwh/demandamallhorakwh.csv              → Mall Demand (8,760 filas) ✅
```

### OE2 Alternativas (válidas si primarias no existen)
```
data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv
data/oe2/Generacionsolar/pv_generation_citylearn_enhanced_v2.csv
data/oe2/bess/bess_hourly_dataset_2024.csv
```

### Interim/Fallback (solo como último recurso)
```
data/interim/oe2/solar/pv_generation_hourly_citylearn_v2.csv
data/interim/oe2/bess/bess_hourly_dataset_2024.csv
```

---

## ❌ RUTAS INVÁLIDAS - NUNCA USAR

```
PROHIBIDO:
  ❌ data/interim/oe2/solar/pv_generation_timeseries.csv
  ❌ data/oe2/bess/bess_simulation_hourly.csv
  ❌ data/oe2/chargers/demanda_vehicular_diaria.csv
  ❌ data/interim/oe2/demanda/mall_demand_hourly.csv
  ❌ data/interim/oe2/grid/grid_frequency_and_carbon.csv
```

---

## 📝 ARCHIVOS QUE USAN ESTAS RUTAS

**Data loaders (deben usar SSOT):**
- `src/dataset_builder_citylearn/data_loader.py` ✅
- `scripts/train/train_ppo_multiobjetivo.py` ✅
- `scripts/train/train_a2c_multiobjetivo.py` ✅
- `scripts/train/train_sac_multiobjetivo.py` ✅

**Configuración:**
- `configs/default.yaml` ✅
- `configs/ppo_optimized.json` ✅
- `configs/sac_optimized.json` ✅

**Utilities:**
- `scripts/list_datasets.py` ✅
- `scripts/prepare_datasets_all_agents.py` ✅

---

## 🔍 VALIDACIÓN

```python
from pathlib import Path
import pandas as pd

canonical_datasets = {
    'Solar': 'data/oe2/Generacionsolar/pv_generation_citylearn2024.csv',
    'BESS': 'data/oe2/bess/bess_ano_2024.csv',
    'Chargers': 'data/oe2/chargers/chargers_ev_ano_2024_v3.csv',
    'Mall': 'data/oe2/demandamallkwh/demandamallhorakwh.csv',
}

for name, path in canonical_datasets.items():
    p = Path(path)
    if p.exists():
        df = pd.read_csv(p)
        print(f"✅ {name}: {len(df)} rows, {len(df.columns)} cols")
    else:
        print(f"❌ {name}: NOT FOUND at {path}")
```

---

## 📊 CAMBIOS v5.7 → v5.8

| Cambio | v5.7 | v5.8 |
|--------|------|------|
| Solar fallback | 3 rutas | 1 primaria + 2 alternatives |
| BESS primaria | bess_hourly_dataset_2024 | bess_ano_2024 |
| Validaciones | Manual | Automated checks |
| Documentación | Básica | Completa con ejemplos |

---

**Status:** ✅ LISTO PARA USO INMEDIATO
