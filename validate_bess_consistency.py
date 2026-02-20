#!/usr/bin/env python
"""
Validador de consistencia BESS v5.8 - Verifica que TODA la codebase use 2000 kWh.

Problema histórico: Conflicto entre:
- bess.py: BESS_CAPACITY_KWH_V53 = 2000.0  ✅ CORRECTO
- balance.py: bess_capacity_kwh = 1700.0  ❌ INCORRECTO (FIJO)

Este script verifica que TODO use 2000 kWh consistently.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent

# Patrones a buscar y su valor CORRECTO
PATTERNS = {
    r'bess_capacity_kwh:\s*float\s*=\s*1700\.0': ('bess_capacity_kwh: float = 2000.0', 'Python dataclass field'),
    r'BESS_CAPACITY_KWH_V53\s*=\s*1700\.0': ('BESS_CAPACITY_KWH_V53 = 2000.0', 'BESS constant definition'),
    r'capacity_kwh:\s*float\s*=\s*1700\.0': ('capacity_kwh: float = 2000.0', 'Function parameter default'),
    r'\*\s*17\.0': ('* 20.0', 'SOC conversion factor (1% of BESS)'),
}

# Archivos a revisar
FILES_TO_CHECK = [
    'src/dimensionamiento/oe2/balance_energetico/balance.py',
    'src/dimensionamiento/oe2/disenobess/bess.py',
    'scripts/regenerate_graphics_v57.py',
    'scripts/regenerate_balance_auto.py',
]

def validate_bess_consistency():
    """Valida que toda la codebase use BESS = 2000 kWh."""
    
    print("=" * 80)
    print("VALIDACIÓN DE CONSISTENCIA BESS v5.8")
    print("=" * 80)
    print("\n✓ BESS capacity CORRECTO: 2,000 kWh")
    print("  BESS power:           400 kW")
    print("  BESS DoD:             80%")
    print("  BESS SOC min/max:     20%-100%")
    print("  1% SOC =              20 kWh")
    
    print("\n" + "=" * 80)
    print("REVISANDO ARCHIVOS")
    print("=" * 80)
    
    violations = []
    
    for file_rel in FILES_TO_CHECK:
        filepath = ROOT / file_rel
        if not filepath.exists():
            print(f"\n❌ No encontrado: {file_rel}")
            continue
        
        print(f"\n📄 {file_rel}")
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
        
        found_issues = False
        for pattern, (correct, desc) in PATTERNS.items():
            matches = re.findall(pattern, content)
            if matches:
                # Get line numbers
                for i, line in enumerate(lines, 1):
                    if re.search(pattern, line):
                        violations.append((file_rel, i, line.strip(), desc))
                        print(f"   ⚠️  Line {i}: {desc}")
                        print(f"       Found:   {line.strip()}")
                        print(f"       Change to: {correct}")
                        found_issues = True
        
        if not found_issues:
            print(f"   ✓ OK - No inconsistencies found")
    
    # Summary
    print("\n" + "=" * 80)
    if violations:
        print(f"❌ FOUND {len(violations)} INCONSISTENCIES")
        print("=" * 80)
        print("\nTo fix automatically, run:")
        print("  python scripts/fix_bess_consistency.py")
        return False
    else:
        print("✅ TODAS LAS REFERENCIAS USANDO BESS = 2,000 kWh")
        print("=" * 80)
        return True

if __name__ == "__main__":
    success = validate_bess_consistency()
    exit(0 if success else 1)
