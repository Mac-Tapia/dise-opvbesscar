import pandas as pd

# Leer archivo como lo hace load_ev_demand
df = pd.read_csv('data/oe2/perfil_horario_carga.csv')
df_ev = df[['interval', 'energy_kwh']].rename(columns={'energy_kwh': 'ev_kwh'})
df_ev_day = df_ev.head(96)

print('Columnas:', df_ev_day.columns.tolist())
print('\nDatos con carga > 0:')
print(df_ev_day[df_ev_day['ev_kwh'] > 0].head(15))
print(f'\nTotal energía día: {df_ev_day["ev_kwh"].sum():.1f} kWh')
print(f'Max valor: {df_ev_day["ev_kwh"].max():.1f} kWh')
max_idx = df_ev_day['ev_kwh'].idxmax()
max_interval = df_ev_day.loc[max_idx, 'interval']
max_hour = max_interval / 4
print(f'Hora pico: {max_hour:.2f}h (intervalo {max_interval})')

print('\nRango horario 9-21:')
df_filtered = df_ev_day[(df_ev_day['interval'] >= 36) & (df_ev_day['interval'] <= 84)]
print(f'Total intervalos: {len(df_filtered)}')
print(f'Total energía: {df_filtered["ev_kwh"].sum():.1f} kWh')
