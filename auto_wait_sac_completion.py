#!/usr/bin/env python
"""Wait for SAC training completion and auto-generate final report."""
import time
import subprocess
from pathlib import Path
from datetime import datetime

def wait_for_sac_completion(target_steps=87600, poll_interval=120):
    """Wait for SAC to reach target steps, then generate report."""
    
    log_file = Path('sac_execution_log.txt')
    report_generated = False
    
    print('\n' + '='*80)
    print('🔄 MONITOR SAC - Esperando completación')
    print('='*80)
    print(f'⏰ Iniciado: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    print(f'🎯 Target: {target_steps:,} timesteps')
    print(f'📊 Monitoring: {log_file.name}')
    print(f'📋 Intervalo de chequeo: {poll_interval} segundos')
    print('='*80 + '\n')
    
    while True:
        try:
            # Leer el log y extraer progreso
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # Buscar la última línea de progreso
                lines = content.strip().split('\n')
                progress_line = None
                for line in reversed(lines):
                    if 'Steps:' in line and 'Progreso:' in line:
                        progress_line = line
                        break
                
                if progress_line:
                    # Extraer números
                    import re
                    match = re.search(r'Steps:\s+(\d+(?:,\d+)*)\s+\|\s+Ep:\s+(\d+)\s+\|\s+Progreso:\s+([\d.]+)%', progress_line)
                    if match:
                        steps_str = match.group(1).replace(',', '')
                        current_steps = int(steps_str)
                        episode = int(match.group(2))
                        progress_pct = float(match.group(3))
                        
                        # Mostrar progreso
                        status_bar = '█' * int(progress_pct / 2) + '░' * (50 - int(progress_pct / 2))
                        print(f'[{status_bar}] {current_steps:,} / {target_steps:,} ({progress_pct:.1f}%)')
                        print(f'         Episodio: {episode}, Hora: {datetime.now().strftime("%H:%M:%S")}', end='\r')
                        
                        # Chequear si completó
                        if current_steps >= target_steps:
                            print(f'\n\n✅ SAC COMPLETADO: {current_steps:,} / {target_steps:,} timesteps')
                            print(f'   Hora: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
                            
                            # Generar reporte
                            if not report_generated:
                                print('\n📊 Generando reporte final...\n')
                                try:
                                    result = subprocess.run(['python', 'generate_sac_report.py'], 
                                                            capture_output=False, text=True, timeout=60)
                                    report_generated = True
                                    print('\n✅ Reporte SAC generado exitosamente')
                                except Exception as e:
                                    print(f'\n⚠️  Error generando reporte: {e}')
                            
                            # Generar comparación final
                            print('\n📊 Generando comparación final de todos los algoritmos...\n')
                            try:
                                result = subprocess.run(['python', 'generate_comparison_report.py'],
                                                        capture_output=False, text=True, timeout=60)
                                print('\n✅ Comparación final generada')
                            except Exception as e:
                                print(f'\n⚠️  Error generando comparación: {e}')
                            
                            print('\n' + '='*80)
                            print('🎉 ¡TODOS LOS ENTRENAMIENTOS COMPLETADOS!')
                            print('='*80)
                            return True
                    
            # Esperar antes del próximo chequeo
            time.sleep(poll_interval)
            
        except KeyboardInterrupt:
            print(f'\n\n⚠️  Monitor interrumpido por usuario')
            return False
        except Exception as e:
            print(f'\n⚠️  Error: {e}')
            time.sleep(poll_interval)

if __name__ == '__main__':
    wait_for_sac_completion()
