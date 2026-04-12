#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BASELINE CALCULATOR — pvbesscar OE3
=====================================
Aplica la FORMULA 1 — BASELINE del entorno (train_sac.py) sobre los
8,760 horas del dataset y guarda los resultados en checkpoints/Baseline/

FORMULA 1 — BASELINE (idéntica a train_sac.py step()):
  - Flota eléctrica → co2_directo_baseline_kg = 0.0 (sin combustión interna)
  - EV red diesel   → co2_indirecto_ev_baseline_kg = ev_demand_kwh[h] * CO2_FACTOR_IQUITOS
  - Mall red diesel → co2_indirecto_mall_baseline_kg = mall_demand_kwh[h] * CO2_FACTOR_IQUITOS
  - co2_indirecto   → ev + mall
  - co2_total       → 0.0 + co2_indirecto
  - co2_reduccion_directa   = co2_avoided_direct_kg   (desde chargers CSV)
  - co2_reduccion_indirecta = 0.0  (sin solar ni BESS)

Uso:
    python scripts/train/run_baseline.py

Salida:
    checkpoints/Baseline/baseline_results.json
    checkpoints/Baseline/baseline_hourly.csv
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# ── rutas ──────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]           # d:\diseñopvbesscar
sys.path.insert(0, str(ROOT / 'scripts' / 'train'))  # common_constants

from common_constants import (
    CO2_FACTOR_IQUITOS,
    HOURS_PER_YEAR,
    CO2_FACTOR_MOTO_KG_KWH,
    CO2_FACTOR_MOTOTAXI_KG_KWH,
)

DATASET_BASE = ROOT / 'data' / 'iquitos_ev_mall'
BASELINE_DIR = ROOT / 'checkpoints' / 'Baseline'
BASELINE_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("BASELINE — FORMULA 1 OE3 (idéntica a train_sac.py)")
print(f"  Dataset : {DATASET_BASE}")
print(f"  Output  : {BASELINE_DIR}")
print("=" * 70)

# ── carga de datasets (misma lógica que train_sac.py) ───────────────────────

# EVs: socket_NNN_charging_power_kw  — fuente: chargers_timeseries.csv
df_chargers = pd.read_csv(DATASET_BASE / 'chargers_timeseries.csv')
N_SOCKETS = 38
N_MOTOS   = 30
_charging_pw = np.array(
    [df_chargers[f'socket_{i:03d}_charging_power_kw'].values[:HOURS_PER_YEAR]
     for i in range(N_SOCKETS)],
    dtype=np.float32,
).T  # (8760, 38)

# ev_demand_dataset_kwh[h] = sum(socket_NNN_charging_power_kw[h])
ev_demand_dataset_kwh = _charging_pw.sum(axis=1)   # (8760,)

# co2_avoided_direct_kg[h] = sum(socket_NNN_co2_reduccion_kg_hora[h])  (fuente: chargers CSV)
co2_avoided_direct_kg = np.zeros(HOURS_PER_YEAR, dtype=np.float32)
for i in range(N_SOCKETS):
    col = f'socket_{i:03d}_co2_reduccion_kg_hora'
    if col in df_chargers.columns:
        co2_avoided_direct_kg += df_chargers[col].values[:HOURS_PER_YEAR].astype(np.float32)
# Fallback idéntico al entorno si la columna no existe
if co2_avoided_direct_kg.sum() == 0.0:
    motos_kw = _charging_pw[:, :N_MOTOS].sum(axis=1)
    taxi_kw  = _charging_pw[:, N_MOTOS:].sum(axis=1)
    co2_avoided_direct_kg = (motos_kw * CO2_FACTOR_MOTO_KG_KWH +
                              taxi_kw  * CO2_FACTOR_MOTOTAXI_KG_KWH).astype(np.float32)

print(f"  [CHARGERS] EV total: {float(ev_demand_dataset_kwh.sum()):>12,.0f} kWh/año")
print(f"  [CHARGERS] CO2 directo evitado: {float(co2_avoided_direct_kg.sum()):>10,.1f} kg/año")

# Mall: mall_demand_kwh[h]  — fuente: mall_demand.csv
df_mall = pd.read_csv(DATASET_BASE / 'mall_demand.csv')
_mall_col = ('mall_demand_kwh' if 'mall_demand_kwh' in df_mall.columns
             else df_mall.select_dtypes(include=[np.number]).columns[0])
mall_demand_kwh_h = df_mall[_mall_col].values[:HOURS_PER_YEAR].astype(np.float32)

print(f"  [MALL]     Mall total: {float(mall_demand_kwh_h.sum()):>12,.0f} kWh/año")

# ── FORMULA 1 — BASELINE (hora a hora, idéntica a train_sac.py) ─────────────

# EMISIONES CO2 DIRECTAS — baseline:
#   Flota eléctrica → sin combustión interna → cero emisión directa
co2_directo_baseline_kg = np.zeros(HOURS_PER_YEAR, dtype=np.float32)  # 0.0 por hora

# EMISIONES CO2 INDIRECTAS — baseline:
#   [EV] Motos/mototaxis REEMPLAZAN combustión fósil → factor gasolina (NO factor red 0.4521)
#   El 0.4521 es el factor de la RED eléctrica de Iquitos (generación diesel).
#   El reemplazo de motos/mototaxis de combustible utiliza factores de combustión:
#     CO2_FACTOR_MOTO_KG_KWH     = 0.87 kg CO2/kWh  (moto gasolina → eléctrica)
#     CO2_FACTOR_MOTOTAXI_KG_KWH = 0.54 kg CO2/kWh  (mototaxi 3 ruedas gasolina → eléctrica, IPCC 2006)
#   Fuente: common_constants.py (derivados de IPCC Tier 1: 2.31 kgCO2/L gasolina)
motos_kw   = _charging_pw[:, :N_MOTOS].sum(axis=1)   # primeros 30 sockets: motos
taxi_kw    = _charging_pw[:, N_MOTOS:].sum(axis=1)   # últimos 8 sockets: mototaxis
co2_indirecto_ev_baseline_kg   = (motos_kw * CO2_FACTOR_MOTO_KG_KWH +
                                   taxi_kw  * CO2_FACTOR_MOTOTAXI_KG_KWH)
#   [MALL] Mall consume de red pública DIESEL → factor red correcto (0.4521 kg CO2/kWh)
#   El mall SIEMPRE fue eléctrico, no hay reemplazo de combustible.
co2_indirecto_mall_baseline_kg = mall_demand_kwh_h * CO2_FACTOR_IQUITOS
co2_indirecto_baseline_kg      = co2_indirecto_ev_baseline_kg + co2_indirecto_mall_baseline_kg
co2_total_baseline_kg          = co2_directo_baseline_kg + co2_indirecto_baseline_kg  # = co2_indirecto

# REDUCCIONES CO2 — baseline:
#   Directa: cambio combustible fósil → eléctrico (desde chargers CSV)
co2_reduccion_directa_baseline_kg   = co2_avoided_direct_kg
#   Indirecta: sin solar ni BESS → cero desplazamiento de red diesel
co2_reduccion_indirecta_baseline_kg = np.zeros(HOURS_PER_YEAR, dtype=np.float32)

# Totales anuales
co2_indirecto_annual  = float(co2_indirecto_baseline_kg.sum())
co2_total_annual      = float(co2_total_baseline_kg.sum())
co2_directo_annual    = float(co2_reduccion_directa_baseline_kg.sum())

print()
print("RESULTADOS FORMULA 1 — BASELINE:")
print(f"  co2_directo_baseline   : {0.0:>12,.1f} kg/año  (flota eléctrica → 0)")
print(f"  co2_indirecto_ev       : {float(co2_indirecto_ev_baseline_kg.sum()):>12,.1f} kg/año  (motos×{CO2_FACTOR_MOTO_KG_KWH} + taxis×{CO2_FACTOR_MOTOTAXI_KG_KWH} — factor combustion IPCC 2006)")
print(f"  co2_indirecto_mall     : {float(co2_indirecto_mall_baseline_kg.sum()):>12,.1f} kg/año  (Mall × 0.4521 — factor red)")
print(f"  co2_indirecto_baseline : {co2_indirecto_annual:>12,.1f} kg/año  (EV + Mall)")
print(f"  co2_total_baseline     : {co2_total_annual:>12,.1f} kg/año  (= indirecto)")
print(f"  co2_reduccion_directa  : {co2_directo_annual:>12,.1f} kg/año  (evitado por electrificación)")
print(f"  co2_reduccion_indirecta: {0.0:>12,.1f} kg/año  (sin solar ni BESS)")
print()

# ── perfil horario completo ──────────────────────────────────────────────────
df_hourly = pd.DataFrame({
    'hour':                              np.arange(HOURS_PER_YEAR).tolist(),
    'ev_demand_dataset_kwh':             ev_demand_dataset_kwh.tolist(),
    'mall_demand_kwh_h':                 mall_demand_kwh_h.tolist(),
    'co2_directo_baseline_kg':           co2_directo_baseline_kg.tolist(),
    'co2_indirecto_ev_baseline_kg':      co2_indirecto_ev_baseline_kg.tolist(),
    'co2_indirecto_mall_baseline_kg':    co2_indirecto_mall_baseline_kg.tolist(),
    'co2_indirecto_baseline_kg':         co2_indirecto_baseline_kg.tolist(),
    'co2_total_baseline_kg':             co2_total_baseline_kg.tolist(),
    'co2_reduccion_directa_baseline_kg': co2_reduccion_directa_baseline_kg.tolist(),
    'co2_reduccion_indirecta_baseline_kg': co2_reduccion_indirecta_baseline_kg.tolist(),
})

hourly_path = BASELINE_DIR / 'baseline_hourly.csv'
df_hourly.to_csv(hourly_path, index=False)
print(f"  [OK] baseline_hourly.csv  -> {hourly_path}")

# ── resultado JSON ────────────────────────────────────────────────────────────
result: dict = {
    'timestamp':             datetime.now().isoformat(),
    'agent':                 'Baseline (NoControl — Formula 1 OE3)',
    'project':               'pvbesscar',
    'location':              'Iquitos, Peru',
    'co2_factor_grid_kg_per_kwh': CO2_FACTOR_IQUITOS,
    'co2_factor_moto_kg_per_kwh': CO2_FACTOR_MOTO_KG_KWH,
    'co2_factor_mototaxi_kg_per_kwh': CO2_FACTOR_MOTOTAXI_KG_KWH,
    'formula': (
        'FORMULA 1 — BASELINE idéntica a train_sac.py | '
        f'EV: factor gasolina IPCC2006 (motos={CO2_FACTOR_MOTO_KG_KWH}, taxis={CO2_FACTOR_MOTOTAXI_KG_KWH} kg CO2/kWh) | '
        'Mall: factor red (0.4521 kg CO2/kWh)'
    ),
    'annual_kwh': {
        'ev_demand':   round(float(ev_demand_dataset_kwh.sum()), 1),
        'mall_demand': round(float(mall_demand_kwh_h.sum()), 1),
    },
    'annual_co2_kg': {
        'co2_directo_baseline':            0.0,
        'co2_indirecto_ev_baseline':       round(float(co2_indirecto_ev_baseline_kg.sum()), 1),
        'co2_indirecto_mall_baseline':     round(float(co2_indirecto_mall_baseline_kg.sum()), 1),
        'co2_indirecto_baseline':          round(co2_indirecto_annual, 1),
        'co2_total_baseline':              round(co2_total_annual, 1),
        'co2_reduccion_directa_baseline':  round(co2_directo_annual, 1),
        'co2_reduccion_indirecta_baseline': 0.0,
    },
    'files': {
        'hourly_csv':    str(hourly_path),
        'results_json':  str(BASELINE_DIR / 'baseline_results.json'),
    },
}

json_path = BASELINE_DIR / 'baseline_results.json'
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print(f"  [OK] baseline_results.json -> {json_path}")
print()
print("=" * 70)
print("BASELINE COMPLETADO — checkpoints/Baseline/")
print("=" * 70)
