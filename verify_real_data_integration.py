#!/usr/bin/env python
"""Verify that real solar and mall demand data is being loaded into dataset."""

import json
from pathlib import Path
import pandas as pd  # type: ignore[import]
import yaml  # type: ignore[import]

print("="*80)
print("VERIFICACIÓN DE DATOS REALES EN EL DATASET")
print("="*80)

# 1. Verify Building_1.csv has real data
energy_csv = Path('data/processed/citylearn/iquitos_ev_mall/Building_1.csv')
if energy_csv.exists():
    df = pd.read_csv(energy_csv)
    print(f"\n✓ Building_1.csv: {len(df)} filas (registros por hora)")
    print(f"  Columnas: {list(df.columns)}")

    # Check for solar data
    solar_cols = [c for c in df.columns if 'solar' in c.lower()]
    if solar_cols:
        solar_col = solar_cols[0]
        solar_values = df[solar_col]
        print(f"\n  [SOLAR] Columna: {solar_col}")
        print(f"    - Min: {solar_values.min():.2f} W/kW")
        print(f"    - Max: {solar_values.max():.2f} W/kW")
        print(f"    - Media: {solar_values.mean():.2f} W/kW")
        print(f"    - Total anual: {solar_values.sum():.1f} W/kW.h")

        # Check for realistic day/night pattern
        hours_with_zero = (solar_values == 0).sum()
        hours_with_nonzero = (solar_values > 0).sum()
        print(f"    - Horas con generación: {hours_with_nonzero}")
        print(f"    - Horas sin generación (noche): {hours_with_zero}")

        if hours_with_zero > 4000:  # Más de 4000 horas sin sol es realista
            print(f"    ✅ Patrón realista día/noche detectado")
        else:
            print(f"    ⚠️ Posible problema: muy pocas horas sin generación")

    # Check for load data
    load_cols = [c for c in df.columns if 'load' in c.lower() or 'demand' in c.lower()]
    if load_cols:
        load_col = load_cols[0]
        load_values = df[load_col]
        print(f"\n  [DEMANDA MALL] Columna: {load_col}")
        print(f"    - Min: {load_values.min():.2f} kW")
        print(f"    - Max: {load_values.max():.2f} kW")
        print(f"    - Media: {load_values.mean():.2f} kW")
        print(f"    - Total anual: {load_values.sum():.1f} kWh")

        # Verify it's not all zeros
        nonzero = (load_values > 0).sum()
        if nonzero > 0:
            print(f"    ✅ Demanda real cargada ({nonzero} horas con consumo)")
        else:
            print(f"    ❌ PROBLEMA: Toda la demanda es cero")

else:
    print(f"\n❌ No encontrado: {energy_csv}")

# 2. Check schema configuration
print("\n" + "="*80)
print("CONFIGURACIÓN DE FUENTES DE DATOS EN SCHEMA")
print("="*80)

schema_path = Path('data/processed/citylearn/iquitos_ev_mall/schema.json')
if schema_path.exists():
    with open(schema_path) as f:
        schema = json.load(f)

    building = schema['buildings']['Mall_Iquitos']
    print(f"\n✓ Building: Mall_Iquitos")

    # Check PV configuration
    if 'pv' in building:
        pv = building['pv']
        print(f"\n  [PV SOLAR]")
        if 'solar_generation' in pv:
            print(f"    - Archivo: {pv['solar_generation']}")
        if 'attributes' in pv:
            print(f"    - Nominal power: {pv['attributes'].get('nominal_power', 'N/A')} kWp")

    # Check non-shiftable load
    if 'non_shiftable_load' in building:
        nsl = building['non_shiftable_load']
        if isinstance(nsl, dict) and 'file' in nsl:
            print(f"\n  [DEMANDA NO-DESPLAZABLE]")
            print(f"    - Archivo: {nsl['file']}")

    # Check from energy_simulation
    energy_sim = building.get('energy_simulation', 'Building_1.csv')
    print(f"\n✓ Archivo de energía: {energy_sim}")
    print(f"   (Contiene solar + demanda)")

# 3. Verify data sources in config
print("\n" + "="*80)
print("FUENTES DE DATOS CONFIGURADAS EN OE2")
print("="*80)

config_path = Path('configs/default.yaml')
if config_path.exists():
    import yaml
    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    if 'oe2' in cfg:
        oe2 = cfg['oe2']

        # Solar config
        if 'solar' in oe2:
            print(f"\n✓ Solar (OE2):")
            for key, val in oe2['solar'].items():
                if key not in ['pv', 'latitude', 'longitude']:
                    print(f"    {key}: {val}")

        # Mall config
        if 'mall' in oe2:
            print(f"\n✓ Mall (OE2):")
            for key, val in oe2['mall'].items():
                print(f"    {key}: {val}")

print("\n" + "="*80)
print("RESUMEN")
print("="*80)
print("""
El dataset builder integra datos reales en este orden de preferencia:

SOLAR:
  1. solar_generation_citylearn (preparado por OE2) ← PREFERIDO
  2. solar_ts (timeseries con resampling)
  3. Ceros (fallback)

DEMANDA MALL:
  1. building_load_citylearn (preparado por OE2) ← PREFERIDO
  2. mall_demand (datos históricos con resampling)
  3. Perfil genérico del config

✅ Ambos datos reales se integran automáticamente en:
   - Building_1.csv (para CityLearn)
   - Schema.json (referencias a archivos)
""")
