#!/usr/bin/env python3
"""
AUDITORIA COMPLETA DE DATASET_BUILDER_CITYLEARN
Analiza qué archivos se importan realmente en el código.
"""
import os
import re
from pathlib import Path
from collections import defaultdict

# Directorio de análisis
workspace_root = Path(__file__).parent.parent
dataset_builder_dir = workspace_root / "src" / "dataset_builder_citylearn"
scripts_train_dir = workspace_root / "scripts" / "train"
src_agents_dir = workspace_root / "src" / "agents"

# Archivos en dataset_builder_citylearn
builder_files = {f.stem: f for f in dataset_builder_dir.glob("*.py") if f.name != "__pycache__"}

print("=" * 80)
print("🔍 AUDITORIA DE DATASET_BUILDER_CITYLEARN - USO REAL")
print("=" * 80)
print()

# Resultado de búsqueda
usage_map = defaultdict(list)

def analyze_file(filepath):
    """Analizar un archivo para encontrar imports de dataset_builder_citylearn."""
    try:
        content = filepath.read_text(encoding='utf-8', errors='ignore')
        
        # Patrón 1: from src.dataset_builder_citylearn.<module> import
        pattern1 = r'from\s+src\.dataset_builder_citylearn\.(\w+)\s+import'
        # Patrón 2: from dataset_builder_citylearn.<module> import  
        pattern2 = r'from\s+dataset_builder_citylearn\.(\w+)\s+import'
        # Patrón 3: from src.dataset_builder_citylearn import
        pattern3 = r'from\s+src\.dataset_builder_citylearn\s+import'
        # Patrón 4: from dataset_builder_citylearn import
        pattern4 = r'from\s+dataset_builder_citylearn\s+import'
        
        matches1 = re.findall(pattern1, content)
        matches2 = re.findall(pattern2, content)
        
        all_modules = set(matches1 + matches2)
        
        # Buscar imports generales
        has_general1 = bool(re.search(pattern3, content))
        has_general2 = bool(re.search(pattern4, content))
        
        return all_modules, (has_general1 or has_general2)
    except Exception as e:
        print(f"⚠️  Error leyendo {filepath}: {e}")
        return set(), False

# Analizar archivos de entrenamiento
print("📊 TRAINING SCRIPTS (scripts/train/)")
print("-" * 80)
for py_file in sorted(scripts_train_dir.glob("train_*.py")):
    modules, has_general = analyze_file(py_file)
    print(f"\n{py_file.name}:")
    if modules:
        for mod in sorted(modules):
            print(f"  ✓ {mod}.py")
            usage_map[mod].append(py_file.name)
    if has_general:
        print(f"  ✓ __init__.py (general import)")
        usage_map["__init__"].append(py_file.name)
    if not modules and not has_general:
        print(f"  ✗ NO IMPORTS")

# Analizar agentes
print("\n\n📊 AGENTS (src/agents/)")
print("-" * 80)
for py_file in sorted(src_agents_dir.glob("*.py")):
    if py_file.name.startswith("__"):
        continue
    modules, has_general = analyze_file(py_file)
    if modules or has_general:
        print(f"\n{py_file.name}:")
        if modules:
            for mod in sorted(modules):
                print(f"  ✓ {mod}.py")
                usage_map[mod].append(f"agents/{py_file.name}")
        if has_general:
            print(f"  ✓ __init__.py (general import)")
            usage_map["__init__"].append(f"agents/{py_file.name}")

# Analizar otros módulos en src
print("\n\n📊 OTROS MÓDULOS (src/**/*.py)")
print("-" * 80)
for py_file in src_agents_dir.parent.rglob("*.py"):
    if py_file.parent == dataset_builder_dir or py_file.parent == src_agents_dir:
        continue
    if "__pycache__" in str(py_file) or py_file.name == "__init__.py":
        continue
    
    modules, has_general = analyze_file(py_file)
    if modules or has_general:
        rel_path = py_file.relative_to(workspace_root)
        print(f"\n{rel_path}:")
        if modules:
            for mod in sorted(modules):
                print(f"  ✓ {mod}.py")
                usage_map[mod].append(str(rel_path))
        if has_general:
            print(f"  ✓ __init__.py (general import)")
            usage_map["__init__"].append(str(rel_path))

# Resumen
print("\n\n" + "=" * 80)
print("📈 RESUMEN DE USO POR ARCHIVO")
print("=" * 80)
print()

used_files = {}
unused_files = []

for filename in sorted(builder_files.keys()):
    if filename in usage_map:
        count = len(usage_map[filename])
        used_files[filename] = usage_map[filename]
        print(f"✓ {filename:30} - Usado en {count} archivo(s)")
        for use in sorted(usage_map[filename]):
            print(f"  └─ {use}")
    else:
        unused_files.append(filename)
        print(f"✗ {filename:30} - NO USADO")

print("\n\n" + "=" * 80)
print("🎯 CONCLUSIONES")
print("=" * 80)
print()

print(f"📌 ARCHIVOS USADOS: {len(used_files)}")
for fname in sorted(used_files.keys()):
    print(f"   ✓ {fname}")

print(f"\n📌 ARCHIVOS NO USADOS: {len(unused_files)}")
for fname in sorted(unused_files):
    print(f"   ✗ {fname}")

print(f"\n📌 ARCHIVO CONECTA LOS 3 AGENTES (SAC, PPO, A2C):")
# Buscar archivos que aparezcan en train_sac, train_ppo, train_a2c
for fname, uses in sorted(used_files.items()):
    related = [u for u in uses if "train_sac" in u or "train_ppo" in u or "train_a2c" in u]
    if related:
        print(f"   → {fname} (usado en: {', '.join(related)})")

print(f"\n📌 ARCHIVOS SOLO PARA CONSTRUCCIÓN (enriquecimiento/integración):")
for fname, uses in sorted(used_files.items()):
    only_main = all("train" not in u and "agents" not in u and "scripts" not in u for u in uses)
    if only_main and fname != "rewards":
        print(f"   → {fname}")
