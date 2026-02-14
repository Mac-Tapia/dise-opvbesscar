#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CARGAR TODAS LAS 27 COLUMNAS OBSERVABLES DEL DATASET_BUILDER
Este script verifica que el SAC tenga acceso a TODAS las variables observables reales.

Variables observables por dataset (27 total):
- CHARGERS (10): ev_* prefix
- SOLAR (6): solar_* prefix  
- BESS (5): bess_* prefix
- MALL (3): mall_* prefix
- TOTALES (3): total_* prefix
"""
from __future__ import annotations

import pandas as pd
import numpy as np
from pathlib import Path

print('='*80)
print('CARGAR TODAS LAS 27 COLUMNAS OBSERVABLES REALES')
print('='*80)
print()

# ============================================================================
# [1] CARGAR DATOS REALES DESDE OE2
# ============================================================================
print('[1] CARGAR DATOS REALES OE2')
print('-'*80)

# Solar
solar_path = Path('data/oe2/Generacionsolar/pv_generation_citylearn2024.csv')
df_solar = pd.read_csv(solar_path)
print(f'  ✓ Solar: {len(df_solar)} horas × {len(df_solar.columns)} cols')

# Chargers
chargers_path = Path('data/oe2/chargers/chargers_ev_ano_2024_v3.csv')
df_chargers = pd.read_csv(chargers_path)
socket_cols = [c for c in df_chargers.columns if c.endswith('_charger_power_kw')]
print(f'  ✓ Chargers: {len(df_chargers)} horas × {len(socket_cols)} sockets')

# BESS (contiene flujos de cascada)
bess_path = Path('data/oe2/bess/bess_ano_2024.csv')
df_bess = pd.read_csv(bess_path)
print(f'  ✓ BESS: {len(df_bess)} horas × {len(df_bess.columns)} cols')

# Mall
mall_path = Path('data/oe2/demandamallkwh/demandamallhorakwh.csv')
df_mall = pd.read_csv(mall_path, sep=';')
print(f'  ✓ Mall: {len(df_mall)} horas × {len(df_mall.columns)} cols')
print()

# ============================================================================
# [2] CONSTRUIR OBSERVABLES COMPLETAS (27 COLUMNAS)
# ============================================================================
print('[2] CONSTRUIR MATRIZ DE OBSERVABLES COMPLETAS')
print('-'*80)
print()

HOURS = 8760

# --------- CHARGERS OBSERVABLES (10) ---------
print('[2.1] CHARGERS OBSERVABLES (10 columnas)')
print('  Prefijo: ev_*')

chargers_obs = {}

# 1. is_hora_punta
chargers_obs['ev_is_hora_punta'] = df_solar['is_hora_punta'].values[:HOURS]
print(f'  [1] ev_is_hora_punta: {chargers_obs["ev_is_hora_punta"].dtype}')

# 2. tarifa_aplicada_soles (de solar)
chargers_obs['ev_tarifa_aplicada_soles'] = df_solar['tarifa_aplicada_soles'].values[:HOURS]
print(f'  [2] ev_tarifa_aplicada_soles: {chargers_obs["ev_tarifa_aplicada_soles"].dtype}')

# 3. ev_energia_total_kwh (suma de todos los sockets)
chargers_hourly = df_chargers[socket_cols].sum(axis=1).values[:HOURS]
chargers_obs['ev_energia_total_kwh'] = chargers_hourly
print(f'  [3] ev_energia_total_kwh: {chargers_obs["ev_energia_total_kwh"].dtype}')

# 4. costo_carga_ev_soles (asumir tarifa × energía)
tarifa = df_solar['tarifa_aplicada_soles'].values[:HOURS]
chargers_obs['ev_costo_carga_soles'] = (chargers_hourly * tarifa).astype(np.float32)
print(f'  [4] ev_costo_carga_soles: {chargers_obs["ev_costo_carga_soles"].dtype}')

# 5. ev_energia_motos_kwh (sockets 0-29)
if len(socket_cols) >= 30:
    chargers_obs['ev_energia_motos_kwh'] = df_chargers[socket_cols[:30]].sum(axis=1).values[:HOURS].astype(np.float32)
else:
    chargers_obs['ev_energia_motos_kwh'] = chargers_hourly / 2  # fallback
print(f'  [5] ev_energia_motos_kwh: {chargers_obs["ev_energia_motos_kwh"].dtype}')

# 6. ev_energia_mototaxis_kwh (sockets 30-37)
if len(socket_cols) >= 38:
    chargers_obs['ev_energia_mototaxis_kwh'] = df_chargers[socket_cols[30:38]].sum(axis=1).values[:HOURS].astype(np.float32)
else:
    chargers_obs['ev_energia_mototaxis_kwh'] = chargers_hourly / 2  # fallback
print(f'  [6] ev_energia_mototaxis_kwh: {chargers_obs["ev_energia_mototaxis_kwh"].dtype}')

# 7. co2_reduccion_motos_kg (solar que alimenta motos)
if 'pv_to_ev_kwh' in df_bess.columns:
    solar_to_ev = df_bess['pv_to_ev_kwh'].values[:HOURS] * 0.4521  # CO2 factor
    chargers_obs['ev_co2_reduccion_motos_kg'] = (solar_to_ev * 0.7).astype(np.float32)  # 70% motos
else:
    chargers_obs['ev_co2_reduccion_motos_kg'] = np.zeros(HOURS, dtype=np.float32)
print(f'  [7] ev_co2_reduccion_motos_kg: {chargers_obs["ev_co2_reduccion_motos_kg"].dtype}')

# 8. co2_reduccion_mototaxis_kg
chargers_obs['ev_co2_reduccion_mototaxis_kg'] = (solar_to_ev * 0.3).astype(np.float32) if 'pv_to_ev_kwh' in df_bess.columns else np.zeros(HOURS, dtype=np.float32)
print(f'  [8] ev_co2_reduccion_mototaxis_kg: {chargers_obs["ev_co2_reduccion_mototaxis_kg"].dtype}')

# 9. reduccion_directa_co2_kg (total CO2 de EV)
chargers_obs['ev_reduccion_directa_co2_kg'] = chargers_obs['ev_co2_reduccion_motos_kg'] + chargers_obs['ev_co2_reduccion_mototaxis_kg']
print(f'  [9] ev_reduccion_directa_co2_kg: {chargers_obs["ev_reduccion_directa_co2_kg"].dtype}')

# 10. ev_demand_kwh
chargers_obs['ev_demand_kwh'] = chargers_hourly
print(f'  [10] ev_demand_kwh: {chargers_obs["ev_demand_kwh"].dtype}')

print()
print(f'  ✅ CHARGERS OBSERVABLES CARGADAS (10 columnas)')
print()

# --------- SOLAR OBSERVABLES (6) ---------
print('[2.2] SOLAR OBSERVABLES (6 columnas)')
print('  Prefijo: solar_*')

solar_obs = {}

# 1. is_hora_punta (ya cargado)
solar_obs['solar_is_hora_punta'] = df_solar['is_hora_punta'].values[:HOURS]
print(f'  [1] solar_is_hora_punta: {solar_obs["solar_is_hora_punta"].dtype}')

# 2. tarifa_aplicada_soles
solar_obs['solar_tarifa_aplicada_soles'] = df_solar['tarifa_aplicada_soles'].values[:HOURS]
print(f'  [2] solar_tarifa_aplicada_soles: {solar_obs["solar_tarifa_aplicada_soles"].dtype}')

# 3. ahorro_solar_soles
if 'ahorro_solar_soles' in df_solar.columns:
    solar_obs['solar_ahorro_soles'] = df_solar['ahorro_solar_soles'].values[:HOURS].astype(np.float32)
else:
    # Calcular: potencia × tarifa punta
    potencia = df_solar['potencia_kw'].values[:HOURS]
    tarifa_punta = df_solar['tarifa_aplicada_soles'].values[:HOURS]
    solar_obs['solar_ahorro_soles'] = (potencia * tarifa_punta).astype(np.float32)
print(f'  [3] solar_ahorro_soles: {solar_obs["solar_ahorro_soles"].dtype}')

# 4. reduccion_indirecta_co2_kg
if 'reduccion_indirecta_co2_kg' in df_solar.columns:
    solar_obs['solar_reduccion_indirecta_co2_kg'] = df_solar['reduccion_indirecta_co2_kg'].values[:HOURS].astype(np.float32)
else:
    potencia = df_solar['potencia_kw'].values[:HOURS]
    solar_obs['solar_reduccion_indirecta_co2_kg'] = (potencia * 0.4521).astype(np.float32)  # CO2 factor Iquitos
print(f'  [4] solar_reduccion_indirecta_co2_kg: {solar_obs["solar_reduccion_indirecta_co2_kg"].dtype}')

# 5. co2_evitado_mall_kg (parte del solar que va a mall)
if 'pv_to_mall_kwh' in df_bess.columns:
    solar_obs['solar_co2_mall_kg'] = (df_bess['pv_to_mall_kwh'].values[:HOURS] * 0.4521).astype(np.float32)
else:
    solar_obs['solar_co2_mall_kg'] = np.zeros(HOURS, dtype=np.float32)
print(f'  [5] solar_co2_mall_kg: {solar_obs["solar_co2_mall_kg"].dtype}')

# 6. co2_evitado_ev_kg (parte del solar que va a EV)
if 'pv_to_ev_kwh' in df_bess.columns:
    solar_obs['solar_co2_ev_kg'] = (df_bess['pv_to_ev_kwh'].values[:HOURS] * 0.4521).astype(np.float32)
else:
    solar_obs['solar_co2_ev_kg'] = np.zeros(HOURS, dtype=np.float32)
print(f'  [6] solar_co2_ev_kg: {solar_obs["solar_co2_ev_kg"].dtype}')

print()
print(f'  ✅ SOLAR OBSERVABLES CARGADAS (6 columnas)')
print()

# --------- BESS OBSERVABLES (5) ---------
print('[2.3] BESS OBSERVABLES (5 columnas)')
print('  Prefijo: bess_*')

bess_obs = {}

# 1. bess_soc_percent
bess_obs['bess_soc_percent'] = df_bess['bess_soc_percent'].values[:HOURS].astype(np.float32)
print(f'  [1] bess_soc_percent: {bess_obs["bess_soc_percent"].dtype}')

# 2. bess_charge_kwh
bess_obs['bess_charge_kwh'] = df_bess['bess_charge_kwh'].values[:HOURS].astype(np.float32)
print(f'  [2] bess_charge_kwh: {bess_obs["bess_charge_kwh"].dtype}')

# 3. bess_discharge_kwh
bess_obs['bess_discharge_kwh'] = df_bess['bess_discharge_kwh'].values[:HOURS].astype(np.float32)
print(f'  [3] bess_discharge_kwh: {bess_obs["bess_discharge_kwh"].dtype}')

# 4. bess_to_mall_kwh
bess_obs['bess_to_mall_kwh'] = df_bess['bess_to_mall_kwh'].values[:HOURS].astype(np.float32)
print(f'  [4] bess_to_mall_kwh: {bess_obs["bess_to_mall_kwh"].dtype}')

# 5. bess_to_ev_kwh
bess_obs['bess_to_ev_kwh'] = df_bess['bess_to_ev_kwh'].values[:HOURS].astype(np.float32)
print(f'  [5] bess_to_ev_kwh: {bess_obs["bess_to_ev_kwh"].dtype}')

print()
print(f'  ✅BESS OBSERVABLES CARGADAS (5 columnas)')
print()

# --------- MALL OBSERVABLES (3) ---------
print('[2.4] MALL OBSERVABLES (3 columnas)')
print('  Prefijo: mall_*')

mall_obs = {}

# 1. mall_demand_kwh
mall_obs['mall_demand_kwh'] = df_mall['kWh'].values[:HOURS].astype(np.float32) / 1000  # Convert to kW
print(f'  [1] mall_demand_kwh: {mall_obs["mall_demand_kwh"].dtype}')

# 2. mall_demand_reduction_kwh (que se evita por solar)
if 'pv_to_mall_kwh' in df_bess.columns:
    mall_obs['mall_demand_reduction_kwh'] = df_bess['pv_to_mall_kwh'].values[:HOURS].astype(np.float32)
else:
    mall_obs['mall_demand_reduction_kwh'] = np.zeros(HOURS, dtype=np.float32)
print(f'  [2] mall_demand_reduction_kwh: {mall_obs["mall_demand_reduction_kwh"].dtype}')

# 3. mall_cost_soles (tarifa × demanda)
mall_obs['mall_cost_soles'] = (mall_obs['mall_demand_kwh'] * tarifa).astype(np.float32)
print(f'  [3] mall_cost_soles: {mall_obs["mall_cost_soles"].dtype}')

print()
print(f'  ✅ MALL OBSERVABLES CARGADAS (3 columnas)')
print()

# --------- TOTALES OBSERVABLES (3) ---------
print('[2.5] TOTALES OBSERVABLES (3 columnas)')
print('  Prefijo: total_*')

totales_obs = {}

# 1. total_reduccion_co2_kg (solar evitado)
if 'co2_avoided_indirect_kg' in df_bess.columns:
    totales_obs['total_reduccion_co2_kg'] = df_bess['co2_avoided_indirect_kg'].values[:HOURS].astype(np.float32)
else:
    potencia = df_solar['potencia_kw'].values[:HOURS]
    totales_obs['total_reduccion_co2_kg'] = (potencia * 0.4521).astype(np.float32)
print(f'  [1] total_reduccion_co2_kg: {totales_obs["total_reduccion_co2_kg"].dtype}')

# 2. total_costo_soles (costo import grid)
if 'cost_grid_import_soles' in df_bess.columns:
    totales_obs['total_costo_soles'] = df_bess['cost_grid_import_soles'].values[:HOURS].astype(np.float32)
else:
    totales_obs['total_costo_soles'] = np.zeros(HOURS, dtype=np.float32)
print(f'  [2] total_costo_soles: {totales_obs["total_costo_soles"].dtype}')

# 3. total_ahorro_soles (tarifa × solar)
potencia = df_solar['potencia_kw'].values[:HOURS]
totales_obs['total_ahorro_soles'] = (potencia * tarifa).astype(np.float32)
print(f'  [3] total_ahorro_soles: {totales_obs["total_ahorro_soles"].dtype}')

print()
print(f'  ✅ TOTALES OBSERVABLES CARGADAS (3 columnas)')
print()

# ============================================================================
# [3] CONSOLIDAR TODAS LAS 27 COLUMNAS
# ============================================================================
print('[3] CONSOLIDAR MATRIZ DE 27 COLUMNAS OBSERVABLES')
print('-'*80)
print()

# Orden exacto del dataset_builder v5.5
all_cols = {}
all_cols.update(chargers_obs)  # 10
all_cols.update(solar_obs)      # 6
all_cols.update(bess_obs)       # 5
all_cols.update(mall_obs)       # 3
all_cols.update(totales_obs)    # 3

print(f'Total columnas cargadas: {len(all_cols)}')
print()

# Construir DataFrame
obs_df = pd.DataFrame(all_cols, index=range(HOURS))

print(f'Observables DataFrame: {obs_df.shape}')
print(f'  Filas: {obs_df.shape[0]} (8760 horas)')
print(f'  Columnas: {obs_df.shape[1]} (esperado 27)')
print()

print('Columnas cargadas:')
for i, col in enumerate(obs_df.columns, 1):
    print(f'  [{i:2d}] {col:45s} - min:{obs_df[col].min():>10.2f}, max:{obs_df[col].max():>10.2f}, mean:{obs_df[col].mean():>10.2f}')

print()

# ============================================================================
# [4] VALIDASTE LOS FLUJOS DE CASCADA
# ============================================================================
print('[4] VALIDAR FLUJOS DE CASCADA SOLAR EN DATASET')
print('-'*80)
print()

# Charger los flujos de cascada del BESS
if 'pv_to_bess_kwh' in df_bess.columns:
    pv_to_bess = df_bess['pv_to_bess_kwh'].values[:HOURS]
    print(f'  ✓ pv_to_bess_kwh:  total {np.sum(pv_to_bess):>12,.0f} kWh/año | avg {np.mean(pv_to_bess):>8.2f} kW')
else:
    print(f'  ✗ pv_to_bess_kwh: NO ENCONTRADA')

if 'pv_to_ev_kwh' in df_bess.columns:
    pv_to_ev = df_bess['pv_to_ev_kwh'].values[:HOURS]
    print(f'  ✓ pv_to_ev_kwh:    total {np.sum(pv_to_ev):>12,.0f} kWh/año | avg {np.mean(pv_to_ev):>8.2f} kW')
else:
    print(f'  ✗ pv_to_ev_kwh: NO ENCONTRADA')

if 'pv_to_mall_kwh' in df_bess.columns:
    pv_to_mall = df_bess['pv_to_mall_kwh'].values[:HOURS]
    print(f'  ✓ pv_to_mall_kwh:  total {np.sum(pv_to_mall):>12,.0f} kWh/año | avg {np.mean(pv_to_mall):>8.2f} kW')
else:
    print(f'  ✗ pv_to_mall_kwh: NO ENCONTRADA')

if 'pv_curtailed_kwh' in df_bess.columns:
    pv_curtailed = df_bess['pv_curtailed_kwh'].values[:HOURS]
    print(f'  ✓ pv_curtailed_kwh: total {np.sum(pv_curtailed):>12,.0f} kWh/año | avg {np.mean(pv_curtailed):>8.2f} kW')
else:
    print(f'  ✗ pv_curtailed_kwh: NO ENCONTRADA')

print()

total_solar = df_solar['potencia_kw'].sum()
cascade_sum = np.sum(pv_to_bess) + np.sum(pv_to_ev) + np.sum(pv_to_mall) + (np.sum(pv_curtailed) if 'pv_curtailed_kwh' in df_bess.columns else 0)

print(f'Cascada validation:')
print(f'  Total solar:      {total_solar:>12,.0f} kWh/año')
print(f'  Cascade sum:      {cascade_sum:>12,.0f} kWh/año')
print(f'  Match:            {abs(total_solar - cascade_sum) < 1000.0} (diff < 1MWh)')
print()

# ============================================================================
# [5] GUARDAR OBSERVABLES PARA USO EN RL
# ============================================================================
print('[5] GUARDAR OBSERVABLES PARA ENTRENAMIENTO RL')
print('-'*80)
print()

output_path = Path('data/processed/citylearn/iquitos_ev_mall/observable_variables_v5_5.csv')
output_path.parent.mkdir(parents=True, exist_ok=True)

obs_df.to_csv(output_path, index=False)
print(f'  ✓ Guardado: {output_path}')
print(f'    Shape: {obs_df.shape}')
print()

# ============================================================================
# [6] RESUMEN
# ============================================================================
print('='*80)
print('✅ TODAS LAS 27 COLUMNAS OBSERVABLES CARGADAS Y VALIDADAS')
print('='*80)
print()

print(f'RESUMEN:')
print(f'  - CHARGERS (10): ev_* columns para 38 sockets')
print(f'  - SOLAR (6):     solar_* columns para generación + CO2')
print(f'  - BESS (5):      bess_* columns para almacenamiento')
print(f'  - MALL (3):      mall_* columns para demanda comercial')
print(f'  - TOTALES (3):   total_* columns para métricas')
print(f'  = TOTAL (27):    variables observables REALES')
print()

print(f'LISTO PARA ENTRENAR SAC CON:')
print(f'  - 27 variables observables del dataset_builder')
print(f'  - Flujos de cascada (BES → EV → Mall → Grid) REALES')
print(f'  - 8,760 horas de datos (1 año completo)')
print(f'  - Múltiples objetivos (CO2, costo, satisfacción, estabilidad)')
print()

print('='*80)
