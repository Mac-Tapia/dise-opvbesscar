# CityLearn v2.5 - Control Individual de 128 Tomas

## Mapping: Tomas ↔ CityLearn Equipment

### Estructura en Schema JSON

```json
{
  "buildings": [
    {
      "name": "EV_Charging_Mall_Iquitos",
      "equipment": {
        "solar_pv": {
          "nominal_capacity": 4050.0,
          "controllable": false
        },
        "battery_energy_storage": {
          "nominal_capacity": 2000,
          "nominal_power": 1200,
          "controllable": true
        },
        "ev_chargers": [
          {
            "id": "TOMA_0",
            "type": "moto",
            "nominal_power": 2.0,
            "controllable": true,
            "location": "Playa_Motos"
          },
          {
            "id": "TOMA_1",
            "type": "moto",
            "nominal_power": 2.0,
            "controllable": true,
            "location": "Playa_Motos"
          },
          // ... TOMA_2 a TOMA_111 (motos)
          {
            "id": "TOMA_112",
            "type": "mototaxi",
            "nominal_power": 3.0,
            "controllable": true,
            "location": "Playa_Mototaxis"
          },
          // ... TOMA_113 a TOMA_127 (mototaxis)
        ]
      }
    }
  ]
}
```

### Observación - Dimensiones CityLearn

```python
# Obs vector durante step t:
obs_t = [
    # BUILDING-LEVEL (globales)
    solar_generation_kw,           # 1
    total_electricity_demand_kw,   # 1
    grid_import_kw,                # 1
    grid_export_kw,                # 1
    bess_soc_percent,              # 1
    
    # TIME FEATURES
    hour_of_day,                   # 1 (0-23)
    month,                          # 1 (0-11)
    day_of_week,                   # 1 (0-6)
    is_peak_hours,                 # 1 (binary)
    
    # GRID STATE
    grid_carbon_intensity_kgco2_kwh,  # 1
    electricity_tariff_usd_kwh,       # 1
    
    # PER-TOMA (128 × 4 = 512 dims)
    [
        # TOMA 0 (moto)
        toma_0_ev_connected,           # 1
        toma_0_ev_state_of_charge,     # 1 (%)
        toma_0_power_setpoint_kw,      # 1
        toma_0_session_duration_hours, # 1
        
        # TOMA 1 (moto)
        toma_1_ev_connected,
        toma_1_ev_state_of_charge,
        toma_1_power_setpoint_kw,
        toma_1_session_duration_hours,
        
        # ... TOMA 2-111
        
        # TOMA 112 (mototaxi)
        toma_112_ev_connected,
        toma_112_ev_state_of_charge,
        toma_112_power_setpoint_kw,
        toma_112_session_duration_hours,
        
        # ... TOMA 113-127
    ]
]

# TOTAL: 11 (building) + 128 × 4 (tomas) = 523 dims
# (Puede variar según campos adicionales en schema)
```

### Acción - Control Individual

```python
# Action vector (128 dims):
action_t = [
    a_0,     # Toma 0 (moto):     ∈ [0, 1] → P = a_0 × 2.0 kW
    a_1,     # Toma 1 (moto):     ∈ [0, 1] → P = a_1 × 2.0 kW
    # ... a_2 a a_111
    a_112,   # Toma 112 (mototaxi): ∈ [0, 1] → P = a_112 × 3.0 kW
    # ... a_113 a a_127
]

# Interpretación física:
# Si action[i] = 0.5 y hay EV conectado en toma i:
#   - Si i < 112 (moto): Potencia asignada = 0.5 × 2.0 = 1.0 kW
#   - Si i >= 112 (mototaxi): Potencia asignada = 0.5 × 3.0 = 1.5 kW
```

## Dinámica de Timestep (1 hora = 3,600 segundos)

### Pseudocódigo del Environment Step

```python
def step(action):
    """
    Procesa 1 timestep (1 hora) con acción de 128 tomas.
    
    Args:
        action: np.array de shape (128,), valores ∈ [0, 1]
    
    Returns:
        observation, reward, done, info
    """
    
    # 1. CALCULAR DEMANDA POR TOMA
    power_demanded = np.zeros(128)
    for i in range(128):
        if ev_connected[i]:  # ¿Hay EV conectado en toma i?
            p_max = 2.0 if i < 112 else 3.0
            p_requested = action[i] * p_max
            
            # Limitar si EV está lleno
            if ev_soc[i] >= 100:
                p_requested = 0
            
            power_demanded[i] = p_requested
    
    # 2. ENERGÍA TOTAL DEMANDADA (en 1 hora)
    energy_demanded_kwh = power_demanded.sum() * 1.0  # 1 hora
    
    # 3. DESPACHO POR PRIORIDAD (PV > BESS > Grid)
    energy_from_pv = min(energy_demanded_kwh, solar_generation_kwh)
    energy_remaining = energy_demanded_kwh - energy_from_pv
    
    energy_from_bess = min(energy_remaining, bess_available_kwh)
    energy_remaining -= energy_from_bess
    
    energy_from_grid = max(energy_remaining, 0)
    
    # 4. ACTUALIZAR ESTADO
    bess_soc -= (energy_from_bess / bess_capacity) * 100
    bess_soc += (solar_excess / bess_capacity) * 100  # Si hay exceso PV
    bess_soc = np.clip(bess_soc, 20, 100)  # Min SOC 20%
    
    # 5. DISTRIBUIR ENERGÍA A TOMAS
    for i in range(128):
        if power_demanded[i] > 0:
            # Prorrateo de energía disponible
            frac = power_demanded[i] / power_demanded.sum() if power_demanded.sum() > 0 else 0
            energy_to_toma_i = energy_from_pv + energy_from_bess + energy_from_grid * frac
            
            # Actualizar SOC del EV
            if ev_connected[i]:
                energy_kwh = energy_to_toma_i
                ev_soc[i] += (energy_kwh / ev_battery_capacity[i]) * 100
                ev_soc[i] = min(ev_soc[i], 100)  # Limitar a 100%
    
    # 6. CALCULAR RECOMPENSA MULTIOBJETIVO
    reward = compute_reward(
        ev_soc=ev_soc,
        energy_from_grid=energy_from_grid,
        energy_from_pv=energy_from_pv,
        bess_soc=bess_soc,
        actions=action
    )
    
    # 7. GENERAR OBSERVACIÓN SIGUIENTE
    obs_next = build_observation(
        ev_connected=ev_connected,
        ev_soc=ev_soc,
        power_demanded=power_demanded,
        # ... otros campos globales
    )
    
    # 8. VERIFICAR CONDICIÓN DE TÉRMINO
    done = (timestep >= 8760)  # 1 año completo
    
    return obs_next, reward, done, info
```

## Recompensa Multiobjetivo - Desglose por Toma

### Cálculo de Componentes

```python
def compute_reward(ev_soc, energy_from_grid, energy_from_pv, bess_soc, actions):
    """
    Recompensa multiobjetivo viendo estado GLOBAL + por TOMA.
    
    Pesos por defecto (configs/default.yaml):
    - CO₂ (reducción emis): 0.50
    - Solar (autoconsumo):  0.20
    - Costo (tarifario):    0.10
    - EV (satisfacción):    0.10
    - Grid (estabilidad):   0.05
    """
    
    # 1. COMPONENTE CO₂
    # Emisiones evitadas por usar PV + BESS en lugar de grid
    co2_avoided = energy_from_pv * 0.4521  # kg CO₂/kWh grid Iquitos
    co2_baseline = 10200  # kg CO₂/año referencia
    r_co2 = co2_avoided / co2_baseline  # Normalizar [0, 1]
    r_co2 = np.clip(r_co2, -1, 1)
    
    # 2. COMPONENTE SOLAR
    # Fracción de energía demandada que vino de PV
    total_energy = energy_from_pv + energy_from_bess + energy_from_grid
    if total_energy > 0:
        solar_fraction = energy_from_pv / total_energy
    else:
        solar_fraction = 0
    r_solar = solar_fraction  # [0, 1]
    
    # 3. COMPONENTE COSTO
    # Penalidad por importación de grid (alto costo + CO₂)
    energy_cost = energy_from_grid * 0.2  # USD 0.2/kWh
    cost_baseline = 900  # USD/día referencia
    r_cost = 1 - (energy_cost / cost_baseline)
    r_cost = np.clip(r_cost, -1, 1)
    
    # 4. COMPONENTE EV (Satisfacción de carga)
    # EVs cargados al máximo = mejor satisfacción
    ev_satisfaction = ev_soc.mean() / 100  # % promedio
    r_ev = ev_satisfaction  # [0, 1]
    
    # 5. COMPONENTE GRID (Estabilidad)
    # Penalizar picos de importación
    grid_peak_penalty = (energy_from_grid / 500) if energy_from_grid > 100 else 0
    r_grid = 1 - np.clip(grid_peak_penalty, 0, 1)
    
    # 6. RECOMPENSA TOTAL
    weights = {
        'co2': 0.50,
        'solar': 0.20,
        'cost': 0.10,
        'ev': 0.10,
        'grid': 0.05
    }
    
    r_total = (
        weights['co2'] * r_co2 +
        weights['solar'] * r_solar +
        weights['cost'] * r_cost +
        weights['ev'] * r_ev +
        weights['grid'] * r_grid
    )
    
    return r_total
```

## Ejemplo de Episode Completo

### Escenario: Día Soleado (t = 16-20)

```
TIMESTEP 16 (4pm = HORA SOLEADA)
=====================================
Observación:
  - Solar PV: 320 kW
  - Total demand: 180 kW (150 de EVs + 30 del mall)
  - BESS SOC: 60%
  - EVs conectados: 45 motos + 8 mototaxis

Acción del agente (128 dims):
  - action[0:45] = 0.9   (45 motos al 90% potencia)
  - action[45:53] = 0.8  (8 mototaxis al 80% potencia)
  - action[53:128] = 0.0 (resto desconectado)

Cálculo de potencia:
  P_motos = 45 × 0.9 × 2.0 = 81.0 kW
  P_mototaxis = 8 × 0.8 × 3.0 = 19.2 kW
  P_total_EV = 100.2 kW

Despacho (1 hora):
  E_from_pv = min(100.2, 320) = 100.2 kWh   (¡Cero importación de grid!)
  E_from_bess = 0 kWh
  E_from_grid = 0 kWh
  E_solar_exceso = 320 - 100.2 = 219.8 kWh → Cargar BESS

Recompensa:
  r_co2 = 100.2 × 0.4521 / 10200 = +0.0047 (¡Evitó CO₂!)
  r_solar = 100.2 / 100.2 = 1.0 (100% solar, no grid)
  r_cost = 1 - 0 = 1.0 (costo = 0)
  r_ev = 45% (algunos EVs al 90%, algunos al 0%)
  r_grid = 1.0 (cero importación)
  
  r_total = 0.50×0.005 + 0.20×1.0 + 0.10×1.0 + 0.10×0.45 + 0.05×1.0
          = 0.0025 + 0.20 + 0.10 + 0.045 + 0.05
          = +0.3975 ✓ (Recompensa POSITIVA - acción óptima)


TIMESTEP 18 (6pm = HORA PICO SIN SOL)
=====================================
Observación:
  - Solar PV: 25 kW (atardecer)
  - Total demand: 320 kW (270 de EVs + 50 del mall)
  - BESS SOC: 85% (se cargó durante el día)
  - EVs conectados: 85 motos + 15 mototaxis

Acción del agente:
  - action[0:85] = 1.0   (85 motos a máxima potencia)
  - action[85:100] = 1.0 (15 mototaxis a máxima potencia)
  - action[100:128] = 0.0

Cálculo de potencia:
  P_motos = 85 × 1.0 × 2.0 = 170.0 kW
  P_mototaxis = 15 × 1.0 × 3.0 = 45.0 kW
  P_total_EV = 215.0 kW

Despacho (1 hora):
  E_from_pv = min(215.0, 25) = 25.0 kWh
  E_from_bess = min(215.0 - 25, 1700 × 0.80) = 152.0 kWh  (descarga BESS)
  E_from_grid = 215.0 - 25 - 152 = 38.0 kWh
  BESS SOC después: 85% - (152/2000×100) = 77.4%

Recompensa:
  r_co2 = (25 + 152) × 0.4521 / 10200 = 0.0083 (BESS evita grid)
  r_solar = 25 / 215 = 0.116 (solo 11.6% solar, necesitó red)
  r_cost = 1 - (38 × 0.2 / 900) = 0.992 (bajo costo aún)
  r_ev = 95% (casi todos los EVs al 100%)
  r_grid = 0.92 (cierta importación, pero manejada)
  
  r_total = 0.50×0.0083 + 0.20×0.116 + 0.10×0.992 + 0.10×0.95 + 0.05×0.92
          = 0.00415 + 0.0232 + 0.0992 + 0.095 + 0.046
          = +0.268 ✓ (Positiva pero menor - limitado por poca solar)
```

## Checklist: CityLearn Integration

- [ ] Schema genera 128 `ev_chargers` (TOMA_0 a TOMA_127)
- [ ] Obs incluye 4 campos por toma (connected, SOC, power, duration)
- [ ] Action space dimension = 128
- [ ] Dispatch rules implementados (PV > BESS > Grid)
- [ ] Rewards normalizados [0, 1]
- [ ] Episode length = 8,760 timesteps (1 año)
- [ ] Time step = 3,600 segundos (1 hora)
- [ ] Agents (SAC/PPO/A2C) entrenan con 128 acciones
- [ ] Validar que agentes aprenden balanceo de tomas

## Performance Esperado

Con 128 tomas controlables independientemente:

| Metrica | Baseline | SAC | PPO | A2C |
|---------|----------|-----|-----|-----|
| **CO₂ anual (kg)** | 10,200 | 7,500 (-26%) | 7,200 (-29%) | 7,800 (-24%) |
| **Solar utilizado (%)** | 40% | 65% | 68% | 60% |
| **Grid import (kWh/año)** | 41,300 | 28,400 | 26,100 | 30,700 |
| **EV satisfaction (%)** | 100% | 98% | 99% | 97% |
| **Avg reward/episode** | -0.15 | +0.42 | +0.48 | +0.38 |

Este control granular de 128 tomas permite que los agentes RL optimicen de forma mucho más precisa.
