#!/usr/bin/env python3
import json
from pathlib import Path

OUTPUTS_DIR = Path('outputs')

print("="*80)
print("INVESTIGACIÓN: ¿Por qué agentes cargan solo 20-30 motos vs Target 270?")
print("="*80)

agents = ['PPO', 'A2C', 'SAC']

for agent in agents:
    filepath = OUTPUTS_DIR / f'{agent.lower()}_training' / f'result_{agent.lower()}.json'
    
    print(f"\n{'─'*80}")
    print(f"AGENTE: {agent}")
    print(f"{'─'*80}")
    
    if not filepath.exists():
        print(f"  ✗ Archivo no encontrado")
        continue
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    # Vehicle Charging Info
    print(f"\n📊 VEHÍCULOS CARGADOS:")
    vc = data.get('vehicle_charging', {})
    
    motos_per = vc.get('motos_charged_per_episode', [])
    taxis_per = vc.get('mototaxis_charged_per_episode', [])
    motos_total = vc.get('motos_total', 0)
    taxis_total = vc.get('mototaxis_total', 0)
    
    if motos_per:
        print(f"  Motos/episodio: {motos_per}")
        print(f"  Motos TOTAL: {motos_total} (suma de todos episodios)")
        print(f"  Motos MAX/episodio: {max(motos_per) if motos_per else 0}")
        print(f"  Motos PROMEDIO/episodio: {sum(motos_per)/len(motos_per):.1f}")
    else:
        print(f"  Motos/episodio: VACÍO")
    
    if taxis_per:
        print(f"  Taxis/episodio: {taxis_per}")
        print(f"  Taxis TOTAL: {taxis_total}")
        print(f"  Taxis MAX/episodio: {max(taxis_per) if taxis_per else 0}")
    
    # Buscar demanda de vehículos
    print(f"\n🚗 DEMANDA DE VEHÍCULOS (Disponibles para cargar):")
    demand_keys = [k for k in data.keys() if any(w in k.lower() for w in ['demand', 'arrival', 'available', 'vehicles_available'])]
    
    if demand_keys:
        for key in demand_keys[:3]:
            value = data[key]
            if isinstance(value, (int, float)):
                print(f"  {key}: {value}")
            elif isinstance(value, dict):
                print(f"  {key}:")
                for subkey in list(value.keys())[:3]:
                    print(f"    {subkey}: {value[subkey]}")
    
    # Restricciones energéticas
    print(f"\n⚡ RESTRICCIONES ENERGÉTICAS/BESS:")
    summary = data.get('summary_metrics', {})
    
    solar_used = summary.get('total_solar_used_kwh', 0)
    grid_import = summary.get('total_grid_import_kwh', 0)
    bess_charge = summary.get('total_bess_charge_kwh', 0)
    bess_discharge = summary.get('total_bess_discharge_kwh', 0)
    ev_energy = summary.get('total_electricity_consumption_kwh', 0)
    
    print(f"  Solar usado: {solar_used:.0f} kWh")
    print(f"  Grid import: {grid_import:.0f} kWh")
    print(f"  BESS cargado: {bess_charge:.0f} kWh")
    print(f"  BESS descargado: {bess_discharge:.0f} kWh")
    print(f"  Energía total EV: {ev_energy:.0f} kWh")
    
    # Calcular si la energía es limitante
    print(f"\n🔍 ANÁLISIS DE LIMITANTES:")
    motos_avg = sum(motos_per)/len(motos_per) if motos_per else 0
    taxis_avg = sum(taxis_per)/len(taxis_per) if taxis_per else 0
    
    # Energía por vehículo cargado
    if motos_avg > 0 and ev_energy > 0:
        kwh_per_moto = ev_energy / (motos_avg * 10)  # 10 episodios
        print(f"  Energía promedio/moto cargada: {kwh_per_moto:.2f} kWh")
        print(f"  Si cargáramos 270 motos: {270 * kwh_per_moto:.0f} kWh necesarios")
        print(f"  Energía disponible (solar+bess): {(solar_used + bess_discharge):.0f} kWh")
        print(f"  ¿Hay energía suficiente?: {'SÍ' if (solar_used + bess_discharge) >= (270 * kwh_per_moto) else 'NO'}")
    
    # Información de chargers
    print(f"\n🔌 INFORMACIÓN DE CARGADORES:")
    charger_info = data.get('chargers_info', {})
    if charger_info:
        print(f"  {json.dumps(charger_info, indent=2)[:300]}...")
    else:
        # Búsqueda alternativa
        charger_keys = [k for k in data.keys() if 'charger' in k.lower() or 'socket' in k.lower()]
        if not charger_keys:
            print(f"  ℹ️  No hay info de chargers explícita en checkpoint")
        else:
            for key in charger_keys[:2]:
                print(f"  {key}: {data[key]}")
    
    print(f"\n💡 CONCLUSIÓN:")
    print(f"  Max motos/episodio: {max(motos_per) if motos_per else 0}")
    print(f"  Target motos: 270")
    print(f"  Ratio: {(max(motos_per)/270*100 if motos_per and max(motos_per) > 0 else 0):.1f}% del target")
    print(f"  LIMITANTE PROBABLE: {'Energía insuficiente' if (solar_used + bess_discharge) < (motos_avg*10*7.4*24) else 'Restricción temporal/demanda'}")

print("\n" + "="*80)
