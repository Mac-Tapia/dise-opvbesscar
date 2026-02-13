# 📋 REFERENCIA: Columnas Dataset chargers_ev_ano_2024_v3.csv

**Archivo**: `data/oe2/chargers/chargers_ev_ano_2024_v3.csv`  
**Dimensiones**: 8,760 filas × 352 columnas  
**Índice**: DatetimeIndex (2024-01-01 00:00:00 → 2024-12-30 23:00:00)  
**Actualizado**: 2026-02-13

---

## 🎯 VISTA RÁPIDA

### Estructura Columnas

```
[ 38 sockets × 9 variables/socket ] + [ 8 columnas globales ]
= (38 × 9) + 8 = 352 columnas
```

### Distribución de Sockets

| Grupo | Sockets | Rango | Vehículo | Batería | Cargador |
|---|---:|---|---|---:|---:|
| Motos | 30 | socket_000 → socket_029 | MOTO | 4.6 kWh | 7.4 kW |
| Mototaxis | 8 | socket_030 → socket_037 | MOTOTAXI | 7.4 kWh | 7.4 kW |
| **TOTAL** | **38** | | | | **281.2 kW** |

---

## 🔌 COLUMNAS POR SOCKET (9 Variables × 38 Sockets = 342 Columnas)

### Nomenclatura
```
socket_{id:03d}_{variable}

Ejemplo:
  socket_000_soc_current    (socket 0, variable soc_current)
  socket_037_charging_power_kw (socket 37, variable charging_power_kw)
```

### Variables por Socket

#### 1. Potencia Nominal Cargador (ESTÁTICA)
```
socket_{id}_charger_power_kw

Valores:     7.4 kW (constante para todas las horas)
Unidad:      kW
Uso:         Referencia spec cargador (Modo 3, 32A @ 230V)
Aplicable:   Todos los 38 sockets
Tipo:        Constante numérica
```

#### 2. Capacidad Batería (ESTÁTICA)
```
socket_{id}_battery_kwh

Motos (0-29):     4.6 kWh
Mototaxis (30-37): 7.4 kWh
Unidad:            kWh
Uso:               Energía requerida para carga completa
Aplicable:         Todos los 38 sockets
Tipo:              Constante por tipo vehículo
```

#### 3. Tipo Vehículo (ESTÁTICA)
```
socket_{id}_vehicle_type

Valores:    "MOTO" (sockets 0-29) o "MOTOTAXI" (sockets 30-37)
Unidad:     Texto
Uso:        Identificar tipo para factor CO2 diferenciado
Aplicable:  Todos los 38 sockets
Tipo:       Constante por socket
```

#### 4. SOC Actual During Carga (DINÁMICA)
```
socket_{id}_soc_current

Rango:      [0.0, 1.0] (0% a 100%)
Unidad:     Fracción (normalizada)
Actualización: Cada hora (cuando hay vehículo en carga)
Uso:        Observable para RL agent
Aplicable:  Todos los 38 sockets
Tipo:       Variable por hora (0 si socket inactivo)
```

#### 5. SOC al Llegar (DINÁMICA)
```
socket_{id}_soc_arrival

Rango:      [0.0, 1.0]
Unidad:     Fracción
Cuando:     Se registra al conectar vehículo
Uso:        Input para calcular energía requerida
Aplicable:  Todos los 38 sockets
Tipo:       Estocástico (Poisson distribuido)
```

#### 6. SOC Objetivo (DINÁMICA)
```
socket_{id}_soc_target

Rango:      Típicamente 1.0 (100%)
Unidad:     Fracción
Uso:        Meta de Carga
Aplicable:  Todos los 38 sockets
Tipo:       Variable (puede ser < 1.0 ciertos casos)
```

#### 7. Estado Activo (DINÁMICA)
```
socket_{id}_active

Valores:    1 (hay vehículo cargando) o 0 (inactivo)
Unidad:     Binaria {0, 1}
Actualización: Cada hora
Uso:        Indica si socket está disponible para control
Aplicable:  Todos los 38 sockets
Tipo:       Binaria
```

#### 8. Potencia De Carga Instantánea (DINÁMICA - MÁS IMPORTANTE)
```
socket_{id}_charging_power_kw

Rango:       [0, 4.588] kW
Unidad:      kW
Fórmula:     power_nominal × efficiency_factor
             = 7.4 kW × 0.62 = 4.588 kW máximo
Eficiencia:  62% (pérdidas cargador + cable + batería + taper)
Cuando:      0 si socket inactivo, > 0 si activo
Actualización: Cada hora
Uso:         
  • Observable para RL: consumo instantáneo
  • Sumado: demanda total hora (ev_energia_total_kwh)
  • Control: reducir potencia en picos de demanda
Aplicable:   Todos los 38 sockets
Tipo:        Continua [0, 4.588]
```

#### 9. Contador de Vehículos en Cola (DINÁMICA)
```
socket_{id}_vehicle_count

Rango:       [0, N] (típicamente 0-3)
Unidad:      Entero
Uso:         Métrica para congestión (opcional para RL)
Aplicable:   Todos los 38 sockets
Tipo:        Discreta
```

---

## 🌐 COLUMNAS GLOBALES (8 Columnas)

### 1. Marca Hora Punta
```
is_hora_punta

Valores:    1 (hora punta: 18:00-22:59) o 0 (HFP)
Unidad:     Binaria
Actualización: Cada hora (determinista)
Uso:        Selector de tarifa, variable para RL
Aplicable:  Todas las 8,760 horas
```

### 2. Tarifa Aplicada
```
tarifa_aplicada_soles

Hora Punta (18:00-22:59):  0.45 S/./kWh
Fuera de Punta (resto):    0.28 S/./kWh
Unidad:                     S/./kWh
Fuente:                     OSINERGMIN Resolución 047-2024-OS/CD
Uso:                        Observable para minimizar costo en RL
Aplicable:                  Todas las 8,760 horas
```

### 3. Energía Total Cargada (Suma de Sockets)
```
ev_energia_total_kwh

Fórmula:  Σ(socket_{id}_charging_power_kw) para id=0..37
Rango:    [0, 38×4.588] = [0, 174.3] kWh/hora
Unidad:   kWh
Actualización: Cada hora
Uso:      
  • Total demand del EV charging subsystem
  • Suma global de todos los sockets
  • Observable para RL (demanda)
Aplicable: Todas las 8,760 horas
```

### 4. Energía por Tipo - Motos
```
ev_energia_motos_kwh

Fórmula:  Σ(socket_{id}_charging_power_kw) para id=0..29
Rango:    [0, 30×4.588] = [0, 137.6] kWh/hora
Unidad:   kWh
Uso:      
  • Subdivisión por tipo vehículo
  • Control segregado motos vs mototaxis
  • Cálculo de CO2 específico motos
Aplicable: Todas las 8,760 horas
```

### 5. Energía por Tipo - Mototaxis
```
ev_energia_mototaxis_kwh

Fórmula:  Σ(socket_{id}_charging_power_kw) para id=30..37
Rango:    [0, 8×4.588] = [0, 36.7] kWh/hora
Unidad:   kWh
Uso:      
  • Subdivisión por tipo vehículo
  • Control segregado
  • Cálculo de CO2 específico mototaxis
Aplicable: Todas las 8,760 horas
```

### 6. Reducción CO2 - Motos
```
co2_reduccion_motos_kg

Fórmula:  ev_energia_motos_kwh × 0.87 kg CO2/kWh
Rango:    [0, 137.6 × 0.87] = [0, 119.7] kg/hora
Unidad:   kg CO2/hora
Factor:   0.87 kg CO2/kWh (neto: gasolina - grid)
Uso:      
  • Reducción CO2 directa por cambio combustible (moto gasolina → EV)
  • Beneficio ambiental específico motos
  • Observable para reward function RL (ambiental)
Aplicable: Todas las 8,760 horas
```

### 7. Reducción CO2 - Mototaxis
```
co2_reduccion_mototaxis_kg

Fórmula:  ev_energia_mototaxis_kwh × 0.47 kg CO2/kWh
Rango:    [0, 36.7 × 0.47] = [0, 17.3] kg/hora
Unidad:   kg CO2/hora
Factor:   0.47 kg CO2/kWh (neto: gasolina 3-wheel - grid)
Uso:      
  • Reducción CO2 directa por cambio combustible (taxi gasolina → EV)
  • Beneficio ambiental específico mototaxis
  • Observable para reward function RL (ambiental)
Aplicable: Todas las 8,760 horas
```

### 8. Reducción CO2 Total
```
reduccion_directa_co2_kg

Fórmula:  co2_reduccion_motos_kg + co2_reduccion_mototaxis_kg
Rango:    [0, 119.7 + 17.3] = [0, 137.0] kg/hora
Unidad:   kg CO2/hora
Uso:      
  • Reducción CO2 total DIRECTA (cambio combustible)
  • Métrica clave para RL reward (ambiental)
  • Agregado anual: 356,733.7 kg = 356.7 ton/año
Aplicable: Todas las 8,760 horas
```

### 9. Alias para CityLearn (COPIA)
```
ev_demand_kwh

Contenido: Alias de ev_energia_total_kwh
Propósito: Compatibilidad con nomenclatura CityLearn
Unidad:    kWh
```

---

## 📊 ESTADÍSTICAS ANUALES

### Energía

| Métrica | Anual | Máx/hora | Promedio/hora |
|---|---:|---:|---:|
| ev_energia_motos_kwh | 359,149 kWh | 119.3 kWh | 41.0 kWh |
| ev_energia_mototaxis_kwh | 94,201 kWh | 36.7 kWh | 10.8 kWh |
| ev_energia_total_kwh | 453,349 kWh | 156.0 kWh | 51.8 kWh |

### CO2 Reducido (Directo)

| Métrica | Anual | Máx/hora | Promedio/hora |
|---|---:|---:|---:|
| co2_reduccion_motos_kg | 312,459 kg | 103.8 kg | 35.7 kg |
| co2_reduccion_mototaxis_kg | 44,274 kg | 17.3 kg | 5.1 kg |
| reduccion_directa_co2_kg **TOTAL** | **356,734 kg** | **121 kg** | **40.7 kg** |

### Ocupancia

| Métrica | Valor |
|---|---:|
| Horas socket activo (total) | 98,812 horas |
| Promedio sockets activos (simultáneo) | 11.3 / 38 |
| Ocupancia total | 29.7% |

---

## 🎮 CÓMO USAR EN RL (Observables + Actions)

### Observation Space (Ejemplo)

```python
observation_vector = [
    # Global
    df.loc[t, 'ev_energia_total_kwh'],      # Demanda total
    df.loc[t, 'tarifa_aplicada_soles'],     # Precio energía
    df.loc[t, 'reduccion_directa_co2_kg'],  # CO2 ahorrado
    
    # Por socket (vectorizar: 38 valores)
    *[df.loc[t, f'socket_{i:03d}_soc_current'] for i in range(38)],
    *[df.loc[t, f'socket_{i:03d}_active'] for i in range(38)],
    *[df.loc[t, f'socket_{i:03d}_charging_power_kw'] for i in range(38)],
]
```

### Action Space (Ejemplo)

```python
# Control: Ajustar potencia de carga por socket
action = [0.8, 1.0, 0.5, ..., 0.9]  # 38 valores [0, 1]
# Mapear a: actual_power = action[i] × socket_charger_power_kw[i]
```

### Reward Function (Ejemplo)

```python
reward = (
    0.5 * (reduccion_directa_co2_kg / max_co2) +  # Ambiental
    0.3 * (1 - tarifa_aplicada_soles / 0.45) +    # Económico (cargar en HFP)
    0.2 * (-ev_energia_total_kwh / 156.0)          # Eficiencia
)
```

---

## 🔗 INTEGRACIÓN CON dataset_builder.py

El archivo `dataset_builder.py` **automáticamente** extrae:

```python
# Lee chargers_ev_ano_2024_v3.csv y extrae:

for socket_id in range(38):
    soc_values = df[f'socket_{socket_id:03d}_soc_current'].values
    active_values = df[f'socket_{socket_id:03d}_active'].values
    power_values = df[f'socket_{socket_id:03d}_charging_power_kw'].values
    # → Integra en observation space de CityLearn

tariff_values = df['tarifa_aplicada_soles'].values
co2_values = df['reduccion_directa_co2_kg'].values
# → Integra como observables adicionales
```

---

## ✨ RESUMEN DE USO

### Para Control de Sockets Individuales
```
Columnas: socket_{id}_active, socket_{id}_soc_current, socket_{id}_charging_power_kw
Usar para: Decisiones independientes por socket, priorizar carga, reducir picos
```

### Para Optimización Económica
```
Columnas: tarifa_aplicada_soles, ev_energia_total_kwh
Usar para: Despacho inteligente basado en tarifa HP/HFP
```

### Para Optimización Ambiental
```
Columnas: reduccion_directa_co2_kg (+ co2_reduccion_motos_kg, co2_reduccion_mototaxis_kg)
Usar para: Maximizar beneficio ambiental del cambio combustible
```

---

**Columnas totales**: 352  
**Archivo**: `data/oe2/chargers/chargers_ev_ano_2024_v3.csv`  
**Tamaño**: ~2.5 MB  
**Validación**: ✅ Completo
