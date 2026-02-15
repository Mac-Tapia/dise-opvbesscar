#!/usr/bin/env python3
import subprocess
import time
from pathlib import Path

print('\n' + '='*80)
print('MONITOREO DE ENTRENAMIENTO PPO v5.7')
print('='*80 + '\n')

log_file = Path('entrenamiento_ppo.log')
last_lines = 0
check_count = 0

while True:
    check_count += 1
    timestamp = subprocess.check_output('powershell -c "Get-Date -Format HH:mm:ss"', shell=True).decode().strip()
    
    if log_file.exists():
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        current_lines = len(lines)
        new_lines = current_lines - last_lines
        
        print(f'[{timestamp}] Check #{check_count} - Total lines: {current_lines} (+{new_lines})')
        
        # Mostrar últimas líneas si hay nuevas
        if new_lines > 0:
            for line in lines[-5:]:
                line = line.strip()
                if line and ('Steps' in line or 'CO2' in line or 'EPISODIO' in line or 'Step' in line):
                    print(f'  {line}')
        
        last_lines = current_lines
        
        # Verificar si está completo
        if any('COMPLETADO' in line or 'FINALIZADO' in line for line in lines[-10:]):
            print('\nENTRENAMIENTO FINALIZADO')
            break
    else:
        print(f'[{timestamp}] Check #{check_count} - Esperando log...')
    
    print('')
    time.sleep(30)  # Monitorear cada 30 segundos

print('\n' + '='*80)
print('Archivos: outputs/ppo_training/')
print('Checkpoint: checkpoints/PPO/latest.zip')
print('='*80 + '\n')
