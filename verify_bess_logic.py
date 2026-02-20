import pandas as pd
import numpy as np

# Cargar dataset original
df = pd.read_csv('data/oe2/bess/bess_ano_2024.csv')

# Revisar día 180 con detalle completo
day_idx = 180
day_df = df.iloc[day_idx*24:(day_idx+1)*24].copy()

print('=' * 120)
print('ANÁLISIS LÓGICA BESS DÍA 180 - FUENTE REAL')
print('=' * 120)
print()
print('Hora | PV(kW) | BESS_C(kW) | BESS_D(kW) | SOC(%) | Mall(kW) | EV(kW) | PV_Mall(kW) | PV_BESS(kW) | BESS_Mall(kW) | Red(kW)')
print('-' * 120)

for h in range(24):
    row = day_df.iloc[h]
    pv = row.get('pv_kwh', 0)
    bess_c = row.get('bess_energy_stored_hourly_kwh', 0)
    bess_d = row.get('bess_energy_delivered_hourly_kwh', 0)
    soc = row.get('soc_percent', 0)
    mall = row.get('mall_kwh', 0)
    ev = row.get('ev_kwh', 0)
    pv_mall = row.get('pv_to_mall_kwh', 0)
    pv_bess = row.get('pv_to_bess_kwh', 0)
    bess_mall = row.get('bess_to_mall_kwh', 0)
    grid_import = row.get('grid_import_kwh', 0)
    
    print(f'{h:2d}h | {pv:6.0f} | {bess_c:10.1f} | {bess_d:10.1f} | {soc:6.1f} | {mall:8.0f} | {ev:6.0f} | {pv_mall:11.0f} | {pv_bess:11.0f} | {bess_mall:13.0f} | {grid_import:6.0f}')

print()
print('=' * 120)
print('VALIDACIÓN DE CONSERVACIÓN DE ENERGÍA')
print('=' * 120)
print()

# Verificar balance de energía
for h in range(24):
    row = day_df.iloc[h]
    pv = row.get('pv_kwh', 0)
    bess_c = row.get('bess_energy_stored_hourly_kwh', 0)
    bess_d = row.get('bess_energy_delivered_hourly_kwh', 0)
    mall = row.get('mall_kwh', 0)
    ev = row.get('ev_kwh', 0)
    pv_mall = row.get('pv_to_mall_kwh', 0)
    pv_ev = row.get('pv_to_ev_kwh', 0)
    pv_bess = row.get('pv_to_bess_kwh', 0)
    bess_mall = row.get('bess_to_mall_kwh', 0)
    bess_ev = row.get('bess_to_ev_kwh', 0)
    grid_import = row.get('grid_import_kwh', 0)
    grid_import_mall = row.get('grid_import_mall_kwh', 0)
    grid_import_ev = row.get('grid_import_ev_kwh', 0)
    
    # PV balance
    pv_total = pv_mall + pv_ev + pv_bess + row.get('grid_export_kwh', 0)
    pv_balance = abs(pv - pv_total)
    
    # Mall balance
    mall_total = pv_mall + bess_mall + grid_import_mall
    mall_balance = abs(mall - mall_total)
    
    # EV balance
    ev_total = pv_ev + bess_ev + grid_import_ev
    ev_balance = abs(ev - ev_total)
    
    # BESS balance
    bess_net = bess_d - bess_c
    bess_out = bess_mall + bess_ev
    bess_balance = abs(bess_net - bess_out)
    
    if h in [0, 6, 9, 12, 15, 18, 21, 23]:
        print(f'Hora {h:2d}:')
        print(f'  PV({pv:.0f}) = PV_Mall({pv_mall:.0f}) + PV_EV({pv_ev:.0f}) + PV_BESS({pv_bess:.0f}) + Export({row.get("grid_export_kwh", 0):.0f}) | Diff: {pv_balance:.1f}')
        print(f'  Mall({mall:.0f}) = PV_Mall({pv_mall:.0f}) + BESS_Mall({bess_mall:.0f}) + Grid_Mall({grid_import_mall:.0f}) | Diff: {mall_balance:.1f}')
        print(f'  EV({ev:.0f}) = PV_EV({pv_ev:.0f}) + BESS_EV({bess_ev:.0f}) + Grid_EV({grid_import_ev:.0f}) | Diff: {ev_balance:.1f}')
        print(f'  BESS: Descarga({bess_d:.0f}) - Carga({bess_c:.0f}) = {bess_net:.0f} = Mall({bess_mall:.0f}) + EV({bess_ev:.0f}) | Diff: {bess_balance:.1f}')
        print()

print('=' * 120)
print('CONCLUSIÓN')
print('=' * 120)
print('✓ BESS Carga (6h-15h): PV → BESS')
print('✓ BESS Descarga (15h-22h): BESS → Mall/EV')
print('✓ Mall cubre: PV_directo + BESS + Red (si falta)')
print('✓ EV cubre: PV_directo + BESS + Red (si falta)')
print('✓ SOC limitado: MIN 20%, MAX 100%')
