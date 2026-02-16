#!/usr/bin/env python3
"""
RESUMEN CONSOLIDADO: Todos los archivos generados por Entrenamiento PPO
=========================================================================

Este script genera un resumen visual de TODOS los archivos, graficos, datos
y checkpoints generados durante el entrenamiento PPO en:

📁 outputs/ppo_training/
📁 checkpoints/PPO/
📁 train_ppo_log.txt

Creado: 2026-02-14
"""

import json
from pathlib import Path
import pandas as pd

def generate_consolidated_summary():
    """Consolida todos los archivos generados durante entrenamiento PPO"""
    
    print('\n' + '='*100)
    print('[GRAPH] RESUMEN CONSOLIDADO: ARCHIVOS GENERADOS POR ENTRENAMIENTO PPO')
    print('='*100 + '\n')
    
    # Directorios
    outputs_dir = Path('outputs/ppo_training')
    checkpoints_dir = Path('checkpoints/PPO')
    log_file = Path('train_ppo_log.txt')
    
    # ========================================================================
    # 1. OUTPUTS/PPO_TRAINING/ - Resultados completos
    # ========================================================================
    print('📁 1. OUTPUTS Y RESULTADOS (outputs/ppo_training/)')
    print('-'*100 + '\n')
    
    if outputs_dir.exists():
        files = list(outputs_dir.glob('*'))
        
        for i, file in enumerate(sorted(files), 1):
            size_kb = file.stat().st_size / 1024
            print(f"   {i}. {file.name:40s} ({size_kb:10.2f} KB)")
            
            # Descripcion por tipo
            if file.name.endswith('.json'):
                if 'summary' in file.name:
                    print(f"      +- Resumen completo de entrenamiento (hiperparametros, rewards, evolucion)")
                elif 'result' in file.name:
                    print(f"      +- Resultados de validacion (10 episodios deterministicos)")
            
            elif file.name.endswith('.csv'):
                if 'timeseries' in file.name:
                    print(f"      +- Series temporales: metricas por hora (8,760 + 10 episodios)")
                elif 'trace' in file.name:
                    print(f"      +- Trace detallado: paso a paso, todas las observaciones + acciones")
            
            elif file.name.endswith('.png'):
                print(f"      +- Grafico de diagnostico PPO")
        
        print()
    
    # ========================================================================
    # 2. CHECKPOINTS/PPO/ - Modelos entrenados
    # ========================================================================
    print('📁 2. CHECKPOINTS DE MODELOS (checkpoints/PPO/)')
    print('-'*100 + '\n')
    
    if checkpoints_dir.exists():
        checkpoints = list(checkpoints_dir.glob('*.zip'))
        
        for i, ckpt in enumerate(sorted(checkpoints), 1):
            size_mb = ckpt.stat().st_size / (1024 * 1024)
            print(f"   {i}. {ckpt.name:40s} ({size_mb:10.2f} MB)")
            print(f"      +- Modelo PPO en checkpoint (se puede cargar para continuar entrenando)")
        
        print()
    
    # ========================================================================
    # 3. LOG FILE - Registro de entrenamiento
    # ========================================================================
    print('📁 3. DIA RIO DE ENTRENAMIENTO (train_ppo_log.txt)')
    print('-'*100 + '\n')
    
    if log_file.exists():
        size_kb = log_file.stat().st_size / 1024
        print(f"   [OK] {log_file.name:40s} ({size_kb:10.2f} KB)")
        print(f"      +- Registro completo de ejecucion (carga de datos, callbacks, metricas)")
        
        # Contar lineas
        with open(log_file, 'r') as f:
            lines = len(f.readlines())
        print(f"      +- {lines:,} lineas de log\n")
    
    # ========================================================================
    # 4. ANALISIS DE RESULTADOS
    # ========================================================================
    print('[GRAPH] 4. ANALISIS DE RESULTADOS ENTRENAMIENTO')
    print('-'*100 + '\n')
    
    result_file = outputs_dir / 'result_ppo.json'
    if result_file.exists():
        with open(result_file, 'r') as f:
            results = json.load(f)
        
        print('🎯 ENTRENAMIENTO:')
        training = results.get('training', {})
        print(f'   - Total timesteps: {training.get("total_timesteps", 0):,}')
        print(f'   - Episodios: {training.get("episodes", 0)}')
        print(f'   - Duracion: {training.get("duration_seconds", 0):.1f} segundos ({training.get("duration_seconds", 0)/60:.1f} minutos)')
        print(f'   - Velocidad: {training.get("speed_steps_per_second", 0):.1f} steps/sec')
        print(f'   - Dispositivo: {training.get("device", "N/A")}')
        
        print('\n💾 HIPERPARAMETROS:')
        hp = training.get('hyperparameters', {})
        print(f'   - Learning Rate: {hp.get("learning_rate", 0):.4f}')
        print(f'   - n_steps: {hp.get("n_steps", 0)}')
        print(f'   - batch_size: {hp.get("batch_size", 0)}')
        print(f'   - n_epochs: {hp.get("n_epochs", 0)}')
        print(f'   - gamma: {hp.get("gamma", 0)}')
        
        print('\n[OK] VALIDACION (10 episodios deterministicos):')
        validation = results.get('validation', {})
        print(f'   - Reward promedio: {validation.get("mean_reward", 0):.1f} +/- {validation.get("std_reward", 0):.1f}')
        print(f'   - CO2 evitado promedio: {validation.get("mean_co2_avoided_kg", 0):,.0f} kg')
        print(f'   - Solar generado: {validation.get("mean_solar_kwh", 0):,.0f} kWh')
        print(f'   - Grid import: {validation.get("mean_grid_import_kwh", 0):,.0f} kWh')
        
        print('\n[CHART] PROGRESO POR EPISODIO:')
        evolution = results.get('training_evolution', {})
        rewards = evolution.get('episode_rewards', [])
        if rewards:
            print(f'   - Episodio 1: {rewards[0]:,.1f}')
            print(f'   - Episodio 5: {rewards[4] if len(rewards) > 4 else "N/A":,.1f}')
            print(f'   - Episodio 10: {rewards[-1]:,.1f}')
            improvement = (rewards[0] - rewards[-1]) / rewards[0] * 100 if rewards[0] != 0 else 0
            print(f'   - Mejora: {improvement:.1f}% (descenso = mejor optimizacion)')
        
        print()
    
    # ========================================================================
    # 5. ARCHIVOS CSV - Analisis de datos
    # ========================================================================
    print('📋 5. DATOS DETALLADOS (CSV)')
    print('-'*100 + '\n')
    
    timeseries_file = outputs_dir / 'timeseries_ppo.csv'
    if timeseries_file.exists():
        df = pd.read_csv(timeseries_file)
        print(f'   timeseries_ppo.csv:')
        print(f'      - Filas: {len(df):,}')
        print(f'      - Columnas: {len(df.columns)}')
        print(f'      - Columnas: {", ".join(df.columns[:5])}... (y {len(df.columns)-5} mas)')
        print()
    
    trace_file = outputs_dir / 'trace_ppo.csv'
    if trace_file.exists():
        df = pd.read_csv(trace_file)
        print(f'   trace_ppo.csv:')
        print(f'      - Filas: {len(df):,}')
        print(f'      - Columnas: {len(df.columns)}')
        print(f'      - Columnas: {", ".join(df.columns[:5])}... (y {len(df.columns)-5} mas)')
        print()
    
    # ========================================================================
    # 6. GRAFICOS GENERADOS
    # ========================================================================
    print('[GRAPH] 6. GRAFICOS DE DIAGNOSTICO')
    print('-'*100 + '\n')
    
    graphics = [
        ('ppo_dashboard.png', 'Dashboard principal con todas las metricas PPO'),
        ('ppo_kl_divergence.png', 'KL divergence durante entrenamiento'),
        ('ppo_entropy.png', 'Entropia de la politica (exploracion)'),
        ('ppo_clip_fraction.png', 'Fraccion de samples clipeados'),
        ('ppo_value_metrics.png', 'Metricas del value function'),
    ]
    
    for i, (filename, description) in enumerate(graphics, 1):
        filepath = outputs_dir / filename
        if filepath.exists():
            size_kb = filepath.stat().st_size / 1024
            print(f"   {i}. {filename:30s} ({size_kb:8.2f} KB)")
            print(f"      +- {description}")
        else:
            print(f"   {i}. {filename:30s} (no encontrado)")
    
    print()
    
    # ========================================================================
    # 7. RESUMEN FINAL
    # ========================================================================
    print('='*100)
    print('[OK] RESUMEN FINAL')
    print('='*100 + '\n')
    
    print('📦 TODO lo generado esta disponible en:')
    print(f'   📁 outputs/ppo_training/        - Visualizaciones y datos compilados')
    print(f'   📁 checkpoints/PPO/              - Modelos entrenados (pueden reanutarse)')
    print(f'   📄 train_ppo_log.txt             - Registro detallado de ejecucion\n')
    
    print('🚀 Proximos pasos:')
    print('   1. Revisar graficos en outputs/ppo_training/*.png')
    print('   2. Analizar metricas en result_ppo.json')
    print('   3. Cargar modelo: model = PPO.load("checkpoints/PPO/ppo_model_*")')
    print('   4. Continuar entrenamiento: model.learn(total_timesteps=N)')
    print('   5. Comparar con SAC y A2C en outputs/\n')
    
    print('='*100 + '\n')

if __name__ == '__main__':
    generate_consolidated_summary()
