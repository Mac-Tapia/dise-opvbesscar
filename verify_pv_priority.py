import pandas as pd
import numpy as np

# Cargar dataset original
df = pd.read_csv('data/oe2/bess/bess_ano_2024.csv')

# Revisar día 180
day_idx = 180
day_df = df.iloc[day_idx*24:(day_idx+1)*24].copy()

print('=' * 150)
print('PRIORIDAD PV - DÍA 180')
print('=' * 150)
print()
print('Hora | PV | PV→EV | PV→BESS | PV→Mall | PV→Grid | Total_Aloc | EV(100%?) | BESS_D | Condición')
print('-' * 150)

for h in range(24):
    row = day_df.iloc[h]
    pv = row.get('pv_kwh', 0)
    pv_ev = row.get('pv_to_ev_kwh', 0)
    pv_bess = row.get('pv_to_bess_kwh', 0)
    pv_mall = row.get('pv_to_mall_kwh', 0)
    pv_grid = row.get('grid_export_kwh', 0)
    ev = row.get('ev_kwh', 0)
    bess_d = row.get('bess_energy_delivered_hourly_kwh', 0)
    
    total_aloc = pv_ev + pv_bess + pv_mall + pv_grid
    
    ev_pct = (pv_ev / ev * 100) if ev > 0 else 0
    ev_100 = "100%" if pv_ev >= ev else f"{ev_pct:.0f}%"
    
    cond = "PRIORIDAD OK" if (pv_ev >= ev) else "EV INSUFICIENTE"
    
    print(f'{h:2d}h | {pv:5.0f} | {pv_ev:6.0f} | {pv_bess:7.0f} | {pv_mall:7.0f} | {pv_grid:7.0f} | {total_aloc:10.0f} | {ev_100:>7} | {bess_d:6.1f} | {cond}')

print()
print('=' * 150)
print('VERIFICACIÓN: ¿PV alimenta EV y BESS al 100% antes de Mall?')
print('=' * 150)
print()

# Horas críticas
for h in [9, 12, 15, 18]:
    row = day_df.iloc[h]
    pv = row.get('pv_kwh', 0)
    pv_ev = row.get('pv_to_ev_kwh', 0)
    pv_bess = row.get('pv_to_bess_kwh', 0)
    pv_mall = row.get('pv_to_mall_kwh', 0)
    ev = row.get('ev_kwh', 0)
    bess_c = row.get('bess_energy_stored_hourly_kwh', 0)
    mall = row.get('mall_kwh', 0)
    
    ev_covered_by_pv = pv_ev / ev if ev > 0 else 0
    bess_charged = bess_c > 0
    
    print(f'Hora {h}h:')
    print(f'  EV {ev:.0f} kW: {pv_ev:.0f} desde PV ({ev_covered_by_pv*100:.0f}%) → {"✓ 100%" if ev_covered_by_pv >= 1 else "✗ Incompleto"}')
    print(f'  BESS: {pv_bess:.0f} kW carga desde PV → {"✓ Sí" if bess_charged else "✗ No"}')
    print(f'  Mall: {pv_mall:.0f} kW desde PV (resto de {pv:.0f})')
    print()
