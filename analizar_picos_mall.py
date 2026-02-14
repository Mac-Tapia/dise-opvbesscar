import pandas as pd
import numpy as np

# Leer simulación actual
df = pd.read_csv('data/oe2/bess/bess_simulation_hourly.csv')

print("=" * 100)
print("ANÁLISIS: PICOS DEL MALL > 1800 kW Y COBERTURA BESS")
print("=" * 100)

# Convertir datetime
df['datetime'] = pd.to_datetime(df['datetime'])
df['hour'] = df['datetime'].dt.hour
df['day'] = df['datetime'].dt.day

# Análisis de picos MALL
print("\n[1] ESTADÍSTICAS PICOS DEL MALL (TODAS LAS HORAS)")
print("-" * 100)
mall_demand = df['mall_demand_kwh']
print(f"  Demanda mínima: {mall_demand.min():,.0f} kW")
print(f"  Demanda máxima: {mall_demand.max():,.0f} kW")
print(f"  Demanda promedio: {mall_demand.mean():,.0f} kW")
print(f"  Demanda mediana: {mall_demand.median():,.0f} kW")
print(f"  Desv. estándar: {mall_demand.std():,.0f} kW")

# Porcentaje de horas con picos > 1800 kW
picos_1800 = (df['mall_demand_kwh'] > 1800).sum()
picos_1800_pct = (picos_1800 / len(df)) * 100
print(f"\n  [ALERTA] Horas con MALL > 1800 kW: {picos_1800:,} horas ({picos_1800_pct:.1f}% del año)")

# Distribuación de picos
print("\n[2] DISTRIBUCIÓN DE PICOS DEL MALL POR RANGO")
print("-" * 100)
ranges = [
    (0, 500, "0-500 kW (noche baja)"),
    (500, 1000, "500-1000 kW (madrugada)"),
    (1000, 1500, "1000-1500 kW (mañana)"),
    (1500, 1800, "1500-1800 kW (tarde)"),
    (1800, 2000, "1800-2000 kW (PUNTA CRÍTICA)"),
    (2000, 2500, "2000-2500 kW (PUNTA MÁX)"),
    (2500, 99999, ">2500 kW (EXTREMA)"),
]

for min_kw, max_kw, label in ranges:
    count = ((df['mall_demand_kwh'] >= min_kw) & (df['mall_demand_kwh'] < max_kw)).sum()
    pct = (count / len(df)) * 100
    avg = df[(df['mall_demand_kwh'] >= min_kw) & (df['mall_demand_kwh'] < max_kw)]['mall_demand_kwh'].mean()
    print(f"  {label:30s}: {count:4d} horas ({pct:5.1f}%)  |  Promedio={avg:,.0f} kW")

# Análisis en horas críticas (17-22h)
print("\n[3] PICOS DEL MALL EN HORAS CRÍTICAS (17h-22h)")
print("-" * 100)
mall_critica = df[(df['hour'] >= 17) & (df['hour'] <= 22)]
print(f"  Máximo pico (17h-22h): {mall_critica['mall_demand_kwh'].max():,.0f} kW")
print(f"  Mínimo pico (17h-22h): {mall_critica['mall_demand_kwh'].min():,.0f} kW")
print(f"  Promedio (17h-22h): {mall_critica['mall_demand_kwh'].mean():,.0f} kW")

picos_critica_1800 = (mall_critica['mall_demand_kwh'] > 1800).sum()
print(f"  [ALERTA] Horas criticas con pico > 1800 kW: {picos_critica_1800} horas")

# Análisis por hora
print("\n[4] PERFIL DE DEMANDA MALL POR HORA (PROMEDIO ANUAL)")
print("-" * 100)
for h in range(24):
    data_h = df[df['hour'] == h]
    if len(data_h) > 0:
        avg = data_h['mall_demand_kwh'].mean()
        max_h = data_h['mall_demand_kwh'].max()
        bess_desc = data_h['bess_discharge_kwh'].mean()
        bess_mall = data_h['bess_to_mall_kwh'].mean()
        print(f"  {h:02d}h: Promedio={avg:7.0f} kW  |  Máximo={max_h:7.0f}  |  BESS descarga={bess_desc:7.0f}  |  BESS→MALL={bess_mall:7.0f}")

# Impacto de BESS (400 kW)
print("\n[5] IMPACTO DE BESS (400 kW) EN PICOS > 1800 kW")
print("-" * 100)
bess_power = 400.0
picos_altos = df[df['mall_demand_kwh'] > 1800].copy()
picos_altos['reduced_demand'] = picos_altos['mall_demand_kwh'] - bess_power
picos_altos['reduction_pct'] = (bess_power / picos_altos['mall_demand_kwh']) * 100

print(f"  Horas con pico > 1800 kW: {len(picos_altos):,}")
print(f"  \n  REDUCCIÓN CON BESS 400 kW:")
print(f"    - Pico máximo actual: {picos_altos['mall_demand_kwh'].max():,.0f} kW")
print(f"    - Pico máximo reducido: {picos_altos['reduced_demand'].max():,.0f} kW")
print(f"    - % de reducción promedio: {picos_altos['reduction_pct'].mean():.1f}%")
print(f"    - % de reducción en pico máximo: {(bess_power / picos_altos['mall_demand_kwh'].max()) * 100:.1f}%")

# En horas 17-22h específicamente
print("\n[6] ESCENARIOS DE DESCARGA ADICIONAL (17h-22h)")
print("-" * 100)
capacidad_adicional_kwh = 510  # 30% de 1700 kWh
horas_descarga = 5  # 17-22h
potencia_adicional_media = capacidad_adicional_kwh / horas_descarga

print(f"  Energía adicional disponible (SOC 50%→20%): {capacidad_adicional_kwh:,.0f} kWh")
print(f"  Horas para descargar: {horas_descarga}h")
print(f"  Potencia media adicional: {potencia_adicional_media:,.0f} kW/h")
print(f"\n  ESCENARIOS:")
print(f"    • Actual (solo EV): BESS descarga ~350 kWh/h, MALL recibe ~240 kWh/h")
print(f"    • Propuesto (EV+MALL): BESS descarga ~400 kWh/h, MALL recibe ~240+{potencia_adicional_media:.0f}={240+potencia_adicional_media:.0f} kWh/h")
print(f"      → Reducción de pico MALL: +{potencia_adicional_media:.0f} kW vs. actual")

# Qué potencia sería necesario para bajar picos a < 1800 kW
print("\n[7] POTENCIA BESS REQUERIDA PARA BAJAR PICOS < 1800 kW")
print("-" * 100)
picos_altos_17_22 = df[(df['hour'] >= 17) & (df['hour'] <= 22) & (df['mall_demand_kwh'] > 1800)]
if len(picos_altos_17_22) > 0:
    max_pico = picos_altos_17_22['mall_demand_kwh'].max()
    potencia_necesaria = max_pico - 1800
    potencia_en_bess = min(potencia_necesaria, 400)  # Limitado a 400 kW BESS
    reduction_lograda = (potencia_en_bess / max_pico) * 100
    
    print(f"  Pico máximo (17h-22h) > 1800 kW: {max_pico:,.0f} kW")
    print(f"  Potencia necesaria para llegar a 1800 kW: {potencia_necesaria:,.0f} kW")
    print(f"  Potencia BESS disponible: 400 kW")
    print(f"  \n  ✓ BESS SI REDUCE EL PICO:")
    print(f"    - De {max_pico:,.0f} kW a {max_pico - potencia_en_bess:,.0f} kW")
    print(f"    - Reducción: {potencia_en_bess:.0f} kW ({reduction_lograda:.1f}%)")
    print(f"    - Sigue siendo > 1800 kW: {'SÍ' if (max_pico - potencia_en_bess) > 1800 else 'NO'}")

print("\n" + "=" * 100)
