#!/usr/bin/env python3
"""
Monitor PPO Training - Verificar archivos generados cada 10 minutos
"""
import os
import json
import time
from pathlib import Path

def monitor_ppo_training():
    """Monitorea archivos generados durante entrenamiento PPO"""
    
    checkpoint_dir = Path('checkpoints/PPO')
    analyses_dir = Path('analyses/test')
    output_dir = Path('outputs/ppo_training')
    
    print("=" * 80)
    print("MONITOR DE ENTRENAMIENTO PPO")
    print("=" * 80)
    
    # Crear directorios si no existen
    for d in [checkpoint_dir, analyses_dir, output_dir]:
        d.mkdir(parents=True, exist_ok=True)
    
    files_to_watch = {
        'Checkpoints': [
            'checkpoints/PPO/ppo_*.zip',
            'checkpoints/PPO/TRAINING_CHECKPOINTS_SUMMARY_*.json'
        ],
        'Resultados': [
            'analyses/test/result_PPO.json',
            'analyses/test/timeseries_PPO.csv',
            'analyses/test/trace_PPO.csv'
        ],
        'Outputs': [
            'outputs/ppo_training/*.csv',
            'outputs/ppo_training/*.json'
        ]
    }
    
    iteration = 0
    while True:
        iteration += 1
        print(f"\n[{time.strftime('%H:%M:%S')}] ITERACION #{iteration}")
        print("-" * 80)
        
        checkpoints = list(Path('checkpoints/PPO').glob('ppo_*.zip'))
        result_json = Path('analyses/test/result_PPO.json')
        timeseries_csv = Path('analyses/test/timeseries_PPO.csv')
        trace_csv = Path('analyses/test/trace_PPO.csv')
        
        # Checkpoints
        if checkpoints:
            latest = sorted(checkpoints, key=lambda p: p.stat().st_mtime)[-1]
            size_mb = latest.stat().st_size / (1024**2)
            print(f"✓ Checkpoint mas reciente: {latest.name} ({size_mb:.1f} MB)")
        else:
            print("⏳ Esperando primer checkpoint...")
        
        # Result JSON
        if result_json.exists():
            try:
                with open(result_json) as f:
                    data = json.load(f)
                    if 'summary' in data:
                        print(f"✓ result_PPO.json: {len(data['summary'])} episodios completados")
            except:
                print("⚠ result_PPO.json (formato invalido)")
        else:
            print("⏳ Esperando result_PPO.json...")
        
        # Timeseries CSV
        if timeseries_csv.exists():
            lines = len(timeseries_csv.read_text().splitlines())
            print(f"✓ timeseries_PPO.csv: {lines} lineas")
        else:
            print("⏳ Esperando timeseries_PPO.csv...")
        
        # Trace CSV
        if trace_csv.exists():
            lines = len(trace_csv.read_text().splitlines())
            print(f"✓ trace_PPO.csv: {lines} lineas")
        else:
            print("⏳ Esperando trace_PPO.csv...")
        
        # Verificar si el entrenamiento termino
        if result_json.exists() and timeseries_csv.exists() and trace_csv.exists():
            print("\n" + "=" * 80)
            print("✅ ENTRENAMIENTO PPO COMPLETADO")
            print("=" * 80)
            print("\nArchivos generados:")
            print(f"  - {result_json}")
            print(f"  - {timeseries_csv}")
            print(f"  - {trace_csv}")
            break
        
        # Esperar 10 segundos antes de verificar nuevamente
        print("\n[Verificando en 10 segundos...]\n")
        time.sleep(10)

if __name__ == '__main__':
    monitor_ppo_training()
