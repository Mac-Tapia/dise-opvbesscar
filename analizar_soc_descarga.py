import pandas as pd
import numpy as np

# Leer simulación actual
df = pd.read_csv('data/oe2/bess/bess_simulation_hourly.csv')

print("=" * 100)
print("ANÁLISIS ACTUAL: SOC FINAL Y DESCARGA A MALL")
print("=" * 100)

# Convertir datetime
df['datetime'] = pd.to_datetime(df['datetime'])
df['hour'] = df['datetime'].dt.hour
df['day'] = df['datetime'].dt.day

# Estadísticas SOC por hora
print("\n[1] EVOLUCIÓN SOC EN HORAS CRÍTICAS (Día 1 = ejemplo típico)")
print("-" * 100)
día_1 = df[df['day'] == 1].copy()
for h in [6, 9, 12, 15, 17, 18, 19, 20, 21, 22]:
    row = día_1[día_1['hour'] == h]
    if len(row) > 0:
        soc = row['bess_soc_percent'].values[0]
        descarga = row['bess_discharge_kwh'].values[0]
        bess_to_mall = row['bess_to_mall_kwh'].values[0] if 'bess_to_mall_kwh' in df.columns else 0
        ev = row['ev_demand_kwh'].values[0]
        mall = row['mall_demand_kwh'].values[0]
        print(f"  {h:02d}h: SOC={soc:6.1f}%  |  Dsch={descarga:6.1f} kWh  |  BESS→MALL={bess_to_mall:6.1f}  |  EV={ev:6.1f}  |  MALL={mall:6.1f}")

# SOC final (22h cierre)
print("\n[2] SOC FINAL A LAS 22h (CIERRE OPERATIVO)")
print("-" * 100)
soc_22h_all = df[df['hour'] == 22]['bess_soc_percent'].values
soc_22h_min = soc_22h_all.min()
soc_22h_max = soc_22h_all.max()
soc_22h_avg = soc_22h_all.mean()
print(f"  SOC mínimo: {soc_22h_min:6.1f}%")
print(f"  SOC máximo: {soc_22h_max:6.1f}%")
print(f"  SOC promedio: {soc_22h_avg:6.1f}%")

# Demanda MALL en horas críticas
print("\n[3] DEMANDA MALL EN HORAS CRÍTICAS (17h-22h)")
print("-" * 100)
mall_17_22 = df[(df['hour'] >= 17) & (df['hour'] <= 22)]
for h in [17, 18, 19, 20, 21, 22]:
    data_h = mall_17_22[mall_17_22['hour'] == h]
    if len(data_h) > 0:
        mall_mean = data_h['mall_demand_kwh'].mean()
        mall_max = data_h['mall_demand_kwh'].max()
        bess_to_mall_mean = data_h['bess_to_mall_kwh'].mean()
        bess_dsch = data_h['bess_discharge_kwh'].mean()
        print(f"  {h:02d}h: MALL={mall_mean:7.0f} kWh (max={mall_max:7.0f})  |  BESS→MALL={bess_to_mall_mean:7.0f}  |  Descarga={bess_dsch:7.0f}")

# Energía BESS disponible para MALL si descargamos a 20%
print("\n[4] CÁLCULO: ENERGÍA DISPONIBLE PARA MALL (SOC 50% → 20%)")
print("-" * 100)
soc_init = 50.0  # %
soc_final = 20.0  # %
descarga_disponible_pct = soc_init - soc_final
capacidad_bess = 1700.0  # kWh
descarga_disponible_kwh = (descarga_disponible_pct / 100.0) * capacidad_bess
horas_descarga = 5  # 17h-22h = 5 horas
potencia_media = descarga_disponible_kwh / horas_descarga

print(f"  Energía a descargar (50% → 20%): {descarga_disponible_kwh:,.0f} kWh")
print(f"  Horas disponibles: {horas_descarga}h (17h-22h)")
print(f"  Potencia media requerida: {potencia_media:,.0f} kW/h")
print(f"  Potencia nominal BESS actual: 400 kW")
print(f"  ✓ Capacidad: {potencia_media/400*100:.1f}% de potencia nominal")

# Actual: ¿Cuánto descarga hoy?
print("\n[5] DESCARGA ACTUAL EN HORAS 17-22h (TODO EL AÑO)")
print("-" * 100)
descarga_17_22 = df[(df['hour'] >= 17) & (df['hour'] <= 22)]['bess_discharge_kwh'].sum()
descarga_a_ev_17_22 = df[(df['hour'] >= 17) & (df['hour'] <= 22)]['bess_to_ev_kwh'].sum() if 'bess_to_ev_kwh' in df.columns else 0
descarga_a_mall_17_22 = df[(df['hour'] >= 17) & (df['hour'] <= 22)]['bess_to_mall_kwh'].sum()

print(f"  Descarga total (17h-22h): {descarga_17_22:,.0f} kWh/año")
print(f"  - Hacia EV: {descarga_a_ev_17_22:,.0f} kWh")
print(f"  - Hacia MALL: {descarga_a_mall_17_22:,.0f} kWh")
print(f"  Descarga potencial (no usada): {descarga_disponible_kwh*73 - descarga_17_22:,.0f} kWh/año")

print("\n[6] ESTRATEGIA PROPUESTA: Descargar más hacia MALL")
print("-" * 100)
print(f"  Actual:   EV (81%) + MALL (3.3%) = 84.3% de descarga")
print(f"  Propuesto: EV (65%) + MALL (20%) = 85% de descarga")
print(f"  ⬆️  Descargar +400,000 kWh adicionales al MALL en 17-22h")
print(f"  ⬆️  SOC final 22h bajaría: 50% → 20% (máximo aprovechamiento)")
print(f"  ⬆️  Carga inicial al día siguiente: 20% → 100% (reducida)")

print("\n" + "=" * 100)
