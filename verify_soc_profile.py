import pandas as pd

df = pd.read_csv('data/oe2/bess/bess_simulation_hourly.csv')
df['hour'] = pd.to_datetime(df['datetime']).dt.hour

print("\nSOC PERFIL 17h-22h (HORAS CRITICAS):")
print("-" * 110)
criticas = df[(df['hour'] >= 17) & (df['hour'] <= 22)].copy()
for _, row in criticas.iterrows():
    print(f"  {row['hour']:2.0f}h: SOC={row['bess_soc_percent']:5.1f}%, "
          f"EV_dem={row['ev_demand_kwh']:6.1f}, BESS->EV={row['bess_to_ev_kwh']:6.1f}, "
          f"BESS->MALL={row['bess_to_mall_kwh']:6.1f}")

soc_17h = criticas.iloc[0]['bess_soc_percent']
soc_22h = criticas.iloc[-1]['bess_soc_percent']
energy_available = (soc_17h - 20) / 100.0 * 1700

print(f"\n{'=' * 110}")
print(f"ANALISIS DE ENERGIA DISPONIBLE:")
print(f"  SOC a 17h: {soc_17h:.1f}%")
print(f"  SOC a 22h: {soc_22h:.1f}%")
print(f"  Energía disponible total (17h-22h): ({soc_17h:.0f}%-20%) × 1700 = {energy_available:.0f} kWh")
print(f"  Energía a EV (observado): {criticas['bess_to_ev_kwh'].sum():.0f} kWh")
print(f"  Energía a MALL (observado): {criticas['bess_to_mall_kwh'].sum():.0f} kWh")
print(f"  Total descargado: {criticas['bess_to_ev_kwh'].sum() + criticas['bess_to_mall_kwh'].sum():.0f} kWh")
print(f"  Diferencia: {energy_available - (criticas['bess_to_ev_kwh'].sum() + criticas['bess_to_mall_kwh'].sum()):.0f} kWh")
print(f"{'=' * 110}\n")
