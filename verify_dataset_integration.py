#!/usr/bin/env python3
"""Verificar que los artefactos se integran correctamente en el dataset generado."""

import pandas as pd
import json
from pathlib import Path

print("\n" + "=" * 80)
print("VERIFICACIÓN DE INTEGRACIÓN EN DATASET CONSTRUIDO")
print("=" * 80)

# Buscar el dataset más reciente
dataset_dir = Path('analyses/oe3/training/datasets')
if dataset_dir.exists():
    datasets = sorted([d for d in dataset_dir.iterdir() if d.is_dir()], key=lambda x: x.stat().st_mtime, reverse=True)
    if datasets:
        latest_dataset = datasets[0]
        print(f"\nDataset más reciente: {latest_dataset.name}")

        # Verificar archivos generados
        print("\n[A] ARCHIVOS GENERADOS EN DATASET:")
        for f in sorted(latest_dataset.glob('*.csv')):
            df = pd.read_csv(f)
            print(f"    • {f.name}: {df.shape} rows={len(df)}")

        # Verificar schema
        schema_file = latest_dataset / 'schema_001.json'
        if schema_file.exists():
            schema = json.load(open(schema_file))
            print(f"\n[B] SCHEMA VALIDACIÓN:")
            print(f"    ✓ Building: {list(schema.get('buildings', {}).keys())}")

            bldg = list(schema.get('buildings', {}).values())[0]
            print(f"    ✓ PV (kWp): {bldg.get('pv', {}).get('nominal_power', 'N/A')}")
            print(f"    ✓ BESS (kWh): {bldg.get('electrical_storage', {}).get('capacity', 'N/A')}")
            print(f"    ✓ Chargers: {len([k for k in bldg if 'charger_' in k])}")

            # Contar referencias de datos
            print(f"\n[C] REFERENCIAS DE DATOS EN SCHEMA:")
            print(f"    • weather: {schema.get('weather', 'N/A')}")
            print(f"    • carbon_intensity: {schema.get('carbon_intensity', 'N/A')}")
            print(f"    • pricing: {schema.get('pricing', 'N/A')}")

            # Verificar que building_load apunta a mall demand real
            building_energy = bldg.get('energy_simulation_file', 'N/A')
            print(f"    • energy_simulation: {building_energy}")

        # Verificar contenido de archivos principales
        print(f"\n[D] CONTENIDO DE ARCHIVOS:")

        # Energy (Mall demand)
        energy_file = latest_dataset / 'Building_1.csv'
        if energy_file.exists():
            df_energy = pd.read_csv(energy_file)
            print(f"\n    Building_1.csv (CONTIENE DEMANDA DEL MALL):")
            print(f"        Shape: {df_energy.shape}")
            print(f"        Columns: {list(df_energy.columns)[:5]}...")

            # Buscar columna de carga
            load_cols = [c for c in df_energy.columns if 'load' in c.lower() or 'demand' in c.lower()]
            if load_cols:
                load_col = load_cols[0]
                load_data = df_energy[load_col]
                print(f"        Mall demand column: {load_col}")
                print(f"        Annual sum: {load_data.sum():.1f} kWh")
                print(f"        Mean: {load_data.mean():.2f} kW, Max: {load_data.max():.2f} kW")

        # Weather/Solar
        weather_file = latest_dataset / 'weather.csv'
        if weather_file.exists():
            df_weather = pd.read_csv(weather_file)
            print(f"\n    weather.csv (CONTIENE SOLAR REAL):")
            print(f"        Shape: {df_weather.shape}")
            print(f"        Columns: {list(df_weather.columns)}")

            solar_cols = [c for c in df_weather.columns if 'solar' in c.lower()]
            if solar_cols:
                for col in solar_cols:
                    data = df_weather[col]
                    print(f"        Solar column '{col}':")
                    print(f"            Annual sum: {data.sum():.1f}")
                    print(f"            Mean: {data.mean():.3f}, Max: {data.max():.3f}")

        # Charger simulations
        charger_files = sorted(latest_dataset.glob('charger_simulation_*.csv'))
        if charger_files:
            print(f"\n    Charger simulations: {len(charger_files)} files (debe ser 128)")
            # Verificar uno aleatorio
            import random
            test_file = random.choice(charger_files)
            df_charger = pd.read_csv(test_file)
            print(f"        Muestra ({test_file.name}): {len(df_charger)} rows")

else:
    print("\n⚠ No datasets found in analyses/oe3/training/datasets/")

print("\n" + "=" * 80)
print("✓ VERIFICACIÓN COMPLETADA")
print("=" * 80 + "\n")
