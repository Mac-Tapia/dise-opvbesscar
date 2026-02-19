#!/usr/bin/env python
"""Simular que SAC, PPO y A2C cargan el dataset_config_v7.json correctamente."""

from src.dataset_builder_citylearn.data_loader import load_agent_dataset_mandatory
import json

print("\n" + "="*80)
print("SIMULACION: Tres agentes (SAC, PPO, A2C) cargando dataset_config_v7.json")
print("="*80)

agents = ["SAC", "PPO", "A2C"]
config_from_agents = {}

for agent_name in agents:
    print(f"\n{'─'*80}")
    print(f"AGENTE: {agent_name}")
    print(f"{'─'*80}")
    
    # Simular carga desde el agente
    datasets = load_agent_dataset_mandatory(agent_name=agent_name)
    config = datasets["config"]
    
    # Extraer datos relevantes
    vehicles = config["vehicles"]
    system = config["system"]
    
    config_from_agents[agent_name] = {
        "vehicles": vehicles,
        "system": system,
    }
    
    # Mostrar resumen
    print(f"\n📊 CONFIGURACIÓN CARGADA:")
    print(f"   Motos: {vehicles['motos']['count']} units, {vehicles['motos']['sockets']} sockets, "
          f"{vehicles['motos']['chargers_assigned']} chargers")
    print(f"   Mototaxis: {vehicles['mototaxis']['count']} units, {vehicles['mototaxis']['sockets']} sockets, "
          f"{vehicles['mototaxis']['chargers_assigned']} chargers")
    print(f"   Sistema: {system['n_chargers']} chargers × {system['charger_power_kw']} kW")
    print(f"   BESS: {system['bess_capacity_kwh']} kWh")
    print(f"   PV: {system['pv_capacity_kwp']} kWp")

# Validar que todos los agentes leen EXACTAMENTE lo mismo
print(f"\n{'='*80}")
print("VALIDACION: ¿Todos los agentes leen la MISMA configuración?")
print(f"{'='*80}")

base_config = config_from_agents["SAC"]
all_match = True

for agent_name in ["PPO", "A2C"]:
    if config_from_agents[agent_name] == base_config:
        print(f"✅ {agent_name} matches SAC: YES")
    else:
        print(f"❌ {agent_name} matches SAC: NO - DIFERENTES!")
        all_match = False

if all_match:
    print(f"\n{'='*80}")
    print("✅ SUCCESS: Todos los agentes (SAC, PPO, A2C) cargan IDENTICAMENTE")
    print(f"{'='*80}")
    print(f"\n📋 CONFIGURACION MASTER (desde dataset_config_v7.json):")
    print(json.dumps(base_config, indent=2))
else:
    print(f"\n{'='*80}")
    print("❌ FAILED: Los agentes cargan configuraciones DIFERENTES")
    print(f"{'='*80}")
    for agent, config in config_from_agents.items():
        print(f"\n{agent}:")
        print(json.dumps(config, indent=2))
