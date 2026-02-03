#!/usr/bin/env python
"""
Test de validación: Ejecuta un test rápido de los baselines duales.

Verifica que:
1. Baseline CON solar tiene MENOS CO₂ que baseline SIN solar
2. Generación solar en baseline SIN solar es 0
3. Importación de grid es mayor SIN solar
"""

from __future__ import annotations

from pathlib import Path
import sys
import json

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_dual_baselines():
    """Test que ambos baselines se ejecutan correctamente."""

    baseline_dir = Path(__file__).parent.parent / "outputs" / "baselines"

    if not baseline_dir.exists():
        print("❌ ERROR: Baselines no han sido ejecutados")
        print(f"   Ejecuta: python -m scripts.run_dual_baselines")
        return False

    # Cargar comparación JSON
    comparison_json = baseline_dir / "baseline_comparison.json"
    if not comparison_json.exists():
        print("❌ ERROR: No se encontró baseline_comparison.json")
        return False

    with open(comparison_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    with_solar = data["with_solar"]
    without_solar = data["without_solar"]
    impact = data["impact"]

    print("")
    print("=" * 80)
    print("[TEST] Validando Baselines Duales")
    print("=" * 80)
    print("")

    # TEST 1: CON solar tiene MENOS CO₂ que SIN solar
    print("✓ TEST 1: CO₂ comparison")
    co2_with = with_solar["co2_neto_kg"]
    co2_without = without_solar["co2_neto_kg"]

    if co2_with < co2_without:
        print(f"   ✅ PASS: CON solar ({co2_with:,.0f} kg) < SIN solar ({co2_without:,.0f} kg)")
    else:
        print(f"   ❌ FAIL: CON solar ({co2_with:,.0f} kg) >= SIN solar ({co2_without:,.0f} kg)")
        return False

    print("")

    # TEST 2: Generación solar SIN solar es 0
    print("✓ TEST 2: Solar generation (SIN solar must be 0)")
    pv_without = without_solar["pv_generation_kwh"]

    if pv_without == 0.0:
        print(f"   ✅ PASS: SIN solar tiene 0 kWh generación")
    else:
        print(f"   ❌ FAIL: SIN solar tiene {pv_without:,.0f} kWh (debe ser 0)")
        return False

    print("")

    # TEST 3: Generación solar CON solar > 0
    print("✓ TEST 3: Solar generation (CON solar must be > 0)")
    pv_with = with_solar["pv_generation_kwh"]

    if pv_with > 100_000:
        print(f"   ✅ PASS: CON solar tiene {pv_with:,.0f} kWh generación")
    else:
        print(f"   ❌ FAIL: CON solar tiene {pv_with:,.0f} kWh (debe ser > 100k)")
        return False

    print("")

    # TEST 4: Grid import SIN solar > CON solar
    print("✓ TEST 4: Grid import comparison")
    grid_with = with_solar["grid_import_kwh"]
    grid_without = without_solar["grid_import_kwh"]

    if grid_without > grid_with:
        print(f"   ✅ PASS: SIN solar importa {grid_without:,.0f} kWh > CON solar {grid_with:,.0f} kWh")
        print(f"   ✅ Diferencia: {grid_without - grid_with:,.0f} kWh ({((grid_without-grid_with)/grid_without*100):.1f}%)")
    else:
        print(f"   ❌ FAIL: SIN solar ({grid_without:,.0f}) <= CON solar ({grid_with:,.0f})")
        return False

    print("")

    # TEST 5: Impacto solar es positivo
    print("✓ TEST 5: Solar impact (must be positive)")
    solar_impact = impact["solar_co2_avoided_kg"]

    if solar_impact > 100_000:
        print(f"   ✅ PASS: Solar evita {solar_impact:,.0f} kg CO₂/año")
    else:
        print(f"   ❌ FAIL: Solar impact ({solar_impact:,.0f} kg) es muy bajo")
        return False

    print("")
    print("=" * 80)
    print("[RESULTADO] ✅ TODOS LOS TESTS PASARON")
    print("=" * 80)
    print("")
    print("RESUMEN:")
    print(f"  • Baseline 1 (CON solar): {co2_with:,.0f} kg CO₂/año")
    print(f"  • Baseline 2 (SIN solar): {co2_without:,.0f} kg CO₂/año")
    print(f"  • Impacto solar: {solar_impact:,.0f} kg CO₂/año evitado")
    print(f"  • % de mejora solar: {(solar_impact/co2_without*100):.2f}%")
    print("")

    return True

if __name__ == "__main__":
    try:
        success = test_dual_baselines()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
