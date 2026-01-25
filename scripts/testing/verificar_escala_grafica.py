import pandas as pd

df = pd.read_csv('data/oe2/perfil_horario_carga.csv')

print('Perfil de 15 min (valores originales del archivo):')
print(f'  9:00 AM (intervalo 36): {df.loc[36, "energy_kwh"]:.2f} kWh')
print(f'  9:15 AM (intervalo 37): {df.loc[37, "energy_kwh"]:.2f} kWh')
print(f'  Pico 17:15 (intervalo 69): {df.loc[69, "energy_kwh"]:.2f} kWh')
print(f'  21:45 PM (intervalo 87): {df.loc[87, "energy_kwh"]:.2f} kWh')
print(f'  22:00 PM (intervalo 88): {df.loc[88, "energy_kwh"]:.2f} kWh')

print('\nPerfil para gráfica (dividido por 4 para escala horaria):')
print(f'  9:00 AM: {df.loc[36, "energy_kwh"]/4:.2f} kWh/h (equivalente)')
print(f'  9:15 AM: {df.loc[37, "energy_kwh"]/4:.2f} kWh/h')
print(f'  Pico 17:15: {df.loc[69, "energy_kwh"]/4:.2f} kWh/h')
print(f'  21:45 PM: {df.loc[87, "energy_kwh"]/4:.2f} kWh/h')
print(f'  22:00 PM: {df.loc[88, "energy_kwh"]/4:.2f} kWh/h')

print('\nExplicación:')
print('- El archivo tiene energy_kwh para cada intervalo de 15 min')
print('- Para graficar en escala horaria, dividimos por 4')
print('- Así la curva se ve correctamente junto a los datos horarios')
print(f'\nAhora la gráfica mostrará la curva desde 9:15 AM (0.07 kWh/h) hasta 21:45 PM (5.56 kWh/h)')
print(f'Con pico a las 17:15 de {df.loc[69, "energy_kwh"]/4:.1f} kWh/h')
