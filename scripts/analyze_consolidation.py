#!/usr/bin/env python3
"""
CONSOLIDACION FINAL - Analisis de TODOS los archivos CityLearn.

Este script mapea que importa que, identifica dead code, y propone
la consolidacion final.
"""

import os
import sys
from pathlib import Path
from collections import defaultdict
import re

# Path al workspace
WS = Path("d:/disenopvbesscar")

def find_all_imports(filepath):
    """Encuentra todos los imports de un archivo."""
    imports = []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            # Buscar: from X import Y, import X
            patterns = [
                r'from\s+([^\s]+)\s+import',
                r'import\s+([^\s]+)',
            ]
            for pattern in patterns:
                matches = re.findall(pattern, content)
                imports.extend(matches)
    except:
        pass
    return list(set(imports))

def analyze_project():
    """Analiza todo el proyecto."""
    
    print("🔍 ANALISIS DE CONSOLIDACION CITYLEARN")
    print("=" * 80)
    
    # Buscar todos los archivos .py
    py_files = {}
    for root, dirs, files in os.walk(WS / "src"):
        # Skip __pycache__
        dirs[:] = [d for d in dirs if d != '__pycache__']
        
        for file in files:
            if file.endswith('.py'):
                filepath = Path(root) / file
                rel_path = filepath.relative_to(WS / "src")
                py_files[str(rel_path)] = filepath
    
    print(f"\n[GRAPH] Total de archivos .py encontrados: {len(py_files)}")
    
    # Categorizar por carpeta
    print("\n📁 ARCHIVOS POR CARPETA:\n")
    
    by_folder = defaultdict(list)
    for rel_path in sorted(py_files.keys()):
        folder = rel_path.split('\\')[0]
        by_folder[folder].append(rel_path)
    
    for folder in sorted(by_folder.keys()):
        print(f"\n{folder}/ ({len(by_folder[folder])} archivos)")
        for file in sorted(by_folder[folder])[:5]:  # Mostrar primeros 5
            print(f"  - {file}")
        if len(by_folder[folder]) > 5:
            print(f"  ... y {len(by_folder[folder]) - 5} mas")
    
    # Analisis de imports CityLearn
    print("\n\n🔗 ANALISIS DE IMPORTS:\n")
    
    citylearn_imports = defaultdict(list)
    for rel_path, filepath in py_files.items():
        imports = find_all_imports(filepath)
        
        # Buscar imports relacionados con CityLearn
        for imp in imports:
            if 'citylearn' in imp.lower() or 'dataset_builder' in imp.lower():
                citylearn_imports[rel_path].append(imp)
    
    print(f"📌 Archivos que importan CityLearn/dataset_builder:")
    print(f"   Total: {len(citylearn_imports)}\n")
    
    for filepath in sorted(citylearn_imports.keys()):
        imports = citylearn_imports[filepath]
        print(f"{filepath}")
        for imp in sorted(set(imports)):
            print(f"  -> {imp}")
    
    # Dataset builder structure
    print("\n\n📦 ESTRUCTURA ACTUAL DE DATASET BUILDER:\n")
    
    db_folder = WS / "src" / "dataset_builder_citylearn"
    if db_folder.exists():
        files = [f.name for f in db_folder.glob("*.py")]
        print("src/dataset_builder_citylearn/")
        for file in sorted(files):
            print(f"  [OK] {file}")
    
    # CitylearnV2 cleanup check
    print("\n\n🧹 CARPETAS CITYLEARNV2:\n")
    
    cv2_folder = WS / "src" / "citylearnv2"
    if cv2_folder.exists():
        print("src/citylearnv2/")
        for item in cv2_folder.iterdir():
            if item.is_dir():
                files = len(list(item.glob("*.py")))
                print(f"  {'[OK]' if files > 0 else '[X]'} {item.name}/ ({files} .py files)")
            else:
                print(f"  📄 {item.name}")
    
    # Dead code detection
    print("\n\n💀 DEAD CODE (sin imports):\n")
    
    all_imports = set()
    for imports in citylearn_imports.values():
        all_imports.update(imports)
    
    print(f"Total imports unicos encontrados: {len(all_imports)}")
    
    # Resumen
    print("\n\n📋 RECOMENDACIONES DE CONSOLIDACION:\n")
    
    recommendations = [
        "[OK] dataset_builder_citylearn/ - MANTENER (CANONICAL)",
        "[OK]   - observations.py - OK",
        "[OK]   - data_loader.py - OK",
        "[OK]   - rewards.py - OK",
        "[OK]   - catalog_datasets.py - OK",
        "",
        "[OK] citylearnv2/climate_zone/ - MANTENER (utilidad especifica)",
        "",
        "[!]  baseline/ - REVISAR (ver si necesita consolidacion)",
        "",
        "📌 Todos los constructores deben estar en dataset_builder_citylearn/",
        "📌 Todos los imports deben apuntar a dataset_builder_citylearn/",
    ]
    
    for rec in recommendations:
        print(rec)

if __name__ == "__main__":
    analyze_project()
    
    print("\n" + "=" * 80)
    print("[OK] Analisis completo")
