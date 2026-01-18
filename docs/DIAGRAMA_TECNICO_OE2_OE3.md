# 📐 DIAGRAMA TÉCNICO: TRANSFORMACIÓN DE DATOS OE2 → OE3

## Flujo Completo de Pipeline

```text
┌─────────────────────────────────────────────────────────────────────┐
│                    RUN_PIPELINE.PY (ORQUESTADOR)                   │
│                  (secuencia: OE2 → OE3 validado)                   │
└────────────────────────────┬────────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
    ┌────────────┐    ┌─────────────┐    ┌──────────────┐
    │ OE2_SOLAR  │    │OE2_CHARGERS │    │  OE2_BESS    │
    │  (pvlib)   │    │  (profiles) │    │   (timeseries)
    └──────┬─────┘    └──────┬──────┘    └───────┬──────┘
           │                 │                   │
     ┌─────▼─────┐    ┌──────▼──────┐    ┌──────▼───────┐
     │ 8760 rows │    │ 128 × 8760  │    │ 1 × 8760     │
     │ (hourly)  │    │   (chargers)│    │  (SOC)       │
     └─────┬─────┘    └──────┬──────┘    └──────┬───────┘
           │                 │                   │
      data/interim/oe2/solar/
      ├─ pv_generation_timeseries.csv (8760 kW)
      ├─ pv_profile_24h.csv
      └─ solar_results.json (4162 kWp, 8.042 GWh/año)
      
      data/interim/oe2/chargers/
      ?? charger_MOTO_CH_001.csv ... (112)
      ?? charger_MOTO_TAXI_CH_113.csv ... (16)
      ?? perfil_horario_carga.csv (perfil agregado diario)
      ?? demand_scenarios.csv (80/100/120% demanda diaria)
      ?? chargers_results.json (128 cargadores, 272 kW)
      
      data/interim/oe2/bess/
      ├─ bess_soc_timeseries.csv
      └─ bess_results.json (2000 kWh)

           │
           │ (todos los OE2 completados)
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│          RUN_OE3_BUILD_DATASET.PY (CONSTRUCCIÓN)        │
│         (transformación OE2 → CityLearn format)          │
└──────────────────────┬───────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
   ┌────────┐   ┌──────────┐   ┌────────────┐
   │LOAD    │   │LOAD      │   │TRANSFORM   │
   │OE2     │   │TEMPLATE  │   │DATA        │
   │ARTIFACTS   CITYLEARN  │   │            │
   └───┬────┘   └────┬─────┘   └────┬───────┘
       │             │              │
       │       ┌─────▼─────┐        │
       │       │ citylearn │        │
       │       │_challenge_│        │
       │       │_2022_phase│        │
       │       │_all_plus_ │        │
       │       │evs        │        │
       │       │           │        │
       │       │- 8 EVs    │        │
       │       │- Template │        │
       │       │  schema   │        │
       └───────┼───────────┤        │
               │           │        │
               └─────┬─────┘        │
                     │              │
                     ▼              │
         ┌───────────────────┐      │
         │ CREATE "Mall_     │◄─────┘
         │ Iquitos" BUILDING │
         │                   │
         │ - 128 Chargers    │
         │ - 4162 kWp solar  │
         │ - 2000 kWh BESS   │
         │ - 12.4 GWh demand │
         └───────────┬───────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
    SOLAR      CHARGERS      BESS
    transform  aggregation   parameters
    
    pv_generation_timeseries.csv  charger_MOTO_CH_001.csv  bess
    (8760 kW)                      ├─ charger_MOTO_CH_002.csv  │
         │                         ├─ ... (112 motos)         │
         │                         ├─ charger_MOTO_TAXI_...  │
         │                         └─ (16 taxis, 8760 c/u) │
         │                         │
         ▼                         ▼
    Scale 1000×                 Copy to dataset
    (W → Wh in CityLearn)
         │                         │
         └─────────────────┬───────┘
                           │
                           ▼
           ┌───────────────────────────┐
           │ GENERATE TWO SCHEMAS      │
           │                           │
           │ 1) schema_grid_only.json  │  (Baseline)
           │    - No solar (0 kWp)     │
           │    - No BESS (0 kWh)      │
           │    - Grid solo            │
           │                           │
           │ 2) schema_pv_bess.json    │  (Full system)
           │    - Solar: 4162 kWp      │
           │    - BESS: 2000 kWh       │
           │    - Grid + renewables    │
           └───┬──────────────────┬────┘
               │                  │
               ▼                  ▼
    Comparar:              Comparar:
    - Sin control          - Con RL
    - Uncontrolled         - SAC, PPO, A2C
    - Baseline             - Optimizado
```

---

## 🏗️ Estructura OE2 → OE3

```text
DATA/INTERIM/OE2/
├─ solar/
│  ├─ pv_generation_timeseries.csv ─┐
│  ├─ pv_profile_24h.csv           │
│  ├─ solar_results.json           │
│  └─ solar_schema_params.json     │
│                                   │
├─ chargers/                        │
│  ├─ charger_MOTO_CH_001.csv ──┐  │
│  ├─ charger_MOTO_CH_002.csv   │  │
│  ├─ ...                        │  │ CONSOLIDAR EN
│  ├─ charger_MOTO_CH_112.csv   │  │ DATASET
│  ├─ charger_MOTO_TAXI_...──┐  │  │ CITYLEARN
│  ├─ ...                    │  │  │
│  ├─ charger_MOTO_TAXI_...  │  │  │
│  ├─ chargers_results.json  │  │  │
│  └─ perfil_horario_carga   │  │  │
│                             │  │  │
├─ bess/                      │  │  │
│  ├─ bess_soc_timeseries ────┘  │  │
│  └─ bess_results.json       ────┘
│                                   │
└─ citylearn/                       │ (intermediate)
   ├─ solar_generation.csv ────────┘
   ├─ charger_*.csv (128)
   └─ carbon_intensity.csv

                    │
                    │ (procesamiento)
                    ▼

DATA/PROCESSED/CITYLEARN/IQUITOS_EV_MALL/ ← DATASET FINAL
├─ schema_grid_only.json ─────────── Baseline
├─ schema_pv_bess.json ────────────── Full system
├─ Building_1.csv ─────────────────── 12.4 GWh/año demand
├─ solar_generation.csv ───────────── 8760 × 1927 kWh (avg)
├─ carbon_intensity.csv ───────────── 8760 × 0.4521 kg/kWh
├─ charger_MOTO_CH_001.csv ────────┐
├─ charger_MOTO_CH_002.csv        ├─ 128 charger profiles
├─ ...                            │
└─ charger_MOTO_TAXI_CH_128.csv ──┘
```

---

## 📊 Transformación de Datos en Detalle

### 1. Solar Generation Transformation

```text
INPUT: pv_generation_timeseries.csv (OE2)
────────────────────────────────────
timestamp,ac_power_kw
2024-01-01 00:00:00,0.0
2024-01-01 01:00:00,0.0
...
2024-01-01 12:00:00,1856.3
...
2024-12-31 23:00:00,0.0

SUM = 8,042,399 kWh


TRANSFORMATION: W → Wh (CityLearn format)
────────────────────────────────────
Multiply each value by 1000:

0.0 kW × 1000 = 0 Wh
1856.3 kW × 1000 = 1,856,300 Wh
...


OUTPUT: solar_generation.csv (OE3)
────────────────────────────────────
(column vector, 8760 rows)

0, 0, 0, ..., 1856300, 1998500, ..., 0

SUM = 8,042,399,000 Wh = 8,042,399 kWh ✓ (verificado)
```

### 2. Charger Profiles Handling

```text
INPUT: charger_MOTO_CH_001.csv to charger_MOTO_TAXI_CH_128.csv (128 archivos)
──────────────────────────────────────────────────────────────

charger_MOTO_CH_001.csv
timestamp,power_kw,energy_kwh
2024-01-01 00:00:00,0.0,0.0
...
2024-01-01 18:30:00,2.0,2.0
2024-01-01 19:00:00,0.0,0.0
...
2024-12-31 23:00:00,0.0,0.0
(8760 o 8761 registros)


VALIDATION & ADJUSTMENT:
──────────────────────────
if len(df) == 8761:          # Bug pvlib: extra registro
    df = df.iloc[:8760]      # Remover último
    log: "[DEBUG FALLBACK] charger_id: ajustado a 8760"

assert len(df) == 8760 ✓
assert df['power_kw'].min() >= 0 ✓
assert df['power_kw'].max() <= 3.0 ✓


COPY TO DATASET:
──────────────────────────
data/processed/citylearn/iquitos_ev_mall/charger_MOTO_CH_001.csv
data/processed/citylearn/iquitos_ev_mall/charger_MOTO_CH_002.csv
...
data/processed/citylearn/iquitos_ev_mall/charger_MOTO_TAXI_CH_128.csv

(128 archivos, 8760 registros c/u = 1.1 millones de timesteps)
```

### 3. Carbon Intensity Constant

```text
INPUT: Configuration
─────────────────
oe3:
  grid:
    carbon_intensity_kg_per_kwh: 0.4521  # Red térmica aislada Iquitos


GENERATION:
────────────
Generar 8760 valores idénticos (red aislada = constante 24/7)


OUTPUT: carbon_intensity.csv
────────────────────────────
0.4521, 0.4521, 0.4521, ..., 0.4521  (8760 values)
```

---

## 🏢 Edificio Unificado vs. Edificios Separados

### Anterior (Documentación Antigua): 2 Playas Separadas

```json
{
  "buildings": {
    "Playa_Motos": {
      "properties": {
        "solar": {"nominal_power": 3641.8},      // 87.5% de 4162
        "energy_storage": {"capacity": 1750},     // 87.5% de 2000
        "electric_vehicle": [
          {"name": "EV_0", "definition_file": "charger_MOTO_CH_001.csv"},
          ...
          {"name": "EV_111", "definition_file": "charger_MOTO_CH_112.csv"}
        ]
      }
    },
    "Playa_Mototaxis": {
      "properties": {
        "solar": {"nominal_power": 520.2},       // 12.5% de 4162
        "energy_storage": {"capacity": 250},     // 12.5% de 2000
        "electric_vehicle": [
          {"name": "EV_112", "definition_file": "charger_MOTO_TAXI_CH_113.csv"},
          ...
          {"name": "EV_127", "definition_file": "charger_MOTO_TAXI_CH_128.csv"}
        ]
      }
    }
  }
}
```

**Ventajas**: Granularidad, análisis separado por tipo vehículo.
**Desventajas**: Complejidad, 2 esquemas paralelos a mantener.

---

### ACTUAL (Simplificado 14 Enero 2026): 1 Edificio Unificado

```json
{
  "buildings": {
    "Mall_Iquitos": {
      "properties": {
        "solar": {
          "nominal_power": 4162.0,
          "solar_generation_file": "solar_generation.csv"
        },
        "energy_storage": [
          {
            "capacity": 2000.0,
            "max_output_power": 1200.0,
            "efficiency_battery": 0.95
          }
        ],
        "electric_vehicle": [
          {"name": "EV_Charger_0", "definition_file": "charger_MOTO_CH_001.csv"},
          {"name": "EV_Charger_1", "definition_file": "charger_MOTO_CH_002.csv"},
          ...
          {"name": "EV_Charger_111", "definition_file": "charger_MOTO_CH_112.csv"},
          {"name": "EV_Charger_112", "definition_file": "charger_MOTO_TAXI_CH_113.csv"},
          ...
          {"name": "EV_Charger_127", "definition_file": "charger_MOTO_TAXI_CH_128.csv"}
        ]
      }
    }
  }
}
```

**Ventajas**: Simplicidad, un solo edificio, evaluación de todo el sistema conjunto.
**Cambio justificado**: Los 128 cargadores están en el mismo sitio (Mall) → un edificio es más realista.

---

## 🎯 Dos Schemas para Comparación

### Schema 1: grid_only.json (Baseline - Sin Renovables)

```json
{
  "buildings": {
    "Mall_Iquitos": {
      "properties": {
        "solar": {
          "nominal_power": 0.0,              // ✓ SIN SOLAR
          "solar_generation_file": "solar_generation_zero.csv"
        },
        "energy_storage": [
          {
            "capacity": 0.0,                 // ✓ SIN BESS
            "max_output_power": 0.0
          }
        ]
      }
    }
  }
}
```

**Propósito**: Línea base pura red, sin optimización RL.  
**Resultado esperado**: Todas las emisiones de la red térmica (0.4521 kg CO₂/kWh).

### Schema 2: schema_pv_bess.json (Full System - Con Renovables + RL)

```json
{
  "buildings": {
    "Mall_Iquitos": {
      "properties": {
        "solar": {
          "nominal_power": 4162.0,           // ✓ 4.162 MWp instalado
          "solar_generation_file": "solar_generation.csv"
        },
        "energy_storage": [
          {
            "capacity": 2000.0,              // ✓ 2000 kWh BESS
            "max_output_power": 1200.0,      // ✓ 1200 kW max descarga
            "efficiency_battery": 0.95       // ✓ 95% ida y vuelta
          }
        ]
      }
    }
  }
}
```

**Propósito**: Sistema optimizado con RL (SAC, PPO, A2C).  
**Resultado esperado**: 65-70% reducción CO₂ vs baseline.

---

## 📈 Validación de Integridad del Dataset

```bash
POST-BUILD CHECKS (automático):
────────────────────────────────

✓ 128 archivos charger = 128 × 8760 = 1,128,960 timesteps
✓ schema_grid_only.json valid JSON
✓ schema_pv_bess.json valid JSON
✓ solar_generation.csv: 8760 registros, suma = 8.042 GWh
✓ carbon_intensity.csv: 8760 registros, todos = 0.4521
✓ Cada charger: 8760 registros, power_kw ∈ [0, 3]
✓ Building_1.csv: 12,368,653 kWh total = demand anual
```

---

## 🚀 Ejecución Paso a Paso

```bash
# Terminal 1: Ver logs en vivo
cd d:\diseñopvbesscar
.venv\Scripts\python -m scripts.run_pipeline --config configs/default.yaml 2>&1|tee pipeline.log

# Terminal 2: Monitorear checkpoints (cada 5s)
cd d:\diseñopvbesscar
.venv\Scripts\python monitor_checkpoints.py
```

**Tiempo estimado**:

- OE2: 10-15 minutos
- OE3 Build Dataset: 1-2 minutos
- OE3 Simulate (SAC 2 episodios): 30-45 minutos
- Total: ~1-2 horas

---

## 📋 Checklist de Validación

- [x] Datos solares: 8760 registros, 8.042 GWh/año
- [x] Cargadores: 128 × 8760 registros
- [x] BESS: 2000 kWh, 1200 kW, DoD 0.8, c-rate 0.6
- [x] Schemas JSON: sintaxis válida
- [x] Dataset CityLearn: estructura compatible
- [x] Entrenamiento RL: SAC, PPO, A2C desde cero (sin checkpoints previos)
- [x] Recompensa multiobjetivo: CO₂ 50% prioridad

---

## Fin de diagrama técnico
