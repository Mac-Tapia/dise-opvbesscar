#!/usr/bin/env python3
"""Script para verificar energía solar anual en construcción del dataset"""
from __future__ import annotations

from typing import Any
import pandas as pd  # type: ignore
import json
from pathlib import Path as PathlibPath

# Load solar timeseries
solar_path: PathlibPath = PathlibPath("data/interim/oe2/solar/pv_generation_timeseries.csv")
df_solar: pd.DataFrame = pd.read_csv(solar_path)

print("=" * 70)
print("ENERGÍA SOLAR ANUAL EN CONSTRUCCIÓN DEL DATASET OE3")
print("=" * 70)

print(f"\n[TIMESERIES]")
print(f"  Resolución:        Horaria (8,760 filas = 365 días × 24 horas)")
print(f"  Período:           {df_solar['timestamp'].iloc[0]} a {df_solar['timestamp'].iloc[-1]}")
print(f"  Archivo:           {solar_path}")

print(f"\n[ESTADÍSTICAS DE GENERACIÓN]")
print(f"  Potencia pico:     {df_solar['ac_power_kw'].max():.2f} kW")
print(f"  Potencia promedio: {df_solar['ac_power_kw'].mean():.2f} kW")
print(f"  Potencia mínima:   {df_solar['ac_power_kw'].min():.2f} kW")

# Total annual generation
total_energy_kwh: float = df_solar['ac_power_kw'].sum()
total_energy_mwh: float = total_energy_kwh / 1000
total_energy_gwh: float = total_energy_mwh / 1000

print(f"\n[ENERGÍA ANUAL TOTAL GENERADA]")
print(f"  {total_energy_kwh:,.2f} kWh")
print(f"  {total_energy_mwh:,.2f} MWh")
print(f"  {total_energy_gwh:,.3f} GWh")

# Load solar config
config_path: PathlibPath = PathlibPath("data/interim/oe2/solar/pv_config.json")
if config_path.exists():
    with open(config_path, 'r') as f:
        config: dict[str, Any] = json.load(f)

    capacity_kw = config.get("capacity_kw", None)
    if capacity_kw:
        capacity_factor: float = (total_energy_kwh / (capacity_kw * 8760)) * 100
        print(f"\n[CAPACIDAD INSTALADA]")
        print(f"  Potencia: {capacity_kw:,.0f} kW")
        print(f"  Módulo: {config.get('module', 'N/A')}")
        print(f"  Inversor: {config.get('inverter', 'N/A')}")
        print(f"  Pérdidas del sistema: {config.get('system_losses_percent', 'N/A')}%")
        print(f"\n[FACTOR DE CAPACIDAD]")
        print(f"  {capacity_factor:.2f}%")

# Monthly breakdown
df_solar['datetime'] = pd.to_datetime(df_solar['timestamp'])
df_solar['month'] = df_solar['datetime'].dt.strftime('%Y-%m')  # type: ignore
monthly_energy = df_solar.groupby('month')['ac_power_kw'].sum()

print(f"\n[DISTRIBUCIÓN MENSUAL]")
for month, energy in monthly_energy.items():
    pct: float = energy / total_energy_kwh * 100
    print(f"  {month}: {energy:>10,.0f} kWh ({pct:>5.1f}%)")

print("\n" + "=" * 70)
