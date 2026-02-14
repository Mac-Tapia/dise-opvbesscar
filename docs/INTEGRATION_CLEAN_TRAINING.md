# 🚀 INTEGRACIÓN: Reconstrucción OE2 + Entrenamiento RL

**Para principiantes:** Usa la checklist rápida abajo  
**Para expertos:** Lee la sección de arquitectura interna  

---

## ⚡ CHECKLIST RÁPIDA (5 minutos)

```bash
# 1. Reconstruir datasets sin duplicidad
$ python scripts/validate_and_rebuild_oe2.py --cleanup
✓ Solar: 4050.0 kWp, 946.6 kW avg
✓ BESS: 1700.0 kWh, power=342.0 kW
✓ Chargers: 19 units, 38 sockets
✓ Mall Demand: 1411.9 kW avg
✓ Cleanup: Removed 5 duplicate files

# 2. Verificar que no hay errores
# (Si ves "✅ ESTADO FINAL: EXITOSO" → continuar)

# 3. Entrenar agente
$ python scripts/train/train_sac_multiobjetivo.py
# O PPO:
$ python scripts/train/train_ppo_multiobjetivo.py  

# 4. Monitorear progreso
# → Ver checkpoints en: checkpoints/SAC/ (o PPO/, A2C/)
# → Ver métricas en: outputs/sac_training/ (o ppo_training/, etc)
```

---

## 🏗️ ARQUITECTURA SIN DUPLICIDAD

### Flujo de Datos: Reconstrucción → Validación → Entrenamiento

```
┌────────────────────────────────────────────────────────┐
│  DATOS PRIMARIOS (source of truth)                    │
│  data/oe2/                                             │
├────────────────────────────────────────────────────────┤
│ ✓ Generacionsolar/pv_generation_citylearn2024.csv    │
│ ✓ bess/bess_ano_2024.csv                             │
│ ✓ chargers/chargers_ev_ano_2024_v3.csv               │
│ ✓ demandamallkwh/demandamallhorakwh.csv              │
└────────────────────────────────────────────────────────┘
           ↓ (resolve_data_path)
┌────────────────────────────────────────────────────────┐
│  CAPA DE RESOLUCIÓN (data_loader.py)                  │
│  - Detecta rutas primarias                            │
│  - Fallback a data/interim/oe2/ si es necesario       │
│  - Valida 8,760 timesteps                             │
└────────────────────────────────────────────────────────┘
           ↓ (validate_oe2_complete)
┌────────────────────────────────────────────────────────┐
│  VALIDACIÓN COMPLETA                                  │
│  - Solar: 4,050 kWp, mean=946.6 kW ✓                 │
│  - BESS: 1,700 kWh, 342 kW power ✓                   │
│  - Chargers: 38 sockets (19 units) ✓                 │
│  - Mall: 1,411.9 kW promedio ✓                       │
│  - Cleanup: 5 duplicados eliminados ✓                │
└────────────────────────────────────────────────────────┘
           ↓ (load_solar_data + load_bess_data + ...)
┌────────────────────────────────────────────────────────┐
│  DATAFRAMES LIMPIOS (sin duplicidad)                  │
│  - solar_df: 8,760 rows × 2 cols (datetime, potencia) │
│  - bess_df: 8,760 rows × n cols (soc, charge, etc)   │
│  - chargers_df: 8,760 rows × 352 cols (38 × 9)       │
│  - mall_demand_df: 8,760 rows × 2 cols                │
└────────────────────────────────────────────────────────┘
           ↓ (CityLearn v2 Environment)
┌────────────────────────────────────────────────────────┐
│  ENTORNO RL (observation + action spaces)             │
│  - Observation: 124-dim vector                         │
│  - Actions: 39-dim continuous [0,1]                   │
│    (1 BESS + 38 charger sockets)                       │
│  - Episode length: 8,760 timesteps                     │
└────────────────────────────────────────────────────────┘
           ↓ (Agent Training)
┌────────────────────────────────────────────────────────┐
│  AGENTS (SAC / PPO / A2C)                             │
│  - SAC (Soft Actor-Critic): off-policy, asimétrico   │
│  - PPO (Proximal Policy Optimization): on-policy      │
│  - A2C (Advantage Actor-Critic): on-policy, simple    │
└────────────────────────────────────────────────────────┘
           ↓ (Rewards)
┌────────────────────────────────────────────────────────┐
│  OBJETIVO MULTI-OBJETIVO (Reward Weights)            │
│  - CO2 grid minimization: 0.35                        │
│  - Solar self-consumption: 0.20                       │
│  - EV satisfaction: 0.30                              │
│  - Cost minimization: 0.10                            │
│  - Grid stability: 0.05                               │
└────────────────────────────────────────────────────────┘
           ↓
┌────────────────────────────────────────────────────────┐
│  RESULTADOS                                           │
│  - Checkpoints: checkpoints/{SAC,PPO,A2C}/            │
│  - Metrics: outputs/{agent}_training/                 │
│  - CO2 reduction: ~26-29% vs baseline                 │
│  - Solar utilization: ~65-68%                         │
└────────────────────────────────────────────────────────┘
```

---

## 🔌 INTEGRACIÓN CON AGENTS

### Pattern 1: Load Clean Data Directly
```python
from pathlib import Path
from src.dimensionamiento.oe2.disenocargadoresev.data_loader import (
    validate_oe2_complete,
    load_solar_data,
    load_bess_data,
    load_chargers_data,
    load_mall_demand_data
)

# Validar una sola vez
result = validate_oe2_complete(cleanup_interim=True)

if result["is_valid"]:
    # Sus datos están limpios (sin duplicados)
    # Ahora crear CityLearn ambiente
    from src.citylearnv2.environment import CityLearnEnv
    
    env = CityLearnEnv(
        solar_df=result["dataframes"]["solar"],
        bess_df=result["dataframes"]["bess"],
        chargers_df=result["dataframes"]["chargers"],
        mall_demand_df=result["dataframes"]["mall_demand"]
    )
    
    # Entrenar agente
    from src.agents.sac import make_sac
    agent = make_sac(env)
    agent.learn(total_timesteps=87600)  # 10 episodes
```

### Pattern 2: Rebuild Before Each Training Session
```python
from src.dimensionamiento.oe2.disenocargadoresev.data_loader import rebuild_oe2_datasets_complete

def train_with_clean_data():
    # Reconstruir antes de cada sesión
    result = rebuild_oe2_datasets_complete(cleanup_interim=True)
    
    if not result["is_valid"]:
        raise RuntimeError(f"Dataset validation failed: {result['errors']}")
    
    # Proceder con datos limpios
    dfs = result["dataframes"]
    return train_agent(dfs)
```

### Pattern 3: Scheduled Cleanup (Cron-style)
```python
# En scripts/train/train_sac_multiobjetivo.py (ejemplo)

import sys
from pathlib import Path

# Pre-training: Ensure clean datasets
sys.path.insert(0, str(Path.cwd() / "src"))
from dimensionamiento.oe2.disenocargadoresev.data_loader import rebuild_oe2_datasets_complete

print("🔧 Pre-training: Rebuilding datasets...")
result = rebuild_oe2_datasets_complete(cleanup_interim=True)

if not result["is_valid"]:
    print(f"❌ Cannot start training: {result['errors']}")
    sys.exit(1)

print("✅ Datasets validated and cleaned")

# Ahora podrías iniciar entrenamiento
# ... train code ...
```

---

## 📊 RESOLUCIÓN DE PROBLEMAS

### Problema 1: "Solar CSV not found"
```python
# ❌ Problema
from src.dimensionamiento.oe2.disenocargadoresev.data_loader import load_solar_data
solar, df = load_solar_data()  # Error!

# ✅ Solución: Primero validar
from src.dimensionamiento.oe2.disenocargadoresev.data_loader import rebuild_oe2_datasets_complete
result = rebuild_oe2_datasets_complete(cleanup_interim=True)

if result["is_valid"]:
    solar_df = result["dataframes"]["solar"]
    # Ahora proceder con seguridad
```

### Problema 2: "Duplicates consuming memory"
```bash
# ❌ Error: Entrenamiento lento / OOM
# Usuario: "¿Por qué 500 MB de RAM extra?"

# ✅ Solución
python scripts/validate_and_rebuild_oe2.py --cleanup

# Después:
# - 5 duplicados eliminados
# - ~500 MB liberados
# - Entrenamiento más rápido
```

### Problema 3: "Data inconsistency between agents"
```python
# ❌ Problema
# SAC entrena con data/interim/oe2/solar/pv_generation_timeseries.csv (antiguo)
# PPO entrena con data/oe2/Generacionsolar/pv_generation_citylearn2024.csv (nuevo)
# → Resultados no son comparables

# ✅ Solución
python scripts/validate_and_rebuild_oe2.py --cleanup
# Ahora todos los agentes usan el mismo dataset → Resultados comparables
```

---

## 🎯 BEST PRACTICES

### ✅ DO (Fácil, Recomendado)

1. **Siempre ejecutar reconstrucción antes de entrenar:**
   ```bash
   python scripts/validate_and_rebuild_oe2.py --cleanup
   ```

2. **Usar funciones helper en data_loader.py:**
   ```python
   from src.dimensionamiento.oe2.disenocargadoresev.data_loader import rebuild_oe2_datasets_complete
   result = rebuild_oe2_datasets_complete(cleanup_interim=True)
   ```

3. **Verificar `result["is_valid"]` antes de crear ambiente:**
   ```python
   if result["is_valid"]:
       env = CityLearnEnv(result["dataframes"])
   else:
       raise RuntimeError(result["errors"])
   ```

4. **Guardar logs de reconstrucción:**
   ```bash
   python scripts/validate_and_rebuild_oe2.py --cleanup > logs/oe2_rebuild.log
   ```

### ❌ DON'T (Evitar a toda costa)

1. ❌ **No cargar datos directamente sin validar:**
   ```python
   # MAL
   df = pd.read_csv("data/interim/oe2/solar/pv_generation_timeseries.csv")
   # ← Puede ser versión antigua/duplicada
   ```

2. ❌ **No mezclar rutas principales e intermedias:**
   ```python
   # MAL
   solar_df = pd.read_csv("data/interim/oe2/...")
   chargers_df = pd.read_csv("data/oe2/...")
   # ← Datos inconsistentes
   ```

3. ❌ **No entrenar múltiples agentes sin reconstrucción:**
   ```bash
   # MAL
   python train_sac.py
   python train_ppo.py
   python train_a2c.py
   # ← Cada uno podría cargar datos diferentes
   ```

4. ❌ **No ignorar errores de validación:**
   ```python
   # MAL
   try:
       result = rebuild_oe2_datasets_complete()
   except:
       pass  # Ignored - NUNCA HAGAS ESTO
   ```

---

## 📈 VERIFICACIÓN DE INTEGRIDAD

Después de `--cleanup`, ejecutar este check:

```python
#!/usr/bin/env python3
"""Verificar integridad de datasets después de reconstrucción."""

from pathlib import Path
import pandas as pd

def check_integrity():
    """Verifica que todos los dados están OK para CityLearn."""
    
    required_files = {
        "Solar": Path("data/oe2/Generacionsolar/pv_generation_citylearn2024.csv"),
        "BESS": Path("data/oe2/bess/bess_ano_2024.csv"),
        "Chargers": Path("data/oe2/chargers/chargers_ev_ano_2024_v3.csv"),
        "Mall Demand": Path("data/oe2/demandamallkwh/demandamallhorakwh.csv"),
    }
    
    duplicate_files = [
        Path("data/interim/oe2/solar/pv_generation_hourly_citylearn_v2.csv"),
        Path("data/interim/oe2/solar/pv_generation_timeseries.csv"),
        Path("data/interim/oe2/bess/bess_hourly_dataset_2024.csv"),
        Path("data/interim/oe2/chargers/chargers_real_hourly_2024.csv"),
        Path("data/interim/oe2/demandamallkwh/demandamallhorakwh.csv"),
    ]
    
    print("🔍 INTEGRIDAD DE DATASETS\n")
    
    # Verificar principales existen
    print("📦 Archivos principales:")
    for name, path in required_files.items():
        if path.exists():
            size_mb = path.stat().st_size / (1024**2)
            print(f"  ✓ {name}: {path.name} ({size_mb:.1f} MB)")
        else:
            print(f"  ✗ {name}: FALTA {path}")
    
    # Verificar duplicados NO existen
    print("\n🗑️  Archivos duplicados (deben estar eliminados):")
    duplicates_found = 0
    for dup_path in duplicate_files:
        if dup_path.exists():
            print(f"  ✗ {dup_path.name} - TODAVÍA EXISTS!")
            duplicates_found += 1
        else:
            print(f"  ✓ {dup_path.name} - eliminado")
    
    # Resumen
    print(f"\n{'='*50}")
    if duplicates_found == 0 and all(p.exists() for p in required_files.values()):
        print("✅ INTEGRIDAD OK - LISTO PARA ENTRENAR")
    else:
        print(f"❌ PROBLEMAS: {duplicates_found} duplicados aún existen")
    print(f"{'='*50}\n")

if __name__ == "__main__":
    check_integrity()
```

**Guardar como:** `scripts/check_dataset_integrity.py`

**Ejecutar:**
```bash
python scripts/check_dataset_integrity.py
```

---

## 🔐 SEGURIDAD DEL PROYECTO

### ¿Qué sucede si los datos se corrompen?

```bash
# 1. Regenerar datasets desde cero (chargers.py, solar_pvlib.py)
python src/dimensionamiento/oe2/disenocargadoresev/chargers.py
python src/dimensionamiento/oe2/generacionsolar/solar_pvlib.py

# 2. Reconstruir y limpiar
python scripts/validate_and_rebuild_oe2.py --cleanup

# 3. Verificar integridad
python scripts/check_dataset_integrity.py
```

---

## 📌 RESUMEN

| Paso | Comando | Propósito |
|------|---------|----------|
| 1 | `python scripts/validate_and_rebuild_oe2.py --cleanup` | Validar datasets y eliminar duplicados |
| 2 | `python scripts/check_dataset_integrity.py` | Verificar que integridad es OK |
| 3 | `python scripts/train/train_sac_multiobjetivo.py` | Entrenar agente (datos limpios) |
| 4 | Monitor | Ver progreso en `checkpoints/SAC/` |

---

**Versión:** 1.0  
**Fecha:** 2026-02-13  
**Estado:** ✅ Producción

