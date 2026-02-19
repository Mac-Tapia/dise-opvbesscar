import pandas as pd

# Cargar datos reales de PV
df = pd.read_csv('data/oe2/Generacionsolar/pv_generation_citylearn2024.csv')

print('POTENCIA SOLAR REAL (potencia_kw)')
print('=' * 60)
print(f'Min:   {df["potencia_kw"].min():.2f} kW')
print(f'Max:   {df["potencia_kw"].max():.2f} kW')
print(f'Media: {df["potencia_kw"].mean():.2f} kW')
print()

# Perfil diario promedio
df['datetime'] = pd.to_datetime(df['datetime'])
df['hora'] = df['datetime'].dt.hour
hourly = df.groupby('hora')['potencia_kw'].mean()

print('Perfil horario promedio:')
print('Hora | Potencia (kW)')
print('-----+---------------')
for h in range(24):
    if h in hourly.index:
        val = hourly[h]
        print(f'{h:2d}h  | {val:10.2f}')
