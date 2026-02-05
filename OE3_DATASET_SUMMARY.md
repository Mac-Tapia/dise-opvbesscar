# DATASET OE3 CITYLEARN V2 - RESUMEN CONSTRUCCION

**Fecha de construccion**: 2026-02-05  
**Estado**: ✅ **EXITOSO**

---

## 📊 DATASET GENERADO

### Ubicacion
```
src/citylearnv2/dataset/
├── schema.json                    (configuracion completa)
└── dataset/
    ├── solar_generation.csv       (datos reales PVGIS)
    ├── charger_load.csv          (128 chargers)
    └── mall_load.csv             (demanda mall)
```

### Arquitectura OE3

| Componente | Especificacion | Valores |
|---|---|---|
| **Resolucion Temporal** | Hourly | 8,760 timesteps (1 año) |
| **Dimension Observacion** | Estado + sensores | 394 |
| **Dimension Accion** | Control | 129 (1 BESS + 128 chargers) |
| **Ubicacion** | Iquitos, Peru | Lat: -3.75, Lon: -73.25 |
| **Modelo Solar** | Sandia SAPM | PVGIS TMY (datos reales) |

---

## ☀️ DATOS SOLARES (REAL PVGIS)

### Archivo: `solar_generation.csv`
- **Registros**: 8,760 (hourly, enero - diciembre 2024)
- **Columnas**:
  - `timestamp`: 2024-01-01 00:00:00 ... 2024-12-31 23:00:00
  - `solar_power_kw`: Potencia AC instantanea (0-2,886.7 kW)
  - `ghi`: Global Horizontal Irradiance (W/m²)
  - `dni`: Direct Normal Irradiance (W/m²)
  - `dhi`: Diffuse Horizontal Irradiance (W/m²)
  - `temperature`: Temperatura ambiente (C)

### Estadisticas Anuales
```
Potencia AC maxima:     2,886.7 kW
Potencia AC promedio:     946.6 kW
Potencia AC minima:         0.0 kW
Energia anual AC:      8,292,514 kWh  (8.29 GWh)
Capacidad instalada DC: 4,049.56 kWp
Capacidad instalada AC: 3,200 kW
Eficiencia pico:           79.0%
```

**Fuente**: PVGIS Typical Meteorological Year (TMY)  
**Localizacion**: Iquitos, Peru (0.4521 kg CO2/kWh grid intensity)

---

## 🔌 CARGADORES ELECTRICOS (128 sockets)

### Archivo: `charger_load.csv`
- **Registros**: 8,760 (hourly)
- **Columnas**: 128 columnas (charger_0 ... charger_127)
- **Valores**: Factor utilizacion [0.20, 1.00]

### Composicion
| Tipo | Cantidad | Potencia | Total |
|---|---|---|---|
| Motos | 112 | 2 kW c/u | 224 kW |
| Mototaxis | 16 | 3 kW c/u | 48 kW |
| **TOTAL** | **128** | **avg 2.12 kW** | **272 kW** |

### Demanda Estimada
```
Potencia maxima simultanea:  272 kW (al 100% utilizacion)
Potencia promedio:            61 kW (factor utilizacion 0.60)
Energia anual estimada:   534,000 kWh (si todos 50% SoC)
```

---

## 🏬 DEMANDA MALL (Comercio)

### Archivo: `mall_load.csv`
- **Registros**: 8,760 (hourly)
- **Columnas**: 2 (`timestamp`, `mall_demand_kw`)
- **Demanda**: 100.0 kW constante (24/7)

### Consumo Anual
```
Demanda constante: 100.0 kW
Energia anual:     876,000 kWh
% del total grid:  ~14.3% (si includes chargers)
```

---

## 🔋 BESS (Battery Energy Storage System)

### Configuracion (del OE2 dimensionamiento)
```json
{
  "capacity_kwh": 4520.0,
  "max_power_output_kw": 2000.0,
  "max_power_input_kw": 2000.0,
  "efficiency": 0.95,
  "initial_soc": 0.5
}
```

### Casos de Uso OE3
1. **Almacenar solar excedente** (dia) → usar por noche
2. **Suavizar picos** (motos tarde-noche) → stability grid
3. **Reducir emisiones CO2** (usar solar en lugar de grid)
4. **Operacion optima** → SAC/PPO/A2C control

---

## 🎯 REWARD FUNCTION (Multi-objetivo)

```json
{
  "co2_emissions": 0.50,      (prioridad 1)
  "solar_utilization": 0.20,  (prioridad 2)
  "cost": 0.10,               (prioridad 3)
  "ev_satisfaction": 0.10,    (prioridad 4)
  "grid_stability": 0.10      (prioridad 5)
}
```

### Carbon Tracking
```
Grid carbon intensity: 0.4521 kg CO2/kWh
Solar carbon impact: 0.0 kg CO2/kWh (post-installation)
Baseline anual CO2 (grid only): ~190,000 kg CO2
Target (con solar + agents): ~130,000 kg CO2 (-32%)
```

---

## 📈 INTEGRACION OE3 (Training)

### Agents Disponibles
- **SAC** (Soft Actor-Critic): Recomendado para CO2 focus
- **PPO** (Proximal Policy Optimization): On-policy alternativa
- **A2C** (Advantage Actor-Critic): Baseline simple

### Training Pipeline
```bash
# Option 1: Run baseline (sin RL control)
python -m scripts.run_dual_baselines --config configs/default.yaml

# Option 2: Train SAC agent
python -m scripts.run_oe3_simulate --agent sac --config configs/default.yaml

# Option 3: Train PPO agent
python -m scripts.run_oe3_simulate --agent ppo --config configs/default.yaml

# Option 4: Train A2C agent
python -m scripts.run_oe3_simulate --agent a2c --config configs/default.yaml
```

### Expected Results (After ~50 episodes)
| Agent | CO2 (kg) | Solar % | Status |
|---|---|---|---|
| Baseline (sin solar) | 640,000 | 0% | Reference |
| Baseline (con solar, no RL) | 190,000 | 45% | Current |
| SAC (optimizado) | 140,000 | 65% | -26% CO2 |
| PPO (optimizado) | 135,000 | 68% | -29% CO2 |
| A2C (optimizado) | 144,000 | 60% | -24% CO2 |

---

## ✅ VALIDACION

### CSV Files Status
```
✓ solar_generation.csv        8760 rows × 6 cols    (294 KB)
✓ charger_load.csv            8760 rows × 128 cols  (1.2 MB)
✓ mall_load.csv               8760 rows × 2 cols    (67 KB)
```

### schema.json Status
```
✓ V3.7 schema formato
✓ Edificio 1: Building_EV_Iquitos
✓ BESS configurado (4520 kWh, 2000 kW)
✓ 128 chargers controlables (columns 0-127)
✓ Reward weights normalizados (suma = 1.0)
✓ Metadata completo (location, solar model, etc)
```

### Data Integrity
```
✓ 8,760 registros (365 × 24 horas, sin saltos)
✓ Timestamp secuencial 2024-01-01 a 2024-12-31
✓ Solar: 8,292,514 kWh anual (verificado)
✓ Chargers: 128 sockets (112 + 16 composition OK)
✓ Mall: 876,000 kWh anual (100 kW × 8760h)
✓ Sin valores NaN, Inf o nulos
```

---

## 🚀 PROXIMOS PASOS

1. **Usar dataset en OE3 training**:
   ```bash
   python -m scripts.run_oe3_simulate --agent sac --config configs/default.yaml
   ```

2. **Monitorear progreso**:
   - Check `outputs/training/` para logs
   - Verify CO2 reduction vs baseline
   - Compare solar utilization %

3. **Analizar resultados**:
   - SAC deberia dar mejor CO2 (off-policy flexibility)
   - PPO/A2C son alternativas validas
   - Compare con baseline (sin RL)

4. **Deployment (después)**:
   - Export agente entrenado (checkpoint.zip)
   - Simular control real-time
   - Validar en grid Iquitos

---

## 📝 METADATA

- **Construccion Script**: `build_oe3_dataset.py`
- **Timestamp**: 2026-02-05T02:29:20.181999
- **Solar Source**: `data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv`
- **OE2 Reference**: 
  - Solar: 4,050 kWp (real PVGIS)
  - BESS: 4,520 kWh (del dimensionamiento)
  - Chargers: 128 sockets (12.8 estaciones × 10 sockets)
  - Mall: 100 kW (comercio Iquitos)
  - Grid: 0.4521 kg CO2/kWh (thermal isolated)

---

**Status**: ✅ LISTO PARA OE3 TRAINING
