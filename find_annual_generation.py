import json
from pathlib import Path
import pandas as pd

# Find annual generation value
cert_path = Path('data/oe2/Generacionsolar/CERTIFICACION_SOLAR_DATASET_2024.json')
if cert_path.exists():
    with open(cert_path) as f:
        data = json.load(f)
    
    print('CERTIFICACIÓN SOLAR - valores clave:')
    if isinstance(data, dict):
        # Buscar keys relacionadas con generación anual
        for key in sorted(data.keys()):
            val = data[key]
            if isinstance(val, (int, float)):
                print(f'  {key}: {val:,.2f}')
            elif isinstance(val, str) and 'kwh' in key.lower():
                print(f'  {key}: {val}')

# Revisar CSV de generación solar
csv_path = Path('data/processed/citylearn/iquitos_ev_mall/solar_generation.csv')
if csv_path.exists():
    df = pd.read_csv(csv_path)
    print(f'\n\nSOLAR_GENERATION.CSV:')
    print(f'  Shape: {df.shape}')
    print(f'  Columns: {list(df.columns)}')
    
    if 'energia_kwh' in df.columns:
        annual_total = df['energia_kwh'].sum()
        print(f'  Annual total (energia_kwh): {annual_total:,.2f} kWh = {annual_total/1e6:.2f} GWh')
    if 'potencia_kw' in df.columns:
        annual_kwh = df['potencia_kw'].sum()
        print(f'  Annual total (potencia_kw): {annual_kwh:,.2f} kWh = {annual_kwh/1e6:.2f} GWh')

# Revisar archivo de datos de entrada de configuración 
config_path = Path('configs/default.yaml')
if config_path.exists():
    import yaml
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    if 'oe2' in config and 'solar' in config['oe2']:
        print(f'\n\nOE2 SOLAR CONFIG:')
        for key, val in config['oe2']['solar'].items():
            print(f'  {key}: {val}')
