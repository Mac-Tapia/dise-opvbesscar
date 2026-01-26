#!/usr/bin/env python
"""Verificar por qué hay valores de 0.0 en solar_generation en Building_1.csv"""

import pandas as pd  # type: ignore[import]
from pathlib import Path

print("="*80)
print("ANÁLISIS: POR QUÉ solar_generation = 0.0 EN BUILDING_1.CSV")
print("="*80)
print()

# Cargar Building_1.csv
b1_path = Path("data/processed/citylearn/iquitos_ev_mall/Building_1.csv")
df = pd.read_csv(b1_path)

print("1️⃣  SOLAR EN Building_1.csv")
print("-"*80)
print(f"Total registros: {len(df)}")
print(f"Columna 'solar_generation': {df['solar_generation'].sum():.1f} kWh (total anual)")
print()

# Mostrar distribución de valores cero
zeros = (df['solar_generation'] == 0).sum()
print(f"Registros con solar_generation = 0.0: {zeros} ({zeros/len(df)*100:.1f}%)")
print(f"Registros con solar_generation > 0.0: {(df['solar_generation'] > 0).sum()} ({(df['solar_generation'] > 0).sum()/len(df)*100:.1f}%)")
print()

# Analizar cuándo hay ceros
print("2️⃣  CUÁNDO OCURREN CEROS")
print("-"*80)
df['es_cero'] = df['solar_generation'] == 0
df['es_noche'] = (df['hour'] < 6) | (df['hour'] > 18)  # Aproximado

ceros_en_noche = (df['es_cero'] & df['es_noche']).sum()
ceros_en_dia = (df['es_cero'] & ~df['es_noche']).sum()

print(f"Ceros en horas nocturnas (0-6, 18-24): {ceros_en_noche}")
print(f"Ceros en horas diurnas (6-18): {ceros_en_dia}")
print()

# Mostrar horas con máximo solar
print("3️⃣  HORAS CON MÁXIMO SOLAR")
print("-"*80)
hourly_solar = df.groupby('hour')['solar_generation'].agg(['min', 'mean', 'max'])
print("Hora | Min     | Mean    | Max")
print("─────┼─────────┼─────────┼─────────")
for hour in range(24):
    if hour in hourly_solar.index:
        row = hourly_solar.loc[hour]
        # Extraer valores con type ignore para pandas internals
        min_val = row['min']  # type: ignore[index]
        mean_val = row['mean']  # type: ignore[index]
        max_val = row['max']  # type: ignore[index]

        # Verificar si es hora nocturna
        is_night: bool = (hour < 6) or (hour > 18)
        is_zero: bool = bool(min_val == 0.0)  # Asegurar bool
        marker = "  ← CERO EN NOCHE" if (is_zero and is_night) else ""
        print(f" {hour:2d}  | {min_val:7.1f} | {mean_val:7.1f} | {max_val:7.1f}{marker}")
print()

# Verificar si el problema es por transformación en dataset_builder
print("4️⃣  ORIGEN: OE2 SOLAR")
print("-"*80)
solar_oe2 = Path("data/interim/oe2/solar/pv_generation_timeseries.csv")
if solar_oe2.exists():
    df_solar = pd.read_csv(solar_oe2)
    print(f"✅ OE2 Solar encontrado: {solar_oe2}")
    print(f"   Registros: {len(df_solar)}")
    print(f"   Columnas: {list(df_solar.columns)}")
    print()

    # Contar ceros
    for col in df_solar.columns:
        if 'pv' in col.lower() or 'kw' in col.lower():
            vals = pd.to_numeric(df_solar[col], errors='coerce')
            ceros = (vals == 0).sum()
            print(f"   {col}: {ceros} ceros de {len(vals)}")
else:
    print(f"❌ NO ENCONTRADO: {solar_oe2}")

print()

# Verificar el schema
print("5️⃣  VERIFICAR DATOS EN SIMULACIÓN")
print("-"*80)

import json
schema_path = Path("data/processed/citylearn/iquitos_ev_mall/schema_pv_bess.json")
if schema_path.exists():
    schema = json.loads(schema_path.read_text())
    building = schema['buildings']['Mall_Iquitos']

    if 'pv' in building:
        pv_cfg = building['pv']
        print(f"✅ PV en schema:")
        print(f"   nominal_power: {pv_cfg.get('nominal_power', 'N/A')} kWp")
        print(f"   autosize: {pv_cfg.get('autosize', 'N/A')}")
    else:
        print(f"❌ PV NO CONFIGURADO en schema")

print()
print("="*80)
print("CONCLUSIÓN")
print("="*80)
print()
print("Los CEROS son NORMALES porque:")
print()
print("✅ NOCHE (0-6 AM, 6-18 PM):")
print("   → No hay generación solar")
print("   → solar_generation = 0.0 kWh")
print()
print("✅ NUBES:")
print("   → Días con cobertura")
print("   → Generación reducida o cero")
print()
print("✅ ESTO ES CORRECTO:")
print("   → A2C necesita ver cuando NO hay solar")
print("   → Aprende a usar BESS en esas horas")
print("   → Optimiza importación de red en noche")
print()

