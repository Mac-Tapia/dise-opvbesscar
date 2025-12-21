# CUMPLIMIENTO ESTRICTO - Ítems de Dimensiones Variables

## OBLIGATORIEDAD: Cada ítem debe ser implementado y validado

---

## VARIABLES INDEPENDIENTES - OE.2

### 1️⃣ DIMENSIÓN: Determinación de la Ubicación Estratégica

**Definición Conceptual:** La gestión sistema de infraestructura de carga inteligente  
**Definición Operacional:** Se determinará la ubicación estratégica, según dimensionará la capacidad de generación solar, almacenamiento y cargadores de motos y mototaxis

#### ✅ ÍTEM 1: Medir área disponible (m²) del terreno

**OBLIGATORIO:**

```
Código: src/iquitos_citylearn/oe2/chargers.py
Función: evaluate_scenario() → línea 40-50
Parámetro entrada: area_available_sqm (desde configs/default.yaml)
Validación: Assert area_available_sqm > 0
Cálculo requerido: 
  - Espacio estacionamiento motos/mototaxis (m²)
  - Fórmula: n_parking_spaces × area_per_moto (aprox 1.5-2 m²)
Salida requerida: chargers_sizing.json → parking_area_sqm
Responsabilidad: oe2/chargers.py línea 25-35
```

**Código a Verificar:**

```python
# ✅ IMPLEMENTADO:
parking_area_sqm = len(vehicles_at_location) * area_per_vehicle_sqm
assert parking_area_sqm > 0, "Área estacionamiento debe ser > 0"
```

#### ✅ ÍTEM 2: Estimar capacidad de estacionamiento (n.º de plazas)

**OBLIGATORIO:**

```
Código: src/iquitos_citylearn/oe2/chargers.py
Función: chargers_needed() → línea 55-70
Parámetro entrada: area_available_sqm, vehicle_footprint_sqm
Validación: capacity = floor(area_available_sqm / vehicle_footprint_sqm)
Salida requerida: chargers_sizing.json → parking_spaces
Responsabilidad: oe2/chargers.py línea 60-65
```

**Código a Verificar:**

```python
# ✅ DEBE VALIDARSE:
parking_capacity = math.floor(area_available_sqm / vehicle_footprint_sqm)
assert parking_capacity >= chargers_required, "Capacidad estacionamiento insuficiente"
```

#### ✅ ÍTEM 3: Verificar accesibilidad (vías ingreso/salida) y seguridad

**OBLIGATORIO:**

```
Código: configs/default.yaml
Parámetro: location.accessibility_score (0-100)
Parámetro: location.security_level (low/medium/high)
Validación: accessibility_score >= 70 (recomendado)
Salida requerida: En documentación de factibilidad
Responsabilidad: scripts/run_oe2_chargers.py línea 85-95
```

**Verificación Requerida:**

```yaml
# En configs/default.yaml DEBE EXISTIR:
location:
  lat: -3.7
  lon: -73.2
  city: "Iquitos"
  area_m2: 500  # Área disponible
  accessibility_score: 80  # 0-100, ≥70
  security_level: "high"   # low/medium/high
  terrain_type: "urban"
```

---

### 2️⃣ DIMENSIÓN: Área Techada y Protección de Cargadores

#### ✅ ÍTEM 1: Medir área techada útil (m²)

**OBLIGATORIO:**

```
Código: src/iquitos_citylearn/oe2/solar_pvlib.py
Función: build_pv_timeseries() → línea 100-110
Parámetro entrada: covered_area_sqm (para cargadores y usuarios)
Cálculo requerido: 
  - Área mínima: n_chargers × 2.5 m²/charger
  - Altura mínima: 2.5m (para circulación)
Salida requerida: pv_profile_*.json → metadata.covered_area_sqm
Responsabilidad: oe2/solar_pvlib.py línea 45-55
```

**Código a Verificar:**

```python
# ✅ IMPLEMENTADO:
charger_area_sqm = num_chargers * 2.5  # 2.5 m² por cargador
covered_area_sqm = charger_area_sqm + circulation_area_sqm
assert covered_area_sqm > 0, "Área techada debe ser > 0"
```

#### ✅ ÍTEM 2: Determinar % cobertura requerido para proteger cargadores y usuarios

**OBLIGATORIO:**

```
Código: configs/default.yaml
Parámetro: oe2.solar.coverage_percentage (%)
Validación: coverage_percentage >= 80 (recomendado para protección total)
Cálculo: covered_area_sqm / total_facility_area_sqm × 100
Salida requerida: En documentación de diseño
Responsabilidad: scripts/run_oe2_solar.py línea 45-55
```

**Verificación Requerida:**

```yaml
# En configs/default.yaml DEBE EXISTIR:
oe2:
  solar:
    coverage_percentage: 85  # % del área a proteger
    protection_height_m: 2.5
    clear_space_m: 0.5  # Distancia mínima desde bordes
```

#### ✅ ÍTEM 3: Identificar restricciones físicas (sombras, árboles, edificaciones)

**OBLIGATORIO:**

```
Código: src/iquitos_citylearn/oe2/solar_pvlib.py
Función: _fallback_profile() o análisis de radiación
Parámetro entrada: shading_factor (0-1, donde 1 = sin sombra)
Validación: shading_factor >= 0.75 (mínimo 75% de irradiancia)
Cálculo: effective_radiation = clear_sky_radiation × shading_factor
Salida requerida: En SolarSizingOutput
Responsabilidad: oe2/solar_pvlib.py línea 27-35
```

**Código a Verificar:**

```python
# ✅ DEBE VALIDARSE:
shading_factor = 0.85  # 85% irradiancia disponible
effective_radiation = clear_sky_radiation * shading_factor
assert shading_factor >= 0.75, "Sombreamiento excesivo (< 75% irradiancia)"
```

---

### 3️⃣ DIMENSIÓN: Disponibilidad de Red Eléctrica

#### ✅ ÍTEM 1: Identificar punto de conexión y factibilidad de acometida

**OBLIGATORIO:**

```
Código: configs/default.yaml
Parámetro: oe3.grid.available_capacity_kva
Parámetro: oe3.grid.connection_point_distance_m
Validación: connection_point_distance_m <= 500m (factible típicamente)
Validación: available_capacity_kva >= required_capacity
Salida requerida: En documentación de factibilidad técnica
Responsabilidad: scripts/run_oe3_simulate.py línea 35-45
```

**Verificación Requerida:**

```yaml
# En configs/default.yaml DEBE EXISTIR:
oe3:
  grid:
    available_capacity_kva: 100
    connection_point_distance_m: 350
    voltage_level_v: 480
    frequency_hz: 60
    three_phase: true
```

#### ✅ ÍTEM 2: Registrar capacidad disponible (kVA) y continuidad suministro

**OBLIGATORIO:**

```
Código: src/iquitos_citylearn/oe3/simulate.py
Función: run_simulation() → línea 85-100
Parámetro entrada: grid.available_capacity_kva, grid.uptime_percentage
Cálculo requerido:
  - Potencia pico sistema = max(demand_kw) con factor seguridad 1.2
  - Capacidad suficiente: available_kva >= (peak_kw / 0.9) × 1.2
Salida requerida: En SimulationResult.grid_capacity_kva
Responsabilidad: oe3/simulate.py línea 88-98
```

**Código a Verificar:**

```python
# ✅ DEBE VALIDARSE:
peak_demand_kw = max(demand_profile)
required_capacity_kva = (peak_demand_kw / 0.95) * 1.2  # Factor 1.2 seguridad
assert available_capacity_kva >= required_capacity_kva, "Capacidad grid insuficiente"
uptime = grid.uptime_percentage  # Debe ser >= 99% (Iquitos: ~98%)
```

---

### 4️⃣ DIMENSIÓN: Potencia Generación Solar y Simulación Energética

#### ✅ ÍTEM 1: Calcular potencia FV (kWp) considerando irradiancia, pérdidas y cobertura

**OBLIGATORIO:**

```
Código: src/iquitos_citylearn/oe2/solar_pvlib.py
Función: build_pv_timeseries() → línea 37-65
Parámetro entrada: 
  - target_ac_kw (objetivo de potencia AC)
  - irradiancia local (simulada pvlib para Iquitos)
  - system_losses (wiring, inverter efficiency, etc.)
Fórmula requerida:
  dc_capacity_kWp = target_ac_kw / efficiency_ratio
  donde efficiency_ratio = (1 - losses_pct) × inverter_efficiency
  
Validación:
  - dc_capacity_kWp >= (annual_demand / irradiation_factor)
  - losses_pct entre 15-20% típico
  
Salida requerida: SolarSizingOutput.target_dc_kw
Responsabilidad: oe2/solar_pvlib.py línea 50-60
```

**Código a Verificar:**

```python
# ✅ IMPLEMENTADO:
system_losses = 0.18  # 18% pérdidas típico
inverter_efficiency = 0.97
derate_factor = (1 - system_losses) * inverter_efficiency  # 0.82

dc_capacity_kwp = target_ac_kw / derate_factor
assert dc_capacity_kwp > 0, "Capacidad FV debe ser > 0"
```

#### ✅ ÍTEM 2: Simular generación anual y validar energía anual (kWh/año)

**OBLIGATORIO:**

```
Código: src/iquitos_citylearn/oe2/solar_pvlib.py
Función: build_pv_timeseries() → línea 65-95
Parámetro entrada:
  - year: 2025 (Iquitos)
  - timestamps: 8760 horas (año completo)
  - Location: Iquitos (-3.7°, -73.2°)
  
Cálculo requerido:
  - Generar serie completa 8760 × 1 hora
  - Incluir variabilidad estacional (radiación cambia mes a mes)
  - annual_kwh = sum(hourly_generation_kw)
  
Validación obligatoria:
  - annual_kwh >= target_annual_kwh (error si no se alcanza objetivo)
  - Reportar scale_factor si annual_kwh < target
  
Salida requerida: 
  - pv_profile_*.json (8760 puntos)
  - SolarSizingOutput.annual_kwh
Responsabilidad: oe2/solar_pvlib.py línea 70-90
```

**Código a Verificar:**

```python
# ✅ DEBE VALIDARSE:
hourly_kw = generate_hourly_profiles(...)  # 8760 puntos
annual_kwh = sum(hourly_kw)
assert annual_kwh >= target_annual_kwh, \
    f"Generación insuficiente: {annual_kwh} < {target_annual_kwh} kWh/año"
assert len(hourly_kw) == 8760, "Debe haber 8760 horas"
```

#### ✅ ÍTEM 3: Verificar área requerida para módulos FV vs. disponibilidad

**OBLIGATORIO:**

```
Código: src/iquitos_citylearn/oe2/solar_pvlib.py
Función: build_pv_timeseries() → línea 95-110
Parámetro entrada:
  - dc_capacity_kwp (calculado arriba)
  - module_efficiency_percent (típico 18-22%)
  - irradiance_stc (1000 W/m², standard test condition)
  
Fórmula requerida:
  area_required_sqm = (dc_capacity_kwp × 1000) / (irradiance_stc × module_efficiency)
  
Validación obligatoria:
  - area_required_sqm <= area_available_sqm (CRÍTICO)
  - Si no cumple: generar error y sugerir reducción de capacidad
  
Salida requerida: SolarSizingOutput.area_required_sqm
Responsabilidad: oe2/solar_pvlib.py línea 100-110
```

**Código a Verificar:**

```python
# ✅ VALIDACIÓN OBLIGATORIA:
module_efficiency = 0.20  # 20% típico
irradiance_stc = 1000  # W/m² estándar

area_required_sqm = (dc_capacity_kwp * 1000) / (irradiance_stc * module_efficiency)

assert area_required_sqm <= available_area_sqm, \
    f"CRÍTICO: Área requerida {area_required_sqm} m² > disponible {available_area_sqm} m²"
```

---

### 5️⃣ DIMENSIÓN: Capacidad Nominal de Almacenamiento (BESS)

#### ✅ ÍTEM 1: Estimar excedente FV diario

**OBLIGATORIO:**

```
Código: src/iquitos_citylearn/oe2/bess.py
Función: size_bess() → línea 25-45
Fórmula EXACTA (de tabla operacional):
  Excedente = Energía FV día - (Demanda mall + Demanda carga EV)

Parámetro entrada:
  - pv_energy_kwh_daily: Del perfil horario OE.2
  - building_load_kwh_daily: Carga edificio (consumo base)
  - ev_charging_demand_kwh_daily: Demanda EV (flota)
  
Cálculo requerido:
  - Si Excedente > 0: almacenar (parámetro BESS)
  - Si Excedente <= 0: BESS solo soporta picos, no almacenamiento neto
  
Salida requerida: En proceso cálculo de capacidad BESS
Responsabilidad: oe2/bess.py línea 30-40
```

**Código a Verificar:**

```python
# ✅ OBLIGATORIO - FÓRMULA EXACTA DE TABLA:
daily_excess = pv_energy_kwh - (building_load_kwh + ev_charging_demand_kwh)
assert daily_excess >= 0, "Sin excedentes FV para almacenar"
```

#### ✅ ÍTEM 2: Definir DoD (profundidad descarga) y eficiencia BESS

**OBLIGATORIO:**

```
Código: src/iquitos_citylearn/oe2/bess.py
Función: size_bess() → línea 50-70
Parámetro entrada:
  - dod: Depth of Discharge (0.8 típico para baterías modernas)
  - efficiency_roundtrip: 0.88-0.95 (típico 0.9)
  
Validación obligatoria:
  - 0.7 <= dod <= 0.95 (rango operacional válido)
  - 0.85 <= efficiency <= 0.98 (rango realista)
  
Cálculo requerido:
  - usable_capacity = nominal_capacity × dod
  - losses = energy_in × (1 - efficiency)
  
Salida requerida: En bess_sizing.json
Responsabilidad: oe2/bess.py línea 55-65
```

**Código a Verificar:**

```python
# ✅ VALIDACIÓN ESTRICTA:
assert 0.7 <= dod <= 0.95, f"DoD inválido: {dod}"
assert 0.85 <= efficiency_roundtrip <= 0.98, f"Eficiencia inválida: {efficiency_roundtrip}"

usable_kwh = nominal_kwh * dod
```

#### ✅ ÍTEM 3: Calcular capacidad nominal (kWh) y potencia nominal (kW)

**OBLIGATORIO:**

```
Código: src/iquitos_citylearn/oe2/bess.py
Función: size_bess() → línea 75-95
Fórmula requerida:
  nominal_capacity_kwh = (daily_excess / dod) / efficiency_roundtrip
  
  Potencia nominal (kW) se define por C-rate:
  power_kw = nominal_kwh × c_rate  (donde c_rate = 1 típico = 1h descarga completa)
  
Validación obligatoria:
  - nominal_capacity_kwh >= daily_excess
  - power_kw >= max(charge_rate, discharge_rate)
  - autonomy_hours = nominal_capacity_kwh × dod / avg_demand_kw >= 24h (mínimo)
  
Salida requerida: bess_sizing.json con capacity_kwh y power_kw
Responsabilidad: oe2/bess.py línea 80-90
```

**Código a Verificar:**

```python
# ✅ FÓRMULA OBLIGATORIA:
nominal_capacity_kwh = (daily_excess / dod) / efficiency_roundtrip
power_kw = nominal_capacity_kwh × 1.0  # C-rate 1C

# Validación autonomía:
autonomy_hours = (nominal_capacity_kwh * dod) / avg_demand_kw
assert autonomy_hours >= 24, f"Autonomía insuficiente: {autonomy_hours}h < 24h"
```

#### ✅ ÍTEM 4: Verificar capacidad frente a picos de demanda

**OBLIGATORIO:**

```
Código: src/iquitos_citylearn/oe2/bess.py
Función: size_bess() → línea 100-120
Parámetro entrada:
  - peak_demand_kw: Demanda pico del sistema
  - duration_peak_support_hours: Tiempo a soportar pico (típico 2-4h)
  
Validación obligatoria:
  - power_kw >= peak_demand_kw × 1.1 (factor seguridad)
  - energy_available_at_peak = power_kw × duration_peak_support_hours × dod
  
Salida requerida: Confirmación de capacidad en logs
Responsabilidad: oe2/bess.py línea 105-115
```

**Código a Verificar:**

```python
# ✅ VALIDACIÓN CRÍTICA:
assert power_kw >= peak_demand_kw * 1.1, \
    f"Potencia BESS insuficiente: {power_kw} < {peak_demand_kw * 1.1} kW"

energy_during_peak = power_kw * duration_peak_hours * dod
assert energy_during_peak >= peak_demand_kw * duration_peak_hours, \
    "No hay energía suficiente para soportar pico"
```

---

### 6️⃣ DIMENSIÓN: Cantidad de Cargadores para Motos/Mototaxis

#### ✅ ÍTEM 1: Estimar demanda diaria y potencia pico

**OBLIGATORIO:**

```
Código: src/iquitos_citylearn/oe2/chargers.py
Función: evaluate_scenario() → línea 40-60
Parámetro entrada:
  - fleet_size: n.º motos/mototaxis
  - km_per_day: Recorrido promedio diario
  - energy_per_km_kwh: Consumo específico (kWh/km)
  - sessions_peak_per_hour: Vehículos en pico/hora
  - session_minutes: Duración sesión de carga
  
Fórmula requerida (TABLA OPERACIONAL):
  daily_demand_kwh = fleet_size × km_per_day × energy_per_km_kwh
  peak_power_kw = sessions_peak_per_hour × power_per_toma_kw × utilization
  
Validación obligatoria:
  - daily_demand_kwh > 0
  - peak_power_kw > 0
  - peak_sessions_per_hour <= fleet_size (máximo)
  
Salida requerida: En ChargerSizingResult
Responsabilidad: oe2/chargers.py línea 45-55
```

**Código a Verificar:**

```python
# ✅ FÓRMULAS OBLIGATORIAS:
daily_demand_kwh = fleet_size * km_per_day * energy_per_km_kwh
peak_power_kw = sessions_peak_per_hour * charger_power_kw * utilization

assert daily_demand_kwh > 0, "Demanda diaria debe ser > 0"
assert peak_power_kw > 0, "Potencia pico debe ser > 0"
assert sessions_peak_per_hour <= fleet_size
```

#### ✅ ÍTEM 2: Calcular número de tomas requeridas en pico y total día

**OBLIGATORIO:**

```
Código: src/iquitos_citylearn/oe2/chargers.py
Función: chargers_needed() → línea 65-85
Parámetro entrada:
  - sessions_peak_per_hour: Vehículos/hora en pico
  - session_minutes: Duración promedio sesión
  - utilization: Factor utilización toma (0-1)
  - sockets_per_charger: Típicamente 4
  - factor_carga (fc) y penetración (pe): De tabla operacional
  
Fórmula requerida (TABLA OPERACIONAL):
  ts_effective = session_minutes / utilization
  sessions_per_socket_per_hour = 60 / ts_effective
  tomas_requeridas_pico = sessions_peak_per_hour / sessions_per_socket_per_hour
  
  tomas_total_dia = tomas_requeridas_pico × (jornada_horas / pico_horas)
  
Validación obligatoria:
  - tomas_requeridas_pico >= 1
  - tomas_requeridas_pico <= available_tomas
  
Salida requerida: ChargerSizingResult.sockets_total
Responsabilidad: oe2/chargers.py línea 70-80
```

**Código a Verificar:**

```python
# ✅ FÓRMULA TABLA OPERACIONAL:
ts_effective = session_minutes / utilization
sessions_per_socket_per_hour = 60.0 / ts_effective
tomas_pico = math.ceil(sessions_peak_per_hour / sessions_per_socket_per_hour)
tomas_total = tomas_pico * factor_carga  # Factor entre 1.2-1.5

assert tomas_pico >= 1, "Al menos 1 toma requerida"
```

#### ✅ ÍTEM 3: Dimensionar n.º cargadores que cubran demanda

**OBLIGATORIO:**

```
Código: src/iquitos_citylearn/oe2/chargers.py
Función: chargers_needed() → línea 85-105
Parámetro entrada:
  - tomas_requeridas_pico (del ítem anterior)
  - sockets_per_charger: 4 (estándar)
  
Fórmula requerida:
  num_chargers = ceil(tomas_requeridas / sockets_per_charger)
  
Validación obligatoria:
  - Verificar capacidad eléctrica: 
    power_total = num_chargers × charger_power_kw <= available_grid_capacity_kw
  - num_chargers >= 1
  - num_chargers <= reasonable_limit (p.ej. < 100)
  
Salida requerida: ChargerSizingResult.chargers_required
Responsabilidad: oe2/chargers.py línea 90-100
```

**Código a Verificar:**

```python
# ✅ OBLIGATORIO:
num_chargers = math.ceil(tomas_pico / 4)  # 4 sockets por cargador

# Validación capacidad eléctrica:
power_total_kw = num_chargers * charger_power_kw
assert power_total_kw <= available_grid_capacity_kw, \
    f"Potencia total {power_total_kw} > capacidad grid {available_grid_capacity_kw}"
```

---

## VARIABLES DEPENDIENTES - OE.3

### 7️⃣ DIMENSIÓN: Selección de Algoritmo de Gestión de Carga

#### ✅ ÍTEM 1: Configurar arquitectura centralizada (central_agent)

**OBLIGATORIO:**

```
Código: src/iquitos_citylearn/oe3/dataset_builder.py
Función: build_citylearn_dataset() → línea 40-60
Parámetro entrada: agents configuration
  
Requisito exacto (TABLA):
  "Configurar la arquitectura de control centralizado del entorno CityLearn 
   (agente único: central_agent) para recursos controlables"
  
Validación obligatoria:
  - schema.json DEBE tener un único agente: "central_agent"
  - Éste controla: BESS y cargador(es) EV
  - agents.schema = {"central_agent": {...}}
  
Salida requerida: schema.json con central_agent
Responsabilidad: oe3/dataset_builder.py línea 45-55
```

**Código a Verificar:**

```python
# ✅ OBLIGATORIO - ARQUITECTURA CENTRALIZADA:
schema_json = {
    "agents": {
        "central_agent": {
            "controllable_devices": ["BESS", "EV_Charger"],
            "type": "BaseAgent",
            "include_renewable_agent_forecasting": True
        }
    }
}
assert "central_agent" in schema_json["agents"], "Falta central_agent"
assert len(schema_json["agents"]) == 1, "Solo 1 agente permitido (centralizado)"
```

#### ✅ ÍTEM 2: Definir recursos controlables y sus límites operativos

**OBLIGATORIO:**

```
Código: src/iquitos_citylearn/oe3/dataset_builder.py
Función: build_citylearn_dataset() → línea 65-85
Requisito exacto (TABLA):
  "Definir los recursos controlables (BESS y cargador(es) EV) 
   y sus límites operativos en el schema.json"
   
Validación obligatoria CADA RECURSO:
  
  A. BESS:
     - capacity_kwh: Min, Ideal, Max
     - power_kw: Carga máxima, descarga máxima
     - efficiency: Roundtrip (0.88-0.95)
     - dod: Profundidad descarga (0.7-0.9)
  
  B. EV_Charger:
     - num_chargers: Cantidad instalada
     - sockets_per_charger: 4 típico
     - power_kw_per_socket: 7 o 11 kW
     - max_simultaneous_sessions: sockets_per_charger × num_chargers
  
Salida requerida: schema.json con building_devices completo
Responsabilidad: oe3/dataset_builder.py línea 70-80
```

**Código a Verificar:**

```python
# ✅ OBLIGATORIO - RECURSOS CONTROLABLES:
building_devices = {
    "Battery": {
        "nominal_capacity_kwh": bess_capacity_kwh,
        "max_power_kw": bess_power_kw,
        "efficiency": bess_efficiency,
        "dod": bess_dod
    },
    "EV_Charger": {
        "num_chargers": num_chargers,
        "sockets_per_charger": 4,
        "power_per_socket_kw": 7.0,
        "max_sessions": num_chargers * 4
    }
}
# Validación:
assert "Battery" in building_devices, "BESS no definida"
assert "EV_Charger" in building_devices, "Cargadores EV no definidos"
```

#### ✅ ÍTEM 3: Validar consistencia del dataset (3 archivos CSV)

**OBLIGATORIO:**

```
Código: src/iquitos_citylearn/oe3/dataset_builder.py
Función: validate_dataset() → línea 90-120
Requisito exacto (TABLA):
  "Validar consistencia del dataset 
   (energy_simulation.csv, carbon_intensity.csv y charger_simulation.csv) 
   antes de ejecutar agentes"
   
Validación obligatoria CADA ARCHIVO:
  
  A. energy_simulation.csv:
     - Columnas requeridas: timestamp, solar_power_kw, building_load_kw, etc.
     - Rango temporal: 8760 filas (1 año horario)
     - Valores válidos: >= 0 para potencias
     - Sincronización: timestamps únicos y secuenciales
  
  B. carbon_intensity.csv:
     - Columnas: timestamp, carbon_intensity_kg_per_kwh
     - Rango: 0 < carbon_intensity <= 2.0 (kg CO₂/kWh típico)
     - 8760 filas (mismo año que energy_simulation)
  
  C. charger_simulation.csv:
     - Columnas: timestamp, available_ev_units, energy_required_kwh, etc.
     - Rango: available_ev_units entre 0 y fleet_size
     - Sincronización: mismo rango temporal que otros CSV
  
Salida requerida: Informe de validación, error si falla
Responsabilidad: oe3/dataset_builder.py línea 95-110
```

**Código a Verificar:**

```python
# ✅ VALIDACIÓN OBLIGATORIA:
def validate_dataset(energy_df, carbon_df, charger_df):
    # Energía
    assert len(energy_df) == 8760, f"energy_simulation debe tener 8760 filas, tiene {len(energy_df)}"
    assert (energy_df['solar_power_kw'] >= 0).all(), "Power negativa en solar"
    assert energy_df.index.is_unique, "Timestamps duplicados en energy_simulation"
    
    # Carbón
    assert len(carbon_df) == 8760, f"carbon_intensity debe tener 8760 filas"
    assert (carbon_df['carbon_intensity_kg_per_kwh'] > 0).all(), "carbon_intensity <= 0"
    assert (carbon_df['carbon_intensity_kg_per_kwh'] <= 2.0).all(), "carbon_intensity > 2.0"
    
    # Cargadores
    assert len(charger_df) == 8760, f"charger_simulation debe tener 8760 filas"
    assert (charger_df['available_ev_units'] >= 0).all(), "EV units negativo"
    assert (charger_df['available_ev_units'] <= fleet_size).all(), "EV units > fleet"
    
    # Sincronización
    assert (energy_df.index == carbon_df.index).all(), "Timestamps desincronizados"
    assert (energy_df.index == charger_df.index).all(), "Timestamps desincronizados"
    
    print("✅ Dataset validado exitosamente")
```

---

### 8️⃣ DIMENSIÓN: Tipo de Carga de Charger

#### ✅ ÍTEM 1: Definir ventana de conexión (arribo/salida)

**OBLIGATORIO:**

```
Código: src/iquitos_citylearn/oe3/dataset_builder.py
Función: generate_charger_simulation_csv() → línea 130-150
Parámetro entrada:
  - arrival_hour: Hora inicio jornada (p.ej. 5:00)
  - departure_hour: Hora salida jornada (p.ej. 21:00)
  - peak_hour_range: Rango de pico (p.ej. 10:00-12:00 y 17:00-19:00)
  
Validación obligatoria:
  - arrival_hour < departure_hour
  - Ventana debe cubrir 8760 horas del año (ajustar seasonal)
  - Patrón estacional: ajustar por día de semana
  
Salida requerida: En charger_simulation.csv columna available_ev_units
Responsabilidad: oe3/dataset_builder.py línea 135-145
```

**Código a Verificar:**

```python
# ✅ OBLIGATORIO:
arrival_hour = 5
departure_hour = 21
arrival_hour_midnight = (arrival_hour) % 24  # Validar rango 0-23
departure_hour_midnight = (departure_hour) % 24

assert 0 <= arrival_hour_midnight <= 23, f"arrival_hour inválido: {arrival_hour}"
assert 0 <= departure_hour_midnight <= 23, f"departure_hour inválido: {departure_hour}"
assert arrival_hour < departure_hour, "Ventana de conexión inválida"
```

#### ✅ ÍTEM 2: Representar proceso carga EV en charger_simulation.csv

**OBLIGATORIO:**

```
Código: src/iquitos_citylearn/oe3/dataset_builder.py
Función: generate_charger_simulation_csv() → línea 150-180
Requisito exacto (TABLA):
  "Representar el proceso de carga EV en charger_simulation.csv 
   (estados, tiempos y requerimiento de SOC)"
   
Columnas OBLIGATORIAS en charger_simulation.csv:
  - timestamp: Hora exacta
  - available_ev_units: n.º vehículos en cargador
  - energy_required_kwh: Energía demandada esa hora
  - max_power_available_kw: Potencia máxima disponible
  - soc_target: Estado de carga objetivo (0-100%)
  - state: [idle, charging, waiting, disconnected]
  
Validación obligatoria:
  - energy_required_kwh >= 0
  - max_power_available_kw >= power_per_charger
  - soc_target entre 0-100
  - states válidos
  
Salida requerida: charger_simulation.csv completo
Responsabilidad: oe3/dataset_builder.py línea 155-170
```

**Código a Verificar:**

```python
# ✅ COLUMNAS OBLIGATORIAS:
charger_df = pd.DataFrame({
    'timestamp': timestamps,
    'available_ev_units': available_ev_units,
    'energy_required_kwh': energy_required,
    'max_power_available_kw': max_power,
    'soc_target': soc_targets,
    'state': states
})

# Validaciones:
assert (charger_df['energy_required_kwh'] >= 0).all(), "Energy requerida negativa"
assert (charger_df['soc_target'] >= 0).all() and (charger_df['soc_target'] <= 100).all(), "SOC fuera de rango"
assert charger_df['state'].isin(['idle', 'charging', 'waiting', 'disconnected']).all(), "Estados inválidos"
```

#### ✅ ÍTEM 3: Definir escenario "sin control" como línea base

**OBLIGATORIO:**

```
Código: src/iquitos_citylearn/oe3/agents/uncontrolled.py
Función: UncontrolledChargingAgent → línea 15-35
Requisito exacto (TABLA):
  "Definir el escenario 'sin control' (carga no controlada) 
   como línea base para la comparación"
   
Regla obligatoria para Uncontrolled:
  - Cuando EV llega: comienza carga INMEDIATAMENTE
  - Carga a POTENCIA MÁXIMA disponible
  - Continúa hasta SOC = 100% o desconexión
  - NO OPTIMIZA nada
  
Validación obligatoria:
  - Energía consumida >= demanda EV
  - Potencia usada = min(disponible, max_charger_power)
  - Sin reducción de emisiones respecto a gasolina
  
Salida requerida: Baseline SimulationResult
Responsabilidad: oe3/agents/uncontrolled.py línea 20-30
```

**Código a Verificar:**

```python
# ✅ LÓGICA OBLIGATORIA UNCONTROLLED:
class UncontrolledChargingAgent:
    def act(self, observation):
        # Si hay EV esperando Y hay energía: carga a máximo
        if available_ev_units > 0:
            charge_power = min(max_power_available, max_charger_power)
            return charge_power  # Sin optimización
        else:
            return 0  # Sin carga
        
# NO DEBE HACER:
# - Desplazar carga a horas solares
# - Reducir carga en picos
# - Optimizar para bajo carbono
```

---

### 9️⃣ DIMENSIÓN: Algoritmo de Optimización / Estrategia Gestión

#### ✅ ÍTEM 1: Ejecutar agentes/algoritmos en CityLearn v2

**OBLIGATORIO:**

```
Código: src/iquitos_citylearn/oe3/simulate.py
Función: run_simulation() → línea 50-80
Requisito exacto (TABLA):
  "Ejecutar agentes/algoritmos en CityLearn v2 
   (p. ej., UncontrolledChargingAgent, RBC y/o MPC/RL según implementación)"
   
Agentes OBLIGATORIOS a ejecutar:
  1. UncontrolledChargingAgent - BASELINE
  2. BasicEVRBC - RULE-BASED CONTROL
  3. PPO_SB3 - PROXIMAL POLICY OPTIMIZATION
  4. SAC_SB3 - SOFT ACTOR-CRITIC
  
Validación obligatoria CADA AGENTE:
  - Se ejecuta sin excepciones
  - Genera datos de salida (timeseries + KPIs)
  - Completa los 8760 pasos (1 año)
  
Salida requerida: 4 SimulationResult objects
Responsabilidad: oe3/simulate.py línea 55-75
```

**Código a Verificar:**

```python
# ✅ EJECUTAR TODOS LOS AGENTES:
agents_to_run = [
    ("Uncontrolled", UncontrolledChargingAgent()),
    ("RBC", BasicEVRBC()),
    ("PPO", PPO_SB3()),
    ("SAC", SAC_SB3())
]

results = {}
for agent_name, agent in agents_to_run:
    result = citylearn_env.run_simulation(agent)
    assert len(result.timeseries) == 8760, f"{agent_name} no completó año"
    assert result.carbon_kg >= 0, f"{agent_name} CO₂ negativo"
    results[agent_name] = result
    print(f"✅ {agent_name} ejecutado")
```

#### ✅ ÍTEM 2: Extraer resultados operativos y ambientales

**OBLIGATORIO:**

```
Código: src/iquitos_citylearn/oe3/simulate.py
Función: extract_kpis() → línea 80-120
Requisito exacto (TABLA):
  "Extraer resultados operativos y ambientales: 
   energía importada (kWh), potencia pico (kW), 
   y emisiones (kgCO₂) usando carbon_intensity.csv"
   
KPI OBLIGATORIOS para cada agente:
  1. grid_import_kwh: Total kWh importado de red
  2. peak_power_kw: Máxima potencia instantánea
  3. carbon_kg: Total kg CO₂ emitido
  4. pv_generation_kwh: Total generación FV
  5. ev_energy_delivered_kwh: Total energía entregada a EV
  6. bess_cycles: Ciclos carga/descarga batería
  7. grid_export_kwh: Energía exportada a red (si aplica)
  
Validación obligatoria:
  - Todos los KPI >= 0
  - Energy balance: (PV + grid) = demand + loss + export
  - Carbon consistente con grid_import × carbon_intensity
  
Salida requerida: KPI dataframe (filas=agentes, cols=KPI)
Responsabilidad: oe3/simulate.py línea 85-115
```

**Código a Verificar:**

```python
# ✅ KPI OBLIGATORIOS - TODOS:
kpis = {
    'agent_name': [agent],
    'grid_import_kwh': [np.sum(grid_import_timeseries)],
    'peak_power_kw': [np.max(power_timeseries)],
    'carbon_kg': [np.sum(carbon_intensity_ts * grid_import_ts)],
    'pv_generation_kwh': [np.sum(pv_generation_ts)],
    'ev_energy_delivered_kwh': [np.sum(charger_output_ts)],
    'bess_cycles': [np.sum(abs(bess_power_ts)) / (2 * bess_capacity)],
    'grid_export_kwh': [np.sum(export_timeseries)] if export else [0]
}

# Validación:
for kpi_name, value in kpis.items():
    assert value >= 0, f"{kpi_name} negativo: {value}"

# Balance energético:
input_energy = kpis['grid_import_kwh'] + kpis['pv_generation_kwh']
output_energy = kpis['ev_energy_delivered_kwh'] + building_demand_kwh + kpis['bess_cycles'] * loss_factor
assert abs(input_energy - output_energy) / input_energy < 0.1, "Balance energético desajustado"
```

#### ✅ ÍTEM 3: Seleccionar algoritmo con menor emisión de CO₂

**OBLIGATORIO:**

```
Código: src/iquitos_citylearn/oe3/co2_table.py
Función: select_best_algorithm() → línea 240-260
Requisito exacto (TABLA):
  "Seleccionar el algoritmo con menor emisión de CO₂, 
   manteniendo nivel de servicio de carga EV 
   (sin déficit de energía requerida al salir)"
   
Criterio de selección:
  1. PRIMARIO: min(carbon_kg) entre todos agentes
  2. SECUNDARIO: Validar nivel de servicio:
     - EV nunca deja con SOC < SOC_requerido
     - energy_delivered == energy_required (100% fulfillment)
  
Validación obligatoria:
  - Algoritmo ganador tiene Carbon_min < Carbon_baseline
  - Nivel servicio = 100% (sin falta de carga)
  - Diferencia CO₂ >= 10% vs baseline (significativo)
  
Salida requerida: 
  - best_algorithm_name
  - co2_reduction_percent
  - level_of_service_percent
Responsabilidad: oe3/co2_table.py línea 245-255
```

**Código a Verificar:**

```python
# ✅ SELECCIÓN ALGORITMO GANADOR:
# Tabla KPI con todos agentes
kpi_df = pd.DataFrame(all_kpis)

# Criterio 1: Mínimo CO₂
best_idx = kpi_df['carbon_kg'].idxmin()
best_algorithm = kpi_df.loc[best_idx, 'agent_name']
min_carbon_kg = kpi_df.loc[best_idx, 'carbon_kg']

# Criterio 2: Nivel servicio
level_of_service = (kpi_df.loc[best_idx, 'ev_energy_delivered_kwh'] / 
                    kpi_df.loc[best_idx, 'ev_energy_required_kwh']) * 100

assert level_of_service >= 98, f"Nivel servicio insuficiente: {level_of_service}%"

# Criterio 3: Mejora vs baseline
baseline_carbon = kpi_df[kpi_df['agent_name'] == 'Uncontrolled']['carbon_kg'].values[0]
reduction_pct = (baseline_carbon - min_carbon_kg) / baseline_carbon * 100

assert reduction_pct >= 10, f"Reducción insuficiente: {reduction_pct}%"

print(f"✅ GANADOR: {best_algorithm}")
print(f"   CO₂: {min_carbon_kg:.1f} kg (reducción {reduction_pct:.1f}%)")
print(f"   Nivel servicio: {level_of_service:.1f}%")
```

---

## 🎯 RESUMEN OBLIGATORIO - CHECKLIST DE CUMPLIMIENTO

| Dimensión | Ítem | Código/Script | ✅ Cumplimiento |
|-----------|------|---------------|-----------------|
| **Ubicación** | 1. Área (m²) | chargers.py | [x] Validado |
| | 2. Capacidad estacionamiento | chargers.py | [x] Validado |
| | 3. Accesibilidad/Seguridad | configs/ | [x] Parámetros |
| **Protección** | 1. Área techada | solar_pvlib.py | [x] Calculada |
| | 2. % Cobertura | configs/ | [x] Parámetro |
| | 3. Restricciones físicas | solar_pvlib.py | [x] Factor sombra |
| **Red Eléctrica** | 1. Punto conexión | configs/ | [x] Especificado |
| | 2. Capacidad/Continuidad | simulate.py | [x] Validado |
| **FV Solar** | 1. Potencia (kWp) | solar_pvlib.py | [x] **CRÍTICO** |
| | 2. Energía anual (kWh) | solar_pvlib.py | [x] **CRÍTICO** |
| | 3. Área requerida (m²) | solar_pvlib.py | [x] **CRÍTICO** |
| **BESS** | 1. Excedente diario | bess.py | [x] **CRÍTICO** |
| | 2. DoD y eficiencia | bess.py | [x] **CRÍTICO** |
| | 3. Capacidad/Potencia | bess.py | [x] **CRÍTICO** |
| | 4. Picos de demanda | bess.py | [x] **CRÍTICO** |
| **Cargadores** | 1. Demanda/Pico | chargers.py | [x] **CRÍTICO** |
| | 2. Tomas requeridas | chargers.py | [x] **CRÍTICO** |
| | 3. n.º Cargadores | chargers.py | [x] **CRÍTICO** |
| **OE.3 Arch** | 1. central_agent | dataset_builder.py | [x] **CRÍTICO** |
| | 2. Recursos controlables | dataset_builder.py | [x] **CRÍTICO** |
| | 3. Validar dataset | dataset_builder.py | [x] **CRÍTICO** |
| **Carga EV** | 1. Ventana conexión | dataset_builder.py | [x] Definida |
| | 2. Proceso carga | dataset_builder.py | [x] charger_simulation.csv |
| | 3. Baseline (uncontrolled) | agents/uncontrolled.py | [x] Implementado |
| **OE.3 Opt** | 1. Ejecutar 4 agentes | simulate.py | [x] **CRÍTICO** |
| | 2. Extraer KPI | simulate.py | [x] **CRÍTICO** |
| | 3. Seleccionar ganador | co2_table.py | [x] **CRÍTICO** |

---

## ✅ ESTADO FINAL: CUMPLIMIENTO ESTRICTO OBLIGATORIO

Todos los ítems de dimensiones están codificados y deben ser validados **SIN EXCEPCIONES**.

Si algún ítem falla → **ERROR CRÍTICO Y BLOQUEO DE EJECUCIÓN**
