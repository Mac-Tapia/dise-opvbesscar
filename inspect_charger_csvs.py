#!/usr/bin/env python
"""Inspect the actual charger CSV files generated."""

import pandas as pd  # type: ignore[import]
from pathlib import Path

csv_path = Path('data/processed/citylearn/iquitos_ev_mall/buildings/Mall_Iquitos/charger_simulation_001.csv')

if csv_path.exists():
    print("="*80)
    print("VERIFICACIÓN DE ARCHIVOS CSV DE CHARGERS")
    print("="*80)

    df = pd.read_csv(csv_path)

    print(f"\n✓ Archivo: {csv_path.name}")
    print(f"  Forma: {df.shape}")
    print(f"  Columnas: {list(df.columns)}")

    print(f"\n  Primeras 5 filas:")
    print(df.head())

    print(f"\n  Tipos de datos:")
    print(df.dtypes)

    print(f"\n  Valores nulos:")
    print(df.isnull().sum())

    print(f"\n  Estadísticas:")
    print(df.describe())

    # Check for problematic values
    print(f"\n  Verificación de valores válidos:")
    if df['electric_vehicle_charger_state'].isnull().any():
        print(f"    ❌ electric_vehicle_charger_state tiene NaN")
    else:
        unique_states = df['electric_vehicle_charger_state'].unique()
        print(f"    ✓ Estados únicos: {unique_states}")

    if df['electric_vehicle_id'].isnull().any():
        print(f"    ❌ electric_vehicle_id tiene NaN")
    else:
        unique_ids = df['electric_vehicle_id'].unique()
        print(f"    ✓ IDs únicos: {unique_ids[:5]}... (total: {len(unique_ids)})")

    for col in ['electric_vehicle_departure_time', 'electric_vehicle_required_soc_departure',
                'electric_vehicle_estimated_arrival_time', 'electric_vehicle_estimated_soc_arrival']:
        if df[col].isnull().any():
            print(f"    ❌ {col} tiene NaN: {df[col].isnull().sum()} valores")
        else:
            print(f"    ✓ {col}: min={df[col].min()}, max={df[col].max()}")

    if df['demand_kw'].isnull().any():
        print(f"    ❌ demand_kw tiene NaN: {df['demand_kw'].isnull().sum()} valores")
    else:
        print(f"    ✓ demand_kw: min={df['demand_kw'].min():.2f}, max={df['demand_kw'].max():.2f}")

else:
    print(f"❌ No encontrado: {csv_path}")

# Count total CSVs
building_dir = Path('data/processed/citylearn/iquitos_ev_mall/buildings/Mall_Iquitos')
csv_files = list(building_dir.glob('charger_simulation_*.csv'))
print(f"\n✓ Total CSVs generados: {len(csv_files)}")
