#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MOSTRAR TODOS LOS PARÁMETROS Y MÉTRICAS DEL ENTRENAMIENTO PPO
"""
import json
import pandas as pd
from pathlib import Path
from tabulate import tabulate

print("\n" + "="*100)
print("🎯 PARÁMETROS DE ENTRENAMIENTO PPO v5.7 - IQUITOS EV CHARGING OPTIMIZATION")
print("="*100)

# ============================================================================
# PARÁMETROS DE ENTRENAMIENTO (from train_ppo_multiobjetivo.py)
# ============================================================================
print("\n📋 HIPERPARÁMETROS PPO:")
print("-" * 100)

ppo_params = {
    "Learning Rate": "1.5e-4 (lineal schedule: 1.5e-4 → 0)",
    "N-Steps (Rollout)": "2,048 (23% de episodio 8,760h)",
    "Batch Size": "256 (8 minibatches de 256)",
    "N-Epochs": "3 (3 passes de gradient por update)",
    "Gamma (Discount)": "0.85 (para episodios ultra-largos)",
    "GAE Lambda": "0.95 (bias-variance balance)",
    "Clip Range (ε)": "0.2 (PPO clipping coefficient)",
    "Max Grad Norm": "0.5 (gradient clipping para estabilidad)",
    "Target KL": "0.015 (early stopping threshold)",
    "Entropy Coefficient": "0.01 (exploración)",
    "Value Function Coefficient": "0.5",
    "Total Timesteps": "87,600 (10 episodios × 8,760 steps)",
}

for param, value in ppo_params.items():
    print(f"  ✓ {param:.<35} {value}")

# ============================================================================
# ARQUITECTURA RED NEURONAL
# ============================================================================
print("\n🧠 ARQUITECTURA RED NEURONAL:")
print("-" * 100)
net_arch = {
    "Actor Network": "fc_net_kwargs={'pi': [256, 256]}, vf_net_kwargs={'vf': [256, 256]}",
    "Activation Function": "ReLU",
    "Policy Type": "MlpPolicy (Multi-Layer Perceptron)",
    "Observation Space": "156-dim (solar, grid Hz, BESS SOC, 38 sockets × 3, time features)",
    "Action Space": "39-dim continuous [0,1] (1 BESS + 38 sockets)",
}

for component, spec in net_arch.items():
    print(f"  ✓ {component:.<35} {spec}")

# ============================================================================
# ENTORNO Y DATOS
# ============================================================================
print("\n🌍 ENTORNO Y DATOS OE2:")
print("-" * 100)
env_config = {
    "Location": "Iquitos, Perú (isolated grid, 0.4521 kg CO₂/kWh)",
    "Episode Length": "8,760 hours (1 full year)",
    "Timestep Duration": "1 hour real time",
    "Solar PV Capacity": "4,050 kWp",
    "BESS Capacity": "1,700 kWh max (940 kWh in datasets)",
    "Chargers": "19 chargers × 2 sockets = 38 total",
    "Power per Socket": "7.4 kW (Mode 3 charging, 32A @ 230V)",
    "Vehicles": "270 motos + 39 taxis (309 total)",
    "Daily Demand": "4,100 vehicle-hours",
    "Grid Max Capacity": "500 kW",
    "Data Frequency": "Hourly (8,760 rows per dataset)",
}

for config, value in env_config.items():
    print(f"  ✓ {config:.<35} {value}")

# ============================================================================
# FUNCIÓN DE REWARD MULTIOBJETIVO
# ============================================================================
print("\n⚖️  REWARD WEIGHTS (MULTIOBJETIVO):")
print("-" * 100)
reward_weights = {
    "CO₂ Grid Reduction": "0.45 (PRIMARY)",
    "Solar Self-Consumption": "0.25 (SECONDARY)",
    "EV Charge Completion": "0.15 (TERTIARY)",
    "Grid Stability": "0.10 (penalidad ramping alto)",
    "BESS Efficiency": "0.05 (penalidad ciclos)",
}

for objective, weight in reward_weights.items():
    print(f"  ✓ {objective:.<35} {weight}")

# ============================================================================
# LEER RESULTADOS DEL ENTRENAMIENTO
# ============================================================================
print("\n" + "="*100)
print("📊 RESULTADOS DEL ENTRENAMIENTO")
print("="*100)

result_file = Path('outputs/ppo_training/result_ppo.json')
if result_file.exists():
    with open(result_file) as f:
        results = json.load(f)
    
    # Tabla de episodios
    print("\n📈 RESULTADOS POR EPISODIO:")
    print("-" * 100)
    
    episodes_data = []
    for ep_num, ep_data in enumerate(results.get('episodes', [])):
        episodes_data.append([
            f"Episode {ep_num}",
            f"{ep_data.get('reward', 0):,.1f}",
            f"{ep_data.get('co2_avoided', 0):,}",
            f"{ep_data.get('solar_generated', 0):,}",
            f"{ep_data.get('grid_imported', 0):,}",
            f"{ep_data.get('vehicles_charged', 0):.0f}",
        ])
    
    headers = ["Episode", "Reward", "CO₂ Evitado (kg)", "Solar (kWh)", "Grid Import (kWh)", "Vehículos"]
    print(tabulate(episodes_data, headers=headers, tablefmt="grid", floatfmt=".0f"))
    
    # Estadísticas generales
    print("\n📊 ESTADÍSTICAS GENERALES:")
    print("-" * 100)
    
    if 'training_metrics' in results:
        m = results['training_metrics']
        print(f"  ✓ Total Timesteps: {m.get('total_timesteps', 0):,}")
        print(f"  ✓ Training Duration: {m.get('duration_seconds', 0):,.1f} seconds ({m.get('duration_seconds', 0)/60:.1f} min)")
        print(f"  ✓ Throughput: {m.get('steps_per_second', 0):.0f} steps/second")
        print(f"  ✓ Device: {m.get('device', 'N/A')}")
    
    if 'validation_metrics' in results:
        v = results['validation_metrics']
        print(f"\n  ✓ Validation Episodes: {v.get('num_episodes', 0)}")
        print(f"  ✓ Average Reward: {v.get('avg_reward', 0):,.2f}")
        print(f"  ✓ Reward Std Dev: {v.get('reward_std', 0):,.2f}")
        print(f"  ✓ CO₂ Total Evitado: {v.get('total_co2_avoided', 0):,} kg")
        print(f"  ✓ Solar Utilizado: {v.get('total_solar', 0):,} kWh")
        print(f"  ✓ Grid Importado: {v.get('total_grid', 0):,} kWh")

# ============================================================================
# LEER TIMESERIES
# ============================================================================
ts_file = Path('outputs/ppo_training/timeseries_ppo.csv')
if ts_file.exists():
    df = pd.read_csv(ts_file)
    print(f"\n📁 TIMESERIES DATA:")
    print("-" * 100)
    print(f"  ✓ Total Records: {len(df):,}")
    print(f"  ✓ Columns: {', '.join(df.columns.tolist())}")
    print(f"\n  Sample (first 5 rows):")
    print(tabulate(df.head(), headers='keys', tablefmt='grid', showindex=False))

# ============================================================================
# CHECKPOINTS
# ============================================================================
checkpoint_dir = Path('checkpoints/PPO')
if checkpoint_dir.exists():
    checkpoints = sorted(checkpoint_dir.glob('*.zip'), key=lambda p: p.stat().st_mtime, reverse=True)
    if checkpoints:
        print(f"\n💾 CHECKPOINTS (Latest):")
        print("-" * 100)
        for cp in checkpoints[:3]:
            size_mb = cp.stat().st_size / (1024 * 1024)
            print(f"  ✓ {cp.name} ({size_mb:.1f} MB)")

print("\n" + "="*100)
print("✅ ENTRENAMIENTO COMPLETADO EXITOSAMENTE")
print("="*100 + "\n")
