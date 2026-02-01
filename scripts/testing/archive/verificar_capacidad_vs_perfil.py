import pandas as pd

print('CAPACIDAD INSTALADA:')
print('  112 tomas motos × 2 kW = 224 kW')
print('  16 tomas mototaxis × 3 kW = 48 kW')
print('  TOTAL INSTALADO: 272 kW')

print('\nMÁXIMO FÍSICO EN 15 MIN:')
print('  272 kW × 0.25h = 68 kWh')

print('\nPERFIL GENERADO EN EL ARCHIVO:')
df = pd.read_csv('data/oe2/perfil_horario_carga.csv')
max_idx = df['energy_kwh'].idxmax()
print(f'  Pico intervalo {max_idx}: {df.loc[max_idx, "energy_kwh"]:.1f} kWh')
print(f'  Potencia equivalente: {df.loc[max_idx, "power_kw"]:.1f} kW')

print('\n¿PROBLEMA?')
if df.loc[max_idx, 'power_kw'] > 272:
    print(f'  ¡SÍ! El pico ({df.loc[max_idx, "power_kw"]:.0f} kW) excede')
    print('  la capacidad instalada (272 kW)')
    print('\n  Esto significa que el perfil fue generado asumiendo')
    print('  demanda agregada sin restricción de capacidad.')
else:
    print('  NO. El perfil respeta la capacidad instalada.')

print('\nTOTAL DEL DÍA:')
print(f'  {df["energy_kwh"].sum():.0f} kWh')
print('  (correcto: 2,679 motos + 573 mototaxis = 3,252 kWh)')
