import pandas as pd

df = pd.read_csv('data/oe2/perfil_horario_carga.csv')

print('Total del día:', df['energy_kwh'].sum(), 'kWh')
print('Debería ser aprox 813 kWh (demanda diaria EV)')
print('\nValores más altos:')
print(df.nlargest(5, 'energy_kwh')[['interval', 'hour', 'minute', 'energy_kwh', 'power_kw']])

print('\nEn intervalo de 15 min, energy_kwh debería ser power_kw * 0.25h')
print('Verificación intervalo 69:')
row = df.loc[69]
print(f'  energy_kwh={row["energy_kwh"]:.2f}')
print(f'  power_kw={row["power_kw"]:.2f}')
print(f'  power_kw * 0.25 = {row["power_kw"] * 0.25:.2f}')
print(f'  ¿Coincide? {abs(row["energy_kwh"] - row["power_kw"] * 0.25) < 0.01}')

# Verificar si el archivo tiene POTENCIA (kW) en lugar de ENERGÍA (kWh)
print('\n¿El archivo tiene POTENCIA en vez de ENERGÍA?')
print('Si energy_kwh son realmente valores de potencia, la suma debería ser:')
print(f'  {df["energy_kwh"].sum() * 0.25:.1f} kWh (multiplicando por 0.25h)')
