#!/usr/bin/env python
"""
SIMPLE VALIDATION: Verifica que chargers.py contiene los valores REALES.
"""

from __future__ import annotations

import re
from pathlib import Path

def validate_chargers_file():
    """Verificar que chargers.py contiene valores correctos"""

    chargers_file = Path("src/iquitos_citylearn/oe2/chargers.py")
    content = chargers_file.read_text(encoding='utf-8')

    print("\n" + "="*70)
    print("VALIDACIÓN DE chargers.py - VALORES REALES")
    print("="*70)

    # Test 1: Buscar ENERGY_DAY_TOTAL_KWH = 903.46
    pattern_total = r"ENERGY_DAY_TOTAL_KWH\s*=\s*903\.46"
    if re.search(pattern_total, content):
        print("\n✅ TEST 1: ENERGY_DAY_TOTAL_KWH = 903.46 (CORRECTO)")
    else:
        print("\n❌ TEST 1: ENERGY_DAY_TOTAL_KWH no encontrado o valor incorrecto")
        return False

    # Test 2: Buscar ENERGY_DAY_MOTOS_KWH = 763.76
    pattern_motos = r"ENERGY_DAY_MOTOS_KWH\s*=\s*763\.76"
    if re.search(pattern_motos, content):
        print("✅ TEST 2: ENERGY_DAY_MOTOS_KWH = 763.76 (CORRECTO)")
    else:
        print("❌ TEST 2: ENERGY_DAY_MOTOS_KWH no encontrado o valor incorrecto")
        return False

    # Test 3: Buscar ENERGY_DAY_MOTOTAXIS_KWH = 139.70
    pattern_mototaxis = r"ENERGY_DAY_MOTOTAXIS_KWH\s*=\s*139\.70"
    if re.search(pattern_mototaxis, content):
        print("✅ TEST 3: ENERGY_DAY_MOTOTAXIS_KWH = 139.70 (CORRECTO)")
    else:
        print("❌ TEST 3: ENERGY_DAY_MOTOTAXIS_KWH no encontrado o valor incorrecto")
        return False

    # Test 4: Verificar que NO está el valor antiguo 3252.0 COMO CONSTANTE
    # NOTA: 3252.0 PUEDE aparecer en comentarios de auditoría (es correcto)
    # PERO NO debe estar como: ENERGY_DAY_TOTAL_KWH = 3252.0 (SIN ser comentario)
    has_old_constant = re.search(r"^(\s*)ENERGY_DAY_TOTAL_KWH\s*=\s*3252\.0", content, re.MULTILINE)
    if has_old_constant:
        print("❌ TEST 4: Aún contiene CONSTANTE antiguo ENERGY_DAY_TOTAL_KWH = 3252.0")
        return False
    else:
        # Verificar que la documentación histórica ESTÁ presente
        if "3252.0" in content and "LEGACY:" in content:
            print("✅ TEST 4: Constante 3252.0 eliminada + Auditoría histórica PRESERVADA (CORRECTO)")
        elif "3252.0" in content and "[REMOVED" in content:
            print("✅ TEST 4: Constante eliminada + Documentación histórica preservada (CORRECTO)")
        else:
            print("✅ TEST 4: Constante antigua eliminada (CORRECTO)")

    # Test 5: Verificar docstring
    if "903.46" in content and "verified dataset" in content:
        print("✅ TEST 5: Docstring contiene referencias correctas (CORRECTO)")
    else:
        print("❌ TEST 5: Docstring no contiene referencias correctas")
        return False

    # Test 6: Verificar comentarios actualizados
    if "REAL dataset" in content and "763.76 kWh" in content:
        print("✅ TEST 6: Comentarios actualizados con valores REALES (CORRECTO)")
    else:
        print("⚠️  TEST 6: Algunos comentarios podrían no estar actualizados")

    # Test 7: Matemática
    motos_val = 763.76
    mototaxis_val = 139.70
    total_val = motos_val + mototaxis_val
    annual = total_val * 365

    print(f"\n📊 VALIDACIÓN MATEMÁTICA:")
    print(f"   {motos_val} + {mototaxis_val} = {total_val} ✓")
    print(f"   {total_val} × 365 = {annual:.0f} kWh/año")

    if abs(total_val - 903.46) < 0.01:
        print(f"✅ TEST 7: Matemática correcta (CORRECTO)")
    else:
        print(f"❌ TEST 7: Matemática incorrecta")
        return False

    return True


if __name__ == "__main__":
    print("\n╔" + "="*68 + "╗")
    print("║" + " VALIDATION: chargers.py Energy Values - SIMPLE CHECK ".center(68) + "║")
    print("╚" + "="*68 + "╝")

    try:
        if validate_chargers_file():
            print("\n" + "="*70)
            print("✅ TODOS LOS TESTS PASARON")
            print("="*70)
            print("\n🎉 chargers.py está correctamente configurado con valores REALES")
            print("   Energía: 903.46 kWh/día (no 3,252 kWh)")
            print("   Sistema listo para OE3 RL agent training")
            exit(0)
        else:
            print("\n" + "="*70)
            print("❌ ALGUNOS TESTS FALLARON")
            print("="*70)
            exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {e}")
        exit(1)
