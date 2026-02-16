#!/usr/bin/env python3
import json
from pathlib import Path

sac_path = Path('outputs/sac_training/result_sac.json')
if sac_path.exists():
    with open(sac_path, 'r') as f:
        data = json.load(f)
    
    print('SAC result_sac.json - Contenido relevante:')
    print('='*80)
    
    training = data.get('training', {})
    print('TRAINING:')
    print('  episodes_completed:', training.get('episodes_completed', 'N/A'))
    print('  total_timesteps:', training.get('total_timesteps', 'N/A'))
    print('  duration_seconds:', training.get('duration_seconds', 'N/A'))
    print('  speed_steps_per_second:', training.get('speed_steps_per_second', 'N/A'))
    
    print()
    
    if 'training_evolution' in data:
        te = data['training_evolution']
        rewards = te.get('episode_rewards', [])
        print('TRAINING_EVOLUTION:')
        print('  episode_rewards:', len(rewards), 'elementos')
        if rewards:
            print('    initial:', rewards[0])
            print('    final:', rewards[-1])
    
    print()
    print('VALIDATION:')
    val = data.get('validation', {})
    print('  mean_reward:', val.get('mean_reward', 'N/A'))
    print('  mean_co2_avoided_kg:', val.get('mean_co2_avoided_kg', 'N/A'))
else:
    print('SAC file not found')
