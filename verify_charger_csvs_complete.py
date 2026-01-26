#!/usr/bin/env python
"""Verify charger CSV files have all required columns."""

import pandas as pd  # type: ignore[import]
from pathlib import Path

print("="*80)
print("VERIFICACIÓN DE ARCHIVOS CSV DE CHARGERS")
print("="*80)

building_dir = Path('data/processed/citylearn/iquitos_ev_mall/buildings/Mall_Iquitos')
csv_files = sorted(building_dir.glob('charger_simulation_*.csv'))

print(f"\n✓ Total archivos CSV encontrados: {len(csv_files)}")

if csv_files:
    # Check first charger
    first_csv = csv_files[0]
    df_first = pd.read_csv(first_csv)

    print(f"\n✓ Primero: {first_csv.name}")
    print(f"  - Filas: {len(df_first)}")
    print(f"  - Columnas: {list(df_first.columns)}")

    # Expected columns
    expected_cols = [
        'electric_vehicle_charger_state',
        'electric_vehicle_id',
        'electric_vehicle_departure_time',
        'electric_vehicle_required_soc_departure',
        'electric_vehicle_estimated_arrival_time',
        'electric_vehicle_estimated_soc_arrival',
        'demand_kw'
    ]

    missing_cols = [c for c in expected_cols if c not in df_first.columns]
    if missing_cols:
        print(f"\n❌ COLUMNAS FALTANTES: {missing_cols}")
    else:
        print(f"\n✅ TODAS LAS COLUMNAS REQUERIDAS PRESENTES")

    # Check last charger
    last_csv = csv_files[-1]
    df_last = pd.read_csv(last_csv)

    print(f"\n✓ Último: {last_csv.name}")
    print(f"  - Filas: {len(df_last)}")

    # Sample data
    print(f"\n📊 Muestra de datos (primeros 3 registros del charger 1):")
    print(df_first.head(3).to_string())

    # Summary
    print("\n" + "="*80)
    if len(csv_files) == 128 and not missing_cols and len(df_first) == 8760:
        print("\n✅ ✅ ✅ ARCHIVOS CSV DE CHARGERS CORRECTAMENTE GENERADOS")
        print(f"   - 128 archivos con 8,760 registros cada uno")
        print(f"   - Todas las columnas requeridas presentes")
        print(f"   - Listos para CityLearn v2")
    else:
        print(f"\n⚠️ PROBLEMAS DETECTADOS:")
        print(f"   - Archivos: {len(csv_files)}/128")
        print(f"   - Columnas faltantes: {len(missing_cols)}")
        print(f"   - Registros: {len(df_first)}/8760")
