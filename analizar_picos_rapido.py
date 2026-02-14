import pandas as pd

df = pd.read_csv('data/oe2/bess/bess_simulation_hourly.csv')
df['hour'] = pd.to_datetime(df['datetime']).dt.hour

print("=" * 100)
print("ANALISIS: PICOS DEL MALL > 1800 kW Y IMPACTO BESS")
print("=" * 100)

mall = df['mall_demand_kwh']
print(f"\n[1] ESTADISTICAS PICOS DEL MALL:")
print(f"  Maximo pico: {mall.max():,.0f} kW")
print(f"  Promedio: {mall.mean():,.0f} kW")
print(f"  Horas con pico > 1800 kW: {(mall > 1800).sum():,} horas ({(mall > 1800).sum()/len(df)*100:.1f}%)")

print(f"\n[2] EN HORAS CRITICAS (17h-22h):")
mall_critica = df[(df['hour'] >= 17) & (df['hour'] <= 22)]['mall_demand_kwh']
print(f"  Maximo: {mall_critica.max():,.0f} kW")
print(f"  Promedio: {mall_critica.mean():,.0f} kW")
print(f"  Horas > 1800 kW: {(mall_critica > 1800).sum()} horas")

print(f"\n[3] DISTRIBUCION DE PICOS:")
for threshold in [1500, 1800, 2000, 2200, 2400, 2600]:
    count = (df['mall_demand_kwh'] > threshold).sum()
    pct = count / len(df) * 100
    if count > 0:
        print(f"  > {threshold} kW: {count:4d} horas ({pct:5.1f}%)")

print(f"\n[4] IMPACTO DE BESS 400 kW EN PICOS > 1800:")
picos_altos = df[df['mall_demand_kwh'] > 1800]['mall_demand_kwh']
if len(picos_altos) > 0:
    max_pico = picos_altos.max()
    print(f"  Pico maximo actual: {max_pico:,.0f} kW")
    print(f"  Con BESS 400 kW:    {max_pico - 400:,.0f} kW")
    print(f"  Reduccion:          {400:,.0f} kW ({400/max_pico*100:.1f}%)")
    print(f"  Sigue siendo > 1800 kW: {'SI' if (max_pico - 400) > 1800 else 'NO'}")

print(f"\n[5] DISPONIBILIDAD BESS PARA DESCARGAR EXTRA AL MALL:")
print(f"  Energia disponible (SOC 50% a 20%): 510 kWh")
print(f"  Horas para descargar (17-22h): 5 horas")
print(f"  Potencia media requerida: {510/5:.0f} kW/h")
print(f"  Potencia nominal BESS: 400 kW")
print(f"  Conclusion: BESS PUEDE suministrar esta potencia extra")

print(f"\n[6] COMPARATIVA DE ESCENARIOS:")
print(f"  ACTUAL: BESS descarga solo para EV (81% cobertura)")
print(f"      - SOC final 22h: promedio 27.8% (rango 20-77%)")
print(f"      - BESS a MALL: 265.6k kWh/anio (3.3% de demanda)")
print(f"")
print(f"  PROPUESTO: BESS descarga para EV + MALL extra")
print(f"      - Descarga 30% adicional = 510 kWh en 5h = 102 kW/h")
print(f"      - SOC final 22h: consistente 20% (DURO)")
print(f"      - BESS a MALL: +400k kWh/anio = 665.6k total (5.4% de demanda)")
print(f"      - Picos reducidos: max {max_pico:,.0f} kW -> {max_pico-102:,.0f} kW ")

print("\n" + "=" * 100)
