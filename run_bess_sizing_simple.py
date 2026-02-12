#!/usr/bin/env python3
"""Ejecutar BESS sizing con datos reales de EV v5.2

Valores v5.2:
- 19 cargadores × 2 tomas = 38 sockets
- 309 vehículos/día (270 motos + 39 mototaxis)
- ~453,349 kWh/año = 1,242 kWh/día demanda EV
- BESS esperado: ~940 kWh / ~342 kW (exclusivo EV, 100% cobertura)
- Horario operación EV: 9h - 22h (cierre a las 22:00)
"""
print("Iniciando BESS dimensionamiento v5.2...")

from pathlib import Path
import pandas as pd

# Usar datos reales del dataset v3 (no generar sintéticos)
chargers_path = Path('data/interim/oe2/chargers/chargers_ev_ano_2024_v3.csv')
ev_demand_path = Path('data/interim/oe2/chargers/ev_demand_real.csv')

CLOSING_HOUR = 22  # Hora de cierre: 22:00 (después de esta hora EV = 0)
OPENING_HOUR = 9   # Hora de apertura: 9:00

if chargers_path.exists():
    # Leer y agregar demanda real de 38 sockets
    df = pd.read_csv(chargers_path)
    charging_cols = [c for c in df.columns if 'charging_power_kw' in c.lower()]
    
    # Crear serie de demanda EV
    ev_demand = df[charging_cols].sum(axis=1)
    
    # IMPORTANTE: Forzar EV = 0 fuera del horario operativo (9h-22h)
    # Hora 22, 23, 0, 1, ..., 8 = 0
    hours_of_day = pd.Series(range(8760)) % 24
    ev_demand_adjusted = ev_demand.copy()
    ev_demand_adjusted[(hours_of_day >= CLOSING_HOUR) | (hours_of_day < OPENING_HOUR)] = 0
    
    df_ev = pd.DataFrame({
        'hour': range(8760),
        'ev_kwh': ev_demand_adjusted
    })
    df_ev.to_csv(ev_demand_path, index=False)
    
    total = df_ev['ev_kwh'].sum()
    peak = df_ev['ev_kwh'].max()
    print(f"✓ Demanda EV real cargada: {len(charging_cols)} sockets")
    print(f"  Energía anual: {total:,.0f} kWh")
    print(f"  Promedio diario: {total/365:,.0f} kWh/día")
    print(f"  Potencia pico: {peak:.1f} kW")
    print(f"  Horario operación: {OPENING_HOUR}h - {CLOSING_HOUR}h")
else:
    print(f"ERROR: No existe {chargers_path}")
    exit(1)

# Ejecutar BESS sizing
print("\nEjecutando dimensionamiento BESS...")

from src.dimensionamiento.oe2.disenobess.bess import run_bess_sizing

results = run_bess_sizing(
    out_dir=Path('data/oe2/bess'),
    mall_energy_kwh_day=33885.0,
    pv_profile_path=Path('data/interim/oe2/solar/pv_generation_timeseries.csv'),
    ev_profile_path=ev_demand_path,  # Usar demanda EV real v5.2
    dod=0.80,
    c_rate=0.36,  # v5.2: 0.36 C-rate
    round_kwh=10.0,
    efficiency_roundtrip=0.95,  # v5.2
    autonomy_hours=4.0,
    pv_dc_kw=4050.0,
    sizing_mode='ev_open_hours',
    soc_min_percent=20.0,
    generate_plots=True,
)

print("\n" + "="*80)
print("CAPACIDAD BESS DETERMINADA (con datos reales EV v5.2)")
print("="*80)

# Obtener valores con manejo de tipos
capacity = results.get('bess_capacity_kwh', 0) or results.get('capacity_kwh', 0)
power = results.get('bess_power_kw', 0) or results.get('nominal_power_kw', 0)
cycles = results.get('cycles_per_day', 0)

if isinstance(capacity, (int, float)) and capacity > 0:
    print(f"\nCapacidad: {capacity:,.0f} kWh")
else:
    print(f"\nCapacidad: {capacity}")
    
if isinstance(power, (int, float)) and power > 0:
    print(f"Potencia: {power:,.0f} kW")
else:
    print(f"Potencia: {power}")

print(f"DoD: 80%")
print(f"Eficiencia: 95%")

if isinstance(cycles, (int, float)):
    print(f"Ciclos/día: {cycles:.2f}")

print("="*80)
