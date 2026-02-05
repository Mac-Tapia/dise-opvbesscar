#!/usr/bin/env python
"""Verificar si los archivos CSV fueron generados correctamente"""

from pathlib import Path
import pandas as pd

print("=" * 80)
print("VERIFICACIÓN DE ARCHIVOS CSV GENERADOS")
print("=" * 80)

folder = Path("data/oe2/Generacionsolar")
csv_files = list(folder.glob("*.csv"))

print(f"\n✓ Carpeta: {folder.resolve()}")
print(f"✓ Total archivos CSV encontrados: {len(csv_files)}")

if csv_files:
    print("\nARCHIVOS CSV GENERADOS:")
    for f in sorted(csv_files):
        size_kb = f.stat().st_size / 1024
        print(f"  ✓ {f.name:40} ({size_kb:>8.1f} KB)")

        # Leer el archivo y mostrar info
        try:
            df = pd.read_csv(f)
            print(f"      Filas: {len(df):>6} | Columnas: {list(df.columns)[:3]}...")
        except Exception as e:
            print(f"      ERROR al leer: {e}")
else:
    print("\n✗ No se encontraron archivos CSV")

print("\n" + "=" * 80)
