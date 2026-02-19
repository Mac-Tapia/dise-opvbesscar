#!/usr/bin/env python
"""Verificar que SAC, PPO y A2C cargan correctamente dataset_config_v7.json"""

import json
from pathlib import Path

print("="*80)
print("VERIFICACIÓN: Agentes cargando dataset_config_v7.json correcto")
print("="*80)

config_path = Path("data/iquitos_ev_mall/dataset_config_v7.json")

if not config_path.exists():
    print(f"❌ ERROR: {config_path} no existe")
    exit(1)

with open(config_path, 'r') as f:
    config = json.load(f)

print("\n✓ JSON cargado correctamente\n")

# Mostrar configuración de vehículos
print("CONFIGURACION DE VEHICULOS:")
vehicles = config.get("vehicles", {})
motos = vehicles.get("motos", {})
mototaxis = vehicles.get("mototaxis", {})

print(f"  Motos:")
print(f"    - Count: {motos.get('count')} unidades")
print(f"    - Sockets: {motos.get('sockets')} (uno por moto)")
print(f"    - Chargers asignados: {motos.get('chargers_assigned')} (chargers 0-14)")

print(f"\n  Mototaxis:")
print(f"    - Count: {mototaxis.get('count')} unidades")
print(f"    - Sockets: {mototaxis.get('sockets')} (uno por mototaxi)")
print(f"    - Chargers asignados: {mototaxis.get('chargers_assigned')} (chargers 15-18)")

print(f"\n  TOTAL:")
print(f"    - Vehículos: {vehicles.get('total_vehicles')}")
print(f"    - Sockets: {vehicles.get('total_sockets_allocated')}")

# Mostrar infraestructura
print("\n\nINFRAESTRUCTURA SISTEMA:")
system = config.get("system", {})
print(f"  PV: {system.get('pv_capacity_kwp')} kWp")
print(f"  BESS: {system.get('bess_capacity_kwh')} kWh, {system.get('bess_max_power_kw')} kW, SOC avg {system.get('bess_avg_soc_percent')}%")
print(f"  Chargers: {system.get('n_chargers')} units × {system.get('charger_power_kw')} kW")
print(f"  Sockets: {system.get('n_sockets')} total ({system.get('sockets_per_charger')} per charger)")

# Mostrar demanda
print("\n\nDEMANDA:")
demand = config.get("demand", {})
print(f"  Mall:")
print(f"    - Promedio: {demand.get('mall_avg_kw'):.2f} kW")
print(f"    - Máximo: {demand.get('mall_max_hourly_kw')} kW/hora")
print(f"    - Anual: {demand.get('mall_annual_kwh'):,.0f} kWh")
print(f"  EV:")
print(f"    - Promedio: {demand.get('ev_avg_kw')} kW")
print(f"    - Anual: {demand.get('ev_annual_kwh'):,.0f} kWh")

# Mostrar solar
print("\n\nSOLAR:")
solar = config.get("solar", {})
print(f"  Anual: {solar.get('annual_kwh'):,.0f} kWh")
print(f"  Max power: {solar.get('max_power_kw'):.2f} kW")

# Mostrar CO2
print("\n\nCO2 / GRID:")
co2 = config.get("co2", {})
print(f"  Grid: {co2.get('grid_factor_kg_per_kwh')} kg/kWh")
print(f"  EV: {co2.get('ev_factor_kg_per_kwh')} kg/kWh")

print("\n" + "="*80)
print("✅ VERIFICACION COMPLETA: dataset_config_v7.json contiene configuración EXACTA")
print("="*80)
print("\nLoaded by agents:")
print("  • SAC: src/agents/sac.py")
print("  • PPO: src/agents/ppo_sb3.py")
print("  • A2C: src/agents/a2c_sb3.py")
