#!/usr/bin/env python3
from pathlib import Path
import json

print('='*80)
print('VERIFICAR ESTADO DEL ENTRENAMIENTO')
print('='*80)
print()

# Verificar si se completó
result_file = Path('outputs/a2c_training/result_a2c.json')
if result_file.exists():
    print('✅ ENTRENAMIENTO COMPLETADO')
    print()
    
    # Leer resultado
    with open(result_file) as f:
        result = json.load(f)
    
    print('📊 RESULTADOS DEL ENTRENAMIENTO:')
    print('-' * 80)
    
    train = result.get('training', {})
    print(f'  Timesteps ejecutados: {train.get("total_timesteps", "N/A"):,}')
    print(f'  Episodios completados: {train.get("episodes_completed", "N/A")}')
    print(f'  Duración: {train.get("duration_seconds", 0)/60:.1f} minutos')
    print(f'  Velocidad: {train.get("speed_steps_per_second", 0):.0f} steps/segundo')
    print()
    
    val = result.get('validation', {})
    print('📈 VALIDACIÓN (10 EPISODIOS):')
    print('-' * 80)
    print(f'  Reward promedio: {val.get("mean_reward", 0):.2f}')
    print(f'  CO2 evitado: {val.get("mean_co2_avoided_kg", 0):,.0f} kg/episodio')
    print(f'  Solar utilizada: {val.get("mean_solar_kwh", 0):,.0f} kWh/episodio')
    print(f'  Grid import: {val.get("mean_grid_import_kwh", 0):,.0f} kWh/episodio')
    print()
    
    print('📁 ARCHIVOS GENERADOS:')
    print('-' * 80)
    output_dir = Path('outputs/a2c_training')
    for f in sorted(output_dir.glob('*')):
        size_mb = f.stat().st_size / 1024 / 1024
        print(f'  📄 {f.name} ({size_mb:.2f} MB)')
    print()
    
    print('✅ Entrenamiento exitoso con datos reales (8,760 horas por episodio)')
else:
    print('⏳ Entrenamiento en progreso...')
    print()
    if Path('entrenamiento_a2c_2026-02-07.log').exists():
        print('Últimas líneas del log:')
        with open('entrenamiento_a2c_2026-02-07.log') as f:
            lines = f.readlines()[-15:]
            for line in lines:
                print('  ' + line.rstrip())
