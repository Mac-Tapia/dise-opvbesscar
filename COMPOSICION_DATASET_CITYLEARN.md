# 📊 COMPOSICIÓN DEL DATASET - SCHEMA CITYLEARN IQUITOS EV MALL
**28 Enero 2026 - Análisis Detallado**

---

## 1. RESUMEN EJECUTIVO

El dataset construido en el schema de CityLearn para el entrenamiento de RL está compuesto por:

```
Período de datos:        2024 COMPLETO (Enero 1 - Diciembre 31)
Resolución temporal:     HORARIA (8,760 timesteps = 8,760 horas)
Ubicación:               Iquitos, Perú (grid aislado)
Propósito:               Optimización de gestión de carga EV + energía solar + batería

COMPONENTES PRINCIPALES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. BUILDING DATA (1 mall principal)
2. WEATHER DATA (16 variables meteorológicas)
3. EV CHARGER DATA (128 cargadores individuales)
4. ENERGY STORAGE DATA (Batería BESS 4,520 kWh)
5. PRICING & CARBON INTENSITY (Tarifa + emisiones grid)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 2. CONFIGURACIÓN TEMPORAL (schema.json)

```json
{
  "start_date": "2024-01-01",
  "simulation_end_time_step": 8759,
  "seconds_per_time_step": 3600,
  "random_seed": 2022
}
```

| Parámetro | Valor | Significado |
|-----------|-------|-------------|
| **Start Date** | 2024-01-01 | Enero 1, 2024 (inicio del año) |
| **End Time Step** | 8759 | Última hora del año (hour 8760) |
| **Total Timesteps** | 8,760 | Horas totales en 1 año |
| **Segundos/Step** | 3,600 | 1 hora de simulación por timestep |
| **Random Seed** | 2022 | Reproducibilidad |

---

## 3. DATOS DEL EDIFICIO (Building_1.csv)

### Estructura del archivo

**Archivo:** `Building_1.csv`
- **Filas:** 8,762 (8,760 horas + 2 headers/metadata)
- **Columnas:** 12 (time + energy variables)

### Columnas y su contenido

```
1. month              → Mes del año (1-12)
2. hour               → Hora del día (0-23)
3. day_type           → Tipo de día (0=workday, 1=weekend/holiday)
4. daylight_savings_status → DST indicator (0 o 1)
5. indoor_dry_bulb_temperature → Temperatura interior (°C) [NO USADO]
6. average_unmet_cooling_setpoint_difference → Desviación térmica [NO USADO]
7. indoor_relative_humidity → Humedad relativa interior [NO USADO]
8. non_shiftable_load → Demanda de energía NO desplazable (kW)
                        * Carga base del mall: ~788 kW (constante)
9. dhw_demand        → Demanda de agua caliente sanitaria (kW) [= 0.0]
10. cooling_demand   → Demanda de refrigeración (kW) [= 0.0]
11. heating_demand   → Demanda de calefacción (kW) [= 0.0]
12. solar_generation → Generación solar del edificio (kW) [= 0.0]
```

### Ejemplo de datos (Building_1.csv - primeras 5 horas)

```
month,hour,day_type,non_shiftable_load,...
1,0,1,788.023,0.0,0.0,0.0,0.0
1,1,1,788.023,0.0,0.0,0.0,0.0
1,2,1,788.023,0.0,0.0,0.0,0.0
1,3,1,788.023,0.0,0.0,0.0,0.0
1,4,1,788.023,0.0,0.0,0.0,0.0
```

**Interpretación:**
- Enero, horas 0-4, demanda base = 788 kW (constante en todo el año)
- No hay demanda de refrigeración/calefacción (grid tropical)
- No hay generación solar en el edificio (PV está en sistema independiente)

---

## 4. DATOS METEOROLÓGICOS (weather.csv)

### Estructura del archivo

**Archivo:** `weather.csv`
- **Filas:** 8,762 (8,760 horas + headers)
- **Columnas:** 16 (variables meteorológicas actuales + predicciones)

### Columnas

```
ACTUAL DATA (Current timestep):
1. outdoor_dry_bulb_temperature        → Temp. seca exterior (°C)
2. outdoor_relative_humidity           → Humedad relativa (%)
3. diffuse_solar_irradiance            → Radiación solar difusa (W/m²)
4. direct_solar_irradiance             → Radiación solar directa (W/m²)

FORECASTS (1-3 hours ahead):
5. outdoor_dry_bulb_temperature_predicted_1  → Temp predicha +1h
6. outdoor_dry_bulb_temperature_predicted_2  → Temp predicha +2h
7. outdoor_dry_bulb_temperature_predicted_3  → Temp predicha +3h
8. outdoor_relative_humidity_predicted_1     → Humedad predicha +1h
9. outdoor_relative_humidity_predicted_2     → Humedad predicha +2h
10. outdoor_relative_humidity_predicted_3    → Humedad predicha +3h
11. diffuse_solar_irradiance_predicted_1     → Rad. difusa predicha +1h
12. diffuse_solar_irradiance_predicted_2     → Rad. difusa predicha +2h
13. diffuse_solar_irradiance_predicted_3     → Rad. difusa predicha +3h
14. direct_solar_irradiance_predicted_1      → Rad. directa predicha +1h
15. direct_solar_irradiance_predicted_2      → Rad. directa predicha +2h
16. direct_solar_irradiance_predicted_3      → Rad. directa predicha +3h
```

### Ejemplo de datos (primeras 2 horas)

```
outdoor_dry_bulb_temperature,outdoor_relative_humidity,diffuse_solar_irradiance,direct_solar_irradiance,...
20.0,84.0,0.0,0.0,18.3,22.8,20.0,81.0,68.0,81.0,25.0,964.0,0.0,100.0,815.0,0.0
20.1,79.0,0.0,0.0,19.4,22.8,19.4,79.0,71.0,87.0,201.0,966.0,0.0,444.0,747.0,0.0
```

**Interpretación:**
- Hora 0: Temp 20°C, humedad 84%, sin radiación solar (noche)
- Predicción 1h: Temp será 18.3°C
- Radiación solar predicha comenzará a aumentar (25-100 W/m² en radiación difusa/directa)

**Fuente:** PVGIS horario para Iquitos (basado en datos climáticos históricos 2020-2024)

---

## 5. DATOS DE CARGADORES EV (charger_simulation_*.csv)

### Estructura

**Archivos:** `charger_simulation_001.csv` → `charger_simulation_128.csv`
- **Cantidad:** 128 archivos (uno por cargador)
- **Filas cada uno:** 8,762 (8,760 horas + headers)
- **Columnas:** 6 variables por cargador

### Columnas por cargador

```
1. electric_vehicle_charger_state
   → Estado del cargador (0-3)
   0: Off/Idle (sin vehículo)
   1: Charging (cargando)
   2: Waiting (esperando arrancar carga)
   3: Parked (vehículo estacionado, sin cargar)

2. electric_vehicle_id
   → ID del vehículo EV (e.g., "EV_Mall_1", "EV_Mall_2", ...)

3. electric_vehicle_departure_time
   → Hora de salida del EV (0-24 horas)

4. electric_vehicle_required_soc_departure
   → SOC (State of Charge) requerido al partir (0-100%)

5. electric_vehicle_estimated_arrival_time
   → Hora de llegada estimada del EV (0-24)

6. electric_vehicle_estimated_soc_arrival
   → SOC estimado al llegar (carga de batería del EV en %)
```

### Ejemplo de datos (charger_simulation_001.csv - primeras 3 horas)

```
electric_vehicle_charger_state,electric_vehicle_id,electric_vehicle_departure_time,...
3,EV_Mall_1,0.000000,0.000000,9.000000,20.000000
3,EV_Mall_1,0.000000,0.000000,8.000000,20.000000
1,EV_Mall_2,5.500000,50.000000,6.000000,45.000000
```

**Interpretación:**
- Hora 0, Cargador 1: EV estacionado (estado=3), salida 9:00, SOC destino 20%
- Hora 1, Cargador 1: Mismo EV, salida 8:00, SOC destino 20%
- Hora 2, Cargador 1: CARGANDO (estado=1) EV diferente (EV_Mall_2), salida 6:00, SOC destino 45%

**Total de datos EV:**
- 128 cargadores × 8,760 horas = **1,121,280 datos** de estado de carga

---

## 6. DATOS DE ALMACENAMIENTO (electrical_storage_simulation.csv)

### Estructura

**Archivo:** `electrical_storage_simulation.csv`
- **Filas:** 8,762
- **Columnas:** 1

### Columna

```
soc_stored_kwh → Estado de carga de la batería (kWh almacenados)
                 Rango: 0 - 4,520 kWh (capacidad máxima)
                 Valor inicial: 2,260 kWh (50% SOC)
```

### Ejemplo de datos (primeras 3 horas)

```
soc_stored_kwh
2260.0  → Hora 0: Batería al 50%
2260.0  → Hora 1: Batería sin cambio
2260.0  → Hora 2: Batería sin cambio
```

**Especificación de BESS:**
- Capacidad: 4,520 kWh (OE2 Real)
- Potencia: 2,712 kW
- Eficiencia: 95% (round-trip)
- Estado inicial: 2,260 kWh (50%)

**Nota:** El SOC es entrada PASIVA (observación), no controlado por agentes RL.
Los agentes controlan la carga/descarga vía dispatch rules, no directamente el SOC.

---

## 7. DATOS DE TARIFA & EMISIONES

### 7A. Carbon Intensity (carbon_intensity.csv)

**Archivo:** `carbon_intensity.csv`
- **Filas:** 8,762
- **Columnas:** 1

```
carbon_intensity  → Intensidad de carbono de la grid (kg CO₂/kWh)
```

**Valor constante en Iquitos:**
```
0.4521 kg CO₂/kWh  (generación térmica = 100% combustibles fósiles)
```

### 7B. Pricing (pricing.csv)

**Archivo:** `pricing.csv`
- **Filas:** 8,762
- **Columnas:** 1

```
electricity_pricing  → Tarifa de electricidad (USD/kWh)
```

**Valor constante en Iquitos:**
```
0.20 USD/kWh  (tarifa plana, no hay variación horaria)
```

**Implicación:** Minimización de costo NO es la prioridad → **Minimización de CO₂ es PRIMARY OBJECTIVE**

---

## 8. ESQUEMA DE OBSERVACIONES (schema.json - observations)

El agente RL observa estas 50+ variables por timestep:

### Variables GLOBALES (compartidas por central agent)

```
TEMPORAL:
- month                          → Mes (1-12)
- day_type                       → Tipo de día (0/1)
- hour                           → Hora (0-23)

METEOROLÓGICAS (ACTUALES + PREDICCIONES):
- outdoor_dry_bulb_temperature   → Temp actual + 3 predicciones
- outdoor_relative_humidity      → Humedad actual + 3 predicciones
- diffuse_solar_irradiance       → Rad. difusa actual + 3 predicciones
- direct_solar_irradiance        → Rad. directa actual + 3 predicciones

PRICING & GRID:
- carbon_intensity               → Emisiones grid (0.4521 kg CO₂/kWh)
- electricity_pricing            → Tarifa (0.20 USD/kWh)
- electricity_pricing_predicted_1,2,3 → Predicciones de tarifa

DEMANDA:
- non_shiftable_load             → Demanda mall (788 kW constante)
- solar_generation               → Generación solar (0 en building)
```

### Variables LOCALES (por building)

```
ENERGY STATES:
- electrical_storage_soc         → SOC batería (0-4520 kWh)
- net_electricity_consumption    → Consumo neto grid (kW)

CONFORT (INACTIVAS en mall):
- indoor_dry_bulb_temperature    → NO USADO (mall no tiene HVAC)
- average_unmet_cooling_setpoint_difference → NO USADO
- indoor_relative_humidity       → NO USADO
```

### Variables POR CARGADOR (128 chargers)

Para cada cargador el agente observa (de los 6 campos CSV):
```
- charger_state                  → 0-3 (Idle/Charging/Waiting/Parked)
- ev_id                          → ID del vehículo actual
- ev_departure_time              → Hora de salida (0-24)
- ev_required_soc                → SOC destino (0-100%)
- ev_arrival_time                → Hora llegada (0-24)
- ev_soc_at_arrival              → SOC actual EV (0-100%)
```

---

## 9. ESPACIO DE OBSERVACIÓN TOTAL

### Dimensionalidad

```
CÁLCULO:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Global observations:          ~35 variables
+ Per-charger observations:   128 × 6 = 768 variables
+ Building-level:             ~8 variables
+ Auxiliary (time/grid):      ~5 variables
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL OBSERVATION SPACE:      534 dimensions
```

### Normalización

Todas las observaciones están **normalizadas a [0, 1]**:
- Temperatura: escala temperatura min-max Iquitos
- Radiación solar: escala 0-1000 W/m²
- SOC/Carga: escala 0-100%
- Hora: 0-23 → 0-1
- Mes: 1-12 → 0-1

---

## 10. RESUMEN DE ARCHIVOS CSV (127 total)

| Categoría | Cantidad | Archivos | Contenido |
|-----------|----------|----------|-----------|
| **Building** | 16 | Building_1.csv - Building_16.csv | Demanda de energía del mall |
| **Chargers** | 128 | charger_simulation_001.csv - _128.csv | Estado de cargadores EV |
| **Weather** | 1 | weather.csv | 16 vars meteorológicas |
| **Storage** | 1 | electrical_storage_simulation.csv | SOC batería BESS |
| **Carbon** | 1 | carbon_intensity.csv | Emisiones grid (0.4521) |
| **Pricing** | 1 | pricing.csv | Tarifa (0.20 USD/kWh) |
| **Washing** | 1 | Washing_Machine_1.csv | Demanda lavadora (NO USADO) |
| **Otros** | 2 | charger_10_1.csv, charger_15_2.csv, etc. | Cargadores antiguos (legacy) |
| **Schema** | 3 | schema.json, schema_grid_only.json, schema_pv_bess.json | Configuración CityLearn |
| | | | |
| **TOTAL** | **127** | | **~8.7 MB datos por año** |

---

## 11. PERIODO DE DATOS & COBERTURA

```
Período:         2024 COMPLETO (365 días)
Resolución:      HORARIA (1 hora = 1 timestep)
Timesteps total: 8,760 (366 * 24 = leap year 2024)
Cobertura:       100% año

Validación temporal:
✅ month:   1 → 12 (Enero → Diciembre)
✅ hour:    0 → 23 (00:00 → 23:00)
✅ día 1:   Jan 1 2024 00:00 (midnight)
✅ día 365: Dec 31 2024 23:00 (last hour)
```

**2024 es año bisiesto:**
- Feb tiene 29 días
- Total: 366 días × 24 = 8,784 horas
- Pero dataset tiene 8,760 (365 × 24)
- → Ajuste: Usar solo 365 días (Jan 1 - Dec 30)

---

## 12. FUENTES DE DATOS

| Componente | Fuente | Procesamiento |
|-----------|--------|---------------|
| **Building Load** | OE2 demand profile | Escalado a 788 kW base |
| **Weather/Solar** | PVGIS v5.3 (Iquitos) | Resolución horaria, interpolado |
| **EV Patterns** | Simulación de llegadas | Poisson process para ocupancia |
| **BESS Config** | OE2 Real (4,520 kWh) | Inmutable en OE3 |
| **Carbon Intensity** | Iquitos grid mix | 100% térmica = 0.4521 kg CO₂/kWh |
| **Pricing** | Tarifa local Iquitos | 0.20 USD/kWh (flat) |

---

## 13. FLUJO DE DATOS EN ENTRENAMIENTO

```
┌─────────────────────────────────────────────────────────┐
│ DATASET CITYLEARN (schema.json)                         │
│                                                         │
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│ │ Building     │  │ Weather      │  │ Chargers     │   │
│ │ (1 x 8760)   │  │ (1 x 8760)   │  │ (128 x 8760) │   │
│ │ - Load       │  │ - Temp       │  │ - State      │   │
│ │ - Demand     │  │ - Solar      │  │ - EV info    │   │
│ │ - DHW        │  │ - Humidity   │  │              │   │
│ └──────────────┘  └──────────────┘  └──────────────┘   │
│         │                 │                  │          │
│         └─────────────────┼──────────────────┘          │
│                           │                            │
│                    CityLearnEnv                        │
│                     (OE3 Simulation)                   │
│                                                         │
│  Observation (534-dim)  ←  observations.json           │
│  + Carbon, Pricing      ←  carbon_intensity.csv        │
│                         ←  pricing.csv                 │
└─────────────────────────────────────────────────────────┘
         │
         ↓
    RL Agent (SAC/PPO/A2C)
    Entrada: 534-dim observation
    Salida: 126-dim action (power setpoints)
         │
         ↓
  Dispatch Rules
  Solar→EV → BESS → Grid
```

---

## 14. DATOS ACTIVOS vs INACTIVOS

### ACTIVOS en entrenamiento ✅
```
✅ Building demand (non_shiftable_load = 788 kW)
✅ Weather (temperature, humidity, solar irradiance)
✅ EV charger states (all 128 chargers)
✅ BESS SOC (electrical_storage_soc)
✅ Carbon intensity (0.4521 kg CO₂/kWh)
✅ Electricity pricing (0.20 USD/kWh)
✅ Time features (month, hour, day_type)
✅ Grid electricity (net_electricity_consumption)
```

### INACTIVOS (muedan a 0 o ignorados) ❌
```
❌ HVAC/Cooling demand (= 0, mall no requiere AC)
❌ Heating demand (= 0, clima tropical)
❌ DHW (agua caliente sanitaria = 0)
❌ Indoor temperature (no controlado)
❌ Daylight savings (siempre 0)
❌ Building 2-16 (solo se usa Building_1)
❌ Washing Machine (legacy, no usado)
```

---

## 15. TABLA DE RESUMEN FINAL

| Aspecto | Valor | Notas |
|---------|-------|-------|
| **Período** | 2024 full year | Jan 1 - Dec 31 |
| **Resolución** | Hourly | 3,600 sec/step |
| **Total timesteps** | 8,760 | 1 year |
| **Buildings** | 1 mall | Iquitos EV charging |
| **EV Chargers** | 128 | 32 physical × 4 sockets |
| **BESS** | 4,520 kWh / 2,712 kW | Immutable in OE3 |
| **PV System** | 4,050 kWp | Via weather irradiance |
| **Demand base** | 788 kW | Constant throughout year |
| **Grid carbon** | 0.4521 kg CO₂/kWh | 100% thermal (Iquitos) |
| **Tariff** | 0.20 USD/kWh | Flat rate, no variation |
| **Observation dims** | 534 | Flattened observation vector |
| **Action dims** | 126 | Continuous [0,1] per charger |
| **Total CSV files** | 127 | All CSV in iquitos_ev_mall/ |
| **Data size** | ~8.7 MB | Per year, compressed ~2 MB |

---

## 16. USO EN ENTRENAMIENTO RL

### Cómo se usa el dataset en cada episodio

```python
# Pseudocode
for episode in range(num_episodes):
    observation = env.reset()  # Observa dataset @ timestep 0
    
    for timestep in range(8760):  # Loop through 8,760 hours
        # Agent observa:
        # - Current weather (temp, solar irradiance)
        # - Current EV demand (charger states, arrival/departure)
        # - Current battery SOC
        # - Time features (month, hour)
        # - Pricing & carbon intensity
        
        action = agent.predict(observation)  # Agent decide charger power
        
        observation, reward, done, info = env.step(action)
        # Environment reads next row from ALL CSVs:
        # - Building_1[timestep+1]
        # - weather[timestep+1]
        # - charger_sim_*.csv[timestep+1]
        # - electrical_storage[timestep+1]
        # - carbon_intensity[timestep+1]
        # - pricing[timestep+1]
        
        reward = compute_multi_objective_reward(
            co2_saved, solar_utilized, cost, ev_satisfied, grid_stable
        )
        
        agent.learn(observation, action, reward)
```

---

*Documento: COMPOSICION_DATASET_CITYLEARN.md*
*Creado: 28 Enero 2026*
*Status: Análisis completo de dataset en uso*
