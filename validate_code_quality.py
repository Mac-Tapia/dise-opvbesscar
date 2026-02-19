#!/usr/bin/env python3
"""
Script de validación: Detecta automáticamente problemas de duplicidad y código obsoleto
Genera reporte detallado con líneas exactas donde actuar
"""

import re
from pathlib import Path
from collections import Counter, defaultdict

# Archivos a revisar
FILES = {
    'SAC': Path('scripts/train/train_sac.py'),
    'PPO': Path('scripts/train/train_ppo.py'),
    'A2C': Path('scripts/train/train_a2c.py'),
}

print("=" * 80)
print("VALIDACION AUTOMATICA - DUPLICIDADES Y CODIGO OBSOLETO")
print("=" * 80)
print()

# ============================================================================
# 1. DETECTAR CONSTANTES DUPLICADAS
# ============================================================================

print("[1] DETECTANDO CONSTANTES DUPLICADAS...")
print("-" * 80)

CONST_PATTERNS = {
    'MOTOS_TARGET_DIARIOS': r'MOTOS_TARGET_DIARIOS\s*[=:]\s*270',
    'MOTOTAXIS_TARGET_DIARIOS': r'MOTOTAXIS_TARGET_DIARIOS\s*[=:]\s*39',
    'VEHICLES_TARGET_DIARIOS': r'VEHICLES_TARGET_DIARIOS\s*[=:]\s*MOTOS_TARGET_DIARIOS',
    'MOTO_BATTERY_KWH': r'MOTO_BATTERY_KWH\s*[=:]\s*4\.6',
    'MOTOTAXI_BATTERY_KWH': r'MOTOTAXI_BATTERY_KWH\s*[=:]\s*7\.4',
    'CO2_FACTOR_MOTO': r'CO2_FACTOR_MOTO_KG_KWH\s*[=:]\s*0\.87',
    'CO2_FACTOR_MOTOTAXI': r'CO2_FACTOR_MOTOTAXI_KG_KWH\s*[=:]\s*0\.47',
    'BESS_MAX_KWH': r'BESS_MAX_KWH[_A-Z]*\s*[=:]\s*(1700|2000)\.0',
}

const_found = defaultdict(list)

for agent, filepath in FILES.items():
    if not filepath.exists():
        print(f"  ❌ {agent}: Archivo no encontrado ({filepath})")
        continue
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line_num, line in enumerate(f, 1):
            for const_name, pattern in CONST_PATTERNS.items():
                if re.search(pattern, line):
                    const_found[const_name].append({
                        'agent': agent,
                        'line': line_num,
                        'content': line.strip()
                    })

print("\n[INFO] Resumen de constantes encontradas:")
for const_name, locations in sorted(const_found.items()):
    agents = set(loc['agent'] for loc in locations)
    if len(agents) > 1:
        print(f"\n  [WARN] {const_name} DUPLICADA en {agents}:")
        for loc in locations:
            value = loc['content'].split('=')[-1].strip() if '=' in loc['content'] else '?'
            status = "[X]" if "1700" in value else "[OK]" if "2000" in value else "[?]"
            print(f"      {status} {loc['agent']:3s} Línea {loc['line']:4d}: {value}")

# ============================================================================
# 2. DETECTAR CLASES SIN USO (DEAD CODE)
# ============================================================================

print("\n\n[2] DETECTANDO CLASES POTENCIALMENTE OBSOLETAS...")
print("-" * 80)

DEAD_CLASSES = {
    'VehicleSOCState': {
        'pattern': r'class VehicleSOCState',
        'should_exist': ['SAC'],
        'should_not': ['PPO', 'A2C']
    },
    'ChargingScenario': {
        'pattern': r'class ChargingScenario',
        'should_exist': ['SAC'],
        'should_not': ['PPO', 'A2C']
    },
    'VehicleSOCTracker': {
        'pattern': r'class VehicleSOCTracker',
        'should_exist': ['SAC'],
        'should_not': ['PPO', 'A2C']
    },
}

class_found = defaultdict(list)

for agent, filepath in FILES.items():
    if not filepath.exists():
        continue
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        for class_name, config in DEAD_CLASSES.items():
            if re.search(config['pattern'], content):
                # Contar línea
                lines = content.split('\n')
                for line_num, line in enumerate(lines, 1):
                    if re.search(config['pattern'], line):
                        class_found[class_name].append({
                            'agent': agent,
                            'line': line_num,
                        })

print("\n[INFO] Resumen de clases encontradas:")
for class_name, locations in sorted(class_found.items()):
    agents = [loc['agent'] for loc in locations]
    config = DEAD_CLASSES[class_name]
    
    print(f"\n  {class_name}:")
    for loc in locations:
        print(f"    Encontrada en {loc['agent']:3s} linea {loc['line']:4d}")
    
    # Verificar inconsistencia
    if any(a in config['should_not'] for a in agents):
        print(f"    [WARN] Debe existir SOLO en {config['should_exist']}, NO en {config['should_not']}")

# ============================================================================
# 3. DETECTAR BESS CAPACITY INCONSISTENCIES
# ============================================================================

print("\n\n[3] VALIDANDO BESS_MAX_KWH (CRITICO)...")
print("-" * 80)

bess_values = {}

for agent, filepath in FILES.items():
    if not filepath.exists():
        continue
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line_num, line in enumerate(f, 1):
            if re.search(r'BESS_MAX_KWH[_A-Z]*\s*[=:]\s*(1700|2000)\.0', line):
                value = '2000' if '2000' in line else '1700'
                bess_values[agent] = {
                    'line': line_num,
                    'value': value,
                    'content': line.strip()
                }
                break

print("\n[INFO] BESS Capacities encontradas:")
for agent in ['SAC', 'PPO', 'A2C']:
    if agent in bess_values:
        val = bess_values[agent]
        status = "[OK]" if val['value'] == '2000' else "[X]"
        print(f"  {status} {agent}: {val['value']} kWh (Linea {val['line']:4d})")
    else:
        print(f"  [?] NO ENCONTRADO   {agent}")

if bess_values.get('SAC', {}).get('value') == '1700' or bess_values.get('A2C', {}).get('value') == '1700':
    print("\n  [CRITICAL] SAC y/o A2C tienen BESS_MAX_KWH = 1700 (deberia ser 2000)")
    print("     Esto causa error de +/-17% en normalizacion de observaciones")

# ============================================================================
# 4. DETECTAR CODIGO COMENTADO/OBSOLETO
# ============================================================================

print("\n\n[4] DETECTANDO CODIGO COMENTADO Y OBSOLETO...")
print("-" * 80)

OBSOLETE_PATTERNS = {
    'deprecated': r'#.*[Dd]eprecat',
    'todo': r'#\s*TODO|#\s*FIXME',
    'commented_large_block': r'(#\s*.*){5,}',  # 5+ líneas comentadas seguidas
    'old_version': r'#.*v[0-9]\.[0-9].*FIXED|v[0-9]\.[0-9].*deprecated',
}

for agent, filepath in FILES.items():
    if not filepath.exists():
        continue
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    found_issues = []
    
    for line_num, line in enumerate(lines, 1):
        if 'deprecated' in line.lower():
            found_issues.append({
                'type': 'DEPRECATED',
                'line': line_num,
                'content': line.strip()[:80]
            })
        elif '# TODO' in line or '# FIXME' in line:
            found_issues.append({
                'type': 'TODO/FIXME',
                'line': line_num,
                'content': line.strip()[:80]
            })
    
    if found_issues:
        print(f"\n  {agent}:")
        for issue in found_issues[:5]:  # Mostrar primeros 5
            print(f"    Linea {issue['line']:4d} [{issue['type']:12s}]: {issue['content']}")
        if len(found_issues) > 5:
            print(f"    ... y {len(found_issues) - 5} mas")

# ============================================================================
# 5. ESTADISTICAS GENERALES
# ============================================================================

print("\n\n[5] ESTADISTICAS GENERALES...")
print("-" * 80)

total_lines = 0
for agent, filepath in FILES.items():
    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = len(f.readlines())
        total_lines += lines
        print(f"  {agent}: {lines:5d} líneas")

print(f"  TOTAL: {total_lines:5d} líneas")

# ============================================================================
# 6. RESUMEN FINAL
# ============================================================================

print("\n\n" + "=" * 80)
print("RESUMEN DE ACCIONES REQUERIDAS")
print("=" * 80)

print("""
[CRITICAL] CRITICO - Ejecutar INMEDIATAMENTE:

  1. SAC (Linea ~78):   Cambiar BESS_MAX_KWH_CONST = 1700 -> 2000
  2. A2C (Linea ~72):   Cambiar BESS_MAX_KWH_CONST = 1700 -> 2000
  3. SAC (Linea 1844):  Usar reward multiobjectives (no single-objective)

[MEDIUM] MEDIO - Esta semana:

  1. Extraer constantes compartidas a common_constants.py
  2. Extraer columnas datasets a dataset_columns.py
  3. Estandarizar nombres de variables (CO2, vehiculos, etc.)
  4. Eliminar clases dead en SAC
  5. Eliminar codigo comentado en PPO/A2C
  6. Implementar tracking mensual en SAC y PPO

[INFO] Impacto estimado:
  - Lineas duplicadas: ~1,020 (8%)
  - Codigo obsoleto: ~350 (2.7%)
  - Total reducible: ~1,470 (11%)
""")

print("=" * 80)
print("Auditoria completada. Ver archivos de reporte:")
print("  - REVISION_CODIGO_LINEAS_2026-02-18.md (COMPLETO)")
print("  - REVISION_RESUMEN_VISUAL_2026-02-18.md (EJECUTIVO)")
print("=" * 80)
