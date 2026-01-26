#!/usr/bin/env python3
"""
Script para limpiar checkpoints SAC antiguos.
Mantiene solo checkpoints de hoy (26 ene) y ayer (25 ene).
"""
from __future__ import annotations

from pathlib import Path
import os
from datetime import datetime, timedelta

# Paths
checkpoint_dir = Path("analyses/oe3/training/checkpoints/sac")

# Fechas a mantener
today = datetime(2026, 1, 26)
yesterday = datetime(2026, 1, 25)

# Fechas a eliminar (más antiguas que ayer)
cutoff_date = yesterday.date()

print("=" * 80)
print("LIMPIEZA DE CHECKPOINTS SAC - MANTENER SOLO HOY Y AYER")
print("=" * 80)
print(f"\nFechas a mantener:")
print(f"  • Hoy:   26 Enero 2026")
print(f"  • Ayer:  25 Enero 2026")
print(f"\nFechas a eliminar: Antes de {cutoff_date}")

# Listar archivos
if not checkpoint_dir.exists():
    print(f"\n✗ Directorio no existe: {checkpoint_dir}")
    exit(1)

files_to_delete = []
files_to_keep = []

for file in sorted(checkpoint_dir.glob("*.zip")):
    # Obtener fecha de modificación
    mtime = datetime.fromtimestamp(file.stat().st_mtime)
    file_date = mtime.date()

    # Clasificar
    if file_date >= cutoff_date:
        files_to_keep.append((file, mtime))
    else:
        files_to_delete.append((file, mtime))

print(f"\n{'Archivos a MANTENER:':<40} {len(files_to_keep)}")
print("-" * 80)
for file, mtime in files_to_keep[:10]:  # Mostrar primeros 10
    size_mb = file.stat().st_size / (1024 * 1024)
    print(f"  ✓ {file.name:<35} {mtime.strftime('%Y-%m-%d %H:%M')} | {size_mb:>6.2f} MB")

if len(files_to_keep) > 10:
    print(f"  ... y {len(files_to_keep) - 10} más")

total_keep_size = sum(f.stat().st_size for f, _ in files_to_keep) / (1024 * 1024)

print(f"\n{'Archivos a ELIMINAR:':<40} {len(files_to_delete)}")
print("-" * 80)
for file, mtime in files_to_delete[:10]:  # Mostrar primeros 10
    size_mb = file.stat().st_size / (1024 * 1024)
    print(f"  ✗ {file.name:<35} {mtime.strftime('%Y-%m-%d %H:%M')} | {size_mb:>6.2f} MB")

if len(files_to_delete) > 10:
    print(f"  ... y {len(files_to_delete) - 10} más")

total_delete_size = sum(f.stat().st_size for f, _ in files_to_delete) / (1024 * 1024)

print(f"\n{'RESUMEN:':<40}")
print("-" * 80)
print(f"  Mantener: {len(files_to_keep):>3} archivos | {total_keep_size:>8.2f} MB")
print(f"  Eliminar: {len(files_to_delete):>3} archivos | {total_delete_size:>8.2f} MB")
print(f"  Liberados: {total_delete_size:>7.2f} MB de espacio")

# Confirmar eliminación
if files_to_delete:
    print("\n" + "=" * 80)
    response = input("¿Deseas ELIMINAR los archivos antiguos? (s/n): ").strip().lower()

    if response == 's':
        deleted_count = 0
        for file, _ in files_to_delete:
            try:
                file.unlink()
                deleted_count += 1
                print(f"  ✓ Eliminado: {file.name}")
            except Exception as e:
                print(f"  ✗ Error eliminando {file.name}: {e}")

        print(f"\n{'RESULTADO:':<40}")
        print("-" * 80)
        print(f"  Archivos eliminados: {deleted_count}")
        print(f"  Archivos mantenidos: {len(files_to_keep)}")
        print(f"  Espacio liberado:    {total_delete_size:.2f} MB")
        print(f"\n✓ Limpieza completada exitosamente")
    else:
        print("\n✗ Operación cancelada por el usuario")
else:
    print("\n✓ No hay archivos antiguos para eliminar")

print("\n" + "=" * 80)
