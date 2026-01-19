#!/usr/bin/env python3
"""
Generar 101 escenarios anuales (1 baseline + 100 Monte Carlo) para 128 chargers.

Genera datasets individuales para cada charger en cada escenario.

Uso:
    python generate_101_scenarios.py
"""

import json
from pathlib import Path
import numpy as np
import pandas as pd


def generate_101_scenarios():
    """Generar 101 escenarios Monte Carlo para 128 chargers."""
    
    base_dir = Path("data/interim/oe2/chargers")
    
    # Cargar chargers metadata
    chargers_file = base_dir / "individual_chargers.json"
    with open(chargers_file, 'r') as f:
        chargers = json.load(f)
    
    motos = [c for c in chargers if c['playa'] == 'Playa_Motos']
    taxis = [c for c in chargers if c['playa'] == 'Playa_Mototaxis']
    
    print(f"✓ Cargados {len(motos)} chargers Motos")
    print(f"✓ Cargados {len(taxis)} chargers Mototaxis")
    
    # Cargar baseline (escenario base)
    baseline_motos_dir = base_dir / "annual_datasets" / "Playa_Motos" / "base"
    baseline_taxis_dir = base_dir / "annual_datasets" / "Playa_Mototaxis" / "base"
    
    print("\n[*] Generando 101 escenarios (1 baseline + 100 Monte Carlo)...")
    
    seed = 42
    rng = np.random.RandomState(seed)
    
    # Variabilidad de demanda: factor multiplicador (0.8 a 1.2)
    variability_factors = np.concatenate([
        [1.0],  # Scenario 0: baseline (sin variación)
        rng.uniform(0.8, 1.2, 100)  # Scenarios 1-100: ±20% variación
    ])
    
    for scenario_id, variability in enumerate(variability_factors):
        print(f"\n   [{scenario_id:3d}/100] Escenario {scenario_id} (factor: {variability:.2f})...")
        
        # Crear directorio para escenario
        scenario_motos_dir = base_dir / "annual_datasets" / "Playa_Motos" / str(scenario_id)
        scenario_taxis_dir = base_dir / "annual_datasets" / "Playa_Mototaxis" / str(scenario_id)
        
        scenario_motos_dir.mkdir(parents=True, exist_ok=True)
        scenario_taxis_dir.mkdir(parents=True, exist_ok=True)
        
        # Generar Playa Motos
        for charger in motos:
            charger_id = charger['charger_id']
            baseline_file = baseline_motos_dir / f"{charger_id}.csv"
            
            if baseline_file.exists():
                # Cargar baseline
                df = pd.read_csv(baseline_file, parse_dates=['timestamp'])
                
                # Aplicar variabilidad: multiplicar power_kw y energy_kwh
                if variability != 1.0 and scenario_id > 0:
                    # Agregar ruido estocástico
                    noise = rng.normal(1.0, 0.1, len(df))  # 10% std dev
                    noise = np.clip(noise, 0.5, 1.5)  # Limitar ruido (0.5 a 1.5)
                    df['power_kw'] = df['power_kw'] * variability * noise
                    df['energy_kwh'] = df['energy_kwh'] * variability * noise
                    
                    # Limpiar negativos
                    df['power_kw'] = df['power_kw'].clip(lower=0)
                    df['energy_kwh'] = df['energy_kwh'].clip(lower=0)
                
                # Guardar escenario
                output_file = scenario_motos_dir / f"{charger_id}.csv"
                df.to_csv(output_file, index=False)
        
        # Generar agregado para Playa Motos
        aggregated = []
        for charger in motos:
            charger_id = charger['charger_id']
            output_file = scenario_motos_dir / f"{charger_id}.csv"
            if output_file.exists():
                df = pd.read_csv(output_file, parse_dates=['timestamp'])
                aggregated.append(df)
        
        if aggregated:
            agg_df = aggregated[0][['timestamp']].copy()
            agg_df['power_kw'] = sum(df['power_kw'] for df in aggregated)
            agg_df['energy_kwh'] = sum(df['energy_kwh'] for df in aggregated)
            agg_df.to_csv(scenario_motos_dir / "aggregated_profile.csv", index=False)
        
        # Generar Playa Mototaxis (similar)
        for charger in taxis:
            charger_id = charger['charger_id']
            baseline_file = baseline_taxis_dir / f"{charger_id}.csv"
            
            if baseline_file.exists():
                df = pd.read_csv(baseline_file, parse_dates=['timestamp'])
                
                if variability != 1.0 and scenario_id > 0:
                    noise = rng.normal(1.0, 0.1, len(df))
                    noise = np.clip(noise, 0.5, 1.5)
                    df['power_kw'] = df['power_kw'] * variability * noise
                    df['energy_kwh'] = df['energy_kwh'] * variability * noise
                    df['power_kw'] = df['power_kw'].clip(lower=0)
                    df['energy_kwh'] = df['energy_kwh'].clip(lower=0)
                
                output_file = scenario_taxis_dir / f"{charger_id}.csv"
                df.to_csv(output_file, index=False)
        
        # Generar agregado para Playa Mototaxis
        aggregated_taxis = []
        for charger in taxis:
            charger_id = charger['charger_id']
            output_file = scenario_taxis_dir / f"{charger_id}.csv"
            if output_file.exists():
                df = pd.read_csv(output_file, parse_dates=['timestamp'])
                aggregated_taxis.append(df)
        
        if aggregated_taxis:
            agg_df = aggregated_taxis[0][['timestamp']].copy()
            agg_df['power_kw'] = sum(df['power_kw'] for df in aggregated_taxis)
            agg_df['energy_kwh'] = sum(df['energy_kwh'] for df in aggregated_taxis)
            agg_df.to_csv(scenario_taxis_dir / "aggregated_profile.csv", index=False)
    
    print("\n✓ COMPLETADO: 101 escenarios generados")
    print(f"\nUbicación:")
    print(f"  - {base_dir}/annual_datasets/Playa_Motos/0..100/")
    print(f"  - {base_dir}/annual_datasets/Playa_Mototaxis/0..100/")
    print(f"\nTotal: 101 escenarios × 128 chargers × 8760 horas = 113.3M datos")


if __name__ == "__main__":
    generate_101_scenarios()
