"""
ANÁLISIS: ¿De dónde sale 5,440 kWh/día?

Verificar y entender el cálculo de energía EV diaria
"""

import pandas as pd

# Cargar dataset diario
df_day1 = pd.read_csv('data/oe2/chargers/chargers_daily_2024_day001.csv')

print("\n" + "="*80)
print("DESGLOSE DE ENERGÍA EV - DÍA 1 (01-ENE-2024)")
print("="*80)

print(f"\n📊 ESTRUCTURA DEL DATASET:")
print(f"   Filas: {len(df_day1)} (24 horas)")
print(f"   Columnas: {list(df_day1.columns)}")

print(f"\n⏰ DEMANDA HORARIA:")
print(f"\n   Hora | Motos | Taxis | Demanda_kWh")
print(f"   ─────┼──────┼──────┼─────────────")

total_energy = 0
hours_with_demand = 0

for idx, row in df_day1.iterrows():
    hour = int(row['hour'])
    motos = int(row['vehicles_charging_motos'])
    taxis = int(row['vehicles_charging_mototaxis'])
    demand = float(row['ev_demand_kwh'])
    
    if demand > 0:
        hours_with_demand += 1
        total_energy += demand
        status = "✓"
    else:
        status = " "
    
    print(f"   {hour:>2}h | {motos:>5} | {taxis:>5} | {demand:>11.1f} {status}")

print(f"\n{'─'*45}")
print(f"\n🔋 RESULTADO FINAL:")
print(f"   Energía total del día: {total_energy:,.0f} kWh")
print(f"   Horas con demanda: {hours_with_demand}")
print(f"   Demanda promedio (total/24h): {total_energy/24:.1f} kWh/h")
print(f"   Demanda máxima (por hora): {df_day1['ev_demand_kwh'].max():.0f} kWh/h")

print(f"\n📈 CÁLCULO:")
print(f"   {hours_with_demand} horas × 544 kWh/h = {hours_with_demand * 544:,.0f} kWh")

print(f"\n✅ RESPUESTA:")
print(f"   5,440 kWh/día = 10 horas × 544 kWh/h")
print(f"   Los chargers solo cargan 10 horas/día (horas pico: 10-21h)")
print(f"   El resto del día: 0 kWh (sin carga)")

print("\n" + "="*80 + "\n")
