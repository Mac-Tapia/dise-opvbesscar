"""
Valida el período de carga de EV analizando los datos REALES del dataset
"""
import pandas as pd
import numpy as np
from pathlib import Path

# Buscar los archivos de datos
data_dir = Path('d:/diseñopvbesscar/data')

# 1. Buscar perfil horario de demanda EV
print("="*70)
print("BUSCANDO PERFIL HORARIO DE DEMANDA EV EN DATASET")
print("="*70)

# Opción 1: chargers_timeseries.csv (si existe versión pequeña)
charger_ts_path = data_dir / 'iquitos_ev_mall' / 'chargers_timeseries.csv'
if charger_ts_path.exists():
    try:
        print(f"\n✓ Encontrado: {charger_ts_path}")
        print(f"  Tamaño: {charger_ts_path.stat().st_size / 1_000_000:.1f} MB")
        # Intentar leer solo columnas de EV
        df = pd.read_csv(charger_ts_path, nrows=1000)  # Primeras 1000 filas
        print(f"  Columnas: {df.columns.tolist()}")
        print(f"\n  Primeras filas:")
        print(df.head(10))
    except Exception as e:
        print(f"  ✗ Error al leer: {e}")

# Opción 2: Buscar archivo de datos procesados horarios
processed_dir = data_dir / 'processed' / 'hourly'
if processed_dir.exists():
    print(f"\n✓ Directorio de datos horarios procesados:")
    for f in processed_dir.glob('*.csv'):
        print(f"  - {f.name}")

# Opción 3: Ver qué tiene el código de BESS
print("\n" + "="*70)
print("ANALIZANDO CÓDIGO DE BESS PARA EXTRAER PERÍODO EV")
print("="*70)

bess_path = Path('d:/diseñopvbesscar/src/dimensionamiento/oe2/disenobess/bess.py')
with open(bess_path, 'r', encoding='utf-8') as f:
    content = f.read()
    
# Buscar líneas que mencionen ev_parallel_start o período de EV
lines = content.split('\n')
for i, line in enumerate(lines, 1):
    if 'ev_parallel_start' in line.lower() or ('ev' in line.lower() and 'hora' in line.lower()):
        print(f"Línea {i}: {line.strip()}")

# Opción 4: Verificar en función load_ev_demand (si existe)
print("\n" + "="*70)
print("BUSCANDO FUNCIÓN load_ev_demand()  EN BESS.PY")
print("="*70)

if 'def load_ev_demand' in content:
    start_idx = content.find('def load_ev_demand')
    end_idx = content.find('\ndef ', start_idx + 1)
    if end_idx == -1:
        end_idx = start_idx + 2000
    function_code = content[start_idx:end_idx]
    print(function_code[:1500])

print("\n" + "="*70)
print("PRÓXIMO PASO: Necesito acceso a archivo de demanda horaria")
print("Sin los datos reales NO PUEDO VALIDAR períodos de operación")
print("="*70)
