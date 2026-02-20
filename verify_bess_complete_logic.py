import pandas as pd
import numpy as np

# Cargar dataset original
df = pd.read_csv('data/oe2/bess/bess_ano_2024.csv')

# Revisar día 180 para entender lógica de descarga
day_idx = 180
day_df = df.iloc[day_idx*24:(day_idx+1)*24].copy()

print('=' * 140)
print('LÓGICA DESCARGA BESS REAL - DÍA 180')
print('=' * 140)
print()
print('Hora | PV(kW) | Mall(kW) | EV(kW) | Total(kW) | >1900? | BESS_D(kW) | BESS_EV(kW) | BESS_M(kW) | SOC(%) | Condición')
print('-' * 140)

for h in range(24):
    row = day_df.iloc[h]
    pv = row.get('pv_kwh', 0)
    mall = row.get('mall_kwh', 0)
    ev = row.get('ev_kwh', 0)
    total = mall + ev
    bess_d = row.get('bess_energy_delivered_hourly_kwh', 0)
    bess_e = row.get('bess_to_ev_kwh', 0)
    bess_m = row.get('bess_to_mall_kwh', 0)
    soc = row.get('soc_percent', 0)
    
    exceeds_1900 = "SÍ" if total > 1900 else "NO"
    
    # Determinar condición
    if bess_d > 0:
        cond = f"DESCARGA: PV({pv:.0f}) < Total({total:.0f})"
        if total > 1900:
            cond += " + CRÍTICO"
    elif pv > 0:
        cond = "CARGA (PV disponible)"
    else:
        cond = "SIN BESS (SOC mínimo o PV=0)"
    
    print(f'{h:2d}h | {pv:6.0f} | {mall:8.0f} | {ev:6.0f} | {total:9.0f} | {exceeds_1900:>5} | {bess_d:10.1f} | {bess_e:11.1f} | {bess_m:10.1f} | {soc:6.1f} | {cond}')

print()
print('=' * 140)
print('ANÁLISIS PRIORIDAD EV')
print('=' * 140)
print()

for h in range(12, 23):
    row = day_df.iloc[h]
    ev = row.get('ev_kwh', 0)
    bess_e = row.get('bess_to_ev_kwh', 0)
    grid_e = row.get('grid_import_ev_kwh', 0)
    bess_d = row.get('bess_energy_delivered_hourly_kwh', 0)
    soc = row.get('soc_percent', 0)
    
    total_ev_supply = bess_e + grid_e
    ev_covered_percent = (total_ev_supply / ev * 100) if ev > 0 else 0
    
    print(f'Hora {h:2d}: EV={ev:6.0f} kW → BESS={bess_e:6.1f} + Grid={grid_e:6.0f} = {total_ev_supply:6.1f} ({ev_covered_percent:5.1f}%) | SOC={soc:5.1f}%')

print()
print('=' * 140)
print('CONCLUSIÓN LÓGICA')
print('=' * 140)
print()
print('✓ BESS Descarga = CONDICIONAL + CRÍTICA')
print('  → Descarga cuando: PV < Demanda Total (Mall + EV)')
print('  → PRIORIZA EV: Cubre EV primero, luego Mall')
print('  → Si demanda > 1900 kW: CRÍTICO (máxima descarga)')
print('  → Descarga hasta: SOC mínimo 20% (sin límite de tiempo)')
print('  → Cuando SOC ≤ 20%: No puede descargar más')
