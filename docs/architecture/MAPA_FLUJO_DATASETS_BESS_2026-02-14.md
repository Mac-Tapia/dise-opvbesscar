# 📍 MAPA DE FLUJO - Datasets → Observación → Reward → Logging

```
════════════════════════════════════════════════════════════════════════════════
DATASETS OE2 (5 sources) → ENTRENAMIENTO PPO/A2C (8,760 horas)
════════════════════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────────┐
│ OE2 DATASOURCES - LÍNEA DE CARGA (PASO 3: línea ~2950-3070)   │
├─────────────────────────────────────────────────────────────────┤

📊 DATASET 1: SOLAR (pv_generation_citylearn_v2.csv)
│ └─ Columna: 'pv_generation_kwh' ← 8,760 horas, 8.3M kWh/año
│    Priority: [pv_generation_kwh] → [ac_power_kw] → [potencia_kw]
│    Storage: np.ndarray solar_hourly (8760,) float32
│    Validation: MUST be exactly 8760 rows
│    
│    ✅ Usado en:
│       • _make_observation() obs[0]
│       • step() energy_balance
│       • step() solar_avoided (CO₂)
│       • VehicleChargingSimulator power
│       • Logging callback

📊 DATASET 2: CHARGERS (chargers_ev_ano_2024_v3.csv)
│ └─ Columnas: 38 × 'charger_power_kw' ← 8,760 horas, 2.46M kWh/año
│    Pattern match: auto-detect 'charger_power_kw'
│    If < 38: expand (19 chargers × 2 sockets cada uno)
│    Storage: np.ndarray chargers_hourly (8760, 38) float32
│    
│    ✅ Usado en:
│       • _make_observation() obs[8:46] (demanda)
│       • _make_observation() obs[46:84] (potencia)
│       • step() charger_demand[h]
│       • step() charger_setpoints (action[1:39])
│       • step() ev_charging_kwh
│       • VehicleChargingSimulator (motos vs taxis)
│       • Logging (40+ metrics)
│       • Reward (CO₂ directo)

📊 DATASET 3: MALL (demandamallhorakwh.csv)
│ └─ Columna: última columnanumérica ← 8,760 horas, 12.4M kWh/año
│    Flexible: busca columna numérica (nombre variable)
│    Storage: np.ndarray mall_hourly (8760,) float32
│    
│    ✅ Usado en:
│       • _make_observation() obs[1]
│       • step() mall_kw
│       • step() total_demand_kwh
│       • step() peak_shaving_factor (BESS benefit)
│       • Logging trajectory

📊 DATASET 4: BESS SOC (bess_ano_2024.csv)
│ └─ Columna: 'soc' ← 8,760 horas, auto-normalized [0,1]
│    Pattern match: auto-detect 'soc' column
│    Normalize: if max > 1.0 then divide by 100
│    Storage: np.ndarray bess_soc (8760,) float32
│    
│    ✅ Usado en:
│       • _make_observation() obs[2] (SOC)
│       • _make_observation() obs[3] (bess_energy_available)
│       • _make_observation() obs[150] (should_charge)
│       • _make_observation() obs[151] (should_discharge)
│       • step() bess_soc_actual
│       • step() bess_power_kw (control)
│       • Reward (CO₂ BESS benefit)
│       • Logging (bess_soc_avg, discharge, charge)

📊 DATASET 5: CHARGER STATS (chargers_real_statistics.csv)
│ └─ Columnas: [38] max_power_kw, [38] mean_power_kw
│    ← 7.4 kW nominal Mode 3, 4.6 kW promedio
│    Storage: np.ndarray charger_max_power (38,) float32
│    
│    ✅ Usado en:
│       • step() charger_power_effective = setpoints × max_power
│       • VehicleChargingSimulator(actual_controlled_power)
│       • Observation normalization

└─ Todas las columnas → CityLearnEnvironment.__init__()
   
════════════════════════════════════════════════════════════════════════════════
ENVIRONMENT: CityLearnEnvironment (8,760 timesteps por episodio)
════════════════════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────────┐
│ _make_observation() - 156-dim vector (cada hora)               │
├─────────────────────────────────────────────────────────────────┤

ENERGY [0-7]:  Datos de datasets
├─ obs[0] = solar_kw / SOLAR_MAX_KW           ← DATASET 1 (solar)
├─ obs[1] = mall_kw / MALL_MAX_KW            ← DATASET 3 (mall)
├─ obs[2] = bess_soc                          ← DATASET 4 (BESS)
├─ obs[3] = bess_energy / BESS_MAX            ← DATASET 4 (BESS)
├─ obs[4] = solar_surplus / 50.0              ← Computed
├─ obs[5] = grid_import / 500.0               ← Computed
├─ obs[6] = (solar - demand) / 100            ← Computed
└─ obs[7] = total_charge_capacity / 300       ← Computed

CHARGERS [8-45]: Por cada socket (obs[8:46])
├─ obs[8:46] = charger_demand[:38] / CHARGER_MAX_KW
│              ↑ DATASET 2 (chargers, 38 columnas)

POWER [46-83]: Por cada socket (obs[46:84])
├─ obs[46:84] = charger_setpoints × charger_max_power[:38]
│               ↑ DATASET 5 (charger stats, max_power)

OCUPANCY [84-121]: Por cada socket (obs[84:122])
├─ obs[84:122] = 1.0 if socket_charging else 0.0

VEHICLES [122-137]: Conteos + estadísticas
├─ obs[122] = motos_charging_now / 30        ← VehicleChargingSimulator
├─ obs[123] = taxis_charging_now / 8         ← VehicleChargingSimulator
├─ obs[126] = motos_soc_avg                  ← Computed
├─ obs[127] = taxis_soc_avg                  ← Computed
│ ... (más features de vehículos)

TIME [138-143]: Temporal features
├─ obs[138] = hour / 24                       ← Computed
├─ obs[139] = dayofweek / 7                   ← Computed
├─ obs[140] = month / 12                     ← Computed
├─ obs[141] = is_peak_hour [0,1]             ← Computed
├─ obs[142] = CO2_FACTOR_IQUITOS (0.4521)    ← Constant
└─ obs[143] = tariff (0.15 USD/kWh)          ← Constant

INTER-SYSTEM [144-155]: Comunicación BESS↔Solar↔Grid
├─ obs[144] = bess_can_supply                ← BESS logic
├─ obs[145] = solar_sufficient               ← Solar logic
├─ obs[150] = should_charge_bess = 1 if (solar>100 AND bess_soc<0.8)
├─ obs[151] = should_discharge_bess = 1 if (solar<demand×0.5 AND bess_soc>0.3)
│ ... (más signals de coordinación)
└─ obs[155] = daily_progress / 309 (vehicles/day goal)

════════════════════════════════════════════════════════════════════════════════
step() - Energy Balance & Reward Calculation (cada hora)
════════════════════════════════════════════════════════════════════════════════

┌────────────────────────────────────┐
│ LECTURA DE DATOS (línea ~850-880) │
├────────────────────────────────────┤

solar_kw = float(self.solar_hourly[h])           ← DATASET 1
mall_kw = float(self.mall_hourly[h])             ← DATASET 3
charger_demand = self.chargers_hourly[h]         ← DATASET 2 (38,)
bess_soc = self.bess_soc_hourly[h]               ← DATASET 4
bess_action = action[0]                          ← Agent action
charger_setpoints = action[1:39]                 ← Agent action (38,)

┌────────────────────────────────────┐
│ ENERGY BALANCE (línea ~865-880)   │
├────────────────────────────────────┤

charger_power_effective = charger_setpoints × charger_max_power[:38]
                         ↑ DATASET 5 (max_power)

ev_charging_kwh = sum(min(charger_power_effective, charger_demand))
                  ↑ DATASET 2 (charger_demand)

bess_power_kw = (bess_action - 0.5) × 2.0 × 342.0  ← BESS CONTROL
                [-342 (carga), 0 (idle), +342 (descarga)]

total_demand_kwh = mall_kw + ev_charging_kwh

net_demand = total_demand_kwh - bess_power_kw    ← ⭐ BESS resta de demanda
                                   ↑
             si bess_power > 0 (descarga) → reduce grid import
             si bess_power < 0 (carga) → aumenta grid import

grid_import_kwh = max(0.0, net_demand - solar_kw)
                  ↑ DATASET 1 (solar)

┌────────────────────────────────────┐
│ CO₂ CALCULATIONS (línea ~920-945) │
├────────────────────────────────────┤

CO₂ DIRECTO (EV vs gasolina):
  km_motos = ev_charging_kwh × (30/38) × 50 km/kWh    ← DATASET 2 ratio
  km_mototaxis = ev_charging_kwh × (8/38) × 30        ← DATASET 2 ratio
  litros_evitados = (km_motos × 2.0 + km_mototaxis × 3.0) / 100
  co2_avoided_direct_kg = litros_evitados × 2.31      ← Fixed constant

CO₂ INDIRECTO - SOLAR:
  solar_avoided = min(solar_kw, total_demand_kwh)     ← DATASETS 1, 3
  co2_solar = solar_avoided × 0.4521                  ← Fixed constant

CO₂ INDIRECTO - BESS (⭐ CRITICAL):
  bess_discharge = max(0, bess_power_kw)              ← BESS control
  
  if mall_kw > 2000:
    peak_factor = 1.0 + (mall_kw - 2000) / mall_kw × 0.5
                        ↑ DATASET 3 (mall)
  else:
    peak_factor = 0.5 + mall_kw / 2000 × 0.5
                        ↑ DATASET 3 (mall)
  
  bess_co2_benefit = bess_discharge × peak_factor
  co2_avoided_indirect = (solar_avoided + bess_co2_benefit) × 0.4521
                                  ↑                ↑
                           DATASETS 1,3        BESS control

CO₂ TOTAL:
  co2_total = co2_avoided_direct + co2_avoided_indirect

┌────────────────────────────────────┐
│ VEHICLE CHARGING SIMULATION (línea ~1010-1025) │
├────────────────────────────────────┤

actual_controlled_power = sum(charger_power_effective)   ← DATASET 5
solar_available = max(0, solar - mall)                  ← DATASETS 1, 3
bess_available = max(0, bess_power) if bess_power > 0   ← BESS control
grid_available = 500.0

total_available_power = actual + solar_available + bess_available + grid
                                                  ↑ ⭐ BESS aumenta disponible

available_power = max(50.0, total_available_power)

charging_result = vehicle_simulator.simulate_hourly_charge(scenario, available_power)

motos_10 = charging_result.get('motos_10_percent_charged', 0)
motos_20 = ...
... (7 SOC levels for motos + taxis)

┌────────────────────────────────────┐
│ REWARD CALCULATION (línea ~950-1100) │
├────────────────────────────────────┤

reward = MultiObjectiveReward.compute(
  grid_import_kwh=grid_import_kwh,              ← Computed
  solar_generation_kwh=solar_kw,                ← DATASET 1
  ev_charging_kwh=ev_charging_kwh,              ← Computed
  ev_soc_avg=ev_soc_avg,                        ← Computed
  bess_soc=bess_soc,                            ← DATASET 4
  hour=h % 24,                                  ← Computed
)

# Weights (multiobjetivo):
# CO₂: 0.35
# Solar: 0.20
# EV: 0.30
# Cost: 0.10
# Grid: 0.05

# ⭐ CO₂ component includes:
#    - Direct (EV vs gas): co2_avoided_direct_kg
#    - Indirect solar: solar_avoided × 0.4521
#    - Indirect BESS: bess_co2_benefit × 0.4521  ← BESS REWARD
#
# Total CO₂ reward = (total_avoided / 100.0) × 0.35

════════════════════════════════════════════════════════════════════════════════
LOGGING & TRACKING (Callback)
════════════════════════════════════════════════════════════════════════════════

DetailedLoggingCallback _on_step():
├─ episode_bess_discharged_kwh += max(0, bess_power_kw)
├─ episode_bess_charged_kwh += abs(min(0, bess_power_kw))
├─ episode_co2_avoided_indirect += co2_avoided_indirect
├─ episode_co2_avoided_direct += co2_avoided_direct
├─ episode_solar_kwh += solar_kw
├─ episode_grid_import += grid_import_kwh
│
├─ trace_records.append({
│    'step': step,
│    'solar_kw': solar_kw,
│    'mall_kw': mall_kw,
│    'ev_charging_kwh': ev_charging_kwh,
│    'bess_soc': bess_soc,
│    'bess_power_kw': bess_power_kw,
│    'grid_import_kwh': grid_import_kwh,
│    'co2_direct': co2_avoided_direct_kg,
│    'co2_indirect': co2_avoided_indirect_kg,
│    'motos_10%': motos_10,
│    'motos_20%': motos_20,
│    ... (40+ metrics)
│ })
│
└─ On episode end:
   episode_metrics.append({
      'episode': episode,
      'total_solar': sum(solar_kw),
      'total_ev_charged': sum(ev_charging_kwh),
      'total_bess_discharge': episode_bess_discharged_kwh,
      'total_co2_avoided': co2_total,
      'motos_charged_100%': motos_100,
      'taxis_charged_100%': taxis_100,
      ... (15+ summary metrics)
   })

════════════════════════════════════════════════════════════════════════════════
OUTPUT FILES
════════════════════════════════════════════════════════════════════════════════

outputs/ppo_training/:
├─ result_ppo.json              ← Metricas resumidas por episodio
├─ timeseries_ppo.csv           ← Time series por hora (8,760 rows × episodio)
├─ trace_ppo.csv                ← Detalles paso a paso
├─ ppo_kl_divergence.png        ← KL policy convergence
├─ ppo_entropy.png              ← Policy exploration
├─ ppo_value_metrics.png        ← Value function quality
├─ kpi_carbon_emissions.png     ← CO₂ reduction trajectory
├─ kpi_electricity_consumption.png
└─ ... (11 total PNG graphs)

════════════════════════════════════════════════════════════════════════════════
SUMMARY: Dataset → Observation → Step → Reward → Logging
════════════════════════════════════════════════════════════════════════════════

✅ TODAS LAS COLUMNAS USADAS:
│
├─ SOLAR: pv_generation_kwh
│  ├─ obs[0] (energy)
│  ├─ solar_avoided (CO₂ indirect)
│  ├─ VehicleChargingSimulator power
│  └─ Logging
│
├─ CHARGERS: 38 sockets × charger_power_kw
│  ├─ obs[8:46] (demand)
│  ├─ obs[46:84] (delivered power)
│  ├─ ev_charging_kwh (energy balance)
│  ├─ CO₂ direct (EV vs gas)
│  └─ VehicleChargingSimulator + Logging
│
├─ MALL: demand_kw
│  ├─ obs[1] (energy)
│  ├─ peak_shaving_factor (BESS benefit)
│  ├─ total_demand (energy balance)
│  └─ Logging
│
├─ BESS SOC: soc_%
│  ├─ obs[2,3,144,150-151] (6 features)
│  ├─ bess_power control (energy balance)
│  ├─ CO₂ benefit (BESS discharge × peak_factor)
│  ├─ VehicleChargingSimulator power
│  └─ Logging (episode_bess_kwh)
│
└─ CHARGER STATS: max_power, mean_power (38 values)
   ├─ Power scaling (charger_power_effective)
   ├─ VehicleChargingSimulator (actual_controlled_power)
   └─ Logging

✅ BESS COMPLETAMENTE INCORPORADO:
│
├─ Observation: 6 features
├─ Energy Balance: net_demand -= bess_power
├─ Reward: CO₂ benefit = bess_discharge × peak_shaving_factor × 0.4521
├─ Vehicle Charging: BESS poder disponible
└─ Tracking: episode_bess_discharge/charge_kwh

✅ PPO ≡ A2C:
│
├─ Datasets idénticos
├─ BESS logic idéntica
├─ Observation/action spaces idénticos
└─ Reward calculation idéntica

════════════════════════════════════════════════════════════════════════════════
```

---

## 🎯 Conclusión

**Todas las columnas de TODOS los datasets se usan correctamente en el entrenamiento.**

**BESS está completamente incorporado en:**
1. ✅ Observaciones (obs[2,3,144,150-151] = 6 features)
2. ✅ Energy Balance (net_demand -= bess_power_kw)
3. ✅ Reward Calculation (CO₂ benefit component)
4. ✅ Vehicle Charging (poder disponible aumentado por BESS)
5. ✅ Logging (episode_bess_discharge/charge_kwh + daily values)

**Estado:** ✅ **LISTO PARA ENTRENAMIENTO**
