# 🔧 ESPECIFICACIÓN TÉCNICA: Dataset para CityLearn v2

**Archivo**: `data/oe2/chargers/chargers_ev_ano_2024_v3.csv`  
**Versión**: v2.0  
**Generado**: 2026-02-16  
**Status**: ✅ **Listo para CityLearn v2**

---

## 📄 Estructura General

```
Índice:    datetime (2024-01-01 a 2024-12-30, 8,760 filas)
Columnas:  357 (38 sockets × 9 dinámicas + 47 agregadas)
Formato:   CSV con índice datetime
Rango:     8,760 horas (1 año completo)
Validación: ✅ TODAS las restricciones cumplidas
```

---

## 📊 GRUPOS DE COLUMNAS

### GRUPO 1: Energía y Demanda (4 columnas)

| Columna | Tipo | Rango | Descripción |
|---------|------|-------|-------------|
| `ev_demand_kwh` | float | 0-500 | **Alias principal para CityLearn** |
| `ev_energia_total_kwh` | float | 0-500 | Suma de potencia todos 38 sockets |
| `ev_energia_motos_kwh` | float | 0-450 | Energía sockets 0-29 (motos) |
| `ev_energia_mototaxis_kwh` | float | 0-80 | Energía sockets 30-37 (taxis) |

**Ejemplo horario**:
```
12:00 PM: 15 motos × 3.5 kW = 52.5 kWh motos
12:00 PM: 2 taxis × 3.1 kW = 6.2 kWh taxis
TOTAL: ev_demand_kwh = 58.7 kWh
```

---

### GRUPO 2: Cantidad de Vehículos (3 columnas)

| Columna | Tipo | Rango | Descripción |
|---------|------|-------|-------------|
| `cantidad_motos_activas` | int | 0-30 | Motos siendo cargadas esta hora |
| `cantidad_mototaxis_activas` | int | 0-8 | Taxis siendo cargados esta hora |
| `cantidad_total_vehiculos_activos` | int | 0-38 | Total simultáneo |

**Estadísticas anuales**:
- Promedio motos/hora: 11.86
- Máximo motos: 30
- Ocupación media: ~40% de capacidad

---

### GRUPO 3: CO₂ y Emisiones (5 columnas)

#### A. Reducción Directa (evitar gasolina)

| Columna | Tipo | Rango | Descripción |
|---------|------|-------|-------------|
| `co2_reduccion_motos_kg` | float | 0-200 | CO₂ evitado motos (energía × 0.87) |
| `co2_reduccion_mototaxis_kg` | float | 0-40 | CO₂ evitado taxis (energía × 0.47) |
| `reduccion_directa_co2_kg` | float | 0-240 | Total CO₂ evitado combustible |

#### B. Emisiones Grid

| Columna | Tipo | Rango | Descripción |
|---------|------|-------|-------------|
| `co2_grid_kwh` | float | 0-200 | CO₂ generado importación (energía × 0.4521) |

#### C. Neto (Impacto Real)

| Columna | Tipo | Rango | Descripción |
|---------|------|-------|-------------|
| `co2_neto_por_hora_kg` | float | -50 a 150 | CO₂ neto = reducción - grid |

**Ejemplo**:
```
Energía: 50 kWh (40 kWh motos + 10 kWh taxis)

Reducción motos: 40 × 0.87 = 34.8 kg ↓
Reducción taxis: 10 × 0.47 = 4.7 kg ↓
Total reducción: 39.5 kg ↓ (evitado)

CO₂ grid: 50 × 0.4521 = 22.6 kg ↑ (generado)

CO₂ NETO: 39.5 - 22.6 = 16.9 kg ✅ (evitado neto)
```

**Interpretación**: El cambio de gasolina a EV en Iquitos es beneficioso en 16.9 kg/50 kWh.

---

### GRUPO 4: Tarifa Eléctrica (3 columnas)

| Columna | Tipo | Rango | Descripción |
|---------|------|-------|-------------|
| `is_hora_punta` | int | 0-1 | 1 si 18:00-22:00 |
| `tarifa_aplicada_soles` | float | 0.28-0.45 | OSINERGMIN aplicable |
| `costo_carga_ev_soles` | float | 0-225 | energía × tarifa |

**Tarifas**:
- Hora Punta (18-22h): S/. 0.45/kWh
- Fuera Punta (resto): S/. 0.28/kWh

---

### GRUPO 5: Estado por Socket (38 × 9 columnas = 342 columnas)

**Sockets 0-29**: Motos (30), capacity = 4.6 kWh  
**Sockets 30-37**: Mototaxis (8), capacity = 7.4 kWh

**Columnas por Socket** (ejemplo socket_005):

| Sub-columna | Valor | Descripción |
|-------------|-------|-------------|
| `socket_005_charger_power_kw` | 7.4 | Potencia Modo 3 (const) |
| `socket_005_battery_kwh` | 4.6 | Capacidad moto (const) |
| `socket_005_vehicle_type` | "MOTO" | Tipo vehículo (const) |
| `socket_005_active` | 1 | Hay vehículo (0-1) |
| `socket_005_charging_power_kw` | 3.2 | Potencia instantánea |
| `socket_005_soc_current` | 0.65 | SOC actual (0-1) |
| `socket_005_soc_arrival` | 0.20 | SOC llegada (0.1-0.4) |
| `socket_005_soc_target` | 0.85 | SOC goal (0.6-1.0) |
| `socket_005_vehicle_count` | 156 | Vehículos históricos |

---

## 🎯 Selección de Columnas por Caso de Uso

### Para Agentes RL (Observación + Reward)

```python
# Observación (input al agente)
observation = [
    'ev_demand_kwh',
    'cantidad_motos_activas',
    'cantidad_mototaxis_activas',
    'is_hora_punta',
    'tarifa_aplicada_soles',
] + [f'socket_{i:03d}_active' for i in range(38)]

# Reward (feedback del agente)
reward = [
    'reduccion_directa_co2_kg',      # Maximizar
    'co2_grid_kwh',                  # Minimizar
    'co2_neto_por_hora_kg',          # Maximizar (neto evitado)
]
```

### Para Análisis de CO₂

```python
co2_analysis = [
    'reduccion_directa_co2_kg',
    'co2_grid_kwh',
    'co2_neto_por_hora_kg',
    'ev_energia_motos_kwh',
    'ev_energia_mototaxis_kwh'
]
```

### Para Optimización de Costo

```python
cost_columns = [
    'costo_carga_ev_soles',
    'is_hora_punta',
    'cantidad_total_vehiculos_activos'
]
```

---

## 📈 ESTADÍSTICAS VERIFICADAS

### Totales Anuales

```
ENERGÍA:
  Total:   565,875 kWh
  Motos:   476,501 kWh (84.2%)
  Taxis:   89,374 kWh (15.8%)
  
CO₂ EVITADO (combustible):
  Total:   456,561 kg
  Motos:   414,555 kg
  Taxis:   42,006 kg

CO₂ GRID (importación):
  Total:   255,832 kg
  
CO₂ NETO (impacto real):
  Total:   200,729 kg ✅ EVITADO
  Promedio: 22.91 kg/hora
```

### Por Vehículo

```
MOTOS (sockets 0-29):
  Energía: 476.5 MWh/año
  Promedio: 54.4 kWh/hora
  Máximo: ~450 kWh/hora (30 motos simultáneas)
  Factor CO₂: 0.87 kg/kWh
  
MOTOTAXIS (sockets 30-37):
  Energía: 89.4 MWh/año
  Promedio: 10.2 kWh/hora
  Máximo: ~80 kWh/hora (8 taxis simultáneos)
  Factor CO₂: 0.47 kg/kWh
```

---

## 🔌 INTEGRACIÓN CON CITYLEARNV2

```python
import pandas as pd
from citylearnv2.data import DataSource

# Cargar dataset
df = pd.read_csv('data/oe2/chargers/chargers_ev_ano_2024_v3.csv',
                  index_col=0, parse_dates=True)

# Configurar para CityLearn
config = {
    'path': 'data/oe2/chargers/chargers_ev_ano_2024_v3.csv',
    'columns': {
        'demand': 'ev_demand_kwh',
        'emission_factor': 'co2_grid_kwh',
        'price': 'tarifa_aplicada_soles',
    },
    'reward_weights': {
        'co2_direct': 0.50,      # Reducción directa
        'co2_grid': 0.20,        # Minimizar grid
        'cost': 0.15,            # Costo
        'stability': 0.10,       # Ramping suave
        'constraint': 0.05,      # SOC respeto
    }
}
```

### Observación por Hora

```python
observation_t = {
    'ev_demand': 58.7,
    'motos_active': 15,
    'taxis_active': 2,
    'price': 0.45,
    'peak': 1,
    'co2_factor': 0.4521,
    'socket_states': [  # 38 valores
        {'active': 1, 'soc': 0.65, 'power': 3.2},
        ...
    ]
}
```

### Reward por Hora

```python
reward_components = {
    'co2_evitado_directo': 39.5,  # kg
    'co2_grid': 22.6,             # kg
    'co2_neto': 16.9,             # kg ✅ (meta)
    'costo': 26.0,                # S/.
}

# Ejemplo weighted reward
reward = (
    0.50 * (39.5 - 22.6) / 50 +    # CO₂ neto
    0.30 * max(0, 1 - 26.0/200) +  # Costo bajo
    0.20 * (15/30)                 # Ocupación motos
)
```

---

## ✅ CHECKLIST PRE-USO

- [x] Dataset existe (`data/oe2/chargers/chargers_ev_ano_2024_v3.csv`)
- [x] 8,760 horas (1 año completo)
- [x] 357 columnas presentes
- [x] Energía coherente: motos + taxis = total
- [x] CO₂ factores correctos (0.87 motos, 0.47 taxis)
- [x] Tarifas: HP 0.45, HFP 0.28 S/./kWh
- [x] Cantidades: max 30 motos, 8 taxis
- [x] Sin NaN, Inf, negativos (donde no apliquen)
- [x] SOC rango 0-1

---

## 🚀 SCRIPT CARGA RÁPIDA

```python
import pandas as pd
import numpy as np

# Cargar
df = pd.read_csv('data/oe2/chargers/chargers_ev_ano_2024_v3.csv',
                  index_col=0, parse_dates=True)

# Principales
main_cols = [
    'ev_demand_kwh',
    'reduccion_directa_co2_kg',
    'co2_grid_kwh',
    'co2_neto_por_hora_kg',
    'tarifa_aplicada_soles',
]

df_main = df[main_cols]

print(df_main.describe())
print(f"✅ Dataset ready: {df.shape}")
```

---

**Status**: ✅ LISTO PARA PRODUCCIÓN  
**Relacionado**: [REFERENCIAS_ACADEMICAS_COMPLETAS.md](REFERENCIAS_ACADEMICAS_COMPLETAS.md), [RUTAS_DATOS_FIJAS_v58.md](../src/dataset_builder_citylearn/RUTAS_DATOS_FIJAS_v58.md)

