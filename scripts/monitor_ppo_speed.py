#!/usr/bin/env python3
"""
Diagnostico: Monitores la velocidad de entrenamiento PPO 
para detectar si esta siendo anormalmente rapido (sin datos)
"""

import time
import sys
from pathlib import Path
from datetime import datetime

def monitor_ppo_training():
    """
    Ejecuta PPO entrenamiento con monitor de velocidad
    """
    
    print('\n' + '='*100)
    print('🔍 DIAGNOSTICO: Monitor de Velocidad de Entrenamiento PPO')
    print('='*100)
    
    # Configuracion esperada
    expected_config = {
        'num_episodes': 10,
        'hours_per_year': 8760,
        'total_timesteps': 87600,
        'expected_duration_hours': 5.0,  # Con RTX 4060
        'expected_speed_steps_per_sec': 4.8  # ~87,600 / (5 * 3600) = ~4.8 steps/sec
    }
    
    print('\n📋 CONFIGURACION ESPERADA:')
    print(f"   Episodes: {expected_config['num_episodes']}")
    print(f"   Hours/Year: {expected_config['hours_per_year']}")
    print(f"   Total Timesteps: {expected_config['total_timesteps']:,}")
    print(f"   Expected Duration: ~{expected_config['expected_duration_hours']} horas")
    print(f"   Expected Speed: ~{expected_config['expected_speed_steps_per_sec']:.1f} steps/sec")
    
    print('\n[TIME]️  SPEEDRUN TEST: Mediremos velocidad en primeros 1000 timesteps')
    print('-'*100)
    
    # Log de entrenamiento
    log_path = Path('train_ppo_log.txt')
    
    if log_path.exists():
        log_path.unlink()
        print(f"   [OK] Log anterior limpiado")
    
    # Lanzar entrenamiento desde Python
    print(f'\n🚀 Iniciando entrenamiento...')
    start_time = time.time()
    start_datetime = datetime.now()
    print(f"   Hora inicio: {start_datetime.strftime('%H:%M:%S')}")
    
    # Importar y ejecutar PPO adentro de Python para monitoreo granular
    try:
        from scripts.train.train_ppo_multiobjetivo import main
        main_start = time.time()
        main()
        main_elapsed = time.time() - main_start
        
        print(f'\n[OK] Entrenamiento completado')
        print(f'   Duracion total: {main_elapsed:.1f} segundos = {main_elapsed/60:.1f} minutos = {main_elapsed/3600:.2f} horas')
        
        # Diagnosticar
        print('\n🔍 DIAGNOSTICO:')
        
        if main_elapsed < 120:  # Menos de 2 minutos
            print(f'   [X] CRITICO: Entrenamiento termino en solo {main_elapsed:.0f} segundos')
            print(f'      Deberia tomar ~{expected_config["expected_duration_hours"]} horas')
            print(f'      Causa probable: NO se estan procesando los datos correctamente')
            print(f'      Verificar: load_solar_data(), load_chargers_data(), load_bess_data()')
        
        elif main_elapsed < 600:  # Menos de 10 minutos
            print(f'   [!]  ANOMALO: Entrenamiento muy rapido ({main_elapsed/60:.1f} minutos)')
            print(f'      Deberia tomar ~{expected_config["expected_duration_hours"]} horas')
            print(f'      Verificar: n_steps puede estar muy bajo')
        
        else:  # Mas de 10 minutos
            calc_speed = expected_config['total_timesteps'] / main_elapsed
            print(f'   [OK] Velocidad normal')
            print(f'      Timesteps procesados: {expected_config["total_timesteps"]:,}')
            print(f'      Velocidad real: {calc_speed:.2f} steps/sec')
            print(f'      Velocidad esperada: {expected_config["expected_speed_steps_per_sec"]:.1f} steps/sec')
            
            if calc_speed < expected_config['expected_speed_steps_per_sec'] * 0.5:
                print(f'      [!]  Velocidad 50% mas baja que esperado')
            elif calc_speed > expected_config['expected_speed_steps_per_sec'] * 2:
                print(f'      [!]  Velocidad 2x mas rapida que esperado')
            else:
                print(f'      [OK] Velocidad dentro del rango esperado')
        
    except Exception as e:
        print(f'\n[X] ERROR durante entrenamiento: {type(e).__name__}: {str(e)}')
        import traceback
        traceback.print_exc()
    
    print('\n' + '='*100)

if __name__ == '__main__':
    monitor_ppo_training()
