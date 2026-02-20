import pandas as pd

df = pd.read_csv('data/processed/citylearn/iquitos_ev_mall/bess_timeseries.csv')

print('Dataset info:')
print(f'Shape: {df.shape}')
print(f'\nFirst 5 rows:')
print(df.head())

print(f'\nDuplicated check (all columns):')
dup_all = df.duplicated().sum()
print(f'Total duplicates using all columns: {dup_all}')

print(f'\nDuplicated check (specific columns - energy):')
energy_cols = ['pv_kwh', 'ev_kwh', 'mall_kwh']
dup_energy = df[energy_cols].duplicated().sum()
print(f'Duplicates in {energy_cols}: {dup_energy}')

print(f'\nDuplicated check (tariff columns):')
if 'tariff_period' in df.columns:
    dup_tariff = df[['tariff_period', 'tariff_rate_soles_kwh']].duplicated().sum()
    print(f'Duplicates in tariff columns: {dup_tariff}')
    print(f'This is normal - 1825 HP hours + 6935 HFP hours will have many identical tarifas')

print(f'\nDuplicated rows (completely identical including all columns):')
print(f'True duplicates (row-level): {dup_all}')

if dup_all > 0:
    print(f'\nInvesting duplicates...')
    dup_mask = df.duplicated(keep=False)
    print(f'Rows that are duplicates (first 10):')
    print(df[dup_mask].head(10))
