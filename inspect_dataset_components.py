#!/usr/bin/env python
"""Inspecciona los componentes del dataset CityLearn para el entrenamiento"""

import json
import pandas as pd
from pathlib import Path

def main():
    data_path = Path('data/processed/citylearn/iquitos_ev_mall')
    schema_path = data_path / 'schema.json'

    print('\n' + '='*100)
    print('COMPONENTES DEL DATASET - CITYLEARN IQUITOS EV MALL')
    print('='*100 + '\n')

    # Leer schema
    with open(schema_path) as f:
        schema = json.load(f)

    # TEMPORAL
    print('📅 CONFIGURACIÓN TEMPORAL')
    print('-'*100)
    print(f'  Start Date:        {schema["start_date"]}')
    print(f'  Total Time Steps:  {schema["simulation_end_time_step"] + 1} hours (1 year)')
    print(f'  Seconds/Step:      {schema["seconds_per_time_step"]} seconds (= 1 hour)')
    print(f'  Episode Duration:  8,760 hours (Jan 1 - Dec 31, 2024)')
    print()

    # BUILDINGS
    buildings = schema.get('buildings', [])
    print(f'🏢 BUILDINGS: {len(buildings)} (1 main building = Iquitos EV charging mall)')
    print('-'*100)

    if buildings:
        b = buildings[0]
        print(f'  Name:        {b.get("name")}')
        print(f'  Energy File: {b.get("energy_file")}')

        assets = b.get('assets', [])
        print(f'  Total Assets: {len(assets)}')
        print()
        print('  ASSETS COMPOSITION:')

        asset_types = {}
        for a in assets:
            atype = a.get('type')
            if atype not in asset_types:
                asset_types[atype] = []
            asset_types[atype].append(a.get('name'))

        for atype in sorted(asset_types.keys()):
            count = len(asset_types[atype])
            print(f'    • {atype:25} x{count:3}  ', end='')
            if count <= 5:
                print(f"{', '.join(asset_types[atype][:3])}")
            else:
                print(f"{', '.join(asset_types[atype][:3])}, ...")
    print()

    # CSV FILES
    print('📄 ARCHIVOS CSV DEL DATASET')
    print('-'*100)
    print(f'\n  1. BUILDING DATA')
    building_csv = data_path / 'Building_1.csv'
    if building_csv.exists():
        df = pd.read_csv(building_csv)
        print(f'     Building_1.csv: {len(df)} rows × {len(df.columns)} columns')
        print(f'     Columns: {", ".join(df.columns.tolist()[:8])}...')
        print(f'     Data range: month {df["month"].min()}-{df["month"].max()}, '
              f'hour {df["hour"].min()}-{df["hour"].max()}')

    print(f'\n  2. WEATHER DATA')
    weather_csv = data_path / 'weather.csv'
    if weather_csv.exists():
        df = pd.read_csv(weather_csv)
        print(f'     weather.csv: {len(df)} rows × {len(df.columns)} columns')
        print(f'     Columns: {", ".join(df.columns.tolist())}')

    print(f'\n  3. CHARGER DATA (EV Chargers)')
    charger_files = list(data_path.glob('charger_simulation_*.csv'))
    if charger_files:
        sample = pd.read_csv(charger_files[0])
        print(f'     charger_simulation_*.csv: {len(charger_files)} files')
        print(f'     Each charger: {len(sample)} rows × {len(sample.columns)} columns')
        print(f'     Columns: {", ".join(sample.columns.tolist())}')
        print(f'     Total charger data points: {len(charger_files) * len(sample):,}')

    print(f'\n  4. ENERGY STORAGE DATA')
    storage_csv = data_path / 'electrical_storage_simulation.csv'
    if storage_csv.exists():
        df = pd.read_csv(storage_csv)
        print(f'     electrical_storage_simulation.csv: {len(df)} rows × {len(df.columns)} columns')
        print(f'     Columns: {", ".join(df.columns.tolist())}')

    print(f'\n  5. CARBON INTENSITY & PRICING')
    carbon_csv = data_path / 'carbon_intensity.csv'
    if carbon_csv.exists():
        df = pd.read_csv(carbon_csv)
        print(f'     carbon_intensity.csv: {len(df)} rows × {len(df.columns)} columns')

    pricing_csv = data_path / 'pricing.csv'
    if pricing_csv.exists():
        df = pd.read_csv(pricing_csv)
        print(f'     pricing.csv: {len(df)} rows × {len(df.columns)} columns')

    print()

    # OBSERVATION SPACE
    print('🧠 OBSERVATION SPACE (FEATURES FOR RL AGENT)')
    print('-'*100)
    obs_config = schema.get('observations', {})
    active_obs = [k for k, v in obs_config.items() if v.get('active')]
    print(f'  Total observable variables: {len(active_obs)}')
    print(f'  Active observations (examples):')
    for i, obs in enumerate(active_obs[:15]):
        print(f'    • {obs}')
    if len(active_obs) > 15:
        print(f'    ... and {len(active_obs) - 15} more')

    print()
    print('💡 DATASET SUMMARY')
    print('-'*100)
    print(f'  Data Period:           2024 full year (Jan 1 - Dec 31)')
    print(f'  Time Resolution:       Hourly (8,760 timesteps)')
    print(f'  Buildings:             1 (Iquitos EV charging mall)')
    print(f'  EV Chargers:           128 (4,096 sockets; 32 chargers × 4 sockets)')
    print(f'  Energy Storage:        1 BESS (4,520 kWh / 2,712 kW)')
    print(f'  Solar PV System:       4,050 kWp (via weather.csv)')
    print(f'  Total CSV Files:       ~135 files')
    print(f'  Total Data Points:     ~1.2 million (128 chargers × 8,760 hours + building + weather)')
    print(f'  Geographic Context:    Iquitos, Perú (isolated grid, thermal generation)')
    print()

if __name__ == '__main__':
    main()
