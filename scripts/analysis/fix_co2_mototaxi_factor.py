#!/usr/bin/env python3
"""
fix_co2_mototaxi_factor.py
Corrige factor CO2 mototaxi de 0.47 -> 0.54 (IPCC 2006 Tier 1) en chargers CSV.
Actualiza tambien baseline_results.json para consistencia.
"""
from __future__ import annotations
import json
import numpy as np
import pandas as pd
from pathlib import Path

BASE  = Path(__file__).resolve().parent.parent
CSV   = BASE / 'data/oe2/chargers/chargers_ev_ano_2024_v3.csv'
JSON  = BASE / 'checkpoints/Baseline/baseline_results.json'

F_OLD = 0.47
F_NEW = 0.54
RATIO = F_NEW / F_OLD   # escala factor unico para columnas per-socket/-cargador

print('=' * 60)
print('fix_co2_mototaxi_factor.py')
print(f'  Factor antiguo: {F_OLD}  |  Factor nuevo: {F_NEW}  (IPCC 2006)')
print('=' * 60)

# ── 1. Cargar CSV ─────────────────────────────────────────────
print(f'\n[1/4] Cargando {CSV.name}...')
df = pd.read_csv(CSV)
print(f'      Shape: {df.shape}')

antes = df['reduccion_directa_co2_kg'].sum()
print(f'      reduccion_directa_co2_kg ANTES: {antes:,.1f} kg')

# ── 2. Recalcular columnas globales ───────────────────────────
print('\n[2/4] Recalculando columnas globales...')
day_idx = np.arange(len(df)) // 24

# Mototaxis por energia
df['co2_reduccion_mototaxis_kg'] = df['ev_energia_mototaxis_kwh'] * F_NEW
# Directa total
df['reduccion_directa_co2_kg'] = df['co2_reduccion_motos_kg'] + df['co2_reduccion_mototaxis_kg']
# Acumulados
df['co2_directo_anual_acumulado_kg']  = df['reduccion_directa_co2_kg'].cumsum()
df['co2_directo_acumulado_diario_kg'] = df.groupby(day_idx)['reduccion_directa_co2_kg'].cumsum()
# Neto por hora
df['co2_neto_por_hora_kg'] = df['reduccion_directa_co2_kg'] - df['co2_grid_kwh']

despues = df['reduccion_directa_co2_kg'].sum()
print(f'      reduccion_directa_co2_kg DESPUES: {despues:,.1f} kg')
print(f'      Diferencia: +{despues - antes:,.1f} kg')

# ── 3. Escalar sockets/cargadores de mototaxi ─────────────────
print('\n[3/4] Escalando sockets 030-037 y cargadores 15-18...')

# Sockets 030-037 (8 sockets mototaxi)
for i in range(30, 38):
    s = f'socket_{i:03d}'
    col_h = f'{s}_co2_reduccion_kg_hora'
    if col_h not in df.columns:
        continue
    df[col_h] = df[col_h] * RATIO
    df[f'{s}_co2_reduccion_kg_diario']  = df.groupby(day_idx)[col_h].cumsum()
    df[f'{s}_co2_reduccion_kg_anual']   = df[col_h].cumsum()
    # mensual: cumsum por mes
    if 'datetime' in df.columns:
        mes = pd.to_datetime(df['datetime']).dt.month
        df[f'{s}_co2_reduccion_kg_mensual'] = df.groupby(mes)[col_h].cumsum()
    print(f'      {s}: corregido')

# Cargadores 15-18 (4 cargadores mototaxi)
for i in range(15, 19):
    c = f'cargador_{i:02d}'
    col_h = f'{c}_co2_reduccion_kg_hora'
    if col_h not in df.columns:
        continue
    df[col_h] = df[col_h] * RATIO
    df[f'{c}_co2_reduccion_kg_diario']  = df.groupby(day_idx)[col_h].cumsum()
    df[f'{c}_co2_reduccion_kg_anual']   = df[col_h].cumsum()
    if 'datetime' in df.columns:
        mes = pd.to_datetime(df['datetime']).dt.month
        df[f'{c}_co2_reduccion_kg_mensual'] = df.groupby(mes)[col_h].cumsum()
    print(f'      {c}: corregido')

# ── 4. Guardar CSV ────────────────────────────────────────────
print(f'\n[4/5] Guardando CSV...')
df.to_csv(CSV, index=False)
nuevo_total = df['reduccion_directa_co2_kg'].sum()
print(f'      Nuevo total CO2 directo: {nuevo_total:,.1f} kg')

# ── 5. Actualizar baseline_results.json ───────────────────────
print(f'\n[5/5] Actualizando {JSON.name}...')
bl = json.loads(JSON.read_text('utf-8'))
viejo = bl['annual_co2_kg']['co2_reduccion_directa_baseline']
bl['annual_co2_kg']['co2_reduccion_directa_baseline'] = round(nuevo_total, 1)

# Recalcular CO2_NET implícito (para documentación en JSON)
co2_ind_bl = bl['annual_co2_kg']['co2_indirecto_baseline']
co2_net_bl = co2_ind_bl - nuevo_total
bl['annual_co2_kg']['co2_net_baseline_f5'] = round(co2_net_bl, 1)

# Actualizar nota de formula
bl['formula'] = (
    'FORMULA 1 BASELINE + F5 NETO | '
    'EV indirecto: factor gasolina IPCC2006 (motos=0.87, taxis=0.54 kg CO2/kWh) | '
    'Mall: factor red (0.4521 kg CO2/kWh) | '
    'F5 NETO = CO2_IND - CO2_DIR_EVITADO | '
    'Factor mototaxi corregido 0.47->0.54 (IPCC 2006: 3.50L/100km*2.31/15kWh)'
)
JSON.write_text(json.dumps(bl, indent=2, ensure_ascii=False), encoding='utf-8')

print(f'      co2_reduccion_directa_baseline: {viejo:,.1f} -> {nuevo_total:,.1f} kg')
print(f'      co2_net_baseline_f5: {co2_net_bl:,.1f} kg  (nuevo F5 NETO)')

print('\n' + '=' * 60)
print('CORRECCIÓN COMPLETADA')
print(f'  CO2_DIR_BL:  330,030 -> {nuevo_total:,.0f} kg  (factor 0.47→0.54)')
print(f'  CO2_NET_BL:  5,596,274 -> {co2_net_bl:,.0f} kg')
print('=' * 60)
