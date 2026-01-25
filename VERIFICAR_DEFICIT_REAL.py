"""
Verificar el déficit EV real hora por hora considerando que el mall consume primero.
"""
import pandas as pd
import numpy as np

# Cargar datos
pv_profile = pd.read_csv("data/interim/oe2/solar/pv_profile_24h.csv")
ev_profile = pd.read_csv("data/interim/oe2/chargers/perfil_horario_carga.csv")

# Demanda mall sintética (33,885 kWh/día)
mall_day = 33885
shape = np.array([0.03,0.03,0.03,0.03,0.03,0.04,0.05,0.06,0.07,0.07,0.07,0.06,
                  0.06,0.06,0.06,0.06,0.07,0.08,0.08,0.07,0.06,0.05,0.04,0.03])
shape = shape / shape.sum()
mall_hourly = mall_day * shape

# Crear tabla de balance
balance = pd.DataFrame({
    'Hora': range(24),
    'PV_kWh': pv_profile['pv_kwh'].values,
    'Mall_kWh': mall_hourly,
    'EV_kWh': ev_profile['energy_kwh'].values
})

# Calcular flujos
# 1. Mall consume primero del PV
balance['PV_a_Mall'] = np.minimum(balance['PV_kWh'], balance['Mall_kWh'])
balance['Mall_desde_Red'] = balance['Mall_kWh'] - balance['PV_a_Mall']

# 2. PV remanente disponible para EV
balance['PV_remanente'] = balance['PV_kWh'] - balance['PV_a_Mall']
balance['PV_a_EV'] = np.minimum(balance['PV_remanente'], balance['EV_kWh'])

# 3. Déficit EV (lo que no puede cubrir el solar remanente)
balance['Deficit_EV'] = balance['EV_kWh'] - balance['PV_a_EV']

# 4. Identificar horas con déficit
balance['Hay_Deficit'] = balance['Deficit_EV'] > 0.1

print("\n" + "="*100)
print("BALANCE ENERGÉTICO HORA POR HORA")
print("="*100)
print("\nHorario Mall: 9h-22h (13 horas)")
print("Horario Carga EV: 10h-21h (12 horas)")
print("\n" + "-"*100)

# Mostrar solo horas relevantes (9-22)
print(f"{'Hora':>4} | {'PV':>8} | {'Mall':>8} | {'EV':>8} | {'PV→Mall':>8} | {'PV rem':>8} | {'PV→EV':>8} | {'Déficit EV':>10} | {'BESS?':>6}")
print("-"*100)

for i, row in balance.iterrows():
    if 9 <= i <= 22:
        deficit_str = f"{row['Deficit_EV']:>10.1f}" if row['Deficit_EV'] > 0.1 else f"{'---':>10}"
        bess_str = "🔋 SÍ" if row['Hay_Deficit'] else "☀️ NO"
        print(f"{int(row['Hora']):>4}h | {row['PV_kWh']:>8.1f} | {row['Mall_kWh']:>8.1f} | {row['EV_kWh']:>8.1f} | "
              f"{row['PV_a_Mall']:>8.1f} | {row['PV_remanente']:>8.1f} | {row['PV_a_EV']:>8.1f} | {deficit_str} | {bess_str}")

print("-"*100)

# Totales
print(f"\n{'TOTALES DIARIOS:':>50}")
print(f"  PV generado:              {balance['PV_kWh'].sum():>10.1f} kWh/día")
print(f"  Demanda Mall:             {balance['Mall_kWh'].sum():>10.1f} kWh/día")
print(f"  Demanda EV:               {balance['EV_kWh'].sum():>10.1f} kWh/día")
print(f"  PV usado por Mall:        {balance['PV_a_Mall'].sum():>10.1f} kWh/día")
print(f"  PV remanente disponible:  {balance['PV_remanente'].sum():>10.1f} kWh/día")
print(f"  PV usado por EV:          {balance['PV_a_EV'].sum():>10.1f} kWh/día")
print(f"  DÉFICIT EV (necesita BESS): {balance['Deficit_EV'].sum():>8.1f} kWh/día")
print(f"  Mall desde red:           {balance['Mall_desde_Red'].sum():>10.1f} kWh/día")

print("\n" + "="*100)
print(f"DIMENSIONAMIENTO BESS:")
print(f"  Debe cubrir déficit EV:   {balance['Deficit_EV'].sum():>10.1f} kWh/día")
print(f"  Horas con déficit:        {balance['Hay_Deficit'].sum()} horas")
deficit_hours = balance[balance['Hay_Deficit']]['Hora'].values
print(f"  Horario BESS:             {int(deficit_hours.min())}h - {int(deficit_hours.max())}h")
print(f"  Pico déficit:             {balance['Deficit_EV'].max():>10.1f} kW")
print("="*100 + "\n")
