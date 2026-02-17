#!/usr/bin/env python3
"""Analyze PPO entropy from training outputs"""

import json
import pandas as pd
import numpy as np
from pathlib import Path

def analyze_entropy():
    output_dir = Path('outputs/ppo_training')
    
    # Load result_ppo.json
    result_path = output_dir / 'result_ppo.json'
    with open(result_path, 'r') as f:
        result = json.load(f)
    
    print('📊 METRICS DE ENTRENAMIENTO PPO')
    print('=' * 70)
    print(f'Total Episodes: {result.get("total_episodes", "N/A")}')
    print(f'Total Timesteps: {result.get("total_timesteps", "N/A")}')
    print(f'Mean Reward: {result.get("mean_reward", "N/A")}')
    
    # Try to load entropy history from result
    if 'training_metrics' in result:
        metrics = result['training_metrics']
        print('\nTraining Metrics Available:')
        for key in metrics:
            if 'entropy' in key.lower() or 'loss' in key.lower():
                print(f'  - {key}')
    
    # Analizar PPO específicos
    print('\n' + '=' * 70)
    print('⚙️ CONFIGURACIÓN PPO')
    print('=' * 70)
    if 'hyperparameters' in result:
        hparams = result['hyperparameters']
        important_keys = ['ent_coef', 'learning_rate', 'n_steps', 'batch_size', 'n_epochs', 'gae_lambda', 'gamma']
        for key in important_keys:
            if key in hparams:
                print(f'{key}: {hparams[key]}')
    
    # Load trace for detailed entropy analysis
    trace_path = output_dir / 'trace_ppo.csv'
    if trace_path.exists():
        print('\n' + '=' * 70)
        print('📈 ANÁLISIS DE ENTROPÍA (trace_ppo.csv)')
        print('=' * 70)
        
        df = pd.read_csv(trace_path)
        print(f'Total records: {len(df)}')
        print(f'Columns: {df.columns.tolist()}')
        
        if 'entropy' in df.columns:
            entropy_vals = df['entropy'].dropna()
            print(f'\nEntropy Statistics (n={len(entropy_vals)}):')
            print(f'  Mean:   {entropy_vals.mean():.6f}')
            print(f'  Median: {entropy_vals.median():.6f}')
            print(f'  Min:    {entropy_vals.min():.6f}')
            print(f'  Max:    {entropy_vals.max():.6f}')
            print(f'  Std:    {entropy_vals.std():.6f}')
            print(f'  Q1:     {entropy_vals.quantile(0.25):.6f}')
            print(f'  Q3:     {entropy_vals.quantile(0.75):.6f}')
            
            # Analizar tendencia
            if len(entropy_vals) > 100:
                first_100 = entropy_vals.iloc[:100].mean()
                last_100 = entropy_vals.iloc[-100:].mean()
                print(f'\n  First 100 steps: {first_100:.6f}')
                print(f'  Last 100 steps:  {last_100:.6f}')
                print(f'  Change: {last_100 - first_100:.6f} ({((last_100/first_100 - 1)*100):+.1f}%)')
                
                # Check for collapse
                collapse_threshold = 0.1
                collapse_count = (entropy_vals < collapse_threshold).sum()
                collapse_pct = (collapse_count / len(entropy_vals)) * 100
                print(f'\n⚠️ ANÁLISIS DE COLAPSO:')
                print(f'  Timesteps < 0.1: {collapse_count} ({collapse_pct:.1f}%)')
                if last_100 < 0.5:
                    print(f'  ⚠️ ENTROPÍA BAJA AL FINAL - Posible colapso parcial')
                elif last_100 < 0.1:
                    print(f'  🔴 ENTROPÍA MUY BAJA - Colapso severo de exploración')
                else:
                    print(f'  ✅ Entropía saludable')

if __name__ == '__main__':
    analyze_entropy()
