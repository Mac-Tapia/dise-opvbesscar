#!/usr/bin/env python3
"""
Verificar que datos de 15 minutos (35,040 timesteps) estan conectados en schema CityLearn v2
"""
import json
import pandas as pd
from pathlib import Path

print('='*70)
print('VERIFICACION: DATOS 15 MINUTOS EN SCHEMA CITYLEARN V2')
print('='*70)

# 1. Verificar archivos CSV
print('\n[1] ARCHIVOS CSV GENERADOS (bess.py)')
print('-' * 70)
csv_dir = Path('data/interim/oe2/citylearn')
if csv_dir.exists():
    for filename in ['building_load.csv', 'bess_solar_generation.csv']:
        fpath = csv_dir / filename
        if fpath.exists():
            df = pd.read_csv(fpath)
            rows = len(df)
            cols = list(df.columns)
            match = "✓ OK" if rows == 35040 else "✗ ERROR"
            print(f'\n  {filename}')
            print(f'    Filas: {rows} [{match}]')
            print(f'    Columnas: {cols}')
            if rows > 0:
                print(f'    Rango: {df.iloc[0, 0]:.4f} -> {df.iloc[-1, 0]:.4f}')
        else:
            print(f'\n  {filename}: ✗ NO ENCONTRADO')
else:
    print('  ✗ Directorio data/interim/oe2/citylearn NO EXISTE')

# 2. Verificar schema.json
print('\n[2] SCHEMA JSON (CityLearn v2)')
print('-' * 70)
schema_path = Path('data/processed/citylearn/iquitos_ev_mall/schema.json')
if schema_path.exists():
    with open(schema_path) as f:
        schema = json.load(f)

    buildings = schema.get('buildings', {})
    if 'Mall_Iquitos' in buildings:
        building = buildings['Mall_Iquitos']
        print('\n  Building: Mall_Iquitos ✓')

        # BESS
        bess = building.get('electrical_storage', {})
        if bess:
            cap = bess.get('capacity')
            power = bess.get('nominal_power')
            btype = bess.get('type')
            print(f'\n    BESS:')
            print(f'      Capacidad: {cap} kWh')
            print(f'      Potencia: {power} kW')
            print(f'      Tipo: {btype}')
        else:
            print(f'\n    ✗ BESS NO ENCONTRADO')

        # Chargers
        chargers = building.get('electric_vehicle_charger', [])
        print(f'\n    Chargers: {len(chargers)} encontrados')
        if len(chargers) > 0:
            print(f'      Nombre 1: {chargers[0].get("name", "?")}')
            print(f'      Nombre 128: {chargers[127].get("name", "?") if len(chargers) >= 128 else "N/A"}')

        # Energy simulation
        energy_sim = building.get('energy_simulation')
        if energy_sim:
            df_es = pd.read_csv(energy_sim)
            rows_es = len(df_es)
            cols_es = list(df_es.columns)
            match_es = "✓ OK" if rows_es == 35040 else "✗ ERROR"
            print(f'\n    Energy simulation:')
            print(f'      Filas: {rows_es} [{match_es}]')
            print(f'      Columnas: {cols_es[:3]}...')
    else:
        print('  ✗ Building Mall_Iquitos NO ENCONTRADO')
else:
    print('  ✗ schema.json NO ENCONTRADO')

# 3. Prueba CityLearnEnv
print('\n[3] CARGA CITYLEARN V2')
print('-' * 70)
try:
    from citylearn.citylearn import CityLearnEnv
    print('\n  Importando CityLearnEnv...')
    env = CityLearnEnv(schema=str(schema_path))
    print('  ✓ CityLearnEnv importado')

    obs, info = env.reset()
    print('  ✓ env.reset() exitoso')
    print(f'    Observation dimension: {len(obs)}')
    print(f'    Info keys: {list(info.keys())[:5]}...')

    # Step
    print('\n  Haciendo un step...')
    if isinstance(env.action_space, list):
        action = [space.sample() for space in env.action_space]
    else:
        action = env.action_space.sample()
    obs2, reward, term, trunc, info2 = env.step(action)
    print('  ✓ env.step() exitoso')
    print(f'    Reward: {reward:.6f}')
    print(f'    Terminated: {term}, Truncated: {trunc}')

except Exception as e:
    error_str = str(e)
    print(f'  ✗ ERROR: {error_str[:150]}')
    import traceback
    traceback.print_exc()

print('\n' + '='*70)
print('VERIFICACION COMPLETADA')
print('='*70)
