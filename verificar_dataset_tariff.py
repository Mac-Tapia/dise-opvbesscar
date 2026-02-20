import pandas as pd
import os
import json

csv_files = [
    'd:/diseñopvbesscar/data/processed/citylearn/iquitos_ev_mall/bess_timeseries.csv',
    'd:/diseñopvbesscar/data/processed/citylearn/iquitos_ev_mall/citylearnv2_combined_dataset.csv'
]

print('\n' + '='*80)
print('VERIFICACIÓN DE COLUMNAS TARIFARIAS EN DATASETS')
print('='*80)

for csv_file in csv_files:
    if os.path.exists(csv_file):
        df = pd.read_csv(csv_file)
        filename = csv_file.split('/')[-1]
        print(f'\n📊 {filename}')
        print(f'   Shape: {df.shape}')
        print(f'   Total columns: {len(df.columns)}')
        print(f'\n   Column list:')
        for i, col in enumerate(df.columns):
            print(f'      {i+1}. {col}')
        
        # Check for tariff columns
        tariff_cols = ['tariff_period', 'tariff_rate_soles_kwh', 'cost_savings_hp_soles', 
                      'cost_savings_hfp_soles', 'cost_avoided_by_bess_soles', 
                      'tariff_index_hp_hfp', 'is_peak_hour']
        
        print(f'\n   ✅ TARIFARIAS PRESENTE:')
        has_any_tariff = False
        for col in tariff_cols:
            if col in df.columns:
                print(f'      ✓ {col}')
                has_any_tariff = True
        
        if not has_any_tariff:
            print(f'      ✗ Ninguna columna tariff encontrada')
            print(f'      ⚠️  REQUIERE ACTUALIZACIÓN')
    else:
        print(f'❌ No existe: {csv_file}')

print('\n' + '='*80)
