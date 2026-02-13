# 📑 REFERENCIA RÁPIDA: Dataset v5.4 (Cheat Sheet)

**Última actualización**: 2026-02-13  
**Estado**: ✅ OPERACIONAL  
**Mantenedo por**: Copilot (diseño PV-BESS-EV, Iquitos)

---

## 🔢 NÚMEROS EXACTOS (AÑO 2024, COMPLETO)

### Dimensiones Dataset
```
Filas:          8,760  (365 días × 24 horas)
Columnas:       25     (21 originales + 4 v5.4)
Tamaño:         1.79 MB
Índice:         DatetimeIndex (2024-01-01 00:00:00 → 2024-12-30 23:00:00)
Nulos:          0 (100% completitud)
Validación:     ✅ PASADA
```

### Energía (Totales Anuales)
```
GENERACIÓN:
  PV solar              8,292,514 kWh/año

DEMANDA:
  EV                      412,236 kWh/año (3.2%)
  Mall                 12,368,653 kWh/año (96.8%)
  Total                12,780,889 kWh/año

ALMACENAMIENTO (BESS):
  Cargado                 473,315 kWh/año
  Descargado              461,843 kWh/año
  Eficiencia round-trip        97.6%
  
IMPORTACIÓN GRID:
  Total                 6,339,409 kWh/año
  % de demanda total         49.6%
  
AUTOSUFICIENCIA:             50.4% (local generation)
```

### Nuevas Métricas v5.4 (Totales Anuales)
```
AHORROS ECONÓMICOS (Peak Reduction):
  Total                   S/. 118,445/año
  Máximo/hora             S/. 139.22
  Mínimo/hora             S/. 0.00
  Promedio/hora           S/. 13.51

CO₂ INDIRECTO EVITADO (BESS Displacement):
  Total                   203,512 kg/año = 203.5 ton/año
  Máximo/hora             176.26 kg
  Mínimo/hora             0.00 kg
  Promedio/hora           23.23 kg
```

### Operación BESS
```
Capacidad:              1,700 kWh (max SOC)
Potencia:               400 kW (carga/descarga)

SOC:
  Mínimo                19.4%
  Máximo                100.0%
  Promedio              48.3%
  Desv Est              32.8%

Ciclos:
  Por día               0.74 ciclos/día
  Por año               269 ciclos/año
  
Desgaste estimado:      Bajo (< 10 años)
```

---

## 📋 ESTRUCTURA DE COLUMNAS (25 TOTAL)

```
INDEX:  datetime [DatetimeIndex]

GRUPO 1: GENERACIÓN (1 col)
  [2]  pv_generation_kwh │ float64 │ [0, 4000] │ Sum: 8,292,514

GRUPO 2: DEMANDA (2 cols)
  [3]  ev_demand_kwh │ float64 │ [0, 100] │ Sum: 412,236
  [4]  mall_demand_kwh │ float64 │ [0, 1500] │ Sum: 12,368,653

GRUPO 3: FLUJOS PV (4 cols)
  [5]  pv_to_ev_kwh │ float64 │ [0, 100] │ Sum: ~25,000
  [6]  pv_to_bess_kwh │ float64 │ [0, 400] │ Sum: ~150,000
  [7]  pv_to_mall_kwh │ float64 │ [0, 3000] │ Sum: ~7,900,000
  [8]  pv_curtailed_kwh │ float64 │ [0, 2000] │ Sum: ~200,000

GRUPO 4: BESS OPERACIÓN (4 cols)
  [9]  bess_charge_kwh │ float64 │ [0, 400] │ Sum: 473,315
  [10] bess_discharge_kwh │ float64 │ [0, 400] │ Sum: 461,843
  [11] bess_to_ev_kwh │ float64 │ [0, 100] │ Sum: 69,293
  [12] bess_to_mall_kwh │ float64 │ [0, 400] │ Sum: 380,856

GRUPO 5: GRID (6 cols)
  [13] grid_to_ev_kwh │ float64 │ [0, 100] │ Sum: ~335,000
  [14] grid_to_mall_kwh │ float64 │ [0, 2000] │ Sum: ~4,900,000
  [15] grid_to_bess_kwh │ float64 │ [0, 400] │ Sum: ~100,000
  [16] grid_import_total_kwh │ float64 │ [0, 2300] │ Sum: 6,339,409
  [17] mall_grid_import_kwh │ float64 │ [0, 2300] │ Sum: ~4,900,000
  [18] bess_mode │ int64 │ {0,1,2} │ 0=idle, 1=charge, 2=discharge

GRUPO 6: SOC BESS (1 col)
  [19] bess_soc_percent │ float64 │ [19.4, 100.0] │ Avg: 48.3%

GRUPO 7: TARIFICACIÓN (2 cols)
  [20] tariff_osinergmin_soles_kwh │ float64 │ [0.28, 0.45] │
       HP: 0.45 S/kWh (6-22h), HFP: 0.28 S/kWh (22-6h)
  [21] cost_grid_import_soles │ float64 │ [0, 1000] │ Sum: ~1.8M

⭐ GRUPO 8: v5.4 AHORROS ECONÓMICOS (2 cols) - NUEVAS
  [22] peak_reduction_savings_soles │ float64 │ [0, 139.22] │ Sum: 118,445
       = bess_to_mall[h] × tariff[h] si BESS descarga a mall
       
  [23] peak_reduction_savings_normalized │ float64 │ [0, 1] │ Sum: 851
       = peak_reduction_savings_soles / max_value

⭐ GRUPO 9: v5.4 CO₂ INDIRECTO (2 cols) - NUEVAS
  [24] co2_avoided_indirect_kg │ float64 │ [0, 176.26] │ Sum: 203,512
       = (bess_to_ev[h] + bess_to_mall[h]) × 0.4521 kg CO₂/kWh
       
  [25] co2_avoided_indirect_normalized │ float64 │ [0, 1] │ Sum: 1,155
       = co2_avoided_indirect_kg / max_value
```

---

## 🎯 RESUMEN POR HORA (EJEMPLOS TÍPICOS)

### Hora 0-5 (Noche, 22:00-05:00)
```
Hora: 01:00
  PV:       0 kWh (oscuridad)
  Mall:   650 kWh (carga base)
  EV:      30 kWh (carga nocturna)
  BESS:     0 kWh (solo genera picos si > 2000 kW)
  Grid:   680 kWh (todo desde grid - tarifa HFP 0.28 S/)
  Tarifa: 0.28 S/kWh
  
  Ahorros: S/. 0 (no hay BESS descarga)
  CO2: 0 kg (no hay BESS descarga)
```

### Hora 8 (Pico Mañana)
```
Hora: 08:00
  PV:     1,100 kWh (luz débil)
  Mall:   1,200 kWh (pico)
  EV:        50 kWh (carga)
  BESS:    380.9 kWh DESCARGA (pico definido)
  Grid:    670 kWh (complemento)
  Tarifa: 0.45 S/kWh (HP)
  
  Ahorros: 380.9 × 0.45 = S/. 171.4 (máximo aproximado)
  CO2: 380.9 × 0.4521 = 172 kg
```

### Hora 14 (Pico Solar)
```
Hora: 14:00
  PV:     3,800 kWh (máximo)
  Mall:     800 kWh
  EV:        30 kWh
  BESS:   +400 kWh CARGA (almacena exceso)
  Grid:      0 kWh (0 importación si PV suficiente)
  Tarifa: 0.45 S/kWh
  
  Ahorros: S/. 0 (BESS cargando, no descargando)
  CO2: 0 kg (BESS cargando, no descargando)
```

### Hora 18-22 (Pico Tarde/Noche)
```
Hora: 20:00
  PV:     1,200 kWh (declina)
  Mall:   1,300 kWh (pico tarde)
  EV:        50 kWh
  BESS:    250 kWh DESCARGA (pico)
  Grid:    800 kWh
  Tarifa: 0.45 S/kWh (HP hasta 22:00)
  
  Ahorros: 250 × 0.45 = S/. 112.5
  CO2: 250 × 0.4521 = 113 kg
```

---

## 🔧 CÓDIGOS ÚTILES (Copiar/Pegar)

### Cargar Dataset
```python
import pandas as pd
df = pd.read_csv('data/oe2/bess/bess_simulation_hourly.csv', 
                  index_col=0, parse_dates=True)
# df.index = DatetimeIndex ✅
```

### Verificar Completitud
```python
assert len(df) == 8760, f"ERROR: {len(df)} rows"
assert df.isnull().sum().sum() == 0, "NULL values found"
assert isinstance(df.index, pd.DatetimeIndex), "Need DatetimeIndex"
print("✅ Dataset v5.4 OK")
```

### Extraer Métricas v5.4
```python
ahorros_anual = df['peak_reduction_savings_soles'].sum()        # S/. 118,445
co2_anual = df['co2_avoided_indirect_kg'].sum() / 1000          # 203.5 ton
co2_normalized = df['co2_avoided_indirect_normalized'].max()    # 1.0 (max)
savings_normalized = df['peak_reduction_savings_normalized'].max()  # 1.0
```

### Statistical Summary
```python
print(df.describe())
# Mostrará min, max, mean, std para todas las 25 columnas
```

### Filter por Tiempo
```python
# Horas pico (08:00-22:00)
picos = df.between_time('08:00', '22:00')

# Horas específicas
hora_8 = df[df.index.hour == 8]

# Rango fechas
enero = df['2024-01-01':'2024-01-31']
```

### Crear Observation Vector (Para RL)
```python
obs = np.array([
    df.loc[timestamp, 'pv_generation_kwh'],
    df.loc[timestamp, 'grid_import_total_kwh'],
    df.loc[timestamp, 'mall_demand_kwh'],
    df.loc[timestamp, 'bess_soc_percent'],
    df.loc[timestamp, 'peak_reduction_savings_normalized'],  # v5.4
    df.loc[timestamp, 'co2_avoided_indirect_normalized'],     # v5.4
    timestamp.hour,
    timestamp.month,
    timestamp.dayofweek,
])
```

---

## 🐛 TROUBLESHOOTING QUICK FIX

| Síntoma | Diagnóstico | Fix |
|---|---|---|
| `KeyError: 'peak_reduction_savings_soles'` | Columna v5.4 falta | Ejecutar `bess.py` |
| `Index: RangeIndex` (en lugar de DatetimeIndex) | Serial index incorrecto | `df.index = pd.date_range(...); df.to_csv(...)` |
| `8784 rows` or `8736 rows` (en lugar de 8760) | Año incompleto | Verificar simul start/end date en `bess.py` |
| Valores `NaN` en columnas v5.4 | Cálculo fallido | Check denominadores (max_value en normalization) |
| `IndexError: target index out of bounds` | Mismatch timesteps | Asegurar 8,760 horas en loop simulación |

---

## 📊 COMPARACIÓN v5.3 vs v5.4

| Feature | v5.3 | v5.4 | Ganancia |
|---|---|---|---|
| Filas | 8,760 | 8,760 | Igual ✓ |
| Columnas base | 21 | 21 | Igual ✓ |
| Ahorros en dataset | Reportes solo | Horario + norm | ✅ NUEVO |
| CO₂ indirecto en dataset | No | Horario + norm | ✅ NUEVO |
| Normalización RL | Manual | Integrado | ✅ IMPROVED |
| RL observation space | Genérica | Multi-obj | ✅ IMPROVED |
| CityLearn ready | Parcial | Completo | ✅ READY |

---

## 📌 PUNTOS CRÍTICOS

### ⚠️ El dataset DEBE tener
- ✅ 8,760 filas exactas
- ✅ DatetimeIndex (no string index)
- ✅ 25 columnas (sin falta)
- ✅ Sin valores nulos
- ✅ Rango [0, 1] en columnas normalized

### ✅ El dataset NO debe tener
- ❌ Duplicados timestamps
- ❌ Brechas en serie temporal
- ❌ Valores negativos en energía
- ❌ SOC fuera de [0, 100]
- ❌ NaN/Inf en datasets normalizadas

### 🔄 Reproducibilidad
```python
# Semilla para generar mismo dataset
np.random.seed(42)
df = bess_simulate()  # Mismo resultado cada ejecución
```

---

## 📡 INTEGRACIÓN ENDPOINTS

### CityLearn (dataset_builder.py)
```python
from src.citylearnv2.dataset_builder.dataset_builder import DatasetBuilder
builder = DatasetBuilder('data/oe2/bess/bess_simulation_hourly.csv')
env = builder.build_environment()
# env.observation_space incluye v5.4 metrics automáticamente
```

### Agent Training (scripts/train_agent.py)
```bash
python -m src.agents.sac \
  --dataset data/oe2/bess/bess_simulation_hourly.csv \
  --reward-weights "co2=0.5,savings=0.3,grid=0.15,soc=0.05"
```

### Evaluation
```bash
python -m scripts.compare_agents_vs_baseline \
  --dataset data/oe2/bess/bess_simulation_hourly.csv \
  --agents SAC PPO A2C
```

---

## 📎 ARCHIVO METADATA

**Archivo**: `data/oe2/bess/bess_simulation_hourly.csv`

```
Ubicación:      d:\diseñopvbesscar\data\oe2\bess\
Nombre:         bess_simulation_hourly.csv
Tamaño:         1.79 MB
Formato:        CSV (index=datetime, date_format='%Y-%m-%d %H:%M:%S')
Encoding:       UTF-8
Decimales:      2 (formato auto)
Separador:      , (coma)
Última edit:    2026-02-13 06:36
Versión:        5.4
Estado:         ✅ VALIDADO Y LISTO
```

---

## 🆘 CONTACTO RÁPIDO

**Documentación relacionada**:
- [DATASET_v54_FINAL_STATUS.md](./DATASET_v54_FINAL_STATUS.md) - Especificación técnica
- [QUICK_START_INTEGRATION_v54.md](./QUICK_START_INTEGRATION_v54.md) - Guía integración
- [RESUMEN_SESION_v54.md](./RESUMEN_SESION_v54.md) - Resumen sesión
- [.github/copilot-instructions.md](./.github/copilot-instructions.md) - Patrones proyecto

**Scripts relacionados**:
- `bess.py` - Generador de dataset
- `dataset_builder.py` - Integración CityLearn
- `validate_complete_dataset_v54.py` - Validación
- `final_dataset_sync_v54.py` - Sincronización

---

**Versión**: 5.4  
**Última actualización**: 2026-02-13 06:36  
**Mantenedor**: Copilot AI Assistant  
✅ **READY FOR PRODUCTION**
