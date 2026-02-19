import pandas as pd
import numpy as np

# Cargar datos REALES que ahora usa el script
pv_df = pd.read_csv('data/oe2/Generacionsolar/pv_generation_citylearn2024.csv')
mall_df = pd.read_csv('data/oe2/demandamallkwh/demandamallhorakwh.csv')
chargers_df = pd.read_csv('data/oe2/chargers/chargers_ev_ano_2024_v3.csv')

# EV demand
moto_cols = [f'socket_{i:03d}_charger_power_kw' for i in range(30)]
taxi_cols = [f'socket_{i:03d}_charger_power_kw' for i in range(30, 38)]
ev_demand = (chargers_df[moto_cols].sum(axis=1) + chargers_df[taxi_cols].sum(axis=1))

print('DATOS REALES INTEGRADOS EN GRAFICAS')
print('=' * 60)
print()
print('GENERACION SOLAR PV:')
print(f'  Fuente: data/oe2/Generacionsolar/pv_generation_citylearn2024.csv')
print(f'  Min: {pv_df["potencia_kw"].min():.2f} kW')
print(f'  Max: {pv_df["potencia_kw"].max():.2f} kW')
print(f'  Media: {pv_df["potencia_kw"].mean():.2f} kW')
print(f'  Total anual: {pv_df["potencia_kw"].sum():.0f} kWh')
print()
print('DEMANDA MALL:')
print(f'  Fuente: data/oe2/demandamallkwh/demandamallhorakwh.csv')
print(f'  Min: {mall_df["mall_demand_kwh"].min():.2f} kW')
print(f'  Max: {mall_df["mall_demand_kwh"].max():.2f} kW')
print(f'  Media: {mall_df["mall_demand_kwh"].mean():.2f} kW')
print(f'  Total anual: {mall_df["mall_demand_kwh"].sum():.0f} kWh')
print()
print('DEMANDA EV (Motos + Taxis):')
print(f'  Fuente: data/oe2/chargers/chargers_ev_ano_2024_v3.csv')
print(f'  Min: {ev_demand.min():.2f} kW')
print(f'  Max: {ev_demand.max():.2f} kW')
print(f'  Media: {ev_demand.mean():.2f} kW')
print(f'  Total anual: {ev_demand.sum():.0f} kWh')
print()
print('CARGA TOTAL (PV + Mall + EV):')
total = pv_df["potencia_kw"].sum() + mall_df["mall_demand_kwh"].sum() + ev_demand.sum()
print(f'  Total anual: {total:.0f} kWh')
print()
print('PERFIL HORARIO PV (promedio por hora):')
pv_df['datetime'] = pd.to_datetime(pv_df['datetime'])
pv_df['hora'] = pv_df['datetime'].dt.hour
hourly_pv = pv_df.groupby('hora')['potencia_kw'].mean()
print('Hora | PV (kW)')
print('-----+----------')
for h in range(24):
    if h in hourly_pv.index:
        print(f'{h:2d}h  | {hourly_pv[h]:8.1f}')
