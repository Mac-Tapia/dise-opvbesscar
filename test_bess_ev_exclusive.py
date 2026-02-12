#!/usr/bin/env python3
"""Test BESS sizing exclusivo para EV"""
from pathlib import Path
from src.dimensionamiento.oe2.disenobess.bess import run_bess_sizing

print("="*70)
print("DIMENSIONAMIENTO BESS EXCLUSIVO PARA EV (motos y mototaxis)")
print("="*70)
print()

results = run_bess_sizing(
    out_dir=Path('data/interim/oe2/bess'),
    mall_energy_kwh_day=33885.0,  # 12,368,653 kWh/año / 365 dias
    pv_profile_path=Path('data/oe2/Generacionsolar/pv_generation_hourly_citylearn_v2.csv'),
    ev_profile_path=Path('data/oe2/chargers/chargers_ev_ano_2024_v3.csv'),  # 38 sockets, 412,236 kWh/año (9h-22h)
    dod=0.80,  # 80% DoD (SOC 100% -> 20%)
    c_rate=0.36,  # v5.2: 0.36 C-rate
    round_kwh=10.0,
    efficiency_roundtrip=0.95,  # 95% segun analisis
    autonomy_hours=4.0,  # 4 horas de autonomia
    pv_dc_kw=4050.0,  # 4,050 kWp instalados
    sizing_mode='ev_deficit_100',  # Cubrir 100% deficit EV
    soc_min_percent=20.0,  # SOC minimo 20%
    generate_plots=False,
)

print()
print("="*70)
print("RESULTADO BESS EXCLUSIVO EV")
print("="*70)
cap = results.get('capacity_kwh', 0)
pot = results.get('nominal_power_kw', 0)
print(f"Capacidad: {cap:,.0f} kWh")
print(f"Potencia:  {pot:,.0f} kW")
print(f"DoD:       80%")
print(f"SOC final: 20% al cierre (22:00)")
