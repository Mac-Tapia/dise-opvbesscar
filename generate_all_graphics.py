#!/usr/bin/env python3
"""
Script para generar todas las gráficas de balance energético 
incluyendo exportación solar y peak shaving BESS
"""
from __future__ import annotations

import pandas as pd
from pathlib import Path
import sys
import numpy as np

# Importar el módulo de visualización
sys.path.insert(0, str(Path(__file__).parent / 'src' / 'dimensionamiento' / 'oe2' / 'balance_energetico'))
from balance import BalanceEnergeticoSystem, BalanceEnergeticoConfig

print("=" * 80)
print("GENERACION DE GRAFICAS DE BALANCE ENERGETICO v5.4")
print("=" * 80)

# 1. Cargar dataset BESS
csv_file = Path("data/oe2/bess/bess_ano_2024.csv")
print(f"\n[1] Cargando dataset: {csv_file}")
if not csv_file.exists():
    print(f"    [ERROR] Archivo no encontrado: {csv_file}")
    sys.exit(1)

df = pd.read_csv(csv_file)
print(f"    [OK] Datos cargados:")
print(f"        - Filas: {len(df)}")
print(f"        - Columnas: {len(df.columns)}")

# Mapear columnas del CSV al formato esperado por balance.py
# bess.py outputs _kwh columns (hourly energy), balance.py expects _kw (equivalent for 1h timesteps)
# Actual columns in CSV: pv_kwh, ev_kwh, mall_kwh, load_kwh, pv_to_ev_kwh, etc.
column_mapping = {
    'pv_kwh': 'pv_generation_kw',
    'ev_kwh': 'ev_demand_kw',
    'mall_kwh': 'mall_demand_kw',
    'load_kwh': 'total_demand_kw',
    'pv_to_ev_kwh': 'pv_to_ev_kw',
    'pv_to_bess_kwh': 'pv_to_bess_kw',
    'pv_to_mall_kwh': 'pv_to_mall_kw',
    'bess_charge_kwh': 'bess_charge_kw',
    'bess_discharge_kwh': 'bess_discharge_kw',
    'bess_to_ev_kwh': 'bess_to_ev_kw',
    'bess_to_mall_kwh': 'bess_to_mall_kw',
    'grid_to_ev_kwh': 'grid_to_ev_kw',
    'grid_to_mall_kwh': 'grid_to_mall_kw',
    'grid_to_bess_kwh': 'grid_to_bess_kw',
    'grid_export_kwh': 'pv_to_grid_kw',  # Export = waste in balance.py
}

# Aplikar mapeo de columnas
for csv_col, expected_col in column_mapping.items():
    if csv_col in df.columns:
        df[expected_col] = df[csv_col]

# Para SOC: buscar la columna correcta
soc_col = None
if 'bess_soc_percent' in df.columns:
    soc_col = 'bess_soc_percent'
elif 'soc_percent' in df.columns:
    soc_col = 'soc_percent'
elif any('soc' in c.lower() and 'percent' in c.lower() for c in df.columns):
    soc_col = next(c for c in df.columns if 'soc' in c.lower() and 'percent' in c.lower())

if soc_col and soc_col != 'bess_soc_percent':
    df['bess_soc_percent'] = df[soc_col]

# Crear columnas calculadas faltantes
if 'pv_to_demand_kw' not in df.columns:
    # PV to demand = PV to EV + PV to MALL
    if 'pv_to_ev_kw' in df.columns and 'pv_to_mall_kw' in df.columns:
        df['pv_to_demand_kw'] = df['pv_to_ev_kw'] + df['pv_to_mall_kw']
    elif 'pv_generation_kw' in df.columns:
        # Fallback: use minimum of PV and total demand
        total_demand = df.get('ev_demand_kw', pd.Series(0)) + df.get('mall_demand_kw', pd.Series(0))
        df['pv_to_demand_kw'] = np.minimum(df['pv_generation_kw'], total_demand)

if 'total_demand_kw' not in df.columns:
    # Total demand = EV demand + MALL demand
    ev_dem = df.get('ev_demand_kw', pd.Series(0))
    mall_dem = df.get('mall_demand_kw', pd.Series(0))
    df['total_demand_kw'] = ev_dem + mall_dem

if 'demand_from_grid_kw' not in df.columns:
    # Grid demand = grid to EV + grid to MALL + grid to BESS
    components = []
    for col in ['grid_to_ev_kw', 'grid_to_mall_kw', 'grid_to_bess_kw']:
        if col in df.columns:
            components.append(df[col])
    if components:
        df['demand_from_grid_kw'] = pd.concat(components, axis=1).sum(axis=1)
    else:
        df['demand_from_grid_kw'] = pd.Series(0, index=df.index)

# Add CO2 columns for emissions calculation
# CO2 factor for Iquitos grid (diesel-based): 0.4521 kg CO2/kWh
CO2_FACTOR = 0.4521
if 'co2_from_grid_kg' not in df.columns:
    df['co2_from_grid_kg'] = df['demand_from_grid_kw'] * CO2_FACTOR

# Add hour column for grouping operations
if 'hour' not in df.columns:
    # Extract hour from index if it's datetime
    if isinstance(df.index, pd.DatetimeIndex):
        df['hour'] = df.index.hour * 24 + (np.arange(len(df)) % 24)  # Running hour count
    else:
        df['hour'] = np.arange(len(df))  # Sequential hour index

# Columnas nuevas CityLearn v2 (no se mapean, ya tienen los nombres correctos)
# - grid_export_kwh → se mantiene como está
# - bess_to_mall_kwh → se mantiene como está

# 2. Verificar columnas críticas
print(f"\n[2] Verificando columnas críticas para CityLearn v2:")
critical_cols = [
    'pv_kwh',                # Generación solar (original)
    'ev_kwh',                # Demanda EV (original)
    'mall_kwh',              # Demanda MALL (original)
    'grid_export_kwh',       # NUEVA: Exportación a red pública
    'bess_to_mall_kwh',      # NUEVA: Peak shaving
]

missing_cols = []
for col in critical_cols:
    if col in df.columns:
        print(f"    [OK] {col}")
    else:
        print(f"    [!] {col} - FALTANTE")
        missing_cols.append(col)

if missing_cols:
    print(f"\n    [ERROR] Columnas faltantes: {missing_cols}")
    print("    Se generarán gráficas con datos disponibles")

# 3. Crear configuración
print(f"\n[3] Inicializando configuración de visualización:")
config = BalanceEnergeticoConfig(
    pv_capacity_kwp=4050.0,
    demand_peak_limit_kw=1900.0,
    bess_capacity_kwh=1700.0,
    bess_power_kw=400.0,
)
print(f"    [OK] Config creada (PV: {config.pv_capacity_kwp} kWp, BESS: {config.bess_capacity_kwh} kWh)")

# 4. Crear instancia del generador de gráficas
print(f"\n[4] Inicializando generador de gráficas:")
graphics = BalanceEnergeticoSystem(df, config)
print(f"    [OK] BalanceEnergeticoSystem inicializado")

# 5. Generar todas las gráficas
out_dir = Path("reports/balance_energetico")
print(f"\n[5] Generando gráficas en: {out_dir}")
try:
    graphics.plot_energy_balance(out_dir)
    print(f"\n    [OK] Todas las gráficas generadas exitosamente")
except Exception as e:
    print(f"    [ERROR] Error generating graphics: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 6. Verificar archivos generados
print(f"\n[6] Archivos generados:")
out_dir.mkdir(parents=True, exist_ok=True)
png_files = list(out_dir.glob("*.png"))
if png_files:
    for png in sorted(png_files):
        size_kb = png.stat().st_size / 1024
        print(f"    [OK] {png.name} ({size_kb:.1f} KB)")
else:
    print(f"    [!] No se encontraron archivos PNG en {out_dir}")

print("\n" + "=" * 80)
print("[RESUMEN] Gráficas de Balance Energético Completadas")
print("=" * 80)

# Métricas clave
print(f"\n[METRICAS CLAVE]")
print(f"  Generación PV total:      {df['pv_generation_kw'].sum():>12,.0f} kWh/año")
print(f"  Demanda EV total:         {df['ev_demand_kw'].sum():>12,.0f} kWh/año")
print(f"  Demanda MALL total:       {df['mall_kwh'].sum() if 'mall_kwh' in df.columns else df.get('mall_demand_kw', pd.Series([0])).sum():>12,.0f} kWh/año")

if 'grid_export_kwh' in df.columns:
    print(f"  Exportación a red:        {df['grid_export_kwh'].sum():>12,.0f} kWh/año ✨ NUEVA")
else:
    print(f"  Exportación a red:        [No disponible]")

if 'bess_to_mall_kwh' in df.columns:
    print(f"  Peak shaving BESS-MALL:  {df['bess_to_mall_kwh'].sum():>12,.0f} kWh/año ✨ NUEVA")
else:
    print(f"  Peak shaving BESS-MALL:  [No disponible]")

print("\n[OK] Proceso completado exitosamente")
