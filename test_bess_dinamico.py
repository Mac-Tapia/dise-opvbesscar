#!/usr/bin/env python3
"""Test BESS dimensionamiento con criterio dinámico."""
from pathlib import Path
from src.dimensionamiento.oe2.disenobess.bess import run_bess_sizing

print('🔧 Ejecutando BESS dimensionamiento con criterio DINÁMICO...\n')

out_dir = Path('temp_bess_test')
out_dir.mkdir(exist_ok=True)

pv_profile_path = Path('data/interim/oe2/solar/pv_generation_timeseries.csv')
ev_profile_path = Path('data/interim/oe2/ev_demand_hourly.csv')

results = run_bess_sizing(
    out_dir=out_dir,
    mall_energy_kwh_day=33885.0,
    pv_profile_path=pv_profile_path,
    ev_profile_path=ev_profile_path,
    dod=0.80,
    sizing_mode='ev_open_hours',
    soc_min_percent=20.0,
    load_scope='total',
    generate_plots=False
)

print('\n✅ RESULTADO CON CRITERIO DINÁMICO:')
print(f'   • Capacidad: {results.get("bess_capacity_kwh", "N/A")} kWh')
print(f'   • Potencia:  {results.get("bess_power_kw", "N/A")} kW')
print(f'   • Ciclos/día: {results.get("cycles_per_day", "N/A")}')
print(f'   • Deficit: {results.get("deficit_kwh_day", "N/A")} kWh/día')
print(f'   • Descarga horas: {results.get("discharge_hours", "N/A")}')

