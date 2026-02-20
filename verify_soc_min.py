import pandas as pd
import numpy as np

print('='*80)
print('VERIFICACION: SOC MINIMO DEL BESS EN DATASET')
print('='*80)

# Load dataset
df = pd.read_csv('data/oe2/bess/bess_ano_2024.csv', index_col=0)

print()
print('PARAMETROS CONFIGURADOS:')
print('  SOC_MIN requerido: 20.0%')
print('  SOC_MAX requerido: 100.0%')
print('  DoD (Depth of Discharge): 80%')
print('  Capacidad BESS: 2000 kWh')
print()

print('VALORES EN DATASET:')
soc_min = df['soc_percent'].min()
soc_max = df['soc_percent'].max()
soc_mean = df['soc_percent'].mean()
soc_kwh_min = df['soc_kwh'].min()
soc_kwh_max = df['soc_kwh'].max()

print(f'  SOC_percent minimo: {soc_min:.2f}%')
print(f'  SOC_percent maximo: {soc_max:.2f}%')
print(f'  SOC_percent promedio: {soc_mean:.2f}%')
print(f'  SOC_kWh minimo: {soc_kwh_min:.0f} kWh ({soc_kwh_min/20:.1f}% - corresponde a {soc_kwh_min/2000*100:.1f}%)')
print(f'  SOC_kWh maximo: {soc_kwh_max:.0f} kWh ({soc_kwh_max/20:.1f}% - corresponde a {soc_kwh_max/2000*100:.1f}%)')

print()
print('VALIDACIONES:')

# Validacion 1: SOC >= 20%
check1 = soc_min >= 19.9
print(f'[{"✓" if check1 else "✗"}] SOC minimo >= 20% (actual: {soc_min:.2f}%)')

# Validacion 2: SOC <= 100%
check2 = soc_max <= 100.1
print(f'[{"✓" if check2 else "✗"}] SOC maximo <= 100% (actual: {soc_max:.2f}%)')

# Validacion 3: SOC minimo en kWh
check3 = soc_kwh_min >= 399  # 20% de 2000 = 400
print(f'[{"✓" if check3 else "✗"}] SOC minimo en kWh >= 400 kWh (actual: {soc_kwh_min:.0f} kWh)')

# Validacion 4: Rango operacional
rango = soc_kwh_max - soc_kwh_min
rango_esperado = 1600  # 80% DoD de 2000 kWh
print(f'[{"✓" if rango <= rango_esperado else "✗"}] Rango operacional <= 1600 kWh (actual: {rango:.0f} kWh)')

print()
print('='*80)
