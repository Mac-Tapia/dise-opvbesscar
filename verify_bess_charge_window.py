"""
Verificar que carga BESS SOLO ocurre entre 6h-15h (PROTECCIÓN v5.9)
"""

import pandas as pd
import numpy as np

df = pd.read_csv('data/processed/citylearn/iquitos_ev_mall/bess_timeseries.csv')

print("\n" + "="*80)
print("VERIFICACIÓN: Carga BESS dentro de ventana horaria (6h-15h) v5.9")
print("="*80)

# Aggregar por hora del día
df['hour'] = np.arange(len(df)) % 24
hourly = df.groupby('hour').agg({
    'bess_charge_kw': ['sum', 'mean', 'max'],
    'pv_generation_kw': 'mean',
    'ev_demand_kw': 'mean',
    'mall_demand_kw': 'mean'
})

print("\nRESUMEN POR HORA DEL DÍA:")
print("─" * 80)
print(f"{'Hora':<6} {'BESS Carga':<15} {'BESS Prom':<15} {'BESS Max':<15} {'PV Gen':<12} {'EV Dem':<12}")
print("─" * 80)

for hour in range(24):
    charge_sum = hourly.loc[hour, ('bess_charge_kw', 'sum')]
    charge_mean = hourly.loc[hour, ('bess_charge_kw', 'mean')]
    charge_max = hourly.loc[hour, ('bess_charge_kw', 'max')]
    pv_mean = hourly.loc[hour, ('pv_generation_kw', 'mean')]
    ev_mean = hourly.loc[hour, ('ev_demand_kw', 'mean')]
    
    # Marcar problemas
    marker = ""
    if hour >= 15 and charge_sum > 100:  # Si carga después de 15h
        marker = "❌ PROBLEMA"
    elif 6 <= hour < 15 and charge_sum > 100:
        marker = "✅ OK"
    
    print(f"{hour:02d}h-{hour+1:02d}h {charge_sum:>10,.0f}kWh {charge_mean:>10,.0f}kW {charge_max:>10,.0f}kW {pv_mean:>10,.0f}kW {ev_mean:>10,.0f}kW  {marker}")

print("\n" + "="*80)
print("ANÁLISIS:")
print("="*80)

# Horas problemáticas (carga después de 15h)
carga_tarde = df[df.index % 24 >= 15]['bess_charge_kw'].sum()
carga_manana = df[df.index % 24 < 15]['bess_charge_kw'].sum()
carga_total = df['bess_charge_kw'].sum()

print(f"\n✅ Carga BESS (6h-15h, ventana permitida):    {carga_manana:>12,.0f} kWh ({carga_manana/carga_total*100:>5.1f}%)")
print(f"{'✅' if carga_tarde < 100 else '❌'} Carga BESS (15h+,  DEBE SER CERO):        {carga_tarde:>12,.0f} kWh ({carga_tarde/carga_total*100:>5.1f}%)")
print(f"   Carga BESS (22h+5h,    night):          {df[df.index % 24 >= 22]['bess_charge_kw'].sum():>12,.0f} kWh")
print(f"   Carga BESS TOTAL anual:                  {carga_total:>12,.0f} kWh")

if carga_tarde > 100:
    print(f"\n⚠️  ADVERTENCIA: Aún hay {carga_tarde:,.0f} kWh de carga en la tarde!")
    print(f"   Esto indica que la protección horaria NO está funcionando correctamente.")
    # Mostrar horas específicas
    problema_horas = df[df.index % 24 >= 15]  
    problema_horas = problema_horas[problema_horas['bess_charge_kw'] > 10]
    if len(problema_horas) > 0:
        print(f"\n   Horas con carga después de 15h:")
        for idx, row in problema_horas.head(10).iterrows():
            hour = idx % 24
            print(f"      - Hora {hour:02d}: {row['bess_charge_kw']:.1f} kW")
else:
    print(f"\n✅ ÉXITO: Protección horaria funciona correctamente!")
    print(f"   No hay carga de BESS después de las 15h (3 PM).")

print("\n" + "="*80)
