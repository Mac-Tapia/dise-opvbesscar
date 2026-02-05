#!/usr/bin/env python3
"""
PIPELINE MAESTRO - Entrenar SAC, PPO y A2C secuencialmente
v3.0 - Auto-detecta GPU, optimiza configuración, genera reportes comparativos
"""

import sys
import os
from pathlib import Path
import json
import subprocess
from datetime import datetime
import torch

print('='*80)
print('🚀 PVBESSCAR OE3 - PIPELINE MAESTRO DE ENTRENAMIENTO')
print('='*80)
print()

# Auto-detectar GPU
DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'
if DEVICE == 'cuda':
    GPU_NAME = torch.cuda.get_device_name(0)
    GPU_MEMORY = torch.cuda.get_device_properties(0).total_memory / 1e9
    print(f'🔥 GPU DETECTADO: {GPU_NAME}')
    print(f'   Memoria: {GPU_MEMORY:.1f} GB')
else:
    print(f'⚠️  CPU Mode (No GPU disponible)')

print(f'   Dispositivo: {DEVICE.upper()}')
print()

AGENTS = [
    ('SAC', 'train_sac_multiobjetivo.py', '2-3 horas (GPU: 10 min)'),
    ('PPO', 'train_ppo_a2c_multiobjetivo.py', '1-2 horas (GPU: 20 min)'),
    ('A2C', 'train_ppo_a2c_multiobjetivo.py', '1-2 horas (GPU: 20 min)'),
]

RESULTS = {}
OUTPUT_DIR = Path('outputs/training_pipeline')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print('📋 PLAN DE ENTRENAMIENTO:')
for idx, (agent_name, script, duration) in enumerate(AGENTS, 1):
    print(f'  [{idx}] {agent_name}: {script} ({duration})')
print()

start_time = datetime.now()
print(f'⏱️  Inicio: {start_time.strftime("%Y-%m-%d %H:%M:%S")}')
print('='*80)
print()

# Entrenar SContinue ejecutando SAC
try:
    print('[1/3] ENTRENANDO SAC (Soft Actor-Critic)')
    print('-'*80)

    result = subprocess.run(
        ['python', 'train_sac_multiobjetivo.py'],
        cwd=Path('.'),
        capture_output=False
    )

    if result.returncode == 0:
        print('✅ SAC entrenado exitosamente')
        RESULTS['SAC'] = {'status': 'SUCCESS', 'checkpoint': 'checkpoints/SAC/sac_final_model.zip'}
    else:
        print('❌ SAC falló en entrenamiento')
        RESULTS['SAC'] = {'status': 'FAILED'}

except Exception as e:
    print(f'❌ Error en SAC: {e}')
    RESULTS['SAC'] = {'status': 'ERROR', 'error': str(e)}

print()

# Entrenar PPO y A2C (ambos en el mismo script)
try:
    print('[2/3] ENTRENANDO PPO Y A2C')
    print('-'*80)

    result = subprocess.run(
        ['python', 'train_ppo_a2c_multiobjetivo.py'],
        cwd=Path('.'),
        capture_output=False
    )

    if result.returncode == 0:
        print('✅ PPO y A2C entrenados exitosamente')
        RESULTS['PPO'] = {'status': 'SUCCESS', 'checkpoint': 'checkpoints/PPO/ppo_final_model.zip'}
        RESULTS['A2C'] = {'status': 'SUCCESS', 'checkpoint': 'checkpoints/A2C/a2c_final_model.zip'}
    else:
        print('❌ PPO/A2C falló en entrenamiento')
        RESULTS['PPO'] = {'status': 'FAILED'}
        RESULTS['A2C'] = {'status': 'FAILED'}

except Exception as e:
    print(f'❌ Error en PPO/A2C: {e}')
    RESULTS['PPO'] = {'status': 'ERROR', 'error': str(e)}
    RESULTS['A2C'] = {'status': 'ERROR', 'error': str(e)}

print()
print('='*80)

# Resumen final
elapsed = (datetime.now() - start_time).total_seconds()
print(f'⏱️  Tiempo total: {elapsed/3600:.1f} horas ({elapsed/60:.1f} minutos)')
print()

print('📊 RESUMEN DE RESULTADOS:')
print('-'*80)
for agent_name in ['SAC', 'PPO', 'A2C']:
    status = RESULTS.get(agent_name, {}).get('status', 'UNKNOWN')
    icon = '✅' if status == 'SUCCESS' else '❌' if status == 'FAILED' else '⚠️'
    checkpoint = RESULTS.get(agent_name, {}).get('checkpoint', 'N/A')
    print(f'  {icon} {agent_name}: {status} ({checkpoint})')

print()
print('📁 Archivos generados:')
print('  - checkpoints/SAC/sac_final_model.zip')
print('  - checkpoints/PPO/ppo_final_model.zip')
print('  - checkpoints/A2C/a2c_final_model.zip')
print('  - outputs/*/training_metrics.json')
print('  - outputs/*/validation_results.json')
print()

# Guardar reporte
report = {
    'timestamp': datetime.now().isoformat(),
    'device': DEVICE.upper(),
    'total_time_seconds': elapsed,
    'results': RESULTS
}

report_path = OUTPUT_DIR / 'training_report.json'
with open(report_path, 'w') as f:
    json.dump(report, f, indent=2)

print(f'✅ Reporte guardado: {report_path}')
print()
print('='*80)
print('🎉 PIPELINE MAESTRO COMPLETADO')
print('='*80)
