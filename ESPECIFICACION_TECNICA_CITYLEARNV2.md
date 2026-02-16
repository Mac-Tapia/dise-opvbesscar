# 🔧 ESPECIFICACIÓN TÉCNICA: Dataset para CityLearnv2

**Archivo**: `data/oe2/chargers/chargers_ev_ano_2024_v3.csv`  
**Generado**: 2026-02-16  
**Status**: ✅ **Listo para CityLearnv2**

---

## 📄 Estructura General

```
Índice:    datetime (2024-01-01 a 2024-12-30, 8,760 filas)
Columnas:  357 (38 sockets × 5 dinámicas + 5 constantes + 47 agregadas)
Formato:   CSV con índice datetime
Rango:     8,760 horas (1 año completo)
Validación: ✅ TODAS las restricciones cumplidas
```

---

## 📊 Columnas Agrupadas por Función

### GRUPO 1: Energía y Demanda (4 columnas)

| Columna | Tipo | Rango | Descripción |
|---------|------|-------|-------------|
| `ev_demand_kwh` | float | 0-500 | **Alias principal para CityLearn** (= ev_energia_total_kwh) |
| `ev_energia_total_kwh` | float | 0-500 | Suma de potencia de todos 38 sockets |
| `ev_energia_motos_kwh` | float | 0-450 | Energía de sockets 0-29 (motos) |
| `ev_energia_mototaxis_kwh` | float | 0-80 | Energía de sockets 30-37 (taxis) |

**Ejemplo horario**:
- 12:00 PM: 15 motos × 3.5 kW = 52.5 kWh motos
- 12:00 PM: 2 taxis × 3.1 kW = 6.2 kWh taxis
- **Total**: ev_demand_kwh = 58.7 kWh

---

### GRUPO 2: Cantidad de Vehículos (3 columnas)

| Columna | Tipo | Rango | Descripción |
|---------|------|-------|-------------|
| `cantidad_motos_activas` | int | 0-30 | Número de motos siendo cargadas esta hora |
| `cantidad_mototaxis_activas` | int | 0-8 | Número de taxis siendo cargados esta hora |
| `cantidad_total_vehiculos_activos` | int | 0-38 | Total de vehículos simultáneamente cargándose |

**Estadísticas anuales**:
- Promedio motos/hora: 11.86
- Máximo motos: 30
- Ocupación media: ~40% de capacidad

**Uso para agentes**:
- Determinar "congestión" de sockets
- Priorizar cargas cuando hay pocas
- Predecir demanda próxima

---

### GRUPO 3: CO₂ y Emisiones (5 columnas)

#### A. Reducción Directa (no usar gasolina)

| Columna | Tipo | Rango | Descripción |
|---------|------|-------|-------------|
| `co2_reduccion_motos_kg` | float | 0-200 | CO₂ evitado por energía en motos (energía × 0.87) |
| `co2_reduccion_mototaxis_kg` | float | 0-40 | CO₂ evitado por energía en taxis (energía × 0.47) |
| `reduccion_directa_co2_kg` | float | 0-240 | Total CO₂ evitado por cambio de combustible |

#### B. Emisiones del Grid

| Columna | Tipo | Rango | Descripción |
|---------|------|-------|-------------|
| `co2_grid_kwh` | float | 0-200 | CO₂ generado por importación (energía × 0.4521) |

#### C. Neto

| Columna | Tipo | Rango | Descripción |
|---------|------|-------|-------------|
| `co2_neto_por_hora_kg` | float | -50 a 150 | CO₂ neto (reducción - grid) = impacto real |

**Ejemplo horario**:
```
Energía: 50 kWh (40 kWh motos + 10 kWh taxis)

co2_reduccion_motos = 40 × 0.87 = 34.8 kg (evitado)
co2_reduccion_mototaxis = 10 × 0.47 = 4.7 kg (evitado)
reduccion_directa_co2 = 39.5 kg (evitado total)

co2_grid = 50 × 0.4521 = 22.6 kg (importado)

co2_neto = 39.5 - 22.6 = 16.9 kg (NETO evitado)
```

**Interpretación**:
- Si 50 kWh cargados dejan huella neta de +16.9 kg CO₂
- Significa que cambiar de gasolina a EV es beneficioso en la red diesel de Iquitos

---

### GRUPO 4: Tarifa Eléctrica (3 columnas)

| Columna | Tipo | Rango | Descripción |
|---------|------|-------|-------------|
| `is_hora_punta` | int (0-1) | 0 o 1 | 1 si 18:00-22:00, 0 en otro caso |
| `tarifa_aplicada_soles` | float | 0.28-0.45 | Tarifa OSINERGMIN aplicable (S/./kWh) |
| `costo_carga_ev_soles` | float | 0-225 | Costo de esta hora: energía × tarifa |

**Tarifas fijas**:
- Hora Punta (18-22h): S/. 0.45/kWh
- Fuera Punta (resto): S/. 0.28/kWh

**Horas punta anuales**: 1,460 (= 365 días × 4 horas)

---

### GRUPO 5: Estado por Socket (38 sockets × 9 columnas = 342 columnas)

Nombrados como: `socket_000`, `socket_001`, ..., `socket_037`

#### Sockets 0-29: Motos (30 sockets × 2 por charger)
- power_type = MOTO
- capacity_kwh = 4.6

#### Sockets 30-37: Mototaxis (8 sockets × 2 por charger)
- power_type = MOTOTAXI  
- capacity_kwh = 7.4

#### Columnas por Socket

| Sub-columna | Tipo | Descripción |
|-------------|------|-------------|
| `socket_XXX_charger_power_kw` | float (const) | 7.4 (Modo 3 monofásico) |
| `socket_XXX_battery_kwh` | float (const) | 4.6 (motos) o 7.4 (taxis) |
| `socket_XXX_vehicle_type` | str (const) | "MOTO" o "MOTOTAXI" |
| `socket_XXX_active` | int (0-1) | 1 si hay vehículo, 0 si vacío |
| `socket_XXX_charging_power_kw` | float | Potencia instantánea cargando (0 si vacío) |
| `socket_XXX_soc_current` | float | SOC actual (0-1) |
| `socket_XXX_soc_arrival` | float | SOC al llegar (variable 0.1-0.4) |
| `socket_XXX_soc_target` | float | SOC objetivo (variable 0.6-1.0) |
| `socket_XXX_vehicle_count` | int | Contador histórico de vehículos en esta toma |

**Ejemplo fila: socket_005 (moto)**
```
socket_005_charger_power_kw = 7.4
socket_005_battery_kwh = 4.6
socket_005_vehicle_type = MOTO
socket_005_active = 1 (hay moto cargándose)
socket_005_charging_power_kw = 3.2 (potencia instantánea)
socket_005_soc_current = 0.65 (65% batería)
socket_005_soc_arrival = 0.20 (llegó con 20%)
socket_005_soc_target = 0.85 (quiere cargar a 85%)
socket_005_vehicle_count = 156 (156 motos han pasado por este socket en el año)
```

---

## 🎯 Columnas Recomendadas por Caso de Uso

### Para Agentes RL Estándar

```python
reward_columns = [
    'reduccion_directa_co2_kg',      # Minimizar CO2 del cambio combustible
    'ev_demand_kwh',                  # Minimizar energía/costo
    'co2_neto_por_hora_kg',          # Minimizar impacto neto
]

observation_columns = [
    'ev_demand_kwh',                  # Estado de demanda
    'cantidad_motos_activas',         # Estado de congestión
    'cantidad_mototaxis_activas',
    'is_hora_punta',                  # Para trigger de precio
    'tarifa_aplicada_soles',          # Información de tarifa
] + [f'socket_{i:03d}_active' for i in range(38)]  # Estado de sockets
```

### Para Optimización de Costo

```python
cost_columns = [
    'costo_carga_ev_soles',          # Costo directo
    'is_hora_punta',                  # Indicator de tarifa
    'cantidad_total_vehiculos_activos' # Congestión
]
```

### Para Análisis de CO₂

```python
co2_columns = [
    'reduccion_directa_co2_kg',       # CO₂ evitado
    'co2_grid_kwh',                   # CO₂ importado
    'co2_neto_por_hora_kg',           # Neto final
    'ev_energia_motos_kwh',           # Desglose por tipo
    'ev_energia_mototaxis_kwh'
]
```

---

## 📈 Estadísticas Verificadas

### Totales Anuales

```
ENERGÍA:
  Total: 565,875 kWh
  Motos: 476,501 kWh (84.2%)
  Taxis: 89,374 kWh (15.8%)
  
CO₂ EVITADO (cambio combustible):
  Total: 456,561 kg
  Motos: 414,555 kg
  Taxis: 42,006 kg

CO₂ GRID (importación):
  Total: 255,832 kg
  
CO₂ NETO (impacto real):
  Total: 200,729 kg (evitado neto)
  Promedio: 22.91 kg/hora

TARIFA:
  Costo anual: S/. 192,457
  Promedio: S/. 0.340/kWh (ponderado)
```

### Por Tipo de Vehículo

```
MOTOS (30 sockets, sockets 0-29):
  Energía: 476.5 MWh/año
  Promedio carga: 54.4 kWh/hora
  Máximo: ~450 kWh/hora (cuando 30 activos)
  CO₂ factor: 0.87 kg/kWh
  
MOTOTAXIS (8 sockets, sockets 30-37):
  Energía: 89.4 MWh/año
  Promedio carga: 10.2 kWh/hora
  Máximo: ~80 kWh/hora (cuando 8 activos)
  CO₂ factor: 0.47 kg/kWh
```

---

## 🔌 Integración con CityLearnv2

### Mapeo Recomendado

```python
from citylearnv2.data import DataSource

config = {
    'path': 'data/oe2/chargers/chargers_ev_ano_2024_v3.csv',
    'columns': {
        'demand': 'ev_demand_kwh',                    # Demanda EV
        'generation': None,                           # No hay solar aquí
        'emission_factor': 'co2_grid_kwh',            # Factor emisión
        'price': 'tarifa_aplicada_soles',             # Precio eléctrico
        'observation_demand': 'ev_demand_kwh',
        'vehicle_count': 'cantidad_total_vehiculos_activos',
    },
    'reward_function': {
        'co2_reduction': 'reduccion_directa_co2_kg',  # Maximizar
        'co2_grid': 'co2_grid_kwh',                   # Minimizar
        'cost': 'costo_carga_ev_soles',               # Minimizar
    }
}

ds = DataSource(config)
```

### Observación por Hora

Agentes reciben vector de observación que incluye:

```python
observation = {
    'ev_demand': 58.7,                    # kWh esta hora
    'n_motos_active': 15,                 # Motos cargándose
    'n_taxis_active': 2,                  # Taxis cargándose
    'price': 0.45,                        # S/./kWh
    'is_peak': 1,                         # Hora punta
    'co2_factor': 0.4521,                 # kg CO2/kWh grid
    'socket_states': [                    # 38 valores
        {'active': 1, 'soc': 0.65, 'power': 3.2},  # socket_0
        {'active': 0, 'soc': 0.0, 'power': 0.0},   # socket_1
        ...
    ]
}
```

### Reward por Hora

```python
reward = {
    'co2_evitado_direct': 39.5,           # kg (cambio de combustible)
    'co2_generado_grid': 26.5,            # kg (diesel importado)
    'co2_neto': 13.0,                     # kg (impacto real)
    'costo': 26.0,                        # S/. (tarifa × energía)
}

# Weighted reward (ejemplo)
total_reward = (
    0.50 * (39.5 - 26.5) / 50  +          # CO₂ neto (norm by max energy)
    0.30 * (1 - 26.0/200) +               # Costo (norm [0,200])
    0.20 * (15/30)                        # Ocupación motos (norm 30 max)
)
```

---

## ✅ Checklist Antes de Usar

- [x] Dataset existe y es accesible
- [x] Índice datetime válido (8,760 horas)
- [x] 357 columnas presentes
- [x] Energía coherente (motos + taxis = total)
- [x] CO₂ proporcional (factor 0.87 motos, 0.47 taxis aplicado)
- [x] Tarifas correctas (HP 0.45, HFP 0.28)
- [x] Cantidad de vehículos dentro de límites (max 30 motos, 8 taxis)
- [x] Ningún valor NaN o infinito
- [x] Rango de SOC válido (0-1)

---

## 🚀 Script Rápido para Cargar en CityLearn

```python
import pandas as pd
import numpy as np

# Cargar dataset
df = pd.read_csv('data/oe2/chargers/chargers_ev_ano_2024_v3.csv', 
                   index_col=0, parse_dates=True)

# Seleccionar columnas principales
main_cols = [
    'ev_demand_kwh',
    'cantidad_motos_activas',
    'cantidad_mototaxis_activas',
    'reduccion_directa_co2_kg',
    'co2_grid_kwh',
    'co2_neto_por_hora_kg',
    'tarifa_aplicada_soles',
    'costo_carga_ev_soles'
]

df_main = df[main_cols]

# Seleccionar solo sockets activos (para observación)
socket_cols = [col for col in df.columns if '_active' in col or '_soc_' in col]
socket_active = [col for col in df.columns if '_active' in col]

# Usar en CityLearn
env = setup_citylearn(
    demand_col='ev_demand_kwh',
    co2_col='co2_neto_por_hora_kg',
    price_col='tarifa_aplicada_soles',
    active_cols=socket_active,
    data=df
)
```

---

## 📞 Soporte y Validación

**Validador**: `VALIDACION_DATASET_COMPLETO_v2026-02-16.py`

```bash
# Ejecutar validación en cualquier momento
python VALIDACION_DATASET_COMPLETO_v2026-02-16.py
```

**Documentación relacionada**:
- [RESUMEN_FINAL_DATASET_CO2_CANTIDAD_VEHICULOS.md](RESUMEN_FINAL_DATASET_CO2_CANTIDAD_VEHICULOS.md) - Resumen técnico
- [chargers.py](src/dimensionamiento/oe2/disenocargadoresev/chargers.py) - Código de generación

---

**Status**: ✅ **LISTO PARA PRODUCCIÓN**  
**Generado**: 2026-02-16  
**Dataset**: `data/oe2/chargers/chargers_ev_ano_2024_v3.csv`
