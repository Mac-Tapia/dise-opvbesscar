#!/usr/bin/env python3
"""Verificar playas de estacionamiento OE2"""

import json
from pathlib import Path

chargers = json.load(open('data/interim/oe2/chargers/individual_chargers.json'))

motos = [c for c in chargers if c['playa'] == 'Playa_Motos']
taxis = [c for c in chargers if c['playa'] == 'Playa_Mototaxis']

print('PLAYAS DE ESTACIONAMIENTO - OE2')
print('='*80)

print(f'\nPlaya Motos:')
print(f'  Chargers: {len(motos)}')
print(f'  Sockets totales: {sum(c["sockets"] for c in motos)}')
print(f'  Potencia total: {sum(c["power_kw"] * c["sockets"] for c in motos):.0f} kW')
print(f'  Energia diaria: {sum(c.get("daily_energy_kwh", 0) for c in motos):.0f} kWh')
print(f'  Primeros 3: {[c["charger_id"] for c in motos[:3]]}')
print(f'  Ultimos 3: {[c["charger_id"] for c in motos[-3:]]}')

print(f'\nPlaya Mototaxis:')
print(f'  Chargers: {len(taxis)}')
print(f'  Sockets totales: {sum(c["sockets"] for c in taxis)}')
print(f'  Potencia total: {sum(c["power_kw"] * c["sockets"] for c in taxis):.0f} kW')
print(f'  Energia diaria: {sum(c.get("daily_energy_kwh", 0) for c in taxis):.0f} kWh')
print(f'  Primeros 3: {[c["charger_id"] for c in taxis[:3]]}')
print(f'  Ultimos 3: {[c["charger_id"] for c in taxis[-3:]]}')

print(f'\nTOTAL SISTEMA:')
print(f'  Chargers: {len(motos) + len(taxis)}')
print(f'  Sockets: {sum(c["sockets"] for c in motos) + sum(c["sockets"] for c in taxis)}')
print(f'  Potencia: {sum(c["power_kw"] * c["sockets"] for c in motos) + sum(c["power_kw"] * c["sockets"] for c in taxis):.0f} kW')

print('\n' + '='*80)
print('ARCHIVOS POR PLAYA')
print('='*80)

# Verificar archivos en playas
playas_path = Path('data/interim/oe2/chargers/playas')
if playas_path.exists():
    for playa_dir in playas_path.iterdir():
        if playa_dir.is_dir():
            print(f'\n{playa_dir.name}:')
            if (playa_dir / 'annual_datasets').exists():
                for scenario_dir in (playa_dir / 'annual_datasets').iterdir():
                    if scenario_dir.is_dir():
                        files = list(scenario_dir.glob('charger_*.json'))
                        print(f'  {scenario_dir.name}: {len(files)} chargers')
