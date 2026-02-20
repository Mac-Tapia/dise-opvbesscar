import pandas as pd

# Check transformed dataset
df = pd.read_csv('data/processed/citylearn/iquitos_ev_mall/bess_timeseries.csv')

print('=== DATASET TRANSFORMADO ===')
columnas_relevantes = [c for c in df.columns if any(x in c.lower() for x in ['bess_to', 'pv_to', 'grid', 'to_'])]
print('Columnas de flujos:')
for col in sorted(columnas_relevantes):
    try:
        val = df[col].sum()
        print(f'  {col}: {val:,.0f}')
    except:
        print(f'  {col}: (no numerico)')

print()
print('=== DATASET ORIGINAL ===')
df_orig = pd.read_csv('data/oe2/bess/bess_ano_2024.csv')
columnas_relevantes_orig = [c for c in df_orig.columns if any(x in c.lower() for x in ['bess_to', 'pv_to', 'grid_import', 'grid_export'])]
print('Columnas de flujos:')
for col in sorted(columnas_relevantes_orig):
    try:
        val = df_orig[col].sum()
        print(f'  {col}: {val:,.0f}')
    except:
        print(f'  {col}: (no numerico)')
