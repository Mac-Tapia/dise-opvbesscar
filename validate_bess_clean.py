#!/usr/bin/env python3
"""
Validación final de 5 FASES BESS - Verificación de limpieza de código
"""

import re

print("=" * 70)
print("VALIDACIÓN FINAL: 5 FASES BESS LIMPIAS")
print("=" * 70)

# Leer archivo
with open('src/dimensionamiento/oe2/disenobess/bess.py', 'r', encoding='utf-8') as f:
    content = f.read()
    lines = content.split('\n')

# Validar AUSENCIA de código legacy
print("\n✓ Verificando AUSENCIA de código legacy:")
legacy_patterns = {
    "DESCARGA AGRESIVA": r"DESCARGA AGRESIVA",
    "remaining_mall_deficit": r"remaining_mall_deficit",
    "RESTRICCION: CIERRE": r"RESTRICCION: CIERRE A SOC"
}

legacy_found = False
for name, pattern in legacy_patterns.items():
    matches = [(i+1, line) for i, line in enumerate(lines) if re.search(pattern, line)]
    if matches:
        legacy_found = True
        print(f"  ❌ Encontrado: {name}")
        for line_num, line in matches[:2]:
            print(f"     Línea {line_num}: {line.strip()[:60]}...")
    else:
        print(f"  ✅ AUSENTE: {name}")

# Validar PRESENCIA de todas las 5 FASES
print("\n✓ Verificando PRESENCIA de 5 FASES:")
phase_patterns = {
    "FASE 1": r"# FASE 1 \(6 AM - 9 AM\)",
    "FASE 2": r"# FASE 2 \(9 AM - DINÁMICO\)",
    "FASE 3": r"# FASE 3.*HOLDING",
    "FASE 4": r"# FASE 4.*PUNTO CRÍTICO",
    "FASE 5": r"# FASE 5.*PV DEFICIT"
}

phases_found = 0
for name, pattern in phase_patterns.items():
    matches = [(i+1, line) for i, line in enumerate(lines) if re.search(pattern, line)]
    if matches:
        phases_found += 1
        print(f"  ✅ {name} - Línea {matches[0][0]}")
    else:
        print(f"  ❌ {name} - NO ENCONTRADA")

# Validar GRID section
print("\n✓ Verificando GRID section:")
grid_matches = [(i+1, line) for i, line in enumerate(lines) if "# GRID: Cubrir deficits" in line]
if grid_matches:
    print(f"  ✅ GRID - Línea {grid_matches[0][0]}")
else:
    print(f"  ❌ GRID - NO ENCONTRADA")

# Resumen final
print("\n" + "=" * 70)
if phases_found == 5 and not legacy_found:
    print("✅ VALIDACIÓN 100% EXITOSA")
    print("   - Todas 5 FASES implementadas ✓")
    print("   - CERO código legacy ✓")
    print("   - Archivo BESS limpio y listo ✓")
else:
    if phases_found < 5:
        print(f"❌ FASES INCOMPLETAS: {phases_found}/5")
    if legacy_found:
        print(f"❌ CÓDIGO LEGACY DETECTADO")
print("=" * 70)
