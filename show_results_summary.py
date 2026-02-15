#!/usr/bin/env python3
import json

with open('outputs/ppo_training/result_ppo.json') as f:
    data = json.load(f)

print('\n' + '='*100)
print('🎯 RESUMEN COMPLETO - ENTRENAMIENTO PPO v5.7 IQUITOS EV CHARGING')
print('='*100)

# Training info
print('\n📊 INFORMACIÓN GENERAL:')
print('-'*100)
print(f'  Timestamp: {data["timestamp"]}')
print(f'  Ubicación: {data["location"]}')
print(f'  Factor CO2: {data["co2_factor_kg_per_kwh"]} kg CO2/kWh')

# Training metrics
train = data['training']
print('\n📈 ENTRENAMIENTO:')
print('-'*100)
print(f'  Total Timesteps: {train["total_timesteps"]:,}')
print(f'  Episodios: {train["episodes"]}')
print(f'  Duracion: {train["duration_seconds"]:.1f} segundos ({train["duration_seconds"]/60:.1f} min)')
print(f'  Velocidad: {train["speed_steps_per_second"]:.0f} steps/segundo')
print(f'  Device: {train["device"]}')

# Hyperparameters
hyp = train['hyperparameters']
print('\n🔧 HIPERPARÁMETROS:')
print('-'*100)
print(f'  learning_rate: {hyp["learning_rate"]}')
print(f'  n_steps: {hyp["n_steps"]}')
print(f'  batch_size: {hyp["batch_size"]}')
print(f'  n_epochs: {hyp["n_epochs"]}')
print(f'  gamma: {hyp["gamma"]}')
print(f'  gae_lambda: {hyp["gae_lambda"]}')
print(f'  clip_range: {hyp["clip_range"]}')
print(f'  ent_coef: {hyp["ent_coef"]}')
print(f'  vf_coef: {hyp["vf_coef"]}')

# Validation
val = data['validation']
print('\n✓ VALIDACIÓN:')
print('-'*100)
print(f'  Episodes: {val["num_episodes"]}')
print(f'  Mean Reward: {val["mean_reward"]:.2f}')
print(f'  Std Reward: {val["std_reward"]:.2f}')
print(f'  Mean CO2 Avoided: {val["mean_co2_avoided_kg"]:,.0f} kg')
print(f'  Mean Solar: {val["mean_solar_kwh"]:,.0f} kWh')
print(f'  Mean Grid Import: {val["mean_grid_import_kwh"]:,.0f} kWh')

# Training evolution
evo = data['training_evolution']
print('\n📊 EVOLUCIÓN POR EPISODIO:')
print('-'*100)
print('Ep | Reward      | CO2_Grid   | CO2_Avoid_Ind | CO2_Avoid_Dir |  Solar_kWh  | EV_Charge')
print('-'*100)
rewards = evo['episode_rewards']
co2_grid = evo['episode_co2_grid']
co2_indirect = evo['episode_co2_avoided_indirect']
co2_direct = evo['episode_co2_avoided_direct']
solar = evo['episode_solar_kwh']
ev_charge = evo['episode_ev_charging']

for i in range(len(rewards)):
    print(f'{i:2d} | {rewards[i]:>10.0f} | {co2_grid[i]:>10.0f} | {co2_indirect[i]:>13.0f} | {co2_direct[i]:>13.0f} | {solar[i]:>11.0f} | {ev_charge[i]:>9.0f}')

print('\n' + '='*100)
print('✅ ENTRENAMIENTO EXITOSO - TODOS LOS ARCHIVOS GUARDADOS')
print('='*100 + '\n')
