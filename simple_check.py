"""
Verificar si hay carga BESS en la tarde (despues de 15h) en los primeros 7 dias
"""

import pandas as pd

df = pd.read_csv('data/processed/citylearn/iquitos_ev_mall/bess_timeseries.csv')

# Primeros 7 dias
df_7days = df.iloc[:168].copy()

print("\nVERIFICACION: Primeros 7 dias - Carga BESS por hora del dia\n")

problemas = []
for idx in range(len(df_7days)):
    day = idx // 24 + 1
    hour_day = idx % 24
    charge = df_7days.iloc[idx]['bess_charge_kw']
    
    # Si hay carga despues de 15h
    if hour_day >= 15 and charge > 1.0:
        problemas.append((day, hour_day, charge))
        print(f"PROBLEMA: Dia {day}, Hora {hour_day:02d}h: {charge:.1f} kW de carga (NO debe haber)")

if not problemas:
    print("RESULTADO: Sin problemas detectados")
    print("La carga BESS esta correctamente restringida a 6h-15h")
else:
    print(f"\nTotal problemas: {len(problemas)}")
