# 📊 DOCUMENTACIÓN COMPLETA: CONSTRUCCIÓN DE DATASET CITYLEARN

**Última actualización**: 14 Enero 2026  
**Estado**: Entrenamiento en curso con nuevos datos PV (8.042 GWh/año)

---

## 📋 Tabla de Contenidos

1. Pipeline General
2. Fase OE2: Datos Base
3. Fase OE3: Construccion Dataset
4. Estructura de Archivos
5. Dataclasses y Schemas
6. Validaciones
7. Configuracion

---

## 🔄 Pipeline General

```bash
run_pipeline.py (secuencia orquestada)
│
├─ OE2: DIMENSIONAMIENTO TÉCNICO
│  ├─ run_oe2_solar.py          → PV profile anual (pvlib + PVGIS TMY)
│  ├─ run_oe2_chargers.py       → 128 perfiles de cargadores individuales
│  ├─ run_oe1_location.py       → Validación del sitio
│  └─ run_oe2_bess.py           → BESS fijo (2000 kWh, 1200 kW)
│
├─ OE3: DATASET + ENTRENAMIENTO RL
│  ├─ run_oe3_build_dataset.py  → Construcción de dataset CityLearn
│  ├─ run_oe3_simulate.py       → Entrenamiento de agentes RL
│  └─ run_oe3_co2_table.py      → Tabla comparativa final
│
└─ SALIDAS
   ├─ data/interim/oe2/          (artefactos intermedios OE2)
   ├─ data/processed/citylearn/  (dataset CityLearn final)
   └─ outputs/oe3/               (simulaciones, checkpoints, métricas)
```

**Dependencias**: OE2 → OE3. No hay dependencias dentro de OE2 (se pueden ejecutar en paralelo).

---

## 🔆 Fase OE2: Datos Base

### 1. **C?lculo de Demanda Diaria**

```text
Demanda base (escenario recomendado pe=0.9, fc=0.9):
- Sesiones/d?a: 3,061 (2,679 motos + 382 mototaxis)
- Energ?a/d?a: 3,252 kWh
- Energ?a por sesi?n (30 min): 1.063 kWh promedio (motos 2 kW ? 1.0 kWh; mototaxis 3 kW ? 1.5 kWh)
```

1. **Distribución Temporal**

- Horas pico (18:00-22:00): 50% de energía diaria

- Horas valle (22:00-09:00): distribuido

- Generación de 128 perfiles individuales (112 motos + 16 mototaxis)

1. **Validaciones**

- Suma de potencias: 272 kW (112 × 2kW + 16 × 3kW)

- Factor de simultaneidad: ~0.3 (máx 80 kW simultáneo)

#### Salidas (2)

**Ubicación**: `data/interim/oe2/chargers/`

| Archivo | Descripción |
| --------- | ------------- |
| `charger_MOTO_CH_001.csv` | Perfil cargador motos #1 |
| ... | ... (112 totales motos) |
| `charger_MOTO_TAXI_CH_113.csv` | Perfil cargador mototaxi #1 |
| ... | ... (16 totales mototaxis) |
| `chargers_results.json` | Resumen (128 cargadores, 272 kW) |
| `perfil_horario_carga.csv` | Perfil agregado diario |
| `demand_scenarios.csv` | Tres escenarios de demanda (80%, 100%, 120%) |

**Escenarios de demanda (demand_scenarios.csv):**

| Escenario | Sesiones/d?a | Energ?a/d?a (kWh) | Potencia pico (kW) |
|-----------|--------------|--------------------|--------------------|
| Bajo 80% | 2,448.8 | 2,603.336 | 325.417 |
| Base 100% | 3,061.0 | 3,254.170 | 406.771 |
| Alto 120% | 3,673.2 | 3,905.004 | 488.125 |

**Escenarios representativos PE/FC (tomados de 101 variantes):**

| Escenario | Penetración (pe) | Factor Carga (fc) | Cargadores (4 tomas) | Total Tomas | Energía Día (kWh) |
|-----------|------------------|-------------------|----------------------|-------------|--------------------|
| CONSERVADOR | 0.10 | 0.80 | 4 | 16 | 185.6 |
| MEDIANO | 0.55 | 0.60 | 20 | 80 | 765.6 |
| RECOMENDADO* | 0.90 | 0.90 | 32 | 128 | 3,252.0 |
| OPTIMISTA | 0.90 | 0.90 | 32 | 128 | 3,252.0 |
| MÁXIMO | 1.00 | 1.00 | 36 | 144 | 4,013.6 |

| Escenario | Penetraci?n (pe) | Factor Carga (fc) | Cargadores (4 tomas) | Total Tomas | Energ?a D?a (kWh) |
|-----------|------------------|-------------------|----------------------|-------------|--------------------|
| CONSERVADOR | 0.10 | 0.80 | 4 | 16 | 185.6 |
| MEDIANO | 0.55 | 0.60 | 20 | 80 | 765.6 |
| RECOMENDADO* | 0.90 | 0.90 | 32 | 128 | 3,252.0 |
| M?XIMO (N?) | 1.00 | 0.60 | 35 | 140 | 1,392.0 |
| OPTIMISTA (recalc) | 1.00 | 1.00 | 36 | 144 | 4,013.6 |

**Estad?sticas de 101 variantes PE/FC (chargers_results.json):**

| M?trica | M?nimo | M?ximo | Promedio | Mediana | Desv_Std |
|---------|--------|--------|----------|---------|----------|
| M?trica | M?nimo | M?ximo | Promedio | Mediana | Desv_Std |
|---------|--------|--------|----------|---------|----------|
| Cargadores (4 tomas) [unid] | 4.00 | 35.00 | 20.61 | 20.00 | 9.19 |
| Tomas totales [tomas] | 16.00 | 140.00 | 82.46 | 80.00 | 36.76 |
| Sesiones pico 4h [sesiones] | 103.00 | 1030.00 | 593.52 | 566.50 | 272.09 |
| Cargas día total [cargas] | 87.29 | 3,058.96 | 849.83 | 785.62 | 538.12 |
| Energía día [kWh] | 92.80 | 3,252.00 | 903.46 | 835.20 | 572.07 |
| Potencia pico agregada [kW]* | 11.60 | 406.50 | 112.93 | 104.40 | 71.51 |

*Potencia pico agregada = Energ?a d?a ? 0.125 (perfil: 50% de la energ?a en el bloque de 4 horas pico).

**Ejemplo charger_MOTO_CH_001.csv**:

```text
timestamp,power_kw,energy_kwh
2024-01-01 00:00:00,0.0,0.0
2024-01-01 18:30:00,2.0,2.0
2024-01-01 19:00:00,0.0,0.0
...
```

---

### 3. **BESS (run_oe2_bess.py)**

#### Configuración Fija

```yaml
oe2:
  bess:
    fixed_capacity_kwh: 2000
    fixed_power_kw: 1200
    dod: 0.8
    c_rate: 0.6
    efficiency_roundtrip: 0.95
```

#### Proceso (3)

1. **SOC Timeseries** (Estado de Carga horario)

```text
   Modo: Fijo (sin optimización)

- Carga cuando hay exceso solar

- Descarga durante horas pico (18:00-22:00)

- Mantiene SOC mín 20%
   ```

1. **Validaciones**

```text
   DoD (Depth of Discharge): 0.8 ✓
   C-rate (1200 kW / 2000 kWh): 0.6 ✓
   Eficiencia: 0.95 ✓
   ```

#### Salidas (3)

**Ubicación**: `data/interim/oe2/bess/`

| Archivo | Descripción |
| --------- | ------------- |
| `bess_soc_timeseries.csv` | SOC horario (8760) |
| `bess_results.json` | Parámetros BESS |

---

## 🏢 Fase OE3: Construcción del Dataset

### Flujo de build_citylearn_dataset()

```text
build_citylearn_dataset(cfg, raw_dir, interim_dir, processed_dir)
│
├─ 1. LOAD OE2 ARTIFACTS
│  ├─ solar_generation_timeseries.csv (8760 registros)
│  ├─ charger_MOTO_CH_*.csv (112 archivos)
│  ├─ charger_MOTO_TAXI_CH_*.csv (16 archivos)
│  └─ bess parámetros
│
├─ 2. LOAD CITYLEARN TEMPLATE
│  └─ citylearn_challenge_2022_phase_all_plus_evs (8 EVs definidos)
│
├─ 3. CREATE UNIFIED BUILDING
│  └─ Mall_Iquitos (128 cargadores, 4162 kWp, 2000 kWh)
│
├─ 4. TRANSFORM TO CITYLEARN FORMAT
│  ├─ solar_generation (W/kW.h → kWh)
│  ├─ charger simulations (128 archivos)
│  └─ carbon_intensity (0.4521 kg/kWh constante)
│
└─ 5. GENERATE SCHEMAS
   ├─ schema_grid_only.json (baseline: sin PV/BESS)
   └─ schema_pv_bess.json (con sistema completo)
```

### Paso 1: Cargar Artefactos OE2

```python
# Ubicación de entrada
interim_dir/
├─ oe2/solar/
│  └─ pv_generation_timeseries.csv
├─ oe2/chargers/
│  ├─ charger_MOTO_CH_*.csv
│  └─ charger_MOTO_TAXI_CH_*.csv
└─ oe2/bess/
   └─ bess_results.json

# Validaciones

- Solar: 8760 registros, suma > target_annual_kwh × 0.95

- Chargers: 128 archivos, 8760 registros cada uno

- BESS: capacity_kwh > 0, power_kw > 0
```

### Paso 2: Cargar Template CityLearn

```text
Fuente: citylearn_challenge_2022_phase_all_plus_evs
├─ schema.json (definición de edificios, EVs, parámetros)
├─ Building_1.csv (demanda base del edificio)
├─ solar_generation.csv (perfil solar existente)
├─ carbon_intensity.csv (intensidad carbono de red)
├─ 8 EVCharger definidas
└─ EV types, battery configs, etc.
```

### Paso 3: Crear Edificio Unificado (Mall_Iquitos)

#### Estructura Conceptual

```text
ANTES (template): 2 edificios independientes
├─ Building_1 (comercial)
└─ Building_2 (residencial)

DESPUÉS (iquitos): 1 edificio unificado
└─ Mall_Iquitos
   ├─ Building Energy: 12,368,653 kWh/año (demanda diaria × 365)
   ├─ Solar Generation: 4,162 kWp nominal
   ├─ BESS: 2,000 kWh, 1,200 kW
   ├─ EV Chargers: 128 (112 motos 2kW + 16 mototaxis 3kW)
   └─ Intensidad carbono: 0.4521 kg/kWh
```

#### Configuración JSON

```json
{
  "buildings": {
    "Mall_Iquitos": {
      "properties": {
        "solar": {
          "nominal_power": 4162.0,  // kWp
          "solar_generation_file": "solar_generation.csv"
        },
        "energy_storage": [
          {
            "capacity": 2000.0,         // kWh
            "max_output_power": 1200.0, // kW
            "efficiency_battery": 0.95,
            "type": "battery"
          }
        ],
        "electric_vehicle": [
          {
            "name": "EV_Charger_0",
            "definition_file": "charger_MOTO_CH_001.csv"
          },
          ...
          {
            "name": "EV_Charger_127",
            "definition_file": "charger_MOTO_TAXI_CH_128.csv"
          }
        ]
      }
    }
  }
}
```

### Paso 4: Transformación de Datos

#### 4.1 Solar Generation

```text
Input:  pv_generation_timeseries.csv
        timestamp, ac_power_kw
        2024-01-01 00:00:00, 0.0
        2024-01-01 01:00:00, 0.0
        ...

Transformación:
  W/kW.h → kWh
  Multiplicar por 1000 (escala CityLearn)
  
Output: solar_generation.csv
        0, 0, 0, ..., 1856300, 1998500, ...  (columna de 8760 valores)
```

**Validación**:

```text

- 8760 registros exactamente

- No valores negativos

- Suma ≈ 8.042 GWh/año ✓
```

#### 4.2 Charger Simulations

```text
Input:  charger_MOTO_CH_001.csv hasta charger_MOTO_TAXI_CH_128.csv
        (128 archivos)

Proceso:
  1. Detectar problemas de alineación de timesteps
  2. Si len(df) = 8761 → remover último registro (bug pvlib)
  3. Asegurar índice 0-8759 (8760 registros)

Output: Copia en data/processed/citylearn/iquitos_ev_mall/
        charger_MOTO_CH_001.csv
        charger_MOTO_CH_002.csv
        ...
        charger_MOTO_TAXI_CH_128.csv
```

**Fallback Logic** (si hay problemas):

```python
if len(charger_df) == 8761 and n == 8760:
    charger_df = charger_df.iloc[:8760]  # Remover último
    logger.info(f"[DEBUG FALLBACK] {charger_id}: ajustado a 8760")
```

#### 4.3 Carbon Intensity

```text
Input:  Configuración: 0.4521 kg/kWh (red térmica Iquitos)

Output: carbon_intensity.csv
        0.4521, 0.4521, 0.4521, ... (8760 valores constantes)
        
Nota: Red aislada → constante 24/7 (sin variación horaria)
```

### Paso 5: Generar Schemas

#### Schema 1: grid_only.json (Baseline)

```json
{
  "buildings": {
    "Mall_Iquitos": {
      "properties": {
        "solar": {
          "nominal_power": 0.0      // SIN PV
        },
        "energy_storage": [
          {
            "capacity": 0.0         // SIN BESS
          }
        ]
      }
    }
  }
}
```

**Propósito**: Comparar contra línea base (solo red).

#### Schema 2: schema_pv_bess.json (Full System)

```json
{
  "buildings": {
    "Mall_Iquitos": {
      "properties": {
        "solar": {
          "nominal_power": 4162.0     // 4.162 MWp
        },
        "energy_storage": [
          {
            "capacity": 2000.0         // 2000 kWh
            "max_output_power": 1200.0 // 1.2 MW
          }
        ]
      }
    }
  }
}
```

**Propósito**: Evaluar beneficio de sistema PV+BESS optimizado por RL.

---

## 📁 Estructura de Archivos

```text
d:\diseñopvbesscar/
│
├── configs/
│   └── default.yaml                    ← CONFIG PRINCIPAL
│
├── data/
│   ├── interim/
│   │   └── oe2/
│   │       ├── solar/
│   │       │   ├── pv_generation_timeseries.csv    (8760 rows)
│   │       │   ├── pv_profile_24h.csv
│   │       │   ├── solar_results.json
│   │       │   └── solar_schema_params.json
│   │       ├── chargers/
│   │       │   ├── charger_MOTO_CH_001.csv        (112 archivos)
│   │       │   ├── charger_MOTO_CH_002.csv
│   │       │   ├── ...
│   │       │   ├── charger_MOTO_TAXI_CH_113.csv   (16 archivos)
│   │       │   ├── ...
│   │       │   ├── charger_MOTO_TAXI_CH_128.csv
│   │       │   ├── chargers_results.json
│   │       │   └── perfil_horario_carga.csv
│   │       └── bess/
│   │           ├── bess_soc_timeseries.csv
│   │           └── bess_results.json
│   │
│   └── processed/
│       └── citylearn/
│           └── iquitos_ev_mall/          ← DATASET FINAL
│               ├── schema_grid_only.json
│               ├── schema_pv_bess.json
│               ├── Building_1.csv         (demanda del edificio)
│               ├── solar_generation.csv   (8760 registros)
│               ├── carbon_intensity.csv   (8760 × 0.4521 kg/kWh)
│               ├── charger_MOTO_CH_001.csv
│               ├── charger_MOTO_CH_002.csv
│               ├── ...
│               └── charger_MOTO_TAXI_CH_128.csv
│
├── outputs/
│   └── oe3/
│       ├── simulations/
│       │   ├── sac_grid_only.json
│       │   ├── sac_pv_bess.json
│       │   ├── ppo_grid_only.json
│       │   ├── ppo_pv_bess.json
│       │   ├── a2c_grid_only.json
│       │   └── a2c_pv_bess.json
│       └── checkpoints/
│           ├── sac/
│           │   ├── sac_step_500.zip
│           │   ├── sac_step_1000.zip
│           │   └── sac_final.zip
│           ├── ppo/
│           └── a2c/
│
├── analyses/
│   └── oe3/
│       ├── co2_comparison_table.csv      ← TABLA FINAL
│       ├── co2_comparison_table.md
│       ├── training/
│       │   ├── progress/
│       │   │   ├── sac_progress.csv
│       │   │   ├── ppo_progress.csv
│       │   │   └── a2c_progress.csv
│       │   └── checkpoints/
│       │       ├── sac/
│       │       ├── ppo/
│       │       └── a2c/
│       └── (gráficas, métricas, etc.)
│
└── reports/
    ├── oe1/
    ├── oe2/
    │   └── solar_plots/  (12 gráficas)
    └── oe3/
```

---

## 🎯 Dataclasses y Schemas

### OE2: Outputs (salidas serializadas)

```python
@dataclass(frozen=True)
class SolarSizingOutput:
    location: str                              # "Iquitos, Perú (-3.75, -73.25)"
    target_dc_kw: float                       # 4162.0
    pv_modules_total: int                     # 186279
    pv_capacity_dc_kw: float                  # 3759.86
    pv_capacity_ac_kw: float                  # 3201.2
    annual_energy_ac_kwh: float               # 8042399
    capacity_factor_percent: float             # 28.6
    performance_ratio_percent: float           # 128.5

@dataclass(frozen=True)
class BessSizingOutput:
    capacity_kwh: float                        # 2000.0
    max_output_power_kw: float                # 1200.0
    dod: float                                 # 0.8
    c_rate: float                             # 0.6
    efficiency_roundtrip: float                # 0.95
```

### OE3: CityLearn Schema Structure

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
          ...
          {"name": "EV_Charger_127", "definition_file": "charger_MOTO_TAXI_CH_128.csv"}
        ]
      }
    }
  },
  "carbon_intensity_file": "carbon_intensity.csv",
  "pricing_file": "pricing.csv"
}
```

---

## ✅ Validaciones

### Validación Solar

```python
def validate_solar():
    # Lectura
    df = pd.read_csv("pv_generation_timeseries.csv")
    assert len(df) == 8760, "❌ No tiene 8760 registros"
    
    # Energía
    annual_kwh = df['ac_power_kw'].sum()
    target = 3972478 * 0.95  # 95% del target
    assert annual_kwh >= target, f"❌ {annual_kwh} < {target}"
    
    # Rango
    assert df['ac_power_kw'].min() >= 0, "❌ Valores negativos"
    assert df['ac_power_kw'].max() <= 4000, "❌ Valores > nominal"
    
    print("✅ Solar válida")
```

### Validación Chargers

```python
def validate_chargers():
    # 128 archivos
    charger_files = list(Path("chargers").glob("charger_*.csv"))
    assert len(charger_files) == 128, f"❌ {len(charger_files)} != 128"
    
    for f in charger_files:
        df = pd.read_csv(f)
        assert len(df) == 8760, f"❌ {f}: {len(df)} != 8760"
        assert df['power_kw'].min() >= 0, f"❌ {f}: negativos"
    
    print("✅ Chargers válidos (128 × 8760)")
```

### Validación BESS

```python
def validate_bess():
    with open("bess_results.json") as f:
        cfg = json.load(f)
    
    assert cfg['capacity_kwh'] > 0, "❌ Capacidad ≤ 0"
    assert cfg['dod'] >= 0.7 and cfg['dod'] <= 0.95, "❌ DoD fuera de rango"
    assert cfg['c_rate'] >= 0.4 and cfg['c_rate'] <= 1.0, "❌ C-rate fuera de rango"
    
    print("✅ BESS válida")
```

---

## ⚙️ Configuración (configs/default.yaml)

### Sección OE2: Solar

```yaml
oe2:
  location:
    lat: -3.75            # Latitud Iquitos
    lon: -73.25           # Longitud Iquitos
    tz: America/Lima      # Zona horaria
  
  solar:
    target_ac_kw: 3201.2                    # Potencia AC nominal
    target_dc_kw: 4162.0                    # Potencia DC nominal
    target_annual_kwh: 3972478              # Energía anual target
    use_pvlib: true                         # Usar pvlib (sí)
    scale_to_target_annual: true            # Escalar para cumplir target
    module_name: Kyocera_Solar_KS20__2008__E__
    inverter_name: Eaton__Xpert1670
```

### Sección OE2: Cargadores

```yaml
oe2:
  ev_fleet:
    motos_count: 900              # Motos @ 19:00h
    mototaxis_count: 130          # Mototaxis @ 19:00h
    charger_power_kw_moto: 2.0
    charger_power_kw_mototaxi: 3.0
    session_minutes: 30           # Duración típica de carga
    peak_share_day: 0.5           # 50% de energía en horas pico
    peak_hours:

- 18

- 19

- 20

- 21
```

### Sección OE2: BESS

```yaml
oe2:
  bess:
    fixed_capacity_kwh: 2000
    fixed_power_kw: 1200
    dod: 0.8                      # Depth of Discharge
    c_rate: 0.6                   # Carga/descarga = 0.6 × capacidad/hora
    efficiency_roundtrip: 0.95    # 95% ida y vuelta
```

### Sección OE3: Dataset y Evaluación

```yaml
oe3:
  dataset:
    template_name: citylearn_challenge_2022_phase_all_plus_evs
    name: iquitos_ev_mall
  
  evaluation:
    agents:

- SAC

- PPO

- A2C
    resume_checkpoints: false       # SIN reanudación (entrenamiento desde cero)
    
    sac:
      episodes: 2                   # Episodios de entrenamiento
      batch_size: 4096
      device: cuda
      checkpoint_freq_steps: 500
      use_amp: true                 # Mixed Precision para GPU
      multi_objective_weights:
        co2: 0.50                   # Prioridad CO₂
        cost: 0.15
        solar: 0.20
        ev: 0.10
        grid: 0.05
```

---

## 📊 Ejemplo de Construcción Completa

### Entrada: configs/default.yaml

```yaml
oe2:
  solar:
    target_dc_kw: 4162.0
    use_pvlib: true
  ev_fleet:
    motos_count: 900
    charger_power_kw_moto: 2.0
```

### Proceso (4)

```text
1. OE2 Solar
   ├─ Descargar TMY PVGIS → 8760 registros
   ├─ Seleccionar módulos → Kyocera 20.18 W
   ├─ Diseñar array → 186,279 módulos = 3759.86 kWp
   ├─ Simular año completo → 8,042,399 kWh
   └─ Guardar: pv_generation_timeseries.csv (8760 filas)

1. OE2 Chargers
   ├─ Calcular demanda: 900 motos × 2 kW = 180 kW
   ├─ Distribuir en 112 perfiles individuales
   ├─ Aplicar perfiles de uso (picos 18-22h)
   └─ Guardar: 112 × charger_MOTO_CH_*.csv (8760 filas c/u)

1. OE2 BESS
   ├─ Fijar: 2000 kWh, 1200 kW
   └─ Guardar: bess_results.json

1. OE3 Build Dataset
   ├─ Cargar artefactos OE2
   ├─ Cargar template CityLearn (citylearn_challenge_2022_phase_all_plus_evs)
   ├─ Crear edificio unificado "Mall_Iquitos"
   ├─ Transformar solar: escalar a formato CityLearn
   ├─ Copiar 128 chargers
   ├─ Generar 2 schemas:
   │  ├─ schema_grid_only.json (PV=0, BESS=0) ← baseline
   │  └─ schema_pv_bess.json (PV=4162, BESS=2000) ← full
   └─ Guardar en: data/processed/citylearn/iquitos_ev_mall/

1. OE3 Simulate
   ├─ Cargar schema_pv_bess.json
   ├─ Entrenar SAC (desde cero):
   │  ├─ 2 episodios
   │  ├─ 17,520 timesteps
   │  ├─ Reward multiobjetivo (CO2 50%, solar 20%, ...)
   │  └─ Guardar checkpoints cada 500 steps
   ├─ Entrenar PPO (análogo)
   ├─ Entrenar A2C (análogo)
   └─ Evaluar con schema_grid_only.json (comparar)

1. OE3 CO2 Table
   ├─ Leer salidas de simulación
   ├─ Calcular emisiones anuales
   └─ Generar: co2_comparison_table.csv
```

### Salida: data/processed/citylearn/iquitos_ev_mall/

```text
✅ schema_grid_only.json (baseline)
✅ schema_pv_bess.json (full system)
✅ Building_1.csv (12,368,653 kWh/año)
✅ solar_generation.csv (8760 × 1,927 kWh valor medio)
✅ carbon_intensity.csv (8760 × 0.4521 kg/kWh)
✅ charger_MOTO_CH_001.csv ... charger_MOTO_CH_112.csv (112 archivos)
✅ charger_MOTO_TAXI_CH_113.csv ... charger_MOTO_TAXI_CH_128.csv (16 archivos)
```

---

## 🚀 Comandos para Construcción Manual

```bash
# Entorno
.venv\Scripts\activate

# Solo OE2
python -m scripts.run_oe2_solar --config configs/default.yaml
python -m scripts.run_oe2_chargers --config configs/default.yaml
python -m scripts.run_oe2_bess --config configs/default.yaml

# Solo OE3 (requiere OE2 completado)
python -m scripts.run_oe3_build_dataset --config configs/default.yaml
python -m scripts.run_oe3_simulate --config configs/default.yaml

# Todo de una vez
python -m scripts.run_pipeline --config configs/default.yaml

# Monitorear progreso
python monitor_checkpoints.py
```

---

## 📈 Resultado Esperado (nuevos datos PV)

Con el entrenamiento que está en curso:

| Métrica | Valor |
| --------- | ------- |
| Energía solar anual | 8.042 GWh |
| Capacidad instalada PV | 4,162 kWp |
| Factor de capacidad | 28.6% |
| Cargadores | 128 (272 kW total) |
| BESS | 2,000 kWh / 1,200 kW |
| Agentes entrenados | SAC, PPO, A2C (desde cero) |
| Peso CO₂ en reward | 50% (prioridad) |

**Esperado**: Reducción de CO₂ 65-70% vs línea base.

---

## Fin de documentación de construcción de dataset
