#!/usr/bin/env python3
"""Validar pesos multi-objetivo en todos los archivos de configuración."""
from __future__ import annotations

import json
import re
from pathlib import Path

files_to_check = [
    ('src/rewards/rewards.py', 'python'),
    ('configs/default.yaml', 'yaml'),
    ('configs/default_optimized.yaml', 'yaml'),
    ('configs/agents/sac_config.yaml', 'yaml'),
    ('configs/agents/ppo_config.yaml', 'yaml'),
    ('configs/agents/a2c_config.yaml', 'yaml'),
    ('configs/agents/agents_config.yaml', 'yaml'),
    ('configs/sac_optimized.json', 'json'),
    ('.github/training/training_config.json', 'json'),
    ('data/interim/oe3/schema.json', 'json'),
    ('data/processed/citylearn/iquitos_ev_mall/schema.json', 'json'),
]

EXPECTED = {'co2': 0.35, 'solar': 0.20, 'ev': 0.30, 'cost': 0.10, 'grid': 0.05}

print('=' * 100)
print('VALIDACION FINAL - Pesos Multi-Objetivo Sincronizados')
print('=' * 100)
print(f"{'#':>2} | {'Archivo':<55} | CO2  | Solar| EV   | Cost | Grid | SUMA | Estado")
print('-' * 100)

all_ok = True
for i, (path, ftype) in enumerate(files_to_check, 1):
    p = Path(path)
    if not p.exists():
        print(f"{i:>2} | {path:<55} | ---  | ---  | ---  | ---  | ---  | ---  | NO EXISTE")
        all_ok = False
        continue
    
    content = p.read_text(encoding='utf-8')
    weights = {}
    
    # Extract weights based on file type
    if ftype == 'python':
        # Look for co2_focus preset specifically
        match = re.search(
            r'"co2_focus":\s*MultiObjectiveWeights\(co2=([0-9.]+),\s*cost=([0-9.]+),\s*solar=([0-9.]+),\s*ev_satisfaction=([0-9.]+),\s*ev_utilization=[0-9.]+,\s*grid_stability=([0-9.]+)\)',
            content
        )
        if match:
            weights = {
                'co2': float(match.group(1)),
                'cost': float(match.group(2)),
                'solar': float(match.group(3)),
                'ev': float(match.group(4)),
                'grid': float(match.group(5))
            }
    elif ftype == 'yaml':
        # Look for multi_objective_weights or reward_weights section
        section = None
        for section_name in ['multi_objective_weights:', 'reward_weights:']:
            mo_start = content.find(section_name)
            if mo_start != -1:
                # Find the section (up to next section at same or lower indentation)
                section_start = content.find('\n', mo_start) + 1
                lines_after = content[section_start:].split('\n')
                section_lines = []
                for line in lines_after:
                    if line.strip() and not line.startswith(' ') and not line.startswith('\t'):
                        break  # Found next section at same level
                    section_lines.append(line)
                section = '\n'.join(section_lines)
                break
        
        if section:
            # Extract weights from section (handle various naming conventions)
            # CO2
            m = re.search(r'\b(?:co2|co2_grid_minimization|co2_weight):\s*([0-9.]+)', section)
            if m:
                weights['co2'] = float(m.group(1))
            # Solar
            m = re.search(r'\b(?:solar|solar_self_consumption|solar_weight):\s*([0-9.]+)', section)
            if m:
                weights['solar'] = float(m.group(1))
            # EV
            m = re.search(r'\b(?:ev|ev_satisfaction|ev_satisfaction_weight|ev_charge_completion):\s*([0-9.]+)', section)
            if m:
                weights['ev'] = float(m.group(1))
            # Cost
            m = re.search(r'\b(?:cost|cost_minimization|cost_weight):\s*([0-9.]+)', section)
            if m:
                weights['cost'] = float(m.group(1))
            # Grid
            m = re.search(r'\b(?:grid|grid_stability|grid_stability_weight):\s*([0-9.]+)', section)
            if m:
                weights['grid'] = float(m.group(1))
        
        # If not found, look for individual weight keys (alternative format)
        if not weights:
            # CO2
            match = re.search(r'co2_weight:\s*([0-9.]+)', content)
            if match:
                weights['co2'] = float(match.group(1))
            # Solar
            match = re.search(r'solar_weight:\s*([0-9.]+)', content)
            if match:
                weights['solar'] = float(match.group(1))
            # EV
            match = re.search(r'ev_satisfaction_weight:\s*([0-9.]+)', content)
            if match:
                weights['ev'] = float(match.group(1))
            # Cost
            match = re.search(r'cost_weight:\s*([0-9.]+)', content)
            if match:
                weights['cost'] = float(match.group(1))
            # Grid
            match = re.search(r'grid_stability_weight:\s*([0-9.]+)', content)
            if match:
                weights['grid'] = float(match.group(1))
    elif ftype == 'json':
        data = json.loads(content)
        # Check multiple possible locations for weights
        rw = data.get('reward_weights', {})
        if not rw:
            rw = data.get('rewards', {})
        if not rw:
            rw = data.get('reward_config', {})
        if not rw:
            rw = data.get('multi_objective_weights', {})
        
        if rw:
            # Map various key names to standard names
            weights['co2'] = rw.get('co2', rw.get('co2_grid_minimization', rw.get('co2_weight', 0)))
            weights['solar'] = rw.get('solar', rw.get('solar_self_consumption', rw.get('solar_weight', 0)))
            weights['ev'] = rw.get('ev', rw.get('ev_charge_completion', rw.get('ev_satisfaction_weight', rw.get('ev_weight', 0))))
            weights['cost'] = rw.get('cost', rw.get('cost_minimization', rw.get('cost_weight', 0)))
            weights['grid'] = rw.get('grid', rw.get('grid_stability', rw.get('grid_stability_weight', rw.get('grid_weight', 0))))
    
    if weights and any(v > 0 for v in weights.values()):
        total = sum(weights.values())
        ok = all(abs(weights.get(k, 0) - v) < 0.01 for k, v in EXPECTED.items()) and abs(total - 1.0) < 0.01
        status = 'OK' if ok else 'REVISAR'
        if not ok:
            all_ok = False
        co2_v = weights.get('co2', 0)
        solar_v = weights.get('solar', 0)
        ev_v = weights.get('ev', 0)
        cost_v = weights.get('cost', 0)
        grid_v = weights.get('grid', 0)
        print(f"{i:>2} | {path:<55} | {co2_v:.2f} | {solar_v:.2f} | {ev_v:.2f} | {cost_v:.2f} | {grid_v:.2f} | {total:.2f} | {status}")
    else:
        print(f"{i:>2} | {path:<55} | ---  | ---  | ---  | ---  | ---  | ---  | SIN PESOS")
        all_ok = False

print('=' * 100)
print('PESOS ESPERADOS: CO2=0.35 | Solar=0.20 | EV=0.30 | Cost=0.10 | Grid=0.05 | SUMA=1.00')
print('=' * 100)

if all_ok:
    print('RESULTADO: TODOS LOS ARCHIVOS SINCRONIZADOS CORRECTAMENTE')
else:
    print('RESULTADO: HAY ARCHIVOS QUE REQUIEREN REVISION')
