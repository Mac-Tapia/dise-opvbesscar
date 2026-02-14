#!/usr/bin/env python3
"""Fix mall demand data format"""
import pandas as pd

# Read the original file
try:
    df = pd.read_csv('data/oe2/demandamallkwh/demandamallhorakwh.csv', sep=';')
except:
    df = pd.read_csv('data/oe2/demandamallkwh/demandamallhorakwh.csv', sep=',')

print('Original structure:')
print(df.head())
print('Columns:', df.columns.tolist())

# If column has combined name like 'FECHAHORA;kWh', split it
cols = df.columns.tolist()
if len(cols) == 1 and ';' in cols[0]:
    print('Detected format with separator in column name')
    df_split = df[cols[0]].str.split(';', expand=True)
    df = pd.DataFrame({
        'timestamp': df_split[0],
        'demand_kwh': pd.to_numeric(df_split[1], errors='coerce')
    })
else:
    df = df.iloc[:, [0, 1]]
    df.columns = ['timestamp', 'demand_kwh']

# Clean and validate
df = df.dropna()
print(f'\nValid rows: {len(df)}')
print(f'Total kWh/year: {df["demand_kwh"].sum():.0f}')

# Save
df.to_csv('data/interim/oe2/demandamallkwh/demandamallhorakwh.csv', index=False)
print('✅ File saved')
