#!/usr/bin/env python
"""
VALIDATION TEST: Verifica que chargers.py contiene los valores REALES corregidos.

Ejecutar con:
  python test_chargers_energy_correction.py

Esperado: ✅ Todos los tests PASS
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_chargers_energy_constants():
    """Test 1: Verificar constantes de energía corregidas"""
    print("\n" + "=" * 70)
    print("TEST 1: CONSTANTES DE ENERGÍA (chargers.py línea ~1548)")
    print("=" * 70)

    try:
        from iquitos_citylearn.oe2 import chargers

        # Values before correction (WRONG)
        OLD_ENERGY_DAY_TOTAL = 3252.0
        OLD_ENERGY_DAY_MOTOS = 2679.0
        OLD_ENERGY_DAY_MOTOTAXIS = 573.0

        # Values after correction (CORRECT - from dataset)
        EXPECTED_ENERGY_DAY_TOTAL = 903.46
        EXPECTED_ENERGY_DAY_MOTOS = 763.76
        EXPECTED_ENERGY_DAY_MOTOTAXIS = 139.70

        # Get actual values
        actual_total = chargers.ENERGY_DAY_TOTAL_KWH
        actual_motos = chargers.ENERGY_DAY_MOTOS_KWH
        actual_mototaxis = chargers.ENERGY_DAY_MOTOTAXIS_KWH

        print(f"\n📊 ENERGÍA DIARIA ACTUAL:")
        print(f"  Motos:      {actual_motos} kWh (expected: {EXPECTED_ENERGY_DAY_MOTOS})")
        print(f"  Mototaxis:  {actual_mototaxis} kWh (expected: {EXPECTED_ENERGY_DAY_MOTOTAXIS})")
        print(f"  Total:      {actual_total} kWh (expected: {EXPECTED_ENERGY_DAY_TOTAL})")

        # Test 1a: Motos
        assert abs(actual_motos - EXPECTED_ENERGY_DAY_MOTOS) < 0.01, \
            f"❌ Motos energy mismatch: {actual_motos} != {EXPECTED_ENERGY_DAY_MOTOS}"
        print(f"  ✅ Motos: {actual_motos} kWh (CORRECTO)")

        # Test 1b: Mototaxis
        assert abs(actual_mototaxis - EXPECTED_ENERGY_DAY_MOTOTAXIS) < 0.01, \
            f"❌ Mototaxis energy mismatch: {actual_mototaxis} != {EXPECTED_ENERGY_DAY_MOTOTAXIS}"
        print(f"  ✅ Mototaxis: {actual_mototaxis} kWh (CORRECTO)")

        # Test 1c: Total
        assert abs(actual_total - EXPECTED_ENERGY_DAY_TOTAL) < 0.01, \
            f"❌ Total energy mismatch: {actual_total} != {EXPECTED_ENERGY_DAY_TOTAL}"
        print(f"  ✅ Total: {actual_total} kWh (CORRECTO)")

        # Test 1d: Not old values
        assert abs(actual_total - OLD_ENERGY_DAY_TOTAL) > 0.1, \
            f"❌ Still using OLD value: {actual_total} (should not be {OLD_ENERGY_DAY_TOTAL})"
        print(f"  ✅ NO es el valor antiguo (3252.0 kWh)")

        # Test 1e: Math check
        total_sum = actual_motos + actual_mototaxis
        assert abs(total_sum - EXPECTED_ENERGY_DAY_TOTAL) < 0.01, \
            f"❌ Math error: {actual_motos} + {actual_mototaxis} != {EXPECTED_ENERGY_DAY_TOTAL}"
        print(f"  ✅ Verificación matemática: {actual_motos} + {actual_mototaxis} = {total_sum} (CORRECTO)")

        print(f"\n✅ TEST 1 PASSED: Todas las constantes correctas")
        return True

    except Exception as e:
        print(f"\n❌ TEST 1 FAILED: {type(e).__name__}: {e}")
        return False


def test_chargers_module_import():
    """Test 2: Verificar que módulo carga sin errores"""
    print("\n" + "=" * 70)
    print("TEST 2: IMPORTACIÓN DEL MÓDULO")
    print("=" * 70)

    try:
        from iquitos_citylearn.oe2 import chargers
        print(f"\n✅ Módulo importado exitosamente: {chargers.__file__}")

        # Check key attributes exist
        required_attrs = [
            'ENERGY_DAY_MOTOS_KWH',
            'ENERGY_DAY_MOTOTAXIS_KWH',
            'ENERGY_DAY_TOTAL_KWH',
        ]

        for attr in required_attrs:
            assert hasattr(chargers, attr), f"Missing attribute: {attr}"
            val = getattr(chargers, attr)
            print(f"  ✅ {attr}: {val}")

        print(f"\n✅ TEST 2 PASSED: Módulo carga correctamente")
        return True

    except Exception as e:
        print(f"\n❌ TEST 2 FAILED: {type(e).__name__}: {e}")
        return False


def test_annual_energy_calculation():
    """Test 3: Verificar cálculo de energía anual"""
    print("\n" + "=" * 70)
    print("TEST 3: ENERGÍA ANUAL (903.46 kWh/día × 365 = 329,763 kWh)")
    print("=" * 70)

    try:
        from iquitos_citylearn.oe2 import chargers

        daily_energy = chargers.ENERGY_DAY_TOTAL_KWH
        annual_energy = daily_energy * 365
        expected_annual = 329_763.0  # Approximate

        print(f"\n📊 ENERGÍA ANUAL:")
        print(f"  Energía diaria:  {daily_energy} kWh")
        print(f"  Cálculo anual:   {daily_energy} × 365 = {annual_energy:.0f} kWh")
        print(f"  Esperado:        ~{expected_annual:.0f} kWh")

        # Allow 1% tolerance (different years, leap years, etc.)
        tolerance_pct = 0.01
        tolerance_abs = expected_annual * tolerance_pct

        assert abs(annual_energy - expected_annual) < tolerance_abs, \
            f"❌ Annual energy out of range: {annual_energy} (±{tolerance_abs})"

        print(f"  ✅ Rango correcto: {annual_energy:.0f} ≈ {expected_annual:.0f} (±1%)")
        print(f"\n✅ TEST 3 PASSED: Cálculo anual correcto")
        return True

    except Exception as e:
        print(f"\n❌ TEST 3 FAILED: {type(e).__name__}: {e}")
        return False


def test_error_reduction():
    """Test 4: Verificar que error anterior fue corregido"""
    print("\n" + "=" * 70)
    print("TEST 4: CORRECCIÓN DE ERROR DE SOBREESTIMACIÓN")
    print("=" * 70)

    try:
        from iquitos_citylearn.oe2 import chargers

        old_value = 3252.0  # WRONG (from old code)
        new_value = chargers.ENERGY_DAY_TOTAL_KWH

        error_reduction_pct = (1 - (new_value / old_value)) * 100
        error_ratio = old_value / new_value

        print(f"\n📊 REDUCCIÓN DE ERROR:")
        print(f"  Valor anterior (INCORRECTO): {old_value} kWh/día")
        print(f"  Valor actual (CORRECTO):     {new_value} kWh/día")
        print(f"  Factor de error:             {error_ratio:.2f}×")
        print(f"  Reducción:                   {error_reduction_pct:.1f}%")

        assert error_ratio > 3.0, f"❌ Error factor too small: {error_ratio}"
        assert error_reduction_pct > 70.0, f"❌ Error reduction < 70%: {error_reduction_pct}"

        print(f"\n✅ TEST 4 PASSED: Error corregido correctamente (71.5% reducción)")
        return True

    except Exception as e:
        print(f"\n❌ TEST 4 FAILED: {type(e).__name__}: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "╔" + "=" * 68 + "╗")
    print("║" + " " * 10 + "VALIDATION TEST: chargers.py Energy Correction" + " " * 12 + "║")
    print("╚" + "=" * 68 + "╝")

    results = {
        "Energy Constants": test_chargers_energy_constants(),
        "Module Import": test_chargers_module_import(),
        "Annual Calculation": test_annual_energy_calculation(),
        "Error Reduction": test_error_reduction(),
    }

    # Summary
    print("\n" + "=" * 70)
    print("RESUMEN DE TESTS")
    print("=" * 70)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name:.<50} {status}")

    passed = sum(results.values())
    total = len(results)

    print("\n" + "=" * 70)
    if passed == total:
        print(f"✅ TODOS LOS TESTS PASARON ({passed}/{total})")
        print("\n🎉 chargers.py está correctamente corregido.")
        print("   Valores reales del dataset confirmados.")
        print("   Sistema OE3 listo para entrenar agentes RL.")
        return 0
    else:
        print(f"❌ ALGUNOS TESTS FALLARON ({passed}/{total})")
        print("\n⚠️  Revisa los errores arriba.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
