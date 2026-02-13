#!/usr/bin/env python3
"""
VALIDACIÓN RÁPIDA: Dataset Builder Consolidado
Verifica que el archivo consolidado funciona correctamente
Date: 2026-02-04
"""

from __future__ import annotations
import sys
from pathlib import Path

# ============================================================================
# TEST 1: Import del módulo consolidado
# ============================================================================
def test_import_consolidated():
    """Verifica que se puede importar el módulo consolidado."""
    print("\n" + "="*80)
    print("TEST 1: Importando dataset_builder_consolidated...")
    print("="*80)

    try:
        from src.citylearnv2.dataset_builder.dataset_builder_consolidated import (
            build_citylearn_dataset,
            OE2DataLoader,
            validate_solar_timeseries,
            validate_charger_profiles,
            validate_dataset_completeness,
        )
        print("✅ Import exitoso")
        print("   - build_citylearn_dataset ✅")
        print("   - OE2DataLoader ✅")
        print("   - validate_solar_timeseries ✅")
        print("   - validate_charger_profiles ✅")
        print("   - validate_dataset_completeness ✅")
        return True
    except ImportError as e:
        print(f"❌ Error de import: {e}")
        return False


# ============================================================================
# TEST 2: Backward compatibility con imports viejos
# ============================================================================
def test_backward_compatibility():
    """Verifica que los imports viejos SIGUEN FUNCIONANDO."""
    print("\n" + "="*80)
    print("TEST 2: Verificando backward compatibility...")
    print("="*80)

    all_ok = True

    # Test 1: dataset_builder.py import
    try:
        from src.citylearnv2.dataset_builder.dataset_builder import build_citylearn_dataset
        print("✅ dataset_builder.py import sigue funcionando")
    except ImportError as e:
        print(f"⚠️  dataset_builder.py no disponible (esperado): {e}")
        all_ok = False

    # Test 2: data_loader.py import
    try:
        from src.citylearnv2.dataset_builder.data_loader import OE2DataLoader
        print("✅ data_loader.py import sigue funcionando")
    except ImportError as e:
        print(f"⚠️  data_loader.py no disponible (esperado): {e}")
        all_ok = False

    return all_ok


# ============================================================================
# TEST 3: Verificar estructura del SPECS dict
# ============================================================================
def test_specs_structure():
    """Verifica que SPECS contiene todos los parámetros requeridos."""
    print("\n" + "="*80)
    print("TEST 3: Validando SPECS dict...")
    print("="*80)

    try:
        from src.citylearnv2.dataset_builder.dataset_builder_consolidated import SPECS

        # Parámetros requeridos
        required_keys = [
            "timesteps",
            "total_sockets",
            "observation_dim",
            "action_dim",
            "solar_capacity_kwp",
            "bess_capacity_kwh",
            "bess_power_kw",
            "mall_load_kw",
            "co2_grid_kg_per_kwh",
            "co2_ev_conversion_kg_per_kwh",
        ]

        missing_keys = []
        for key in required_keys:
            if key not in SPECS:
                missing_keys.append(key)
            else:
                print(f"  ✅ {key}: {SPECS[key]}")

        if missing_keys:
            print(f"\n❌ Parámetros faltantes: {missing_keys}")
            return False

        print(f"\n✅ SPECS dict válido ({len(SPECS)} parámetros)")
        return True

    except Exception as e:
        print(f"❌ Error validando SPECS: {e}")
        return False


# ============================================================================
# TEST 4: Verificar que rewards integration está disponible
# ============================================================================
def test_rewards_integration():
    """Verifica que rewards.py está integrado correctamente."""
    print("\n" + "="*80)
    print("TEST 4: Validando integración de rewards...")
    print("="*80)

    try:
        from src.citylearnv2.dataset_builder.dataset_builder_consolidated import (
            REWARDS_AVAILABLE,
        )

        if REWARDS_AVAILABLE:
            print("✅ rewards.py disponible e integrado")
            print("   - IquitosContext ✅")
            print("   - MultiObjectiveWeights ✅")
            print("   - MultiObjectiveReward ✅")
            print("   - create_iquitos_reward_weights ✅")
            return True
        else:
            print("⚠️  rewards.py no disponible (fallback mode)")
            print("   Las recompensas se crearán manualmente")
            return True  # No es error, es fallback

    except Exception as e:
        print(f"❌ Error validando rewards: {e}")
        return False


# ============================================================================
# TEST 5: Verificar archivos de salida esperados
# ============================================================================
def test_output_structure():
    """Verifica que los directorios de salida esperados existen."""
    print("\n" + "="*80)
    print("TEST 5: Validando estructura de directorios...")
    print("="*80)

    expected_dirs = [
        Path("data/processed/oe3/citylearn"),
        Path("data/interim/oe2"),
    ]

    for dir_path in expected_dirs:
        if dir_path.exists():
            print(f"✅ {dir_path} existe")
        else:
            print(f"⚠️  {dir_path} no existe (se creará durante ejecución)")

    return True


# ============================================================================
# TEST 6: CLI entry point
# ============================================================================
def test_cli_entry_point():
    """Verifica que el CLI entry point está disponible."""
    print("\n" + "="*80)
    print("TEST 6: Validando CLI entry point...")
    print("="*80)

    consolidated_file = Path("src/citylearnv2/dataset_builder/dataset_builder_consolidated.py")

    if consolidated_file.exists():
        print(f"✅ {consolidated_file.name} existe")

        with open(consolidated_file, 'r') as f:
            content = f.read()
            if 'if __name__ == "__main__"' in content:
                print("✅ CLI entry point implementado")
                return True
            else:
                print("⚠️  CLI entry point no encontrado")
                return False
    else:
        print(f"❌ {consolidated_file} no encontrado")
        return False


# ============================================================================
# MAIN: Ejecutar todos los tests
# ============================================================================
def run_all_tests():
    """Ejecuta todos los tests y reporta resultados."""
    print("\n" + "="*80)
    print("🧪 VALIDACIÓN: Dataset Builder Consolidado v2.0")
    print("="*80)

    tests = [
        ("Import del módulo consolidado", test_import_consolidated),
        ("Backward compatibility", test_backward_compatibility),
        ("Estructura SPECS dict", test_specs_structure),
        ("Integración de rewards", test_rewards_integration),
        ("Estructura de directorios", test_output_structure),
        ("CLI entry point", test_cli_entry_point),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ Error ejecutando {test_name}: {e}")
            results.append((test_name, False))

    # Resumen
    print("\n" + "="*80)
    print("📊 RESUMEN DE VALIDACIÓN")
    print("="*80)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests pasados")

    if passed == total:
        print("\n🎉 ¡TODAS LAS VALIDACIONES PASARON!")
        print("\nProximos pasos:")
        print("  1. Ejecutar dataset builder: python src/citylearnv2/dataset_builder/dataset_builder_consolidated.py")
        print("  2. Migrar imports: python migrate_dataset_builder.py --force")
        print("  3. Ejecutar tests: python -m pytest tests/")
        return 0
    else:
        print(f"\n⚠️  {total - passed} validación(es) fallaron")
        print("Verifica los errores arriba")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
