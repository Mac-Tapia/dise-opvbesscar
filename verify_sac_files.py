#!/usr/bin/env python3
"""Verificar archivos técnicos generados por SAC v9.2"""
from pathlib import Path
import json

print("="*70)
print("VERIFICACIÓN SAC v9.2 - Archivos Técnicos Generados")
print("="*70)

output_dir = Path('outputs/sac_training')

if not output_dir.exists():
    print(f"\n✗ DIRECTORIO NO ENCONTRADO: {output_dir}")
    exit(1)

print(f"\n✓ Directorio encontrado: {output_dir}")
print()

# Archivos requeridos
required_files = ['result_sac.json', 'timeseries_sac.csv', 'trace_sac.csv']

print("VERIFICACIÓN DE ARCHIVOS REQUERIDOS:")
print("-" * 70)

all_exist = True
for filename in required_files:
    filepath = output_dir / filename
    
    if filepath.exists():
        size_bytes = filepath.stat().st_size
        size_kb = size_bytes / 1024
        
        # Contar líneas
        with open(filepath) as f:
            lines = len(f.readlines())
        
        print(f"\n✓ {filename}")
        print(f"  - Tamaño: {size_kb:.1f} KB ({size_bytes:,} bytes)")
        print(f"  - Líneas: {lines:,}")
        print(f"  - Ruta: {filepath}")
        
        # Mostrar primeras líneas
        with open(filepath) as f:
            first_lines = [f.readline() for _ in range(2)]
        print(f"  - Primeras líneas:")
        for i, line in enumerate(first_lines, 1):
            print(f"    {i}: {line.strip()[:60]}...")
    else:
        print(f"\n✗ {filename} - NO ENCONTRADO")
        all_exist = False

print()
print("="*70)
print("TODOS LOS ARCHIVOS REQUERIDOS:")
print("-" * 70)

if all_exist:
    print("✓ SÍ - Todos los archivos técnicos fueron generados correctamente")
else:
    print("✗ NO - Faltan algunos archivos. Revisar ejecución de SAC")

print("\nArquivos adicionales en directorio:")
all_files = list(output_dir.glob('*'))
for f in sorted(all_files):
    size_kb = f.stat().st_size / 1024
    print(f"  - {f.name}: {size_kb:.1f} KB")

print("\n" + "="*70)
