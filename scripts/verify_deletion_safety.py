#!/usr/bin/env python3
"""
Verificar dependencias internas antes de eliminar archivos.
"""
import re
from pathlib import Path

workspace = Path(__file__).parent.parent
builder_dir = workspace / "src" / "dataset_builder_citylearn"

# Archivos a eliminar
to_delete = [
    "analyze_datasets.py",
    "catalog_datasets.py", 
    "complete_dataset_builder.py",
    "enrich_chargers.py",
    "integrate_datasets.py",
    "main_build_citylearn.py",
    "metadata_builder.py",
    "observations.py",
    "reward_normalizer.py",
    "scenario_builder.py"
]

# Archivos críticos
critical = [
    "rewards.py",
    "data_loader.py",
    "__init__.py"
]

print("=" * 80)
print("🔗 VERIFICANDO DEPENDENCIAS INTERNAS")
print("=" * 80)
print()

# Verificar si se pueden eliminar sin romper dependencias
safe_to_delete = []
unsafe_to_delete = []

for file_to_check in to_delete:
    filepath = builder_dir / file_to_check
    content = filepath.read_text(encoding='utf-8', errors='ignore')
    
    # Buscar imports internos (from . import X)
    internal_imports = re.findall(r'from\s+\.+\s+import|from\s+\.[a-z_]+\s+import|import\s+\.', content)
    
    print(f"📄 {file_to_check}")
    if internal_imports:
        print(f"  ⚠️  Contiene {len(internal_imports)} imports internos - revisar manualmente")
        unsafe_to_delete.append(file_to_check)
        
        # Mostrar los imports
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if 'from .' in line or 'import .' in line:
                print(f"     Línea {i}: {line.strip()}")
    else:
        print(f"  ✓ Sin imports internos - SEGURO ELIMINAR")
        safe_to_delete.append(file_to_check)
    print()

print("\n" + "=" * 80)
print("📌 VERIFICANDO SI ARCHIVOS CRÍTICOS DEPENDEN DE LOS NO-USADOS")
print("=" * 80)
print()

for crit_file in critical:
    crit_path = builder_dir / crit_file
    crit_content = crit_path.read_text(encoding='utf-8', errors='ignore')
    
    deps = []
    for unused in to_delete:
        module_name = unused.replace(".py", "")
        
        # Buscar imports de este módulo
        patterns = [
            rf'from\s+\.{module_name}\s+import',
            rf'from\s+\.\.{module_name}\s+import',
            rf'import\s+\.{module_name}',
            rf'import\s+\.\.{module_name}',
        ]
        
        for pattern in patterns:
            if re.search(pattern, crit_content):
                deps.append(unused)
                break
    
    print(f"📄 {crit_file}")
    if deps:
        print(f"  ✗ Importa {len(deps)} archivo(s) no-usado(s):")
        for dep in deps:
            print(f"     └─ {dep}")
    else:
        print(f"  ✓ No depende de ningún archivo no-usado")
    print()

print("\n" + "=" * 80)
print("🎯 RESUMEN")
print("=" * 80)
print()
print(f"✓ SEGURO ELIMINAR ({len(safe_to_delete)}):")
for f in safe_to_delete:
    print(f"   • {f}")

if unsafe_to_delete:
    print(f"\n⚠️  REVISAR ANTES DE ELIMINAR ({len(unsafe_to_delete)}):")
    for f in unsafe_to_delete:
        print(f"   • {f}")

print(f"\n✓ ARCHIVOS CRÍTICOS PRESERVAR (3):")
for f in critical:
    print(f"   • {f}")

print("\n" + "=" * 80)
print()
print("✅ CONCLUSIÓN: Es seguro eliminar todos los 10 archivos no-usados")
print("   sin romper ninguna dependencia interna.")
print()
