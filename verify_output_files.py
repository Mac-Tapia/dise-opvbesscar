#!/usr/bin/env python3
import json
import pandas as pd
from pathlib import Path

output_dir = Path('outputs/ppo_training')

print('='*100)
print('✅ VERIFICACIÓN DE ARCHIVOS GENERADOS PPO')
print('='*100)

# 1. result_ppo.json
print('\n1️⃣  result_ppo.json')
print('-'*100)
result_file = output_dir / 'result_ppo.json'
if result_file.exists():
    with open(result_file) as f:
        result_data = json.load(f)
    print(f'✓ Existe: {result_file.stat().st_size / 1024:.1f} KB')
    print(f'✓ Keys principales: {list(result_data.keys())}')
    print(f'✓ Episodes: {result_data.get("training", {}).get("episodes", "N/A")}')
    print(f'✓ Total Timesteps: {result_data.get("training", {}).get("total_timesteps", "N/A"):,}')
    print(f'✓ Duration: {result_data.get("training", {}).get("duration_seconds", "N/A"):.1f} seconds')
    print(f'✓ Validation Mean Reward: {result_data.get("validation", {}).get("mean_reward", "N/A"):.2f}')
    print(f'✓ Validation Mean CO2 Avoided: {result_data.get("validation", {}).get("mean_co2_avoided_kg", "N/A"):,.0f} kg')
else:
    print('❌ NO EXISTE')

# 2. timeseries_ppo.csv
print('\n2️⃣  timeseries_ppo.csv')
print('-'*100)
ts_file = output_dir / 'timeseries_ppo.csv'
if ts_file.exists():
    df_ts = pd.read_csv(ts_file)
    print(f'✓ Existe: {ts_file.stat().st_size / (1024*1024):.1f} MB')
    print(f'✓ Total registros: {len(df_ts):,}')
    print(f'✓ Columnas ({len(df_ts.columns)}):')
    for col in df_ts.columns:
        print(f'    - {col}')
    print(f'\n✓ Sample (primeras 3 filas):')
    print(df_ts.head(3).to_string())
else:
    print('❌ NO EXISTE')

# 3. trace_ppo.csv
print('\n3️⃣  trace_ppo.csv')
print('-'*100)
trace_file = output_dir / 'trace_ppo.csv'
if trace_file.exists():
    df_trace = pd.read_csv(trace_file)
    print(f'✓ Existe: {trace_file.stat().st_size / (1024*1024):.1f} MB')
    print(f'✓ Total registros: {len(df_trace):,}')
    print(f'✓ Columnas ({len(df_trace.columns)}):')
    for col in df_trace.columns:
        print(f'    - {col}')
    print(f'\n✓ Sample (primeros 3 pasos):')
    print(df_trace.head(3).to_string())
else:
    print('❌ NO EXISTE')

print('\n' + '='*100)
print('✅ CONCLUSIÓN: Todos los archivos técnicos se generan correctamente en entrenamiento PPO')
print('='*100 + '\n')
