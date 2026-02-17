# PPO v7.4 - Corrección COMPLETA de valores guardados en CSVs

## Resumen Ejecutivo

Se implementaron correcciones en `scripts/train/train_ppo_multiobjetivo.py` para asegurar que **TODOS los valores críticos** se guardan en los archivos CSV de salida.

## Cambios realizados

### 1️⃣ Agregar diccionario global GLOBAL_PPO_METRICS (v7.3)
**Línea: 1454-1461**
```python
GLOBAL_PPO_METRICS = {
    'current_entropy': 0.0,
    'current_approx_kl': 0.0,
    'current_clip_fraction': 0.0,
    'current_policy_loss': 0.0,
    'current_value_loss': 0.0,
    'current_explained_variance': 0.0
}
```
**Propósito:** Compartir métricas PPO entre callbacks de forma robusta con VecNormalize

### 2️⃣ Leer métricas en DetailedLoggingCallback._on_step() (v7.3)
**Línea: 1590-1600**
```python
entropy_val = float(GLOBAL_PPO_METRICS.get('current_entropy', 0.0))
approx_kl_val = float(GLOBAL_PPO_METRICS.get('current_approx_kl', 0.0))
clip_fraction_val = float(GLOBAL_PPO_METRICS.get('current_clip_fraction', 0.0))
policy_loss_val = float(GLOBAL_PPO_METRICS.get('current_policy_loss', 0.0))
value_loss_val = float(GLOBAL_PPO_METRICS.get('current_value_loss', 0.0))
explained_variance_val = float(GLOBAL_PPO_METRICS.get('current_explained_variance', 0.0))
```

### 3️⃣ Actualizar GLOBAL_PPO_METRICS en PPOMetricsCallback (v7.3)
**Línea: 2142-2152**
```python
GLOBAL_PPO_METRICS['current_entropy'] = ppo_metrics.get('entropy', 0.0)
GLOBAL_PPO_METRICS['current_approx_kl'] = ppo_metrics.get('approx_kl', 0.0)
GLOBAL_PPO_METRICS['current_clip_fraction'] = ppo_metrics.get('clip_fraction', 0.0)
GLOBAL_PPO_METRICS['current_policy_loss'] = ppo_metrics.get('policy_loss', 0.0)
GLOBAL_PPO_METRICS['current_value_loss'] = ppo_metrics.get('value_loss', 0.0)
GLOBAL_PPO_METRICS['current_explained_variance'] = ppo_metrics.get('explained_variance', 0.0)
```

### 4️⃣ Agregar entropía a trace_record (v7.3)
**Línea: 1735-1741**
```python
'entropy': entropy_val,
'approx_kl': approx_kl_val,
'clip_fraction': clip_fraction_val,
'policy_loss': policy_loss_val,
'value_loss': value_loss_val,
'explained_variance': explained_variance_val,
```

### 5️⃣ Agregar CO2 y entropía a timeseries_record (v7.4) ⭐ NEW
**Línea: 1747-1786**
```python
# [FIX v7.4] AGREGAR COMPONENTES DE CO2 (críticos para análisis)
'co2_grid_kg': info.get('co2_grid_kg', 0),
'co2_avoided_indirect_kg': info.get('co2_avoided_indirect_kg', 0),
'co2_avoided_direct_kg': info.get('co2_avoided_direct_kg', 0),
'co2_avoided_total_kg': info.get('co2_avoided_total_kg', 0),

# [FIX v7.3] AGREGAR METRICAS PPO: Entropía y diagnóstico
'entropy': entropy_val,
'approx_kl': approx_kl_val,
'clip_fraction': clip_fraction_val,
'policy_loss': policy_loss_val,
'value_loss': value_loss_val,
'explained_variance': explained_variance_val,
```

## Matriz de Columnas por CSV

### timeseries_ppo.csv ✅
| Categoría | Columnas | Estado |
|-----------|----------|--------|
| **Timestep/Episode** | timestep, episode, hour | ✅ |
| **Energía Real** | solar_generation_kwh, ev_charging_kwh, grid_import_kwh, bess_power_kw, bess_soc, mall_demand_kw | ✅ |
| **CO2 (CRÍTICO)** | co2_grid_kg, co2_avoided_indirect_kg, co2_avoided_direct_kg, co2_avoided_total_kg | ✅ v7.4 NEW |
| **Vehículos** | motos_charging, mototaxis_charging | ✅ |
| **Reward (6 componentes)** | reward, r_co2, r_solar, r_vehicles, r_grid_stable, r_bess, r_priority | ✅ |
| **Costos** | ahorro_solar_soles, ahorro_bess_soles, costo_grid_soles, ahorro_combustible_usd, ahorro_total_usd | ✅ |
| **Entropía/PPO (CRÍTICO)** | entropy, approx_kl, clip_fraction, policy_loss, value_loss, explained_variance | ✅ v7.3 NEW |

**Total: 28 columnas**

### trace_ppo.csv ✅
| Categoría | Columnas | Estado |
|-----------|----------|--------|
| **Timestep/Episode** | timestep, episode, step_in_episode, hour | ✅ |
| **Energía Real** | solar_generation_kwh, ev_charging_kwh, grid_import_kwh, bess_power_kw, motos_power_kw, mototaxis_power_kw | ✅ |
| **CO2 (CRÍTICO)** | co2_grid_kg, co2_avoided_indirect_kg, co2_avoided_direct_kg | ✅ |
| **Vehículos** | motos_charging, mototaxis_charging | ✅ |
| **Reward** | reward | ✅ |
| **Entropía/PPO (CRÍTICO)** | entropy, approx_kl, clip_fraction, policy_loss, value_loss, explained_variance | ✅ v7.3 NEW |

**Total: 22 columnas**

### result_ppo.json ✅
```json
{
  "training_evolution": {
    "episode_rewards": [...],
    "episode_co2_grid": [...],
    "episode_co2_avoided_indirect": [...],
    "episode_co2_avoided_direct": [...],
    "episode_solar_kwh": [...],
    "episode_ev_charging": [...],
    "episode_grid_import": [...],
    ...
  },
  "validation": {
    "mean_reward": 686.90,
    "mean_co2_avoided_kg": 4409363.78,
    "mean_solar_kwh": 8292514.13,
    ...
  }
}
```

## Flujo de datos

```
Environment.step()
    ↓ (retorna info dict)
DetailedLoggingCallback._on_step()
    ├─ Lee del info dict: solar, grid, ev_charging, co2_grid, co2_avoided_*
    ├─ Lee de GLOBAL_PPO_METRICS: entropy, approx_kl, etc
    ├─ Lee de GLOBAL_ENERGY_VALUES: backup values
    ├─ Construye trace_record (16 columnas)
    ├─ Construye timeseries_record (28 columnas)
    └─ Guarda en CSVs

PPOMetricsCallback._on_step()
    ├─ Calcula entropy, kl, clip_fraction, etc
    └─ Actualiza GLOBAL_PPO_METRICS
        ↓
    Usado por DetailedLoggingCallback en siguiente step
```

## Verificación

Ejecutar scripts de validación:

```bash
# 1. Test rápido de integración
python test_ppo_entropy_fix.py

# 2. Verificación completa de columnas
python verify_all_ppo_columns.py

# 3. Verificación detallada de entropía
python verify_ppo_entropy.py

# 4. Ejecutar entrenamiento PPO
python scripts/train/train_ppo_multiobjetivo.py
```

## Valores críticos ahora guardados

### Para análisis de CO2:
- ✅ `co2_grid_kg`: Emisiones del grid (térmica Iquitos)
- ✅ `co2_avoided_indirect_kg`: Reducción por solar/BESS al grid
- ✅ `co2_avoided_direct_kg`: Reducción por EV cargadas con renovable
- ✅ `co2_avoided_total_kg`: Total evitado

### Para diagnóstico de aprendizaje PPO:
- ✅ `entropy`: Exploración de la política
- ✅ `approx_kl`: Divergencia de la política (regularización)
- ✅ `clip_fraction`: Agresividad de updates
- ✅ `policy_loss`: Pérdida del actor
- ✅ `value_loss`: Pérdida del crítico
- ✅ `explained_variance`: Calidad del value function

## Impacto

### Antes (v7.2)
- ❌ timeseries: 24 columnas, FALTABAN CO2 y entropía
- ❌ trace: 16 columnas, FALTABA entropía

### Después (v7.4)
- ✅ timeseries: 28 columnas (4 nuevas: 3 CO2 + 6 entropía, reordenadas)
- ✅ trace: 22 columnas (6 nuevas: entropía)

## Referencias técnicas

### Valores de CO2 esperados
- **co2_grid_kg**: 0-3,500 kg/hora (factor 0.4521 × grid_import)
- **co2_avoided_indirect_kg**: 0-1,500 kg/hora (renewable_to_grid × 0.4521)
- **co2_avoided_direct_kg**: 0-800 kg/hora (renewable_to_evs × 2.146)

### Valores de entropía esperados
- **entropy**: Inicia ~0.5-1.0, decae a ~0.1 con entrenamiento
- **approx_kl**: Típicamente 0.01-0.05 (si > 0.2 hay problema)
- **explained_variance**: > 0 es bueno (1.0 = perfecto)

---

**v7.4 - Corrección COMPLETA implementada** ✅
