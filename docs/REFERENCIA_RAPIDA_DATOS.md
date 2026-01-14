# 🔍 REFERENCIA RÁPIDA: CONSTRUCCIÓN DE DATOS

## En 60 Segundos

```text
OE2 (Dimensionamiento)
├─ Solar:    Genera 8.042 GWh/año (4162 kWp)  → pv_generation_timeseries.csv
├─ Chargers: 128 perfiles (112 motos 2kW + 16 taxis 3kW) → charger_*.csv (128)
└─ BESS:     2000 kWh, 1200 kW                 → bess_soc_timeseries.csv

OE3 (Dataset + RL)
└─ Build Dataset:
   - Cargar 128 CSVs de OE2
   - Crear edificio "Mall_Iquitos" en CityLearn
   - Generar 2 schemas (baseline + full)
   - Entrenar SAC, PPO, A2C desde cero
   
Salida: data/processed/citylearn/iquitos_ev_mall/ (128 archivos + schemas)
```

---

## 📁 Rutas Críticas

```text
ENTRADA OE2                              SALIDA OE3
────────────────────────────────────────────────────────────
data/interim/oe2/solar/
  pv_generation_timeseries.csv  ──────→  solar_generation.csv
                                          (8760 × 1927 kWh)

data/interim/oe2/chargers/
  charger_MOTO_CH_*.csv (112)    ──────→  charger_MOTO_CH_*.csv (copia)
  charger_MOTO_TAXI_*.csv (16)   ──────→  charger_MOTO_TAXI_*.csv (copia)
  
data/interim/oe2/bess/
  bess_results.json              ──────→  schema_pv_bess.json
                                          (BESS: 2000 kWh, 1200 kW)

configs/default.yaml
  solar.target_dc_kw: 4162.0     ──────→  solar nominal_power: 4162.0
  ev_fleet: 900 motos, 130 taxis ──────→  128 EVCharger definitions
  grid.carbon_intensity: 0.4521  ──────→  carbon_intensity.csv (8760×)
```

---

## 🔧 Transformaciones Principales

| Paso | Entrada | Proceso | Salida |
| ------ | --------- | --------- | -------- |
| 1 | pv_generation_timeseries.csv (8760 kW) | Escalar × 1000 | solar_generation.csv (8760 Wh) |
| 2 | 128 charger CSVs | Validar 8760 registros, remover extras | Copiar con ajustes |
| 3 | 0.4521 kg/kWh (config) | Generar vector 8760 constante | carbon_intensity.csv |
| 4 | 128 chargers + solar + bess | Crear edificio CityLearn | schema_pv_bess.json |
| 5 | schema_pv_bess.json | Clonar y desactivar solar/bess | schema_grid_only.json |

---

## 📊 Números Clave

```text
ENTRADA OE2:
  - Solar capacity:        4,162 kWp DC
  - Solar annual energy:   8,042,399 kWh
  - Chargers count:        128 (272 kW total)
  - BESS:                  2,000 kWh @ 1,200 kW
  - Timesteps:             8,760 (horarios × 1 año)
  
SALIDA OE3:
  - Dataset files:         128 chargers + 3 base CSVs (building, solar, carbon)
  - Schemas:               2 (grid_only + pv_bess)
  - Total size:            ~50 MB (CSV) + 2 KB (schemas)
  - Timesteps:             128 chargers × 8760 = 1.128M
```

---

## ⚠️ Validaciones Automáticas

```python
# Solar
assert len(solar_df) == 8760 ✓
assert solar_df.sum() >= 3972478 * 0.95 ✓

# Chargers
assert count_charger_files == 128 ✓
for charger in chargers:
    assert len(charger) == 8760 ✓
    assert charger['power'].min() >= 0 ✓

# BESS
assert bess.capacity > 0 ✓
assert bess.dod in [0.7, 0.95] ✓
assert bess.c_rate >= 0.4 ✓

# Dataset
assert "schema_grid_only.json" exists ✓
assert "schema_pv_bess.json" exists ✓
assert len(chargers_in_dataset) == 128 ✓
```

---

## 🎯 Estados del Sistema

| Etapa | Ubicación | Status | Acción |
| ------- | ----------- | -------- | -------- |
| OE2 Solar | `data/interim/oe2/solar/` | ✅ Completado | Ver `solar_results.json` |
| OE2 Chargers | `data/interim/oe2/chargers/` | ✅ Completado | Ver `chargers_results.json` |
| OE2 BESS | `data/interim/oe2/bess/` | ✅ Completado | Ver `bess_results.json` |
| OE3 Dataset | `data/processed/citylearn/` | 🔄 En construcción | Monitorear logs |
| OE3 Training | `outputs/oe3/checkpoints/` | 🔄 En curso | `python monitor_checkpoints.py` |

---

## 💾 Archivos Más Importantes

```text
[ENTRADA]
├─ configs/default.yaml                    ← MODIFICA AQUÍ parámetros
├─ data/interim/oe2/solar/pv_generation_timeseries.csv
├─ data/interim/oe2/chargers/charger_MOTO_CH_*.csv (128)
└─ data/interim/oe2/bess/bess_results.json

[SALIDA]
├─ data/processed/citylearn/iquitos_ev_mall/
│  ├─ schema_grid_only.json                ← Baseline
│  ├─ schema_pv_bess.json                  ← Full system
│  ├─ solar_generation.csv
│  └─ charger_MOTO_CH_*.csv (128)
├─ outputs/oe3/simulations/
│  ├─ sac_pv_bess.json
│  ├─ ppo_pv_bess.json
│  └─ a2c_pv_bess.json
└─ analyses/oe3/
   └─ co2_comparison_table.csv             ← RESULTADO FINAL
```

---

## 🚀 Comandos Frecuentes

```bash
# Ver estado actual
.venv\Scripts\python show_training_status.py

# Monitorear en vivo
.venv\Scripts\python monitor_checkpoints.py

# Relanzar solo OE3 (OE2 completo)
.venv\Scripts\python -m scripts.run_oe3_build_dataset --config configs/default.yaml
.venv\Scripts\python -m scripts.run_oe3_simulate --config configs/default.yaml

# Relanzar todo desde cero
.venv\Scripts\python -m scripts.run_pipeline --config configs/default.yaml

# Ver logs del último pipeline
Get-Content pipeline.log -Tail 100

# Verificar dataset
ls -la data/processed/citylearn/iquitos_ev_mall/|Measure-Object
```

---

## 🔄 Transformación Conceptual

```text
OE2: HARDWARE DESIGN                OE3: SOFTWARE SIMULATION
──────────────────────────────────────────────────────────
Física PV ──────────────┐
Demanda EV ──────────────┼──→ Datos horarios (8760)
Energía almacenada ──────┘
                              │
                              ├─→ Normalización CityLearn
                              │   (W → Wh, escalas, etc.)
                              │
                              ├─→ Edificio virtual
                              │   (Mall_Iquitos)
                              │
                              ├─→ 2 Escenarios
                              │   ├─ Sin renovables (baseline)
                              │   └─ Con RL (optimizado)
                              │
                              └─→ Entrenamiento RL
                                  (SAC, PPO, A2C desde cero)
                                  
                              ↓
                              CO₂ 65-70% reducción esperada
```

---

## 📈 Evolución de Datos

```text
Configuración (YAML)
  ↓ (run_oe2_solar.py)
Datos TMY PVGIS + Componentes
  ↓ (ModelChain pvlib)
PV Generation Timeseries (8760 kW)
  ↓ (run_oe2_chargers.py)
EV Demand Profiles (128 × 8760 kW)
  ↓ (run_oe2_bess.py)
Battery SOC Timeseries (8760 kWh)
  ↓ (run_oe3_build_dataset.py)
CityLearn Dataset (1 edificio unificado)
  ├─ schema_grid_only.json (sin renovables)
  └─ schema_pv_bess.json (con renovables + RL)
  ↓ (run_oe3_simulate.py)
Agentes RL Entrenados (SAC, PPO, A2C)
  ↓ (run_oe3_co2_table.py)
Tabla Comparativa CO₂ (anual + 20 años)
```

---

## 🛠️ Personalización

### Si cambias solar

```yaml
# ANTES
solar:
  target_dc_kw: 4162.0
  target_annual_kwh: 3972478

# DESPUÉS (ejemplo: 5000 kWp)
solar:
  target_dc_kw: 5000.0
  target_annual_kwh: 4800000

# LUEGO
.venv\Scripts\python -m scripts.run_oe2_solar --config configs/default.yaml
.venv\Scripts\python -m scripts.run_oe3_build_dataset --config configs/default.yaml
```

### Si cambias cargadores

```yaml
# ANTES
ev_fleet:
  motos_count: 900
  mototaxis_count: 130
  charger_power_kw_moto: 2.0
  charger_power_kw_mototaxi: 3.0

# DESPUÉS (ejemplo: 50% más motos)
ev_fleet:
  motos_count: 1350
  mototaxis_count: 130
  
# Esto generará ~190 cargadores en lugar de 128
```

### Si cambias pesos de reward RL

```yaml
# ANTES
sac:
  multi_objective_weights:
    co2: 0.50
    cost: 0.15
    solar: 0.20
    ev: 0.10
    grid: 0.05

# DESPUÉS (ejemplo: maximizar solar)
sac:
  multi_objective_weights:
    co2: 0.30
    cost: 0.10
    solar: 0.40
    ev: 0.10
    grid: 0.10
```

---

## 📚 Más Información

- **Construcción completa**: [`docs/CONSTRUCCION_DATASET_COMPLETA.md`](CONSTRUCCION_DATASET_COMPLETA.md)
- **Diagrama técnico**: [`docs/DIAGRAMA_TECNICO_OE2_OE3.md`](DIAGRAMA_TECNICO_OE2_OE3.md)
- **Estado actual**: Entrenamiento en curso (SAC, PPO, A2C desde cero con nuevos datos PV)
- **Última actualización**: 14 Enero 2026
