#!/usr/bin/env python3
"""
Analizador de logs PPO: Verifica si el entrenamiento esta procesando datos reales
y que la ejecucion esta tomando el tiempo esperado
"""

import re
from pathlib import Path
from datetime import datetime
import time

def analyze_ppo_logs():
    """Analiza train_ppo_log.txt para diagnosticar la velocidad de entrenamiento"""
    
    print('\n' + '='*100)
    print('[GRAPH] ANALISIS DE LOGS PPO - Diagnostico de Velocidad')
    print('='*100 + '\n')
    
    log_file = Path('train_ppo_log.txt')
    
    if not log_file.exists():
        print('[X] train_ppo_log.txt no encontrado')
        print('   Ejecuta primero: python scripts/train/train_ppo_multiobjetivo.py')
        return
    
    # Leer logs
    with open(log_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f'📋 Total de lineas en log: {len(lines)}')
    
    # Extraer timestamps y eventos clave
    print('\n🔍 EVENTOS CLAVE DETECTADOS:\n')
    
    start_time = None
    end_time = None
    episodes = 0
    timesteps = 0
    updates = 0
    
    # Regex patterns
    patterns = {
        'Solar REAL': r'Solar REAL.*(\d+\.\d+) kWh',
        'Chargers REALES': r'Chargers REALES.*(\d+) sockets.*(\d+) kWh',
        'BESS REAL': r'BESS REAL.*(\d+.\d+)%',
        'Mall REAL': r'Mall REAL.*(\d+) kWh',
        'learn() start': r'training.ppo\.learn\(\)',
        'Episode': r'Episode (\d+).*reward',
        'Update': r'Update (\d+)',
        'mean reward': r'mean reward=(-?\d+.\d+)',
    }
    
    found_solar = False
    found_chargers = False
    found_bess = False
    found_mall = False
    
    for i, line in enumerate(lines):
        # Data loading checks
        if 'Solar REAL' in line and not found_solar:
            print(f'   [OK] {i}: Datos SOLAR cargados')
            print(f'      {line.strip()[:80]}...')
            found_solar = True
        
        if 'Chargers REALES' in line and not found_chargers:
            print(f'   [OK] {i}: Datos CHARGERS cargados')
            print(f'      {line.strip()[:80]}...')
            found_chargers = True
        
        if 'BESS REAL' in line and not found_bess:
            print(f'   [OK] {i}: Datos BESS cargados')
            print(f'      {line.strip()[:80]}...')
            found_bess = True
        
        if 'Mall REAL' in line and not found_mall:
            print(f'   [OK] {i}: Datos MALL cargados')
            print(f'      {line.strip()[:80]}...')
            found_mall = True
        
        # Training progress
        if 'learn(' in line and 'total_timesteps' in line:
            print(f'   🚀 {i}: learn() iniciado')
            
        if '[PPO-POWER-DEBUG]' in line:
            timesteps += 1
        
        if 'Episode' in line and 'mean reward' in line:
            episodes += 1
    
    # Estadisticas finales
    print(f'\n[GRAPH] ESTADISTICAS DE ENTRENAMIENTO:')
    print(f'   Total lineas de log: {len(lines)}')
    print(f'   Timesteps debugger: {timesteps}')
    print(f'   Episodes detectados: {episodes}')
    
    # Duracion estimada
    if start_time and end_time:
        duration = (end_time - start_time).total_seconds()
        print(f'   Duracion: {duration/3600:.2f} horas')
    
    # Analisis final
    print(f'\n🎯 ANALISIS:')
    
    if found_solar and found_chargers and found_bess and found_mall:
        print(f'   [OK] TODOS los datos OE2 fueron cargados')
        print(f'      - Solar: [OK]')
        print(f'      - Chargers: [OK]')
        print(f'      - BESS: [OK]')
        print(f'      - Mall: [OK]')
    else:
        print(f'   [X] ALGUNOS datos NO fueron cargados:')
        print(f'      - Solar: {"[OK]" if found_solar else "[X]"}')
        print(f'      - Chargers: {"[OK]" if found_chargers else "[X]"}')
        print(f'      - BESS: {"[OK]" if found_bess else "[X]"}')
        print(f'      - Mall: {"[OK]" if found_mall else "[X]"}')
    
    if timesteps > 0:
        print(f'   [OK] Timesteps procesados: {timesteps:,}')
    else:
        print(f'   [X] NO se encontraron timesteps procesados')
        print(f'      Significa: Entrenamiento termino sin procesar datos')
    
    if episodes > 0:
        print(f'   [OK] Episodes completados: {episodes}')
    else:
        print(f'   [!]  NO se encontraron episodios completados')
    
    # Mostrar ultimas lineas para ver estado final
    print(f'\n📝 ULTIMAS 10 LINEAS:')
    print('   ' + '-'*96)
    for line in lines[-10:]:
        print(f'   {line.rstrip()[:96]}')
    
    print('\n' + '='*100 + '\n')

if __name__ == '__main__':
    analyze_ppo_logs()
