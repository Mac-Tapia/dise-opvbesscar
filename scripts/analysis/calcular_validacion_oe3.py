#!/usr/bin/env python3
"""Script temporal: validar fórmulas CO2 y ranking agentes OE3."""
from __future__ import annotations
import json, pathlib

BASE = pathlib.Path(__file__).resolve().parents[1]
CO2_GRID  = 0.4521
CO2_MOTO  = 0.87
CO2_TAXIS = 0.54

def load(p): return json.loads(pathlib.Path(p).read_text(encoding='utf-8'))

agents_raw = {
    'SAC': load(BASE / 'outputs/sac_training/result_sac.json'),
    'A2C': load(BASE / 'outputs/a2c_training/result_a2c.json'),
    'PPO': load(BASE / 'outputs/ppo_training/result_ppo.json'),
}
bl = load(BASE / 'checkpoints/Baseline/baseline_results.json')
co2_bl = bl['annual_co2_kg']
ev_kwh   = bl['annual_kwh']['ev_demand']
mall_kwh = bl['annual_kwh']['mall_demand']

print('=== VALIDACION FORMULAS ===')
print(f'CO2 grid Iquitos: {CO2_GRID} kg/kWh | CO2 moto: {CO2_MOTO} | CO2 mototaxi: {CO2_TAXIS}')
print()

# FORMULA 1 - BASELINE
co2_ev_bl  = ev_kwh * CO2_GRID
co2_mall_bl = mall_kwh * CO2_GRID
co2_total_bl_calc = co2_ev_bl + co2_mall_bl
print('--- FORMULA 1 BASELINE ---')
print(f'CO2 indirecto EV   = {ev_kwh:,.1f} x {CO2_GRID} = {co2_ev_bl:,.1f} kg/anyo')
print(f'CO2 indirecto Mall = {mall_kwh:,.1f} x {CO2_GRID} = {co2_mall_bl:,.1f} kg/anyo')
print(f'CO2 TOTAL calc     = {co2_total_bl_calc:,.1f} kg/anyo')
co2_bl_json = co2_bl['co2_total_baseline']
print(f'CO2 TOTAL JSON     = {co2_bl_json:,.1f} kg/anyo')
dif = abs(co2_total_bl_calc - co2_bl_json)
print(f'Diferencia         = {dif:,.1f} kg  -- {"OK VALIDADO" if dif < 1 else "DISCREPANCIA"}')
print()

co2_dir_bl = co2_bl.get('co2_reduccion_directa_baseline', 330029.7)
print(f'CO2 reduccion directa (electrificacion) = {co2_dir_bl:,.1f} kg/anyo')
ev_bl_moto  = ev_kwh * CO2_MOTO
difference_direct = ev_bl_moto - co2_ev_bl
print(f'Diferencia fosil-electrico motos       = {ev_kwh:,.1f} x ({CO2_MOTO}-{CO2_GRID}) = {difference_direct:,.1f} kg/anyo')
print()

# FORMULA 2 - CONTROL
print('--- FORMULA 2 CONTROL INTELIGENTE ---')
results_table = []
for ag, d in agents_raw.items():
    v  = d['validation']
    sm = d.get('summary_metrics', {})
    eps = int(d['training'].get('episodes_completed', d['training'].get('episodes', 50)))
    grid_val    = v.get('mean_grid_import_kwh', 0)
    co2_ctrl    = grid_val * CO2_GRID
    co2_dir_ep  = sm.get('total_co2_avoided_direct_kg', 0) / max(eps, 1)
    co2_ind_ep  = sm.get('total_co2_avoided_indirect_kg', 0) / max(eps, 1)
    co2_total_avoided = v.get('mean_co2_avoided_kg', 0)
    delta       = co2_bl_json - co2_ctrl
    red_pct     = delta / co2_bl_json * 100
    dur_min     = d['training']['duration_seconds'] / 60
    reward      = v['mean_reward']
    print(f'{ag}: grid={grid_val:,.0f} kWh/anyo | CO2_ctrl={co2_ctrl:,.0f} kg | reduccion={red_pct:.1f}% | reward={reward:.2f} | {dur_min:.1f} min')
    results_table.append((ag, reward, co2_ctrl, red_pct, dur_min, eps, grid_val, co2_dir_ep, co2_ind_ep, co2_total_avoided))
print()

# FORMULA 3 - CUANTIFICACION TOTAL
print('--- FORMULA 3 CUANTIFICACION TOTAL CO2 REDUCIDO ---')
for ag, rw, co2, red, dur, eps, grid, co2_d, co2_i, co2_tot in results_table:
    total_sistema = co2_dir_bl + (co2_bl_json - co2)
    print(f'{ag}: CO2_directo={co2_d:,.1f} + CO2_indirecto={co2_i:,.1f} = CO2_total_evitado={co2_tot:,.1f} kg/anyo')
    print(f'     CO2_sistema_total = {co2_dir_bl:,.1f}(directo) + {co2_bl_json-co2:,.1f}(indirecto) = {total_sistema:,.1f} kg/anyo')
print()

# RANKING
print('=== RANKING OE3 (menor CO2_grid = mejor) ===')
sorted_agents = sorted(results_table, key=lambda x: x[2])
for r, (ag, rw, co2, red, dur, eps, grid, co2_d, co2_i, co2_tot) in enumerate(sorted_agents, 1):
    print(f'#{r} {ag}: CO2_grid={co2:,.0f} kg/anyo | Reduccion={red:.1f}% | Reward={rw:.2f} | {dur:.1f} min | {eps} eps')
