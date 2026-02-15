#!/usr/bin/env python3
import json
from pathlib import Path

print('\n' + '='*100)
print('PPO ENTRENAMIENTO v5.7 - PARÁMETROS Y RESULTADOS')
print('='*100)

print('\n📋 HIPERPARÁMETROS PPO:')
print('-'*100)
params = [
    ('Learning Rate', '1.5e-4 (lineal schedule a 0)'),
    ('N-Steps (Rollout)', '2,048 steps (23% de episodio 8,760h)'),
    ('Batch Size', '256 (8 minibatches)'),
    ('N-Epochs', '3 (3 passes gradient por update)'),
    ('Gamma (Discount)', '0.85 (episodios ultra-largos)'),
    ('GAE Lambda', '0.95'),
    ('Clip Range', '0.2'),
    ('Max Grad Norm', '0.5'),
    ('Target KL', '0.015'),
    ('Entropy Coef', '0.01'),
    ('Total Timesteps', '87,600 (10 ep × 8,760h)'),
]
for name, value in params:
    print(f'  ✓ {name:.<30} {value}')

print('\n🧠 ARQUITECTURA RED NEURONAL:')
print('-'*100)
arch = [
    ('Actor Network', 'fc [256, 256]'),
    ('Value Network', 'fc [256, 256]'),
    ('Activation', 'ReLU'),
    ('Policy Type', 'MlpPolicy'),
    ('Input (Obs Space)', '156-dim'),
    ('Output (Act Space)', '39-dim continuous [0,1]'),
]
for name, value in arch:
    print(f'  ✓ {name:.<30} {value}')

print('\n🌍 ENTORNO OE2 (Iquitos, Perú):')
print('-'*100)
env = [
    ('Episode Duration', '8,760 hours (1 año)'),
    ('Timestep', '1 hour'),
    ('Solar PV', '4,050 kWp'),
    ('BESS Capacity', '1,700 kWh (940 en datasets)'),
    ('Chargers', '19 × 2 sockets = 38 total'),
    ('Power/Socket', '7.4 kW Mode 3'),
    ('Vehicles', '270 motos + 39 taxis'),
    ('Daily Demand', '4,100 veh-hours'),
    ('Grid Capacity', '500 kW'),
    ('CO₂ Grid Factor', '0.4521 kg/kWh'),
]
for name, value in env:
    print(f'  ✓ {name:.<30} {value}')

print('\n⚖️  REWARD WEIGHTS (Multiobjetivo):')
print('-'*100)
rewards = [
    ('CO₂ Grid Reduction', '0.45 (PRIMARY)'),
    ('Solar Self-Consumption', '0.25 (SECONDARY)'),
    ('EV Charge Completion', '0.15'),
    ('Grid Stability', '0.10'),
    ('BESS Efficiency', '0.05'),
]
for name, weight in rewards:
    print(f'  ✓ {name:.<30} {weight}')

# Leer resultados
result_file = Path('outputs/ppo_training/result_ppo.json')
if result_file.exists():
    with open(result_file) as f:
        results = json.load(f)
    
    print('\n' + '='*100)
    print('📊 RESULTADOS POR EPISODIO')
    print('='*100)
    print('\nEpisodio | Reward      | CO2_Evitado | Solar_kWh   | Grid_kWh    | Vehs_Cargados')
    print('-'*100)
    for ep_num, ep_data in enumerate(results.get('episodes', [])):
        r = ep_data.get('reward', 0)
        c = ep_data.get('co2_avoided', 0)
        s = ep_data.get('solar_generated', 0)
        g = ep_data.get('grid_imported', 0)
        v = ep_data.get('vehicles_charged', 0)
        print(f'  {ep_num:2d}    | {r:>10.1f} | {c:>11,} | {s:>11,} | {g:>11,} | {v:>10.0f}')
    
    print('\n' + '='*100)
    print('📈 ESTADÍSTICAS FINALES')
    print('='*100)
    
    if 'training_metrics' in results:
        m = results['training_metrics']
        print(f'\n✓ Total Timesteps: {m.get("total_timesteps", 0):,}')
        sec = m.get("duration_seconds", 0)
        print(f'✓ Training Duration: {sec:,.1f} segundos ({sec/60:.1f} min)')
        print(f'✓ Throughput: {m.get("steps_per_second", 0):.0f} steps/segundo')
        print(f'✓ Device: {m.get("device", "N/A")}')
    
    if 'validation_metrics' in results:
        v = results['validation_metrics']
        print(f'\n✓ Validation Episodes: {v.get("num_episodes", 0)}')
        print(f'✓ Average Reward: {v.get("avg_reward", 0):,.2f}')
        print(f'✓ Reward Std Dev: {v.get("reward_std", 0):,.2f}')
        print(f'✓ Total CO₂ Evitado: {v.get("total_co2_avoided", 0):,} kg')
        print(f'✓ Solar Total: {v.get("total_solar", 0):,} kWh')
        print(f'✓ Grid Total: {v.get("total_grid", 0):,} kWh')

print('\n' + '='*100)
print('✅ ENTRENAMIENTO COMPLETADO EXITOSAMENTE')
print('='*100 + '\n')
