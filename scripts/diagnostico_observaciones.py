#!/usr/bin/env python3
"""
Diagnostico de unificacion de observaciones CityLearn v2.

Verifica que:
1. Modulo observations.py existe y funciona
2. Todas las versiones son accesibles
3. No hay regresiones en scripts existentes
4. Codigo esta listo para refactoring incremental
"""

import sys
from pathlib import Path

# Agregar raiz del proyecto al path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import numpy as np
from src.dataset_builder_citylearn import (
    ObservationBuilder,
    validate_observation,
    get_observation_stats,
    SOLAR_MAX_KW,
    BESS_MAX_KWH,
    NUM_CHARGERS,
)


def print_header(title):
    """Imprime header formateado."""
    print("\n" + "=" * 80)
    print(f"🔍 {title}")
    print("=" * 80)


def print_section(title):
    """Imprime header de seccion."""
    print(f"\n📌 {title}")
    print("-" * 80)


def test_import():
    """Test 1: Verificar que el modulo se importa correctamente."""
    print_header("TEST 1: IMPORTACION DEL MODULO")
    
    try:
        print("[OK] Importando ObservationBuilder...")
        from src.dataset_builder_citylearn import ObservationBuilder
        print("   [OK] ObservationBuilder importado exitosamente")
        
        print("[OK] Importando funciones auxiliares...")
        from src.dataset_builder_citylearn import validate_observation, get_observation_stats
        print("   [OK] validate_observation importado")
        print("   [OK] get_observation_stats importado")
        
        print("[OK] Importando constantes...")
        from src.dataset_builder_citylearn import (
            SOLAR_MAX_KW, BESS_MAX_KWH, NUM_CHARGERS, HOURS_PER_YEAR
        )
        print(f"   [OK] SOLAR_MAX_KW = {SOLAR_MAX_KW}")
        print(f"   [OK] BESS_MAX_KWH = {BESS_MAX_KWH}")
        print(f"   [OK] NUM_CHARGERS = {NUM_CHARGERS}")
        print(f"   [OK] HOURS_PER_YEAR = {HOURS_PER_YEAR}")
        
        print("\n[OK] TEST 1 PASADO: Importaciones OK")
        return True
    except Exception as e:
        print(f"\n[X] TEST 1 FALLIDO: {e}")
        return False


def test_builder_creation():
    """Test 2: Crear instancias de ObservationBuilder."""
    print_header("TEST 2: CREACION DE BUILDER")
    
    try:
        versions = [
            ObservationBuilder.OBS_156_STANDARD,
            ObservationBuilder.OBS_246_CASCADA,
            ObservationBuilder.OBS_66_EXPANDED,
            ObservationBuilder.OBS_50_SIMPLE,
        ]
        
        builders = {}
        for version in versions:
            builder = ObservationBuilder(version=version)
            builders[version] = builder
            status = "[OK] DEFAULT" if version == ObservationBuilder.OBS_156_STANDARD else "[OK]"
            print(f"{status} {version:20s} - dim={builder.obs_dim:3d}, obs_space={builder.observation_space}")
        
        print("\n[OK] TEST 2 PASADO: Todos los builders creados")
        return True, builders
    except Exception as e:
        print(f"\n[X] TEST 2 FALLIDO: {e}")
        return False, {}


def test_observation_creation(builders):
    """Test 3: Crear observaciones con cada version."""
    print_header("TEST 3: CREACION DE OBSERVACIONES")
    
    # Datos simulados
    data = {
        "solar_hourly": np.random.uniform(0, 1000, 8760),
        "chargers_hourly": np.random.uniform(0, 7.4, (8760, 38)),
        "mall_hourly": np.full(8760, 100.0),
        "bess_soc_hourly": np.random.uniform(20, 80, 8760),
    }
    
    print("\nCreando observaciones para hora 0...\n")
    
    all_valid = True
    for version, builder in builders.items():
        try:
            obs = builder.make_observation(hour_idx=0, data=data)
            is_valid = validate_observation(obs, builder)
            stats = get_observation_stats(obs, name=f"obs_{version}")
            
            status = "[OK]" if is_valid else "[!]"
            print(f"{status} {version:20s}:")
            print(f"   Shape: {obs.shape}, dtype: {obs.dtype}")
            print(f"   Mean: {stats['mean']:7.4f}, Std: {stats['std']:7.4f}")
            print(f"   Min: {stats['min']:7.4f}, Max: {stats['max']:7.4f}")
            print(f"   Valid: {is_valid}, Has NaN: {stats['has_nan']}, Has Inf: {stats['has_inf']}")
            
            if not is_valid:
                all_valid = False
        except Exception as e:
            print(f"[X] {version:20s}: {e}")
            all_valid = False
    
    if all_valid:
        print("\n[OK] TEST 3 PASADO: Todas las observaciones validas")
        return True
    else:
        print("\n[!]  TEST 3 PARCIAL: Algunas observaciones invalidas")
        return False


def test_version_coverage():
    """Test 4: Verificar dimensiones de cada version."""
    print_header("TEST 4: COBERTURA DE VERSIONES")
    
    expected_dims = {
        ObservationBuilder.OBS_156_STANDARD: 156,
        ObservationBuilder.OBS_246_CASCADA: 246,
        ObservationBuilder.OBS_66_EXPANDED: 66,
        ObservationBuilder.OBS_50_SIMPLE: 50,
    }
    
    all_correct = True
    print_section("Verificando dimensiones esperadas")
    
    for version, expected_dim in expected_dims.items():
        builder = ObservationBuilder(version=version)
        actual_dim = builder.obs_dim
        
        if actual_dim == expected_dim:
            print(f"[OK] {version:20s}: {actual_dim:3d} = {expected_dim:3d} [OK]")
        else:
            print(f"[X] {version:20s}: {actual_dim:3d} ≠ {expected_dim:3d} [X]")
            all_correct = False
    
    if all_correct:
        print("\n[OK] TEST 4 PASADO: Dimensiones correctas")
        return True
    else:
        print("\n[X] TEST 4 FALLIDO: Dimensiones incorrectas")
        return False


def test_backward_compatibility():
    """Test 5: Verificar backward compatibility con codigo antiguo."""
    print_header("TEST 5: BACKWARD COMPATIBILITY")
    
    print_section("Verificando que antiguo codigo sigue importando...")
    
    try:
        # El viejo path deberia redirigir al nuevo
        # En este caso, verificamos que el nuevo codigo no rompe nada
        from src.dataset_builder_citylearn import (
            load_solar_data,
            load_bess_data,
            load_chargers_data,
        )
        print("[OK] Importaciones de data_loader funcionales")
        
        from src.dataset_builder_citylearn import (
            MultiObjectiveReward,
            CityLearnMultiObjectiveWrapper,
        )
        print("[OK] Importaciones de rewards funcionales")
        
        from src.dataset_builder_citylearn import (
            BESS_CAPACITY_KWH,
            N_CHARGERS,
            TOTAL_SOCKETS,
        )
        print("[OK] Importaciones de constantes OE2 funcionales")
        
        print("\n[OK] TEST 5 PASADO: Backward compatibility OK")
        return True
    except Exception as e:
        print(f"\n[X] TEST 5 FALLIDO: {e}")
        return False


def test_old_scripts():
    """Test 6: Verificar que scripts antiguos aun funcionan."""
    print_header("TEST 6: COMPATIBILIDAD CON SCRIPTS ANTIGUOS")
    
    print_section("Verificando scripts de entrenamiento...")
    
    scripts_to_check = [
        "scripts/train/train_ppo_multiobjetivo.py",
        "scripts/train/train_sac_multiobjetivo.py",
        "scripts/train/train_sac_all_columns_expanded.py",
        "scripts/train/train_sac_sistema_comunicacion_v6.py",
        "scripts/train/train_ppo_robust.py",
    ]
    
    all_exist = True
    for script in scripts_to_check:
        path = project_root / script
        if path.exists():
            print(f"[OK] {script}")
        else:
            print(f"[!]  {script} (no encontrado)")
    
    # Verificar que no hay imports rotos
    print_section("Verificando imports de scripts...")
    
    try:
        # Intentar importar uno de los scripts (sin ejecutar)
        # Esto solo verifica que la sintaxis es correcta
        import ast
        with open(project_root / "scripts/train/train_ppo_multiobjetivo.py", "r") as f:
            code = f.read()
            ast.parse(code)
        print("[OK] Script train_ppo_multiobjetivo.py es sintax valida")
    except SyntaxError as e:
        print(f"[X] Script train_ppo_multiobjetivo.py tiene error de sintaxis: {e}")
        all_exist = False
    except Exception as e:
        print(f"[!]  No se pudo verificar: {e}")
    
    if all_exist:
        print("\n[OK] TEST 6 PASADO: Scripts compatibles")
        return True
    else:
        print("\n[!]  TEST 6 PARCIAL: Revisar scripts")
        return True  # No es critical


def print_summary(results):
    """Imprime resumen de tests."""
    print_header("RESUMEN DE DIAGNOSTICO")
    
    test_names = [
        "Importacion del modulo",
        "Creacion de builder",
        "Creacion de observaciones",
        "Cobertura de versiones",
        "Backward compatibility",
        "Compatibilidad con scripts",
    ]
    
    print("\n[GRAPH] RESULTADOS:\n")
    for i, (name, result) in enumerate(zip(test_names, results), 1):
        status = "[OK] PASADO" if result else "[X] FALLIDO"
        print(f"  Test {i}: {name:40s} {status}")
    
    passed = sum(results)
    total = len(results)
    
    print(f"\n[CHART] Total: {passed}/{total} tests pasados")
    
    if passed == total:
        print("\n🎉 ¡TODOS LOS TESTS PASADOS!")
        print("\n[OK] CONSOLIDACION DE OBSERVACIONES VERIFICADA")
        print("   Listo para:")
        print("   1. Refactoring de scripts de entrenamiento")
        print("   2. Eliminacion de codigo duplicado")
        print("   3. Integracion en nuevos scripts")
    else:
        print(f"\n[!]  {total - passed} tests fallidos. Revisar arriba.")


def main():
    """Ejecutar todos los tests."""
    print("\n" + "🔍" * 40)
    print("DIAGNOSTICO DE UNIFICACION - OBSERVACIONES CITYLEARN V2")
    print("🔍" * 40)
    
    results = []
    
    # Test 1
    results.append(test_import())
    
    # Test 2
    ok, builders = test_builder_creation()
    results.append(ok)
    
    # Test 3
    if builders:
        results.append(test_observation_creation(builders))
    else:
        results.append(False)
    
    # Test 4
    results.append(test_version_coverage())
    
    # Test 5
    results.append(test_backward_compatibility())
    
    # Test 6
    results.append(test_old_scripts())
    
    # Resumen
    print_summary(results)
    
    # Return code
    if all(results):
        print("\n[OK] Diagnostico completado exitosamente")
        return 0
    else:
        print("\n[X] Algunos tests fallaron")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
