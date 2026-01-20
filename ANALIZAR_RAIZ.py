#!/usr/bin/env python3
"""
Analizar archivos en la raíz para detectar:
1. Duplicados con código similar pero nombres diferentes
2. Archivos vinculados a baseline, entrenamiento, configuración
"""

import os
import hashlib
from pathlib import Path
from collections import defaultdict
import difflib

ROOT = Path("d:/diseñopvbesscar")

# Palabras clave para identificar archivos a eliminar
BASELINE_KEYWORDS = [
    "baseline", "compare", "comparacion", "comparativa", 
    "benchmark", "base_", "initial_"
]

TRAINING_KEYWORDS = [
    "entrenamiento", "training", "rl_", "agent", "ppo", "a2c", "sac",
    "train_", "learn_", "episode", "reward", "policy"
]

CONFIG_KEYWORDS = [
    "config", "setup", "install", "patch", "monkeypatch",
    "environment", "citylearn", "schema", "charger"
]

CLEANUP_KEYWORDS = [
    "fix_", "cleanup", "clean_", "debug_", "diagnose",
    "audit", "verificar", "verify", "check_", "test_",
    "analisis", "analysis", "generador", "generate"
]

def get_file_hash(filepath):
    """Obtener hash del archivo para comparación"""
    try:
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except:
        return None

def get_code_similarity(file1, file2):
    """Comparar similitud de código entre dos archivos"""
    try:
        with open(file1, 'r', encoding='utf-8', errors='ignore') as f1:
            content1 = f1.readlines()
        with open(file2, 'r', encoding='utf-8', errors='ignore') as f2:
            content2 = f2.readlines()
        
        similarity = difflib.SequenceMatcher(None, content1, content2).ratio()
        return similarity
    except:
        return 0

def identify_file_purpose(filename):
    """Identificar el propósito del archivo"""
    filename_lower = filename.lower()
    
    if any(kw in filename_lower for kw in BASELINE_KEYWORDS):
        return "BASELINE"
    elif any(kw in filename_lower for kw in TRAINING_KEYWORDS):
        return "TRAINING"
    elif any(kw in filename_lower for kw in CONFIG_KEYWORDS):
        return "CONFIG"
    elif any(kw in filename_lower for kw in CLEANUP_KEYWORDS):
        return "CLEANUP"
    else:
        return "OTHER"

def analyze_root_files():
    """Analizar archivos en la raíz"""
    
    print("\n" + "="*80)
    print("ANÁLISIS DE ARCHIVOS EN LA RAÍZ")
    print("="*80)
    
    # Obtener archivos .py
    py_files = list(ROOT.glob("*.py"))
    print(f"\nTotal de archivos .py: {len(py_files)}\n")
    
    # Clasificar por propósito
    files_by_purpose = defaultdict(list)
    for py_file in py_files:
        purpose = identify_file_purpose(py_file.name)
        files_by_purpose[purpose].append(py_file)
    
    # Mostrar clasificación
    print("CLASIFICACIÓN POR PROPÓSITO:")
    print("-" * 80)
    for purpose, files in sorted(files_by_purpose.items()):
        print(f"\n{purpose}: {len(files)} archivos")
        for f in sorted(files):
            print(f"  • {f.name}")
    
    # Detectar duplicados por similitud de código
    print("\n" + "="*80)
    print("DETECCIÓN DE DUPLICADOS POR SIMILARIDAD DE CÓDIGO")
    print("="*80)
    
    duplicates = []
    checked = set()
    
    for i, file1 in enumerate(py_files):
        for file2 in py_files[i+1:]:
            if (file1.name, file2.name) in checked or (file2.name, file1.name) in checked:
                continue
            
            checked.add((file1.name, file2.name))
            
            # Comparar similitud
            similarity = get_code_similarity(file1, file2)
            
            if similarity > 0.75:  # Más de 75% similar = posible duplicado
                duplicates.append({
                    'file1': file1.name,
                    'file2': file2.name,
                    'similarity': similarity,
                    'purpose1': identify_file_purpose(file1.name),
                    'purpose2': identify_file_purpose(file2.name),
                    'size1': file1.stat().st_size,
                    'size2': file2.stat().st_size
                })
    
    if duplicates:
        print(f"\n✓ Se encontraron {len(duplicates)} posibles duplicados:\n")
        for dup in sorted(duplicates, key=lambda x: x['similarity'], reverse=True):
            print(f"Similitud: {dup['similarity']:.1%}")
            print(f"  • {dup['file1']} ({dup['purpose1']}, {dup['size1']/1024:.1f} KB)")
            print(f"  • {dup['file2']} ({dup['purpose2']}, {dup['size2']/1024:.1f} KB)")
            print()
    else:
        print("\n✗ No se encontraron duplicados significativos")
    
    # Generar reporte de limpieza
    print("\n" + "="*80)
    print("REPORTE DE LIMPIEZA RECOMENDADA")
    print("="*80)
    
    to_delete = []
    
    # Archivos de BASELINE
    baseline_files = files_by_purpose.get("BASELINE", [])
    if baseline_files:
        print(f"\n🎯 BASELINE ({len(baseline_files)} archivos a ELIMINAR):")
        for f in sorted(baseline_files):
            print(f"  DELETE: {f.name}")
            to_delete.append(f)
    
    # Archivos de TRAINING
    training_files = files_by_purpose.get("TRAINING", [])
    # Conservar solo scripts principales, eliminar scripts de prueba/debug
    training_to_keep = [
        "train_agents.py", "train_rl_agents.py", "training.py",
        "entrenamiento.py", "rl_training.py"
    ]
    training_delete = [f for f in training_files 
                       if f.name not in training_to_keep and 
                       not f.name.startswith("checkpoint")]
    
    if training_delete:
        print(f"\n🎯 TRAINING ({len(training_delete)} archivos a ELIMINAR):")
        for f in sorted(training_delete):
            print(f"  DELETE: {f.name}")
            to_delete.extend([f])
    
    # Archivos de CONFIG
    config_files = files_by_purpose.get("CONFIG", [])
    config_to_keep = [
        "citylearn_patch.py", "apply_citylearn_patches.py", 
        "construct_schema_with_chargers.py"
    ]
    config_delete = [f for f in config_files if f.name not in config_to_keep]
    
    if config_delete:
        print(f"\n🎯 CONFIG ({len(config_delete)} archivos a ELIMINAR):")
        for f in sorted(config_delete):
            print(f"  DELETE: {f.name}")
            to_delete.append(f)
    
    # Archivos de CLEANUP
    cleanup_files = files_by_purpose.get("CLEANUP", [])
    if cleanup_files:
        print(f"\n🎯 CLEANUP ({len(cleanup_files)} archivos a ELIMINAR):")
        for f in sorted(cleanup_files):
            print(f"  DELETE: {f.name}")
            to_delete.append(f)
    
    # Duplicados
    if duplicates:
        print(f"\n🎯 DUPLICADOS ({len(duplicates)} pares a revisar):")
        for dup in sorted(duplicates, key=lambda x: x['similarity'], reverse=True):
            print(f"  [{dup['similarity']:.0%}] {dup['file1']} ↔ {dup['file2']}")
    
    # Resumen final
    print("\n" + "="*80)
    print(f"RESUMEN: {len(set(to_delete))} archivos para eliminar")
    print("="*80)
    
    return sorted(list(set(to_delete)), key=lambda x: x.name)

if __name__ == "__main__":
    to_delete = analyze_root_files()
    
    print("\n📋 Archivos identificados para eliminar:")
    print("-" * 80)
    for f in to_delete:
        size = f.stat().st_size / 1024
        print(f"  • {f.name} ({size:.1f} KB)")
    
    print(f"\n⚠️  Total: {len(to_delete)} archivos")
    print("\n✅ Ejecutar LIMPIAR_RAIZ.py para proceder con la eliminación")
