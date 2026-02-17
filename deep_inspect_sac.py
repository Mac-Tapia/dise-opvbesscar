#!/usr/bin/env python3
"""Deep inspection of SAC real results"""

import json
from pathlib import Path

with open('outputs/sac_training/result_sac.json', encoding='utf-8') as f:
    data = json.load(f)

print("\n" + "="*110)
print("SAC v7.1 - INSPECTION PROFUNDA DE RESULTADOS REALES")
print("="*110 + "\n")

print("METADATA:")
print(f"  Agent: {data['agent']}")
print(f"  Version: {data['version']}")
print(f"  Total Timesteps: {data['total_timesteps']:,}")
print(f"  Episodes Completed: {data['episodes_completed']}")
print(f"  Checkpoint: {data['model_path']}")
print(f"  Timestamp: {data['timestamp']}")
print()

# Check for metrics summary
if 'metrics_summary' in data:
    print("METRICS SUMMARY:")
    for key, val in data['metrics_summary'].items():
        if isinstance(val, float):
            print(f"  {key}: {val:,.2f}")
        else:
            print(f"  {key}: {val}")
    print()

# Check for KPI summary
if 'kpi_summary' in data:
    print("KPI SUMMARY:")
    for key, val in data['kpi_summary'].items():
        if isinstance(val, (int, float)):
            print(f"  {key}: {val}")
        else:
            print(f"  {key}: {val}")
    print()

# Episode rewards
ep_rewards = data.get('episode_rewards', [])
print(f"EPISODE REWARDS ({len(ep_rewards)} episodes):")
for i, r in enumerate(ep_rewards, 1):
    print(f"  Episode {i}: {r}")
print()

# Episode CO2
ep_co2 = data.get('episode_co2_grid_kg', [])
print(f"EPISODE CO2 GRID ({len(ep_co2)} episodes):")
for i, c in enumerate(ep_co2, 1):
    print(f"  Episode {i}: {c:,.0f} kg")
print()

# Episode metrics
ep_solar = data.get('episode_solar_kwh', [])
ep_grid = data.get('episode_grid_import_kwh', [])
ep_ev = data.get('episode_ev_charging_kwh', [])
ep_bess = data.get('episode_bess_discharge_kwh', [])

print(f"EPISODE SOLAR ({len(ep_solar)} episodes):")
for i, s in enumerate(ep_solar[:5], 1):
    print(f"  Episode {i}: {s:,.0f} kWh")
if len(ep_solar) > 5:
    print(f"  ... {len(ep_solar) - 5} more episodes")
print()

# Analyze learning
print("\nANALISIS DE APRENDIZAJE:")
if ep_rewards:
    print(f"  First reward: {ep_rewards[0]}")
    print(f"  Last reward: {ep_rewards[-1]}")
    improvement = ((ep_rewards[-1] - ep_rewards[0]) / abs(ep_rewards[0])) * 100 if ep_rewards[0] != 0 else 0
    print(f"  Improvement: {improvement:.1f}%")
    print()

if ep_co2:
    print(f"  Best CO2 (lowest): {min(ep_co2):,.0f} kg")
    print(f"  Worst CO2 (highest): {max(ep_co2):,.0f} kg")
    print(f"  Average CO2: {sum(ep_co2)/len(ep_co2):,.0f} kg")
    reduction = ((4485286 - sum(ep_co2)/len(ep_co2)) / 4485286) * 100
    print(f"  CO2 Reduction vs Baseline: {reduction:.1f}%")
    print()
    
    # Check convergence
    co2_improvement = ((ep_co2[0] - ep_co2[-1]) / ep_co2[0]) * 100
    print(f"  CO2 Improvement (ep1 to ep10): {co2_improvement:.1f}%")

print("="*110 + "\n")
