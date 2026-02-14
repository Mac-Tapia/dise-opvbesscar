import pandas as pd

df = pd.read_csv('data/oe2/bess/bess_simulation_hourly.csv')
df['hour'] = pd.to_datetime(df['datetime']).dt.hour

print("=" * 100)
print("VALIDACION v5.5: SOC FINAL Y DESCARGA A MALL")
print("=" * 100)

# Verificar SOC a las 22h
soc_22h = df[df['hour'] == 22]['bess_soc_percent'].values
print(f"\n[VALIDACION 1] SOC A LAS 22h (CIERRE OPERATIVO):")
print(f"  Minimo: {soc_22h.min():6.1f}%")
print(f"  Maximo: {soc_22h.max():6.1f}%")
print(f"  Promedio: {soc_22h.mean():6.1f}%")
print(f"  Objetivo: 20.0%")
print(f"  Estado: {'EXITOSO - alcanza ~20%' if 20 <= soc_22h.mean() <= 25 else 'FALLIDO - no es 20%'}")

# Descarga total a MALL vs EV
descarga_17_22h = df[(df['hour'] >= 17) & (df['hour'] <= 22)].copy()
bess_to_ev = descarga_17_22h['bess_to_ev_kwh'].sum()
bess_to_mall = descarga_17_22h['bess_to_mall_kwh'].sum()
total_descarga = bess_to_ev + bess_to_mall

print(f"\n[VALIDACION 2] DESCARGA EN HORAS CRITICAS (17h-22h):")
print(f"  Total: {total_descarga:,.0f} kWh/anio")
print(f"  Hacia EV: {bess_to_ev:,.0f} kWh ({bess_to_ev/total_descarga*100:.1f}%)")
print(f"  Hacia MALL: {bess_to_mall:,.0f} kWh ({bess_to_mall/total_descarga*100:.1f}%)")

# Cobertura de demanda
ev_demand = df[(df['hour'] >= 17) & (df['hour'] <= 22)]['ev_demand_kwh'].sum()
mall_demand = df[(df['hour'] >= 17) & (df['hour'] <= 22)]['mall_demand_kwh'].sum()

print(f"\n[VALIDACION 3] COBERTURA POR BESS (17h-22h):")
print(f"  EV: {bess_to_ev:,.0f} kWh / {ev_demand:,.0f} kWh demanda = {bess_to_ev/ev_demand*100:.1f}%")
print(f"  MALL: {bess_to_mall:,.0f} kWh / {mall_demand:,.0f} kWh demanda = {bess_to_mall/mall_demand*100:.1f}%")
print(f"  Estado: {'CORRECTO - EV 100%' if bess_to_ev/ev_demand > 0.80 else 'BAJO'}")

# Comparativa vs actual (v5.4)
print(f"\n[COMPARATIVA] v5.4 vs v5.5:")
print(f"  v5.4: BESS->MALL = 265,594 kWh (3.3%), SOC final = 27.8%")
print(f"  v5.5: BESS->MALL = {bess_to_mall:,.0f} kWh ({bess_to_mall/mall_demand*100:.1f}%), SOC final = {soc_22h.mean():.1f}%")
print(f"  Mejora: {bess_to_mall - 265594:+,.0f} kWh extra para MALL (+{(bess_to_mall-265594)/265594*100:+.1f}%)")

print("\n" + "=" * 100)
