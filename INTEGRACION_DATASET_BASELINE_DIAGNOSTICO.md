# 📋 Diagnóstico: Integración Dataset ↔ Baseline v5.4

**Fecha**: 2026-02-13  
**Estado**: ⚠️ VALIDACIÓN EN PROGRESO

---

## 1. ✅ Qué Está Integrado Correctamente

### Dataset Builder (dataset_builder.py)
- ✅ Carga 5 archivos reales OE2 v5.4:
  - chargers_ev_ano_2024_v3.csv (38 sockets, 353 columnas)
  - bess_simulation_hourly.csv (8,760 horas)
  - demandamallhorakwh.csv (8,760 horas)
  - pv_generation_hourly_citylearn_v2.csv (8,760 horas, 18 columnas)
  - chargers_real_statistics.csv

- ✅ Genera 38 archivos charger_simulation_XXX.csv para CityLearn
- ✅ Crea electric_vehicles_def con especificaciones v5.2 (38 EVs)
- ✅ Integra factores CO₂ OSINERGMIN en schema
- ✅ Genera observables_oe2.csv con variables combinadas
- ✅ Crea schema_pv_bess.json y schema_grid_only.json para comparación
- ✅ Importa clases de rewards (MultiObjectiveWeights, IquitosContext)

### Observable Variables (35 columnas)
- ✅ EV: is_hora_punta, tarifa, energía, costo, CO₂ directo
- ✅ Solar: is_hora_punta, tarifa, ahorro, CO₂ indirecto
- ✅ Totales: reducción CO₂ combinada, costo, ahorro

---

## 2. ⚠️ Problemas Identificados

### Problema 1: BESS Version Mismatch
**Ubicación**: dataset_builder.py líneas 1225-1227  
**Descripción**: Todavía usa v5.2 BESS (940 kWh) en fallback  
**Impact**: Si no encuentra bess_results.json, asigna valores antiguos  
**Solución**: Actualizar a v5.4 (1,700 kWh)

```python
# ACTUAL (INCORRECTO v5.2):
if bess_cap is None or bess_cap == 0.0:
    bess_cap = 940.0  # ← DEBERÍA SER 1,700.0
```

### Problema 2: Sin Integración con Módulos Baseline
**Descripción**: Los módulos creados (baseline_calculator_v2.py, agent_baseline_integration.py) NO están importados ni usados en dataset_builder.py  
**Impact**: 
- No se calcula automáticamente CON_SOLAR (3,059 t CO₂) vs SIN_SOLAR (5,778 t CO₂)
- No hay conexión automática baseline → observables → training

**Solución Requerida**:
```python
# Agregar en imports:
from src.baseline.baseline_calculator_v2 import BaselineCalculator
from src.baseline.citylearn_baseline_integration import BaselineCityLearnIntegration

# Agregar en build_citylearn_dataset():
baseline_integration = BaselineCityLearnIntegration(output_dir=out_dir)
baselines = baseline_integration.compute_baselines()
```

### Problema 3: Observables No Usan Datos BESS Completos
**Descripción**: observables_oe2.csv no incluye variables de BESS (SOC, carga, descarga)  
**Impact**: Agentes no ven estado BESS en observaciones  
**Solución**: Agregar columnas BESS a _extract_observable_variables()

---

## 3. 📊 Datos Integrando (Verificación)

### Chargers Dataset (chargers_ev_ano_2024_v3.csv)
```
Filas: 8,760 (8,760 ✅)
Columnas: 353 (38 sockets × 9 features + time)
  - socket_XXX_is_occupied: bool
  - socket_XXX_soc_percent: 0-100
  - socket_XXX_power_kwh: float
  - socket_XXX_connected_duration_hours: int
  - socket_XXX_vehicle_type: [MOTO|MOTOTAXI]
  + 4 más...

Energía anual: summa(ev_demand_kwh) = 412,236 kWh ✅
Potencia instalada: 38 sockets × 7.4 kW = 281.2 kW ✅
```

### BESS Dataset (bess_simulation_hourly.csv)
```
Filas: 8,760 (8,760 ✅)
Columnas: 12 (energía + SOC + carga/descarga)
  - pv_generation_kwh: sum = 8,292,514 kWh ✅
  - ev_demand_kwh: sum = 412,236 kWh ✅
  - mall_demand_kwh: sum = 12,368,653 kWh ✅
  - bess_soc_percent: 0-100
  - bess_charge_kwh: carga horaria
  - bess_discharge_kwh: descarga horaria
  
Capacidad BESS: 1,700 kWh (desde config, NO en CSV)
Potencia BESS: 400 kW (desde config, NO en CSV)
```

### Solar Dataset (pv_generation_hourly_citylearn_v2.csv)
```
Filas: 8,760 (8,760 ✅)
Columnas: 18 (características PVGIS + energy)
  - ghi_wm2, dni_wm2, dhi_wm2 (radiación)
  - temp_air_c, wind_speed_ms (condiciones)
  - dc_power_kw, ac_power_kw (potencias)
  - pv_generation_kwh: sum = 8,292,514 kWh ✅

Validada hourly (no 15-min) ✅
```

### Mall Demand (demandamallhorakwh.csv)
```
Filas: 8,760 (8,760 ✅)
Columnas: 2 (timestamp + demand_kwh)
  - demand_kwh: sum = 12,368,653 kWh ✅
  
Perfil horario: ~0.5 MW promedio, picos 1.5 MW
```

---

## 4. 📦 Pipeline Actual vs Requerida

### Pipeline Actual
```
data/oe2/ (5 archivos reales)
    ↓ [dataset_builder.py _load_oe2_artifacts()]
artifacts dict
    ↓ [build_citylearn_dataset()]
observables_oe2.csv + 38 charger_simulation_XXX.csv + schema.json
    ↓ [CityLearn v2 Environment]
Observations (sin baseline)
    ↓ [RL Agents: SAC/PPO/A2C]
Training (sin referencia baseline)
```

### Pipeline Requerida
```
data/oe2/ (5 archivos reales) ──────────────────────╮
    ↓ [dataset_builder.py + baseline integration]   │
    ├─→ artifacts dict                               │
    │       ↓ [build_citylearn_dataset()]            │
    │   observables_oe2.csv + schema.json            │
    │                                                  │
    └──→ baselines (CON_SOLAR, SIN_SOLAR)           ├→ Schema mejorado
            ↓ [BaselineCalculator]                    │
        baseline_con_solar.json                      │
        baseline_sin_solar.json                      │
        baseline_comparison.csv                      │
            ↓ [schema["baselines"]]  ───────────────╯
        
        ↓
Observations + Baselines (en schema)
    ↓
CityLearn v2 Environment
    ↓
Observations (con referencia a baseline)
    ↓
RL Agents + AgentBaselineIntegration
    ↓
Training con comparación automática vs baselines
```

---

## 5. 🔧 Cambios Requeridos

### 5.1 Actualizar BESS a v5.4
**Archivo**: [dataset_builder.py](dataset_builder.py#L1225-L1230)

```python
# CAMBIAR DE:
if bess_cap is None or bess_cap == 0.0:
    bess_cap = 940.0   # v5.2
    bess_pow = 342.0   # v5.2

# CAMBIAR A:
if bess_cap is None or bess_cap == 0.0:
    bess_cap = 1700.0  # ✅ v5.4
    bess_pow = 400.0   # ✅ v5.4
    logger.warning("[EMBEDDED-FIX] BESS capacity corregido a OE2 v5.4: 1700.0 kWh / 400.0 kW")
```

### 5.2 Importar Módulos Baseline
**Archivo**: [dataset_builder.py](dataset_builder.py#L60-L70)

```python
# Agregar después de imports existentes:
try:
    from src.baseline.baseline_calculator_v2 import BaselineCalculator
    from src.baseline.citylearn_baseline_integration import BaselineCityLearnIntegration
    BASELINE_AVAILABLE = True
    logger.info("[BASELINE] Successfully imported baseline modules")
except (ImportError, ModuleNotFoundError) as e:
    logger.warning("[BASELINE] Baseline modules not available: %s", e)
    BASELINE_AVAILABLE = False
```

### 5.3 Integrar Cálculo Baseline en build_citylearn_dataset()
**Ubicación**: Antes de return statement (próximo a línea 2200)

```python
# === INTEGRACIÓN: Calcular y guardar baselines ===
if BASELINE_AVAILABLE:
    logger.info("")
    logger.info("=" * 80)
    logger.info("[BASELINE INTEGRATION] Calculando baselines CON_SOLAR y SIN_SOLAR...")
    logger.info("=" * 80)
    
    try:
        baseline_integration = BaselineCityLearnIntegration(output_dir=out_dir)
        baselines = baseline_integration.compute_baselines()
        baseline_integration.save_baselines(baselines)
        baseline_integration.print_summary()
        
        # Agregar referencias baseline al schema
        schema["baselines"] = {
            "con_solar": baselines.get("con_solar", {}),
            "sin_solar": baselines.get("sin_solar", {}),
        }
        
        logger.info("[BASELINE INTEGRATION] ✅ Baselines integrados al schema")
    except Exception as e:
        logger.error("[BASELINE INTEGRATION] ❌ Error: %s", e)
else:
    logger.warning("[BASELINE INTEGRATION] Baseline modules no disponibles, skip")
```

### 5.4 Agregar BESS Observables a _extract_observable_variables()
**Ubicación**: [dataset_builder.py](dataset_builder.py#L379-L500)

```python
def _extract_observable_variables(...):
    # ... código existente ...
    
    # =========================================================================
    # EXTRAER VARIABLES DE BESS (prefijo "bess_")
    # =========================================================================
    if bess_df is not None:  # ← Parámetro nuevo
        obs_df['bess_soc_percent'] = bess_df.get('bess_soc_percent', 50)
        obs_df['bess_charge_kwh'] = bess_df.get('bess_charge_kwh', 0)
        obs_df['bess_discharge_kwh'] = bess_df.get('bess_discharge_kwh', 0)
        obs_df['bess_available_capacity_kwh'] = 1700.0 - obs_df['bess_soc_percent']/100 * 1700.0
    else:
        obs_df['bess_soc_percent'] = 50.0
        obs_df['bess_charge_kwh'] = 0.0
        obs_df['bess_discharge_kwh'] = 0.0
        obs_df['bess_available_capacity_kwh'] = 850.0  # 50% of 1700 kWh
```

---

## 6. ✅ Validaciones a Ejecutar Después

```bash
# 1. Verificar dataset se genera con BESS v5.4
python -c "
import json
with open('outputs/citylearnv2_dataset_v5_4/citylearn/dataset_oe3/schema.json') as f:
    schema = json.load(f)
    bess = schema['buildings']['Mall_Iquitos']['electrical_storage']
    print(f'BESS: {bess.get(\"capacity\")} kWh')
    assert bess['capacity'] == 1700.0, 'BESS debe ser 1,700 kWh v5.4'
print('✅ BESS v5.4 verificado (1,700 kWh)')
"

# 2. Verificar baselines en schema
python -c "
import json
with open('outputs/citylearnv2_dataset_v5_4/citylearn/dataset_oe3/schema.json') as f:
    schema = json.load(f)
    assert 'baselines' in schema, 'Schema debe tener baselines'
    assert 'con_solar' in schema['baselines']
    assert 'sin_solar' in schema['baselines']
print('✅ Baselines integrados en schema')
"

# 3. Verificar observables contiene todas columnas
python -c "
import pandas as pd
obs = pd.read_csv('outputs/citylearnv2_dataset_v5_4/citylearn/dataset_oe3/observables_oe2.csv')
required_cols = ['ev_energia_total_kwh', 'solar_reduccion_indirecta_co2_kg', 'total_reduccion_co2_kg', 'bess_soc_percent']
for col in required_cols:
    assert col in obs.columns, f'Falta columna {col}'
print(f'✅ Observables v5.3: {obs.shape[1]} columnas, todas presentes')
"
```

---

## 7. 📈 Resultado Esperado Después de Cambios

```
DATASET INTEGRATION v5.4 ✅
├─ BESS: 1,700 kWh / 400 kW (ACTUALIZADO v5.4)
├─ Chargers: 38 sockets (19×2), 281.2 kW
├─ Solar: 4,050 kWp, 8,292,514 kWh/año
├─ Baselines integrados:
│  ├─ CON_SOLAR: 3,059 t CO₂/año
│  └─ SIN_SOLAR: 5,778 t CO₂/año
├─ Observables v5.3: 40+ columnas
│  ├─ EV: energía, costo, CO₂ directo
│  ├─ Solar: ahorro, CO₂ indirecto
│  ├─ BESS: SOC, carga, descarga
│  └─ Totales: reducción CO₂ combinada
└─ Schema con references a baselines

LISTO PARA:
✅ CityLearn v2 entrenamiento
✅ RL Agents con baseline tracking
✅ Comparación automática CON_SOLAR vs SIN_SOLAR
✅ Métricas de mejora (% CO₂ reduction vs baselines)
```

---

## 8. 🔗 Referencias Relacionadas

- [baseline_calculator_v2.py](src/baseline/baseline_calculator_v2.py) - Calculador de baselines
- [agent_baseline_integration.py](src/baseline/agent_baseline_integration.py) - Integración con agentes
- [BASELINE_INTEGRATION_v54_README.md](src/baseline/BASELINE_INTEGRATION_v54_README.md) - Documentación completa
- [test_baseline_integration_v54.py](test_baseline_integration_v54.py) - Suite de pruebas

---

**Estado**: ⏳ PENDIENTE IMPLEMENTACIÓN DE CAMBIOS  
**Estimado**: 30-45 minutos
