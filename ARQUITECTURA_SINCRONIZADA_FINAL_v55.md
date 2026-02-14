# ARQUITECTURA SINCRONIZADA FINAL - Entrenamientos v5.5
**ESTADO:** 🟢 DISEÑO COMPLETO - LISTO PARA IMPLEMENTAR  
**FECHA:** 2026-02-13  
**VERSIÓN:** 5.5 (Con sincronización de constructor integrado)

---

## 🏗️ FLUJO DE ARQUITECTURA DESPUÉS DE SINCRONIZACIÓN

```
DATA SOURCES (source of truth)
├── data/oe2/Generacionsolar/pv_generation_citylearn2024.csv
├── data/oe2/bess/bess_ano_2024.csv
├── data/oe2/chargers/chargers_ev_ano_2024_v3.csv
└── data/oe2/demandamallkwh/demandamallhorakwh.csv

         │
         ▼
    
DATA LOADER (data_loader.py) ◄─── Define funciones de carga PRINCIPALES
├── load_solar_data()       ✅ 
├── load_bess_data()        ✅
├── load_chargers_data()    ✅
├── load_mall_demand_data() ✅
└── validate_oe2_complete() ✅

         │
         ▼
    
INTEGRATED DATASET BUILDER (NEW - integrated_dataset_builder.py)
├── [PASO 1] Validar integridad OE2
│   └── Usa: validate_oe2_complete() de data_loader
│
├── [PASO 2] Cargar datos usando data_loader
│   ├── load_solar_data()          ← SAC, PPO, A2C SINCRONIZADOS
│   ├── load_bess_data()           ← SAC, PPO, A2C SINCRONIZADOS
│   ├── load_chargers_data()       ← SAC, PPO, A2C SINCRONIZADOS
│   └── load_mall_demand_data()    ← SAC, PPO, A2C SINCRONIZADOS
│
├── [PASO 3] Crear contexto Iquitos
│   └── IquitosContext() + create_iquitos_reward_weights()
│
├── [PASO 4] Extraer observables sincronizadas
│   ├── CO2 DIRECTO (from chargers):
│   │   ├── ev_energia_motos_kwh
│   │   ├── ev_energia_mototaxis_kwh
│   │   ├── ev_co2_reduccion_motos_kg        (0.87 factor)
│   │   ├── ev_co2_reduccion_mototaxis_kg    (0.47 factor)
│   │   └── ev_reduccion_directa_co2_kg      (TOTAL)
│   │
│   └── CO2 INDIRECTO (from solar):
│       ├── solar_reduccion_indirecta_co2_kg (0.4521 factor)
│       ├── solar_co2_mall_kg                (67% asignado)
│       └── solar_co2_ev_kg                  (33% asignado)
│
├── [PASO 5] Integrar baselines CON_SOLAR / SIN_SOLAR
│   └── BaselineCalculator() integrado
│
└── [SALIDA] Dataset SINCRONIZADO:
    ├── solar              np.ndarray (8760,)
    ├── chargers           pd.DataFrame (8760, 38+)
    ├── mall               np.ndarray (8760,)
    ├── bess               BESSData
    ├── context            IquitosContext
    ├── observables_df     pd.DataFrame (8760, 31)  ◄─ CO2 TRACKING COMPLETO
    ├── validation         dict
    └── baselines          dict (CON_SOLAR, SIN_SOLAR)

         │
         ▼
    
RL AGENTS (SAC, PPO, A2C) - TODOS SINCRONIZADOS
│
├── SAC (train_sac_multiobjetivo.py)
│   ├── Importa: build_integrated_dataset()
│   ├── Env: RealOE2Environment
│   ├── Usa observables: ✅ ev_reduccion_directa_co2_kg
│   │                    ✅ solar_reduccion_indirecta_co2_kg
│   ├── Usa baselines: ✅ baseline_con_solar, baseline_sin_solar
│   └── Metrics: CO2, solar, EV, cost, stability
│
├── PPO (train_ppo_multiobjetivo.py)
│   ├── Importa: build_integrated_dataset()
│   ├── Env: CityLearnEnvironment
│   ├── Usa observables: ✅ ev_reduccion_directa_co2_kg
│   │                    ✅ solar_reduccion_indirecta_co2_kg
│   ├── Usa baselines: ✅ baseline_con_solar, baseline_sin_solar
│   └── Metrics: CO2, solar, EV, cost, stability
│
└── A2C (train_a2c_multiobjetivo.py)
    ├── Importa: build_integrated_dataset()
    ├── Env: CityLearnEnvironment
    ├── Usa observables: ✅ ev_reduccion_directa_co2_kg
    │                    ✅ solar_reduccion_indirecta_co2_kg
    ├── Usa baselines: ✅ baseline_con_solar, baseline_sin_solar
    └── Metrics: CO2, solar, EV, cost, stability

         │
         ▼

OUTPUTS y RESULTADOS
├── Checkpoints: checkpoints/{SAC,PPO,A2C}/
├── Metrics CSV: reports/oe3/training_metrics_{agent}.csv
├── CO2 Tracking: reports/oe3/co2_reduction_{agent}.csv
├── Baseline Comparison: outputs/baselines/{with_solar,without_solar}/
└── Agent Comparison: reports/oe3/agents_comparison_v55.csv
```

---

## 📊 VARIABLES OBSERVABLES - COMPLETE LIST (31 columnas)

### EV Observables (10 columnas - CO2 DIRECTO)
```python
CHARGERS_OBSERVABLE_COLS = [
    'ev_is_hora_punta',              # Hour peak indicator
    'ev_tarifa_aplicada_soles',      # Applied tariff (HP/HFP)
    'ev_energia_total_kwh',          # Total EV energy
    'ev_costo_carga_soles',          # Total cost
    'ev_energia_motos_kwh',          # Motos energy
    'ev_energia_mototaxis_kwh',      # Mototaxis energy
    'ev_co2_reduccion_motos_kg',     # CO2 avoided motos (0.87 factor)
    'ev_co2_reduccion_mototaxis_kg', # CO2 avoided mototaxis (0.47 factor)
    'ev_reduccion_directa_co2_kg',   # TOTAL DIRECT CO2
    'ev_demand_kwh',                 # EV demand (alias)
]
```

### SOLAR Observables (6 columnas - CO2 INDIRECTO)
```python
SOLAR_OBSERVABLE_COLS = [
    'solar_is_hora_punta',           # Hour peak indicator
    'solar_tarifa_aplicada_soles',   # Applied tariff
    'solar_ahorro_soles',            # Solar savings S/.
    'solar_reduccion_indirecta_co2_kg',  # CO2 avoided solar (0.4521 factor)
    'solar_co2_mall_kg',             # CO2 allocated to mall (67%)
    'solar_co2_ev_kg',               # CO2 allocated to EV (33%)
]
```

### TOTAL/Combined Observables (15 columnas más)
```python
PREFIXED_COLS = [
    # Chargers with prefix 'ev_' (10 + 0 = 10)
    'ev_is_hora_punta',
    'ev_tarifa_aplicada_soles',
    ... (9 more)
    
    # Solar with prefix 'solar_' (6)
    'solar_is_hora_punta',
    'solar_tarifa_aplicada_soles',
    ... (4 more)
    
    # Combined totals (3)
    'total_reduccion_co2_kg',       # total_directa + total_indirecta
    'total_costo_soles',            # EV cost + solar savings
    'total_ahorro_soles',           # Solar savings only
]
```

**TOTAL: 10 + 6 + 15 = 31 columnas sincronizadas en todos los agentes**

---

## ⚙️ INTEGRACION CON DATASET BUILDER

### Antes (Dataset Builder DESCONECTADO):
```python
# dataset_builder.py define observables pero NO las usa
CHARGERS_OBSERVABLE_COLS = [...]  # Definidas pero sin usar
SOLAR_OBSERVABLE_COLS = [...]     # Definidas pero sin usar

# Entrenamientos NO importan dataset_builder
# Pierden tracking de CO2 directo/indirecto
```

### Después (Dataset Builder INTEGRADO):
```python
# integrated_dataset_builder.py IMPORTA dataset_builder
from src.citylearnv2.dataset_builder.dataset_builder import (
    CHARGERS_OBSERVABLE_COLS,
    SOLAR_OBSERVABLE_COLS,
    ALL_OBSERVABLE_COLS,
    FACTOR_CO2_*,  # Todas las constantes CO2
)

# Entrenamientos importan IntegratedDatasetBuilder
from src.citylearnv2.dataset_builder.integrated_dataset_builder import (
    build_integrated_dataset,
)

# RESULTADO: observables extraídas automáticamente
dataset = build_integrated_dataset()
observables = dataset['observables_df']  # Contains all 31 cols
```

---

## 🔄 SINCRONIZACIÓN DE FLUJOS OE2 → OE3

### OE2 (Dimensionamiento) → Output
```
src/dimensionamiento/oe2/
├── disenocargadoresev/
│   ├── chargers.py          → chargers_ev_ano_2024_v3.csv (38 sockets)
│   ├── data_loader.py       → load_solar_data, load_bess_data, etc.
│   └── ...
├── disenobess/
│   └── bess.py              → bess_ano_2024.csv (1,700 kWh)
├── generacionsolar/
│   └── solar_pvlib.py       → pv_generation_citylearn2024.csv (4,050 kWp)
└── demandamallkwh/
    └── mall_demand.py       → demandamallhorakwh.csv
```

### OE3 (Control) → Input
```
src/citylearnv2/dataset_builder/
├── dataset_builder.py       ← Contiene constantes y definiciones
└── integrated_dataset_builder.py  ← NUEVO: Constructor unificado
    └── Llama a:
        └── data_loader.py (source of truth)

scripts/train/
├── train_sac_multiobjetivo.py  → Usa IntegratedDatasetBuilder
├── train_ppo_multiobjetivo.py  → Usa IntegratedDatasetBuilder
└── train_a2c_multiobjetivo.py  → Usa IntegratedDatasetBuilder
```

### Flujo Centralizado
```
[OE2] → data_loader (load functions)
    ↓
[OE3-Dataset] → integrated_dataset_builder (construction + validation)
    ↓
[OE3-Agents] → SAC, PPO, A2C (training)
    ↓
[Results] → metrics, checkpoints, comparisons
```

---

## ✅ VALIDACIÓN DE SINCRONIZACIÓN

Para verificar que todo está conectado correctamente:

### 1. Importaciones Correctas
```python
# Todos deben poder hacer:
from src.citylearnv2.dataset_builder.integrated_dataset_builder import build_integrated_dataset
dataset = build_integrated_dataset()
```

### 2. Observables Extraidas
```python
observables = dataset['observables_df']
assert observables.shape == (8760, 31), f"Expected 31 cols, got {observables.shape[1]}"
assert 'ev_reduccion_directa_co2_kg' in observables.columns
assert 'solar_reduccion_indirecta_co2_kg' in observables.columns
```

### 3. Baselines Available
```python
baselines = dataset['baselines']
assert 'con_solar' in baselines
assert 'sin_solar' in baselines
```

### 4. Validación OE2 Completa
```python
validation = dataset['validation']
assert validation['all_valid'] == True, f"OE2 validation failed: {validation['errors']}"
```

### 5. Test Equal Output
```bash
# Los 3 agentes deben mostrar igual output inicialmente:
python scripts/train/train_sac_multiobjetivo.py --test-load-only
python scripts/train/train_ppo_multiobjetivo.py --test-load-only
python scripts/train/train_a2c_multiobjetivo.py --test-load-only

# Todos deberían mostrar:
# [INTEGRATED BUILDER] Inicializando...
# [PASO 1] Validar integridad OE2... ✅
# [PASO 2] Cargar datos desde data_loader... ✅
# [PASO 3] Crear contexto Iquitos... ✅
# [PASO 4] Extraer variables observables... ✅ (31 cols)
# [PASO 5] Calcular baselines... ✅
```

---

## 📋 ESTADO DE IMPLEMENTACION

### ✅ COMPLETADO
- [x] Análisis de inconsistencias detallado
- [x] Constructor integrado (integrated_dataset_builder.py)
- [x] Documentación de integración
- [x] Auditoria de consistencia script

### 🟡 PENDIENTE (Requiere cambios en 3 archivos de entrenamiento)
- [ ] Actualizar train_sac_multiobjetivo.py
  - Reemplazar `load_datasets_from_processed()` con `build_integrated_dataset()`
  - Extraer observables
  - Integrar baselines

- [ ] Actualizar train_ppo_multiobjetivo.py
  - Reemplazar `validate_oe2_datasets()` con `build_integrated_dataset()`
  - Extraer observables
  - Integrar baselines

- [ ] Actualizar train_a2c_multiobjetivo.py
  - Reemplazar `build_oe2_dataset()` con `build_integrated_dataset()`
  - Extraer observables
  - Integrar baselines

### 🟢 VALIDACIÓN (Después de cambios)
- [ ] Ejecutar audit_training_dataset_consistency.py
- [ ] Verificar 3 agentes mostran mismo output inicial
- [ ] Validar observables (31 cols en los 3)
- [ ] Comparar baselines (CON_SOLAR, SIN_SOLAR)

---

## 📊 IMPACTO ESPERADO DESPUÉS DE SINCRONIZACIÓN

### CO2 Tracking
```
ANTES (Sin sincronización):
  - cada agente calcula CO2 diferente
  - No hay observables de dataset
  - Baselines desvinculados
  
DESPUÉS (Sincronizado):
  ✅ CO2 directo (EVs):    ~357 ton/año (Todos los agentes same value)
  ✅ CO2 indirecto (Solar): ~3,749 ton/año (Todos los agentes same value)
  ✅ Total combinado:       ~4,106 ton/año (Verificable cross-agents)
```

### Comparabilidad entre Agentes
```
ANTES:
  SAC vs PPO vs A2C → Resultados incomparables (diferentes datasets)
  
DESPUÉS:
  SAC vs PPO vs A2C → Comparables directamente
  "PPO reducción: 25% vs SAC reducción: 23%" → VÁLIDO
```

### Mantenibilidad
```
ANTES:
  3 funciones diferentes × 3 archivos = 9 puntos de mantención
  
DESPUÉS:
  1 constructor (IntegratedDatasetBuilder) = 1 punto de mantención
  Cambios a data_loader afectan automáticamente a todos los 3 agentes
```

---

## 🎯 PRÓXIMOS PASOS

1. **Implementar cambios** en los 3 entrenamientos (2-3 horas)
   - Seguir GUIA_INTEGRACION_ENTRENAMIENTOS_v55.md
   
2. **Testing** (30 minutos)
   - Ejecutar `--test-load-only` en los 3
   - Verificar observables extraídas
   
3. **Validación** (15 minutos)
   - Ejecutar audit_training_dataset_consistency.py
   - Verificar sincronización
   
4. **Entrenamiento inicial** (6-8 horas total)
   - Train SAC (4-5h), PPO (3-4h), A2C (2-3h)
   - Comparar resultados

---

