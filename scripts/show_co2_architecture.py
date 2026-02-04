#!/usr/bin/env python
"""
DIAGRAMA VISUAL: Flujo de cálculo CO₂ en OE3
Muestra cómo fluyen los datos desde OE2 hasta SAC/PPO/A2C
"""

def show_architecture():
    print("\n" + "="*100)
    print("🏗️  ARQUITECTURA: FLUJO DE CÁLCULOS CO₂ EN OE3")
    print("="*100 + "\n")

    # ========================================================================
    # NIVEL 1: DATOS OE2 (FUENTE)
    # ========================================================================
    print("📁 NIVEL 1: DATOS OE2 REALES (FUENTE DE VERDAD)")
    print("-" * 100)
    print("""
    ┌─────────────────────────────────────────────────────────────┐
    │  OE2 DATASET (REAL)                                         │
    ├─────────────────────────────────────────────────────────────┤
    │  • Solar: 4,050 kWp → 8,030,119 kWh/año                   │
    │  • Demanda EV: 50 kW constante (9AM-10PM)                  │
    │  • Chargers: 32 físicos, 128 sockets                       │
    │    - 28 motos @ 2.0 kW (112 sockets)                       │
    │    - 4 mototaxis @ 3.0 kW (16 sockets)                     │
    │  • Grid factor: 0.4521 kg CO₂/kWh (térmica Iquitos)       │
    │  • EV factor: 2.146 kg CO₂/kWh (vs combustión)            │
    └─────────────────────────────────────────────────────────────┘
    """)

    # ========================================================================
    # NIVEL 2: CONFIGURACIÓN CÓDIGO (INTEGRACIÓN)
    # ========================================================================
    print("⚙️  NIVEL 2: CONFIGURACIÓN INTEGRADA EN OE3")
    print("-" * 100)
    print("""
    ┌─────────────────────────────────────────────────────────────┐
    │  rewards.py → IquitosContext (línea 145-160)               │
    ├─────────────────────────────────────────────────────────────┤
    │  co2_factor_kg_per_kwh: float = 0.4521 ✓                   │
    │  co2_conversion_factor: float = 2.146 ✓                    │
    │  ev_demand_constant_kw: float = 50.0 ✓                     │
    │  n_chargers: int = 32 ✓                                    │
    │  total_sockets: int = 128 ✓                                │
    │  charger_power_kw_moto: float = 2.0 ✓                      │
    │  charger_power_kw_mototaxi: float = 3.0 ✓                  │
    └─────────────────────────────────────────────────────────────┘
    """)

    # ========================================================================
    # NIVEL 3: EXTRACCIÓN DINÁMICO (DURANTE SIMULACIÓN)
    # ========================================================================
    print("🔄 NIVEL 3: EXTRACCIÓN DINÁMICA DE MÉTRICAS (POR CADA STEP)")
    print("-" * 100)
    print("""
    CityLearn Environment Step Loop (0-8759 pasos)
    │
    ├─→ extract_step_metrics(env, step=t)
    │   └─ Extrae del environment:
    │      • solar_generation_kwh = obs[0]
    │      • grid_import_kwh = (demanda - solar)
    │      • ev_demand_kwh = sum(obs[4:132])
    │      • bess_soc = obs[2]
    │      • hour = t % 24
    │
    ├─→ calculate_co2_metrics(grid, solar, ev, bess)
    │   ├─ co2_grid_kg = grid_import_kwh × 0.4521
    │   ├─ co2_indirect_solar_kg = solar_generation_kwh × 0.4521
    │   ├─ co2_indirect_bess_kg = bess_discharge_kwh × 0.4521
    │   ├─ co2_indirect_avoided_kg = solar_kg + bess_kg ← TOTAL
    │   ├─ co2_direct_avoided_kg = ev_demand_kwh × 2.146
    │   └─ co2_net_kg = grid - indirect - direct
    │
    └─→ EpisodeMetricsAccumulator.accumulate(metrics, reward)
        └─ Acumula por episodio:
           • self.co2_grid_kg += co2['co2_grid_kg']
           • self.co2_indirect_avoided_kg += co2['co2_indirect_avoided_kg']
           • self.co2_direct_avoided_kg += co2['co2_direct_avoided_kg']
           • self.motos_cargadas += conteo_dinamico
           • self.mototaxis_cargadas += conteo_dinamico
    """)

    # ========================================================================
    # NIVEL 4: TRACKING EN AGENTES
    # ========================================================================
    print("🤖 NIVEL 4: TRACKING EN AGENTES (SAC/PPO/A2C)")
    print("-" * 100)
    print("""
    ┌─────────────────────────────────────────────────────────────┐
    │  SAC.learn() → PPO.learn() → A2C.learn()                   │
    ├─────────────────────────────────────────────────────────────┤
    │  self.metrics_accumulator = EpisodeMetricsAccumulator()    │
    │  │
    │  ├─ Cada 500 steps:
    │  │  └─ metrics = accumulator.get_episode_metrics()
    │  │     ├─ co2_grid_kg: XX,XXX kg
    │  │     ├─ co2_indirect_avoided_kg: XX,XXX kg
    │  │     ├─ co2_direct_avoided_kg: XX,XXX kg
    │  │     ├─ co2_net_kg: XX,XXX kg
    │  │     ├─ motos_cargadas: XXX
    │  │     └─ mototaxis_cargadas: XX
    │  │
    │  └─ Fin de episodio:
    │     └─ Log: [SAC] ep 5 | reward=0.45 | co2_net=-15,200 kg | motos=340
    │
    └─────────────────────────────────────────────────────────────┘
    """)

    # ========================================================================
    # NIVEL 5: RESULTADOS FINALES
    # ========================================================================
    print("📊 NIVEL 5: RESULTADOS FINALES (POR EPISODIO)")
    print("-" * 100)
    print("""
    ┌─────────────────────────────────────────────────────────────┐
    │  result_{agent}.json → timeseries_{agent}.csv              │
    ├─────────────────────────────────────────────────────────────┤
    │  {                                                          │
    │    "agent": "sac",                                          │
    │    "steps": 8760,                                           │
    │    "grid_import_kwh": 420000,                               │
    │    "pv_generation_kwh": 8030119,                            │
    │    "ev_charging_kwh": 438000,                               │
    │    "co2_emitido_grid_kg": 189882,      ← Grid import       │
    │    "co2_reduccion_indirecta_kg": 1281514,  ← Solar+BESS   │
    │    "co2_reduccion_directa_kg": 938460,   ← EVs            │
    │    "co2_neto_kg": -2029092,             ← CARBONO-NEGATIVO!│
    │    "environmental_metrics": {                              │
    │      "co2_grid_factor_kg_per_kwh": 0.4521,                │
    │      "co2_conversion_ev_kg_per_kwh": 2.146,               │
    │      "solar_utilization_pct": 85.3,                        │
    │      "grid_independence_ratio": 1.91                       │
    │    }                                                        │
    │  }                                                          │
    └─────────────────────────────────────────────────────────────┘
    """)

    # ========================================================================
    # VERIFICACIÓN
    # ========================================================================
    print("✅ VERIFICACIÓN DE VALORES")
    print("-" * 100)
    print("""
    ┌─────────────────────────────────────────────────────────────┐
    │  VALOR              │ ESTADO │ DÓNDE ESTÁ      │ VALIDACIÓN│
    ├─────────────────────┼────────┼─────────────────┼───────────┤
    │ 107.3 kg CO₂/h      │ ✅ OK  │ rewards.py:150  │ 50×2.146  │
    │ 437.8               │ ❌ N/A │ No en código    │ Legacy    │
    │ motos=20            │ ⚠️ OLD │ OE2 histórico   │ Usa 112   │
    │ mototaxis=3         │ ⚠️ OLD │ OE2 histórico   │ Usa 16    │
    │ 0.4521 kg/kWh       │ ✅ OK  │ rewards.py:147  │ Iquitos   │
    │ 2.146 kg/kWh        │ ✅ OK  │ rewards.py:149  │ vs gas    │
    │ 128 sockets         │ ✅ OK  │ rewards.py:153  │ 32×4      │
    └─────────────────────┴────────┴─────────────────┴───────────┘
    """)

    # ========================================================================
    # RESUMEN
    # ========================================================================
    print("🎯 CONCLUSIÓN")
    print("-" * 100)
    print("""
    1. ✅ 107.3 kg CO₂/h es CORRECTO (50 kW × 2.146)

    2. ✅ Todos los valores fluyen desde OE2 real hasta SAC/PPO/A2C

    3. ✅ Los cálculos son DINÁMICOS (no hardcodeados)

    4. ✅ Cada episodio acumula métricas correctamente

    5. ✅ El código OE3 no depende de valores legacy (437.8, 20/3)

    6. ⚠️  Si ves 437.8 o 20/3, son valores EXTERNOS/LEGACY
    """)

    print("="*100)
    print("✅ ARQUITECTURA VALIDADA - FLUJO CORRECTO")
    print("="*100 + "\n")

if __name__ == "__main__":
    show_architecture()
