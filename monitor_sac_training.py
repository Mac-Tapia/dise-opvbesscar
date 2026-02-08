#!/usr/bin/env python
"""Monitor SAC training progress and alert on completion."""
import time
from pathlib import Path
import pandas as pd

def check_sac_progress(max_steps=87600, check_interval=30):
    """Monitor SAC training progress."""
    csv_patterns = [
        Path('outputs/sac_training/trace_sac.csv'),
        Path('outputs/sac_training/timeseries_sac.csv'),
    ]
    
    print('🔄 Iniciando monitor de SAC...')
    print(f'   Intervalo de chequeo: {check_interval} segundos')
    print(f'   Target: {max_steps:,} timesteps')
    print('   ' + '='*70)
    
    started = False
    last_steps = 0
    
    while True:
        try:
            # Buscar CSV
            csv_file = None
            for pattern in csv_patterns:
                if pattern.exists():
                    csv_file = pattern
                    break
            
            if not csv_file:
                if not started:
                    print(f'⏳ Esperando outputs de SAC... ({check_interval}s)')
                    time.sleep(check_interval)
                    continue
                else:
                    print(f'⚠️  CSV no encontrado después de iniciar')
                    time.sleep(check_interval)
                    continue
            
            # Cargar progreso
            df = pd.read_csv(csv_file)
            if len(df) == 0:
                print(f'⏳ CSV existe pero está vacío... esperando')
                time.sleep(check_interval)
                continue
            
            # Si es la primera ejecución, marcar como iniciado
            if not started:
                print(f'✅ SAC iniciado. Monitoreando {csv_file.name}...\n')
                started = True
            
            # Determinar step count (puede ser índice o columna)
            if len(df) > 0:
                current_steps = len(df) if 'step' not in df.columns else df['step'].iloc[-1]
            else:
                current_steps = 0
            
            progress_pct = (current_steps / max_steps) * 100
            
            # Info adicional si está disponible
            extra_info = ''
            if 'reward' in df.columns:
                avg_reward = df['reward'].tail(100).mean()
                extra_info += f' | Reward: {avg_reward:.4f}'
            if 'co2_avoided_indirect_kg' in df.columns:
                total_co2 = df['co2_avoided_indirect_kg'].sum()
                extra_info += f' | CO₂ evitado: {total_co2:,.0f} kg'
            
            # Rate of progress
            if last_steps > 0 and current_steps > last_steps:
                steps_delta = current_steps - last_steps
                print(f'⏳ {current_steps:>7,} / {max_steps:,} pasos ({progress_pct:>5.1f}%){extra_info}')
            else:
                print(f'⏳ {current_steps:>7,} / {max_steps:,} pasos ({progress_pct:>5.1f}%){extra_info}')
            
            last_steps = current_steps
            
            # Chequear si completó
            if current_steps >= max_steps:
                print('\n' + '='*70)
                print(f'✅ SAC ENTRENAMIENTO COMPLETADO')
                print(f'   Timesteps: {current_steps:,} / {max_steps:,}')
                print(f'   Progreso: 100%')
                print(f'   CSV: {csv_file.name}')
                print('='*70 + '\n')
                return True
            
            time.sleep(check_interval)
            
        except (KeyboardInterrupt, EOFError):
            print(f'\n⚠️  Monitor interrumpido por usuario')
            return False
        except Exception as e:
            print(f'⚠️  Error: {e}. Reinicio en {check_interval}s...')
            time.sleep(check_interval)

if __name__ == '__main__':
    check_sac_progress()
