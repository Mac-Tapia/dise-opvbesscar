#!/usr/bin/env python3
"""
Mostrar resultados del pipeline en consola.
"""

import json
from pathlib import Path

def show_results():
    summary_path = Path('outputs/oe3/simulations/simulation_summary.json')
    if not summary_path.exists():
        print('No se encontro simulation_summary.json')
        return
    
    with open(summary_path, encoding='utf-8') as f:
        summary = json.load(f)
    
    print('\n' + '='*100)
    print('RESULTADOS DEL PIPELINE COMPLETO')
    print('='*100)
    
    # Baseline
    if 'pv_bess_uncontrolled' in summary:
        baseline = summary['pv_bess_uncontrolled']
        print('\n[BASELINE - Sin Control Inteligente]')
        print(f'  CO2 Total: {baseline.get("carbon_kg", 0):.0f} kg/año')
        print(f'  Importacion red: {baseline.get("grid_import_kwh", 0):.0f} kWh')
        print(f'  Carga EV: {baseline.get("ev_charging_kwh", 0):.0f} kWh')
        print(f'  Generacion PV: {baseline.get("pv_generation_kwh", 0):.0f} kWh')
        baseline_co2 = baseline.get('carbon_kg', 0)
    else:
        baseline_co2 = 0
    
    # Agentes
    if 'pv_bess_results' in summary:
        results = summary['pv_bess_results']
        
        print('\n[AGENTES ENTRENADOS - Con Control Inteligente]')
        for agent_name in sorted(results.keys()):
            result = results[agent_name]
            co2 = result.get('carbon_kg', 0)
            reduction = ((baseline_co2 - co2) / baseline_co2 * 100) if baseline_co2 > 0 else 0
            
            print(f'\n  {agent_name}:')
            print(f'    CO2: {co2:.0f} kg/año')
            print(f'    Reduccion vs baseline: {reduction:.2f}%')
            print(f'    Grid import: {result.get("grid_import_kwh", 0):.0f} kWh')
            print(f'    Generacion PV integrada: {result.get("pv_generation_kwh", 0):.0f} kWh')
    
    # Mejor agente
    best = summary.get('best_agent', 'N/A')
    print(f'\n[MEJOR AGENTE]: {best}')
    
    print('\n' + '='*100)
    print('ARCHIVOS GENERADOS:')
    print('  - outputs/oe3/simulations/simulation_summary.json')
    print('  - outputs/oe3/simulations/co2_comparison.md')
    print('  - outputs/oe3/simulations/timeseries_uncontrolled.csv')
    print('  - outputs/oe3/simulations/timeseries_sac.csv')
    print('  - outputs/oe3/simulations/timeseries_ppo.csv')
    print('  - outputs/oe3/simulations/timeseries_a2c.csv')
    print('='*100 + '\n')

if __name__ == '__main__':
    show_results()
