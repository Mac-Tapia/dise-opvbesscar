import time
import json
from pathlib import Path

print('='*80)
print('📊 MONITOREO DEL ENTRENAMIENTO A2C')
print('='*80)
print()

checkpoint_dir = Path('checkpoints/A2C')
output_dir = Path('outputs/a2c_training')

# Monitor por 3 minutos
for attempt in range(36):
    checkpoints = sorted(list(checkpoint_dir.glob('*.zip')), key=lambda x: x.stat().st_mtime, reverse=True)
    if checkpoints:
        latest = checkpoints[0]
        name = latest.name
        if '_steps' in name:
            try:
                steps_str = name.split('_')[2].replace('_steps.zip','')
                steps = int(steps_str)
                pct = int(100.0 * steps / 87600)
                print(f'[{time.strftime("%H:%M:%S")}] Checkpoint: {name}')
                print(f'             Progreso: {steps:,} / 87,600 steps ({pct}%)')
            except:
                pass
    
    # Verificar si completó
    if (output_dir / 'result_a2c.json').exists():
        print()
        print('✅ ENTRENAMIENTO COMPLETADO!')
        print()
        
        # Leer resultado
        with open(output_dir / 'result_a2c.json', 'r') as f:
            result = json.load(f)
            training = result.get('training', {})
            validation = result.get('validation', {})
            print('RESUMEN FINAL:')
            print(f'  - Episodios completados: {training.get("episodes_completed", "?")}')
            print(f'  - Duración: {training.get("duration_seconds", "?"):.0f} segundos')
            print(f'  - Velocidad: {training.get("speed_steps_per_second", "?"):.0f} sps')
            print()
            print('VALIDACION (10 episodios):')
            print(f'  - Reward promedio: {validation.get("mean_reward", "?"):.4f}')
            print(f'  - CO2 evitado: {validation.get("mean_co2_avoided_kg", "?"):.0f} kg')
            print(f'  - Solar aprovechado: {validation.get("mean_solar_kwh", "?"):.0f} kWh')
        break
    
    print()
    time.sleep(5)
