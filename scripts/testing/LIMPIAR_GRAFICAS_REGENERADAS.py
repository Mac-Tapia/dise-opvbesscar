#!/usr/bin/env python3
"""
Limpiar gráficas regeneradas: eliminar duplicados y mantener las nuevas
"""

import hashlib
from pathlib import Path
from collections import defaultdict

PLOTS_FOLDER = Path("analyses/oe3/training/plots")

def get_file_hash(filepath):
    """Calcular hash SHA256"""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def clean_regenerated_graphics():
    """Limpiar gráficas regeneradas"""
    print("\n" + "="*70)
    print("LIMPIEZA DE GRAFICAS REGENERADAS")
    print("="*70)
    
    # Obtener todas las PNG
    all_pngs = list(PLOTS_FOLDER.glob("*.png"))
    print(f"\nGraficas presentes: {len(all_pngs)}")
    
    # Agrupar por nombre base (sin número de versión)
    name_groups = defaultdict(list)
    
    for png in all_pngs:
        name = png.name
        
        # Normalizar nombres para agrupar duplicados
        base_name = name
        if name.startswith("01_A2C"):
            base_name = "A2C_training"
        elif name.startswith("02_A2C"):
            base_name = "A2C_training_updated"
        elif name.startswith("03_PPO"):
            base_name = "PPO_training"
        elif name.startswith("04_PPO"):
            base_name = "PPO_training_updated"
        elif name.startswith("05_SAC"):
            base_name = "SAC_training"
        elif name.startswith("06_SAC"):
            base_name = "SAC_training_updated"
        
        name_groups[base_name].append((name, png))
    
    # Detectar y eliminar duplicados
    to_delete = []
    
    print("\nAnalisis de archivos:")
    for base_name, files in name_groups.items():
        if len(files) > 1:
            print(f"\nDUPLICADOS detectados para {base_name}:")
            
            hashes = {}
            for name, path in files:
                file_hash = get_hash(path)
                if file_hash not in hashes:
                    hashes[file_hash] = []
                hashes[file_hash].append((name, path))
            
            # Mantener la versión nueva (regenerada)
            for file_hash, duplicates in hashes.items():
                if len(duplicates) > 1:
                    # Ordenar por tamaño (archivos nuevos suelen ser más grandes/diferentes)
                    duplicates.sort(key=lambda x: x[1].stat().st_size, reverse=True)
                    keep = duplicates[0]
                    delete = duplicates[1:]
                    
                    print(f"  MANTENER: {keep[0]} ({keep[1].stat().st_size} bytes)")
                    for del_name, del_path in delete:
                        print(f"  ELIMINAR: {del_name} ({del_path.stat().st_size} bytes)")
                        to_delete.append(del_path)
    
    # Eliminar archivos
    if to_delete:
        print(f"\nEliminando {len(to_delete)} archivos duplicados...")
        for path in to_delete:
            try:
                path.unlink()
                print(f"✓ Eliminado: {path.name}")
            except Exception as e:
                print(f"✗ Error al eliminar {path.name}: {e}")
    
    # Verificación final
    final_pngs = list(PLOTS_FOLDER.glob("*.png"))
    print(f"\nGraficas finales: {len(final_pngs)}")
    
    return len(final_pngs)

def get_hash(filepath):
    """Wrapper para get_file_hash"""
    return get_file_hash(filepath)

if __name__ == "__main__":
    count = clean_regenerated_graphics()
    print("\n" + "="*70)
    print(f"LIMPIEZA COMPLETADA: {count} graficas finales")
    print("="*70)
