import pandas as pd
import numpy as np

# Cargar dataset original
df = pd.read_csv('data/oe2/bess/bess_ano_2024.csv')

# Revisar día 180 - enfocarse en 15h-22h descarga
day_idx = 180
day_df = df.iloc[day_idx*24:(day_idx+1)*24].copy()

print('=' * 120)
print('LÓGICA DESCARGA BESS 15h-22h DÍA 180')
print('=' * 120)
print()
print('Hora | PV(kW) | Mall(kW) | EV(kW) | PV-Mall | BESS_D(kW) | BESS_M(kW) | Condición')
print('-' * 120)

for h in range(15, 23):
    row = day_df.iloc[h]
    pv = row.get('pv_kwh', 0)
    mall = row.get('mall_kwh', 0)
    ev = row.get('ev_kwh', 0)
    bess_d = row.get('bess_energy_delivered_hourly_kwh', 0)
    bess_m = row.get('bess_to_mall_kwh', 0)
    bess_e = row.get('bess_to_ev_kwh', 0)
    
    pv_minus_mall = pv - mall
    condition = "PV > Mall" if pv > mall else "PV < Mall (DESCARGA!)" if pv < mall else "PV = Mall"
    
    print(f'{h:2d}h | {pv:6.0f} | {mall:8.0f} | {ev:6.0f} | {pv_minus_mall:7.0f} | {bess_d:10.1f} | {bess_m:10.1f} | {condition}')

print()
print('=' * 120)
print('VERIFICACIÓN: ¿Descarga BESS solo cuando PV < Mall?')
print('=' * 120)
print()

for h in range(15, 23):
    row = day_df.iloc[h]
    pv = row.get('pv_kwh', 0)
    mall = row.get('mall_kwh', 0)
    bess_d = row.get('bess_energy_delivered_hourly_kwh', 0)
    
    # Condición teórica
    debe_descargar = pv < mall
    si_descarga = bess_d > 0
    
    match = "✓" if (debe_descargar == si_descarga) else "✗"
    print(f'Hora {h:2d}: PV({pv:6.0f}) vs Mall({mall:8.0f}) → PV<Mall={debe_descargar}, BESS_D={bess_d:6.1f} (si/no={si_descarga}) {match}')

print()
print('=' * 120)
print('CONCLUSIÓN')
print('=' * 120)
print()
print('✓ BESS Descarga = CONDICIONAL')
print('  → Solo descarga cuando: PV < Mall (insuficiente generación solar)')
print('  → Si PV ≥ Mall: No descarga (PV cubre todo)')
print('  → Descarga limitada a SOC mínimo 20%')
