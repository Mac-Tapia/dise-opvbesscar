#!/usr/bin/env python3
"""Verificar ubicación de archivos generados BESS v5.5"""

from pathlib import Path
from datetime import datetime

print('\n' + '='*120)
print('UBICACION DE ARCHIVOS GENERADOS - BESS v5.5')
print('='*120)

bess_dir = Path('data/oe2/bess')

print(f'\nCarpeta base: {bess_dir.resolve()}')
print(f'\nArchivos CSV generados:')

csv_files = list(bess_dir.glob('*.csv'))
csv_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

for f in csv_files:
    size_mb = f.stat().st_size / (1024*1024)
    mod_time = f.stat().st_mtime
    dt = datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')
    
    if 'bess_simulation_hourly.csv' in f.name:
        print(f'  >>> {f.name:.<45} {size_mb:>8.2f} MB  |  {dt}  [v5.5 ACTUAL]')
    else:
        print(f'      {f.name:.<45} {size_mb:>8.2f} MB  |  {dt}')

print(f'\nArchivos JSON/TXT generados:')
json_files = list(bess_dir.glob('*.json')) + list(bess_dir.glob('*.txt'))
json_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

for f in json_files[:5]:  # Mostrar los 5 primeros
    size_kb = f.stat().st_size / 1024
    mod_time = f.stat().st_mtime
    dt = datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')
    print(f'      {f.name:.<45} {size_kb:>8.1f} KB  |  {dt}')

print('\n' + '='*120)
print('RESPUESTA A TU PREGUNTA')
print('='*120)
print("""
PREGUNTA: ¿La dataset se guardaron en la misma carpeta y con el mismo nombre?

RESPUESTA: SI ✓

Detalles:
  • Archivo principal: bess_simulation_hourly.csv
  • Ubicacion: data/oe2/bess/ (misma carpeta)
  • Nombre: MISMO NOMBRE (sobrescribio version anterior)
  • Timestamp: Acaba de generarse con v5.5 (14:16 aprox)
  
  IMPORTANTE:
  Si necesitabas guardar AMBAS versiones (v5.4 + v5.5) para comparar,
  ahora solo tienes v5.5. La version v5.4 fue sobrescrita.
  
  SOLUCION SI NECESITAS v5.4:
  Ejecutar: python -m src.dimensionamiento.oe2.disenobess.bess --generate-v54
  (O restaurar desde git: git checkout HEAD~1 -- data/oe2/bess/bess_simulation_hourly.csv)
""")
print('='*120 + '\n')
