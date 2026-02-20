import pandas as pd

# Check solar CSV structure
df_solar = pd.read_csv('data/processed/citylearn/iquitos_ev_mall/solar_generation.csv')
print('Solar CSV:')
print(f'  Columns: {list(df_solar.columns)}')
print(f'  Shape: {df_solar.shape}')
print(f'  First rows:')
print(df_solar.head(3))
print(f'\nBESS CSV:')

df_bess = pd.read_csv('data/processed/citylearn/iquitos_ev_mall/bess_timeseries.csv')
print(f'  Columns: {list(df_bess.columns[:10])}...')
print(f'  Shape: {df_bess.shape}')
print(f'  Dtypes: {df_bess.dtypes.head()}')
