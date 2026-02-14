## FLUJO DE CASCADA SOLAR VALIDADO CONTRA DATOS REALES

**Generado**: 2026-02-14
**Status**: ✅ VALIDADO CON DATOS OE2 REALES

---

### 1. FLUJO DE CASCADA SOLAR (Teórico)

```
Solar (8.29 GWh/año, max 2,887 kW)
  ↓
[PRIORIDAD 1] BESS (940 kWh, 342 kW)
  - Almacenar energía para noche/nublado
  - Suavizar picos de carga
  ↓ (después BESS está lleno)
[PRIORIDAD 2] EV Chargers (38 sockets, 281.2 kW)
  - Cargar motos + mototaxis
  - 2.46 GWh/año demanda
  ↓ (después EVs cargados)
[PRIORIDAD 3] Mall (variable, max 2,763 kW)
  - Alimentar demanda comercial
  - 12.37 GWh/año demanda
  ↓ (si aun hay exceso)
[PRIORIDAD 4] Red Pública
  - Inyectar energía sobrante
  - Venta a grid (tarifa de inyección)
```

---

### 2. DATOS REALES CARGADOS

#### SOLAR GENERATION (pv_generation_citylearn2024.csv)
- **Potencia nominal**: 4,050 kWp
- **Potencia máxima observada**: 2,887 kW
- **Irradiancia**: GHI, DNI, DHI (PVGIS real)
- **Temperatura**: Aire (RTi-Dry)
- **Viento**: Velocidad m/s
- **Generación anual**: 8,292,514 kWh
- **Columnasutilizables**: 
  - `potencia_kw` (potencia instantánea)
  - `energia_kwh` (energía horaria)
  - `is_hora_punta` (tarifa punta/fuera punta)
  - `ahorro_solar_soles` (valor económico)
  - `reduccion_indirecta_co2_kg` (CO2 evitado por generación)

#### BESS OPERATION (bess_ano_2024.csv) [CONTIENE CASCADA PRE-SIMULADA]
- **Capacidad**: 940 kWh (usado: 20-100% SOC)
- **Potencia**: 342 kW carga/descarga maximo
- **Columnas de CASCADA (REALES)**:
  - `pv_to_bess_kwh` ← **Solar a BESS (Prioridad 1)**
  - `pv_to_ev_kwh` ← **Solar a EV (Prioridad 2)**
  - `pv_to_mall_kwh` ← **Solar a Mall (Prioridad 3)**
  - `pv_curtailed_kwh` ← **Exceso descartado (raro)**
  - `bess_to_ev_kwh` ← **BESS a EV (cuando baja SOC)**
  - `bess_to_mall_kwh` ← **BESS a Mall (opcionalmente)**
- **Columnas deoperación**:
  - `bess_charge_kwh` (energía entrada)
  - `bess_discharge_kwh` (energía salida)
  - `bess_soc_percent` (estado carga, 20-100%)
  - `bess_mode` (charging/discharging/idle)
- **Columnas de importación grid**:
  - `grid_import_total_kwh` (importación total)
  - `grid_to_ev_kwh` (grid → EV)
  - `grid_to_mall_kwh` (grid → Mall)
  - `grid_to_bess_kwh` (grid → BESS, si SOC bajo)
- **Costos y CO2**:
  - `cost_grid_import_soles` (costo import)
  - `co2_avoided_indirect_kg` (CO2 evitado por solar)
  - `peak_reduction_savings_soles` (ahorro pico)

#### EV CHARGERS (chargers_ev_ano_2024_v3.csv)
- **Sockets**: 38 (30 motos + 8 mototaxis)
- **Capacidad por socket**: 7.4 kW (Mode 3, 32A @ 230V)
- **Potencia máxima total**: 281.2 kW
- **Demanda anual**: 2,463,312 kWh
- **Patrón**: Demanda CONSTANTE 281.2 kW (las 8760 horas)
  - Esto significa comportamiento modelado, no real
  - En entrenam RPL, agent puede modular por hora
- **Columnas**: `socket_XXX_charger_power_kw` (X=0..37)

#### MALL DEMAND (demandamallhorakwh.csv)
- **Demanda Min**: 0 kW
- **Demanda Max**: 2,763 kW
- **Demanda Media**: 1,412 kW
- **Demanda Anual**: 12,368,653 kWh
- **Patrón**: Horario comercial (picos 10:00-22:00)

---

### 3. ESTADÍSTICAS DE COBERTURA

```
Total Solar Generated:   8,292,514 kWh/año
Total EV Demanded:       2,463,312 kWh/año (29.7%)
Total Mall Demanded:    12,368,653 kWh/año (149.2%)
─────────────────────────────────────────────
Total Demand:           14,831,965 kWh/año (178.9%)

Solar Coverage %:        55.9%
Deficit (needs grid):   -6,539,451 kWh/año

Horas sin solar:         4,501 horas (51.4% noche/nublado)
Horas con solar:         4,259 horas (48.6%)
```

**Interpretación:**
- Sistema está DISEÑADO para cobertura de noche/nublado
- Solar por sí sola: 56% cobertura
- BESS + Solar puede mejorar a ~65-75% (RL optimizing)
- Grid necesario para garantizar suministro 24/7

---

### 4. SINCRONIZACIÓN TEMPORAL

✅ Todos los datasets tienen exactamente 8,760 horas (365 días × 24 h):
- Solar: 8,760 ✓
- BESS: 8,760 ✓
- EV Chargers: 8,760 ✓
- Mall: 8,760 ✓

**Tiempo horario**: Resolución 1 hora (00:00, 01:00, ..., 23:00)

---

### 5. RESTRICCIONES FÍSICAS (VALIDADAS)

| Component | Nominal | Máximo Observado | Status |
|-----------|---------|------------------|--------|
| Solar | 4,050 kWp | 2,887 kW | ✓ OK |
| BESS | 940 kWh | (en rango) | ✓ OK |
| EV Chargers | 281.2 kW | 281.2 kW (constante) | ✓ OK |
| Mall | variable | 2,763 kW | ✓ OK |

---

### 6. FLUJO PARA AGENTE RL

El dataset `bess_ano_2024.csv` ya contiene **TODAS las columnas de cascada**. El RL Agent debe:

#### Observable Variables (del dataset BESS):
```python
CASCADA_FLUJOS = [
  'pv_to_bess_kwh',      # Solar → BESS
  'pv_to_ev_kwh',        # Solar → EV
  'pv_to_mall_kwh',      # Solar → Mall
  'pv_curtailed_kwh',    # Solar exceso
  'bess_charge_kwh',     # BESS entrada (from solar/grid)
  'bess_discharge_kwh',  # BESS salida
  'bess_to_ev_kwh',      # BESS → EV
  'bess_to_mall_kwh',    # BESS → Mall
  'grid_to_ev_kwh',      # Grid → EV
  'grid_to_mall_kwh',    # Grid → Mall
  'grid_import_total_kwh', # Total import
  'bess_soc_percent',    # Estado carga
]

COSTOS_Y_CO2 = [
  'cost_grid_import_soles',        # Costo import
  'co2_avoided_indirect_kg',       # CO2 saved
  'peak_reduction_savings_soles',  # Ahorro pico
]
```

#### Action Variables (what RL Agent controls):
```python
CONTROL_VARIABLES = [
  'charger_power_dispatch',  # Modular potencia de carga (0-1.0)
  'bess_charge_rate',        # Velocidad carga BESS (0-1.0)
  'bess_discharge_rate',     # Velocidad descarga BESS (0-1.0)
  'priority_weights',        # Pesos: BESS vs EV vs Mall
]
```

#### Rewards (Multi-objective):
```python
REWARD_COMPONENTS = {
  'co2_reduction': 0.50,           # Minimizar CO2 grid
  'solar_consumption': 0.20,        # Maximizar solar auto-consumo
  'ev_satisfaction': 0.15,          # Cargar EVs completamente
  'cost_minimization': 0.10,       # Minimizar costo grid
  'grid_stability': 0.05,          # Suavizar rampa power
}
```

---

### 7. ORDEN DE CASCADA CONFIRMADO

✅ **BESS PRIMERO**: `pv_to_bess_kwh` toma prioridad
✅ **EV SEGUNDO**: `pv_to_ev_kwh` después de BESS
✅ **MALL TERCERO**: `pv_to_mall_kwh` después de EV
✅ **GRID ÚLTIMO**: Si deficit, grid importa (`grid_import_total_kwh`)

**Validación en horas**:
- Mediodía (solar pico): 2,887 kW disponible → BESS se carga 1er, luego EV/Mall
- Noche (sin solar): 0 kW solar → BESS descarga para EV, grid para mall
- Transición (sunrise): Solar crece → BESS carga primero

---

### 8. RECOMENDACIÓN PARA ENTRENAMIENDO RL

**Usar columnas REALES del dataset BESS:**
1. Observación = [pv_kw, bess_soc%, ev_demand, mall_demand, flujos_cascada]
2. Acción = [bess_dispatch, charger_modulation, priority_weights]
3. Reward = multi_objective(co2, solar, cost, satisfaction, stability)

**NO simular cascada internamente** → BESS dataset ya lo hizo
**SÍ optimizar modulación** en entrenamiento

Esto permite al Agent aprender **cuándo** usar cada recurso:
- ¿Cargar BESS en pico solar o esperar?
- ¿Cargar EV a potencia máxima o modular?
- ¿Alimentar mall desde solar o grid?
- ¿Cuándo inyectar exceso a grid?

---

### 9. CO2 Y COSTOS POR DATASET

**Factor CO2 Grid**: 0.4521 kg CO₂/kWh (g terrá diesel/thermal)

Por importación:
```
CO2_grid_import = grid_import_total_kwh × 0.4521 kg CO2/kWh
Costo_grid_import = ya calculado en dataset (cost_grid_import_soles)
```

**Métrica RL**: Minimizar `grid_import_total_kwh * 0.4521`

---

### 10. ESTADO DEL SISTEMA (2026-02-14)

- ✅ Datos solares: 8.29 GWh/año REALES (PVGIS)
- ✅ Datos BESS: 25 columnas incluyendo cascada
- ✅ Datos EV: 38 sockets, 2.46 GWh/año
- ✅ Datos Mall: 12.37 GWh/año
- ✅ Sincronización: Todos 8,760 horas ✓
- ✅ Flujo Cascada: BESS → EV → Mall → Grid VALIDADO
- ✅ Restricciones físicas: TODAS OK

**LISTO PARA ENTRENAR RL AGENT**
