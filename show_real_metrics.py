#!/usr/bin/env python3
import json

with open('outputs/real_agent_comparison/real_metrics.json', encoding='utf-8') as f:
    data = json.load(f)

versions = {"A2C": "7.2", "PPO": "9.3", "SAC": "9.2"}

print('\n' + '='*110)
print('RESUMEN DE DATOS REALES EXTRAIDOS DE LOS CHECKPOINTS')
print('='*110 + '\n')

for agent_name in ['A2C', 'PPO', 'SAC']:
    metrics = data[agent_name]
    
    print(f'{agent_name} v{versions[agent_name]}')
    print('─' * 110)
    print(f'  Checkpoint: {metrics["checkpoint"]}')
    print(f'  Episodes: {metrics["episodes"]}')
    print(f'  Timesteps: {metrics["total_timesteps"]:,}')
    print(f'  Training Time: {metrics["duration_seconds"]:.1f} seconds')
    print(f'  Speed: {metrics["speed_steps_per_sec"]:.1f} steps/sec')
    print(f'  Device: {metrics["device"]}')
    print()
    print(f'  📊 REWARDS:')
    print(f'     Final Reward: {metrics["final_reward"]:.2f}')
    print(f'     Best Reward: {metrics["best_reward"]:.2f}')
    print(f'     Mean Reward: {metrics["mean_reward"]:.2f}')
    print(f'     Convergence: {metrics["convergence_pct"]:.1f}%')
    print()
    print(f'  🌍 CO2 METRICS:')
    print(f'     Final CO₂: {metrics["final_co2"]:,.0f} kg')
    print(f'     Mean CO₂: {metrics["mean_co2"]:,.0f} kg')
    print(f'     CO₂ Reduction: {metrics["co2_reduction_pct"]:.1f}%')
    print()
    print(f'  ⚡ ENERGY:')
    print(f'     Mean Grid Import: {metrics["mean_grid_import"]:,.0f} kWh')
    print(f'     Mean Solar: {metrics["mean_solar"]:,.0f} kWh')
    print()
    print(f'  🔧 HYPERPARAMS:')
    print(f'     LR: {metrics["learning_rate"]}, γ: {metrics["gamma"]}, λ: {metrics["lambda"]}, n_steps: {metrics["n_steps"]}')
    print()

print('='*110)
print('BASELINE (SIN CONTROL): 4,485,286 kg CO₂/año')
print('='*110 + '\n')
