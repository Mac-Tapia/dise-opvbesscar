"""
Análisis de cruce de curvas: Solar vs Demanda EV
Para determinar punto exacto de activación BESS
"""
import pandas as pd
import numpy as np

print("=" * 80)
print("ANÁLISIS DE CRUCE DE CURVAS: SOLAR vs DEMANDA EV")
print("=" * 80)

# 1. Cargar perfil solar de 15 min
df_pv_24h = pd.read_csv('data/oe2/pv_profile_24h.csv')
# Expandir a 96 intervalos de 15 min
pv_15min = []
for _, row in df_pv_24h.iterrows():
    hour = int(row['hour'])
    pv_kwh_hour = row['pv_kwh']
    # Dividir energía horaria en 4 intervalos de 15 min
    for i in range(4):
        pv_15min.append({
            'interval': hour * 4 + i,
            'hour': hour,
            'minute': i * 15,
            'pv_kwh': pv_kwh_hour / 4.0,  # kWh por intervalo de 15 min
        })
df_pv = pd.DataFrame(pv_15min)

# 2. Cargar perfil EV de 15 min
df_ev = pd.read_csv('data/oe2/perfil_horario_carga.csv')

# 3. Cargar o generar perfil Mall
# Usar perfil sintético simple: 33,885 kWh/día distribuido
# Asumimos que durante horas solares (5-17h) el mall consume del solar
df_mall_24h = pd.DataFrame({
    'hour': range(24),
    'mall_kwh': 33885 / 24  # Distribución uniforme simplificada
})
mall_15min = []
for _, row in df_mall_24h.iterrows():
    hour = int(row['hour'])
    mall_kwh_hour = row['mall_kwh']
    for i in range(4):
        mall_15min.append({
            'interval': hour * 4 + i,
            'mall_kwh': mall_kwh_hour / 4.0,
        })
df_mall = pd.DataFrame(mall_15min)

# Merge todos los perfiles
df_merge = pd.merge(df_pv, df_ev[['interval', 'energy_kwh']], on='interval', how='left')
df_merge = df_merge.rename(columns={'energy_kwh': 'ev_kwh'})
df_merge = pd.merge(df_merge, df_mall[['interval', 'mall_kwh']], on='interval', how='left')

# 4. Calcular excedente/déficit
# IMPORTANTE: EV solo opera de 9h a 22h (intervalos 36-87)
# Filtrar solo horario de operación EV
df_merge = df_merge[(df_merge['interval'] >= 36) & (df_merge['interval'] <= 87)].copy()

# Asumiendo que el mall consume primero el solar
# Mall demanda ~33,885 kWh/día = ~22,036 kWh durante horas solares (5-17h)
# Solar genera ~22,036 kWh/día
# Entonces solar cubre ~100% mall, excedente para EV es ~0
# PERO en realidad, durante horas pico solar (12-14h), hay excedente

# Calcular solar neto para EV: solar - mall
df_merge['solar_for_ev'] = np.maximum(0, df_merge['pv_kwh'] - df_merge['mall_kwh'])

# Déficit EV (cuando solar no cubre demanda EV)
df_merge['deficit_ev'] = np.maximum(0, df_merge['ev_kwh'] - df_merge['solar_for_ev'])

# 5. Encontrar primer intervalo con déficit EV
deficit_mask = df_merge['deficit_ev'] > 0.1  # Umbral 0.1 kWh
first_deficit_idx = df_merge[deficit_mask].index.min() if deficit_mask.any() else None

if first_deficit_idx is not None:
    first_deficit = df_merge.loc[first_deficit_idx]
    interval_start = int(first_deficit['interval'])
    hour_start = int(first_deficit['hour'])
    minute_start = int(first_deficit['minute'])

    print(f"\n🔍 PUNTO DE ACTIVACIÓN BESS:")
    print(f"   Intervalo: {interval_start} ({hour_start:02d}:{minute_start:02d})")
    print(f"   Solar disponible para EV: {first_deficit['solar_for_ev']:.2f} kWh")
    print(f"   Demanda EV: {first_deficit['ev_kwh']:.2f} kWh")
    print(f"   Déficit: {first_deficit['deficit_ev']:.2f} kWh")

    # 6. Calcular déficit total desde activación hasta cierre (22h = intervalo 87)
    closing_interval = 87  # 21:45 (último intervalo antes de 22:00)
    df_discharge = df_merge[(df_merge['interval'] >= interval_start) &
                            (df_merge['interval'] <= closing_interval)]

    total_deficit = df_discharge['deficit_ev'].sum()
    max_deficit = df_discharge['deficit_ev'].max()
    hours_discharge = len(df_discharge) / 4.0  # Convertir intervalos a horas

    print(f"\n📊 DÉFICIT TOTAL DESDE ACTIVACIÓN HASTA CIERRE:")
    print(f"   Desde intervalo: {interval_start} ({hour_start:02d}:{minute_start:02d})")
    print(f"   Hasta intervalo: {closing_interval} (21:45)")
    print(f"   Duración: {len(df_discharge)} intervalos ({hours_discharge:.2f} horas)")
    print(f"   Déficit total: {total_deficit:.1f} kWh")
    print(f"   Déficit pico (intervalo): {max_deficit:.1f} kWh")
    print(f"   Déficit pico (potencia): {max_deficit / 0.25:.1f} kW")

    # 7. Dimensionamiento BESS
    DoD = 0.80  # 80%
    efficiency = 0.95  # 95%

    # Capacidad necesaria para cubrir déficit total con SOC final 20%
    # SOC inicial 100%, SOC final 20%, DoD = 80%
    # Energía disponible = Capacidad × DoD
    # Energía necesaria = Déficit / eficiencia
    energy_needed = total_deficit / efficiency
    capacity_bess = energy_needed / DoD

    # Potencia necesaria (C-rate)
    power_bess = max_deficit / 0.25 / efficiency  # kW pico necesario

    print(f"\n🔋 DIMENSIONAMIENTO BESS:")
    print(f"   Energía necesaria: {energy_needed:.1f} kWh")
    print(f"   Capacidad BESS: {capacity_bess:.1f} kWh (DoD {DoD*100:.0f}%)")
    print(f"   Potencia BESS: {power_bess:.1f} kW")
    print(f"   SOC inicial: 100%")
    print(f"   SOC final: 20%")

    # 8. Mostrar tabla de intervalos críticos
    print(f"\n📋 INTERVALOS CON DÉFICIT (primeros 10):")
    print(df_discharge[df_discharge['deficit_ev'] > 0][
        ['interval', 'hour', 'minute', 'pv_kwh', 'ev_kwh', 'solar_for_ev', 'deficit_ev']
    ].head(10).to_string(index=False))

else:
    print("\n✅ NO HAY DÉFICIT: Solar cubre toda la demanda EV durante el día")

print("\n" + "=" * 80)
