import pandas as pd
import numpy as np

# Cargar dataset original
df = pd.read_csv('data/oe2/bess/bess_ano_2024.csv')

# Revisar día 180 - analizar cuándo se carga BESS
day_idx = 180
day_df = df.iloc[day_idx*24:(day_idx+1)*24].copy()

print('=' * 140)
print('ANÁLISIS LÓGICA CARGA BESS - DÍA 180')
print('=' * 140)
print()
print('Hora | PV(kW) | Mall(kW) | Total(kW) | >1900? | PV-Mall | BESS_C(kW) | SOC(%) | Condición')
print('-' * 140)

for h in range(24):
    row = day_df.iloc[h]
    pv = row.get('pv_kwh', 0)
    mall = row.get('mall_kwh', 0)
    ev = row.get('ev_kwh', 0)
    total = mall + ev
    bess_c = row.get('bess_energy_stored_hourly_kwh', 0)
    soc = row.get('soc_percent', 0)
    
    pv_minus_mall = pv - mall
    exceeds_1900 = "SÍ" if total > 1900 else "NO"
    
    # Determinar condición
    if bess_c > 0:
        cond = f"CARGA: PV({pv:.0f}) > Mall({mall:.0f})"
        if total > 1900:
            cond += " + CRÍTICO (>1900)"
        cond += f" → Sobra={pv_minus_mall:.0f}"
    else:
        cond = "NO CARGA"
    
    print(f'{h:2d}h | {pv:6.0f} | {mall:8.0f} | {total:9.0f} | {exceeds_1900:>5} | {pv_minus_mall:7.0f} | {bess_c:10.1f} | {soc:6.1f} | {cond}')

print()
print('=' * 140)
print('VERIFICACIÓN: ¿Carga BESS SOLO cuando hay déficit solar?')
print('=' * 140)
print()

for h in range(6, 16):
    row = day_df.iloc[h]
    pv = row.get('pv_kwh', 0)
    mall = row.get('mall_kwh', 0)
    ev = row.get('ev_kwh', 0)
    total = mall + ev
    bess_c = row.get('bess_energy_stored_hourly_kwh', 0)
    soc = row.get('soc_percent', 0)
    
    # Condición teórica
    hay_excedente = pv > mall
    si_carga = bess_c > 0
    critico = total > 1900
    
    print(f'Hora {h:2d}: PV({pv:6.0f}) vs Mall({mall:8.0f})+EV({ev:6.0f})=Total({total:9.0f})')
    print(f'         Excedente PV={hay_excedente}, BESS_C={bess_c:6.1f}, Crítico(>1900)={critico}, SOC={soc:5.1f}%')
    print()

print('=' * 140)
print('CONCLUSIÓN')
print('=' * 140)
print()
print('¿Carga BESS al 100%?')
print('  → Solo cuando hay EXCEDENTE PV (PV > Mall+EV)?')
print('  → O solo cuando hay DÉFICIT y demanda > 1900kW (crítico)?')
