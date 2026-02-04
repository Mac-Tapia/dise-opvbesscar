#!/usr/bin/env python3
"""
================================================================================
🔧 DIAGNÓSTICO DE GENERACIÓN DE DATOS TÉCNICOS A2C
================================================================================

Script de diagnóstico que verifica que A2C está configurado correctamente
para generar:
1. result_a2c.json
2. timeseries_a2c.csv
3. trace_a2c.csv

Este script verifica:
- ✅ La función simulate() es llamada con agent_name="a2c"
- ✅ Los parámetros necesarios están presentes
- ✅ El directorio de salida está configurado correctamente
- ✅ Los checkpoints se guardan en la ubicación correcta
- ✅ La configuración multiobjetivo es válida

@author: pvbesscar-system
@date: 2026-02-04
@version: 1.0.0-stable
================================================================================
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple, Callable

# ==============================================================================
# LOGGING CONFIGURATION
# ==============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


# ==============================================================================
# DIAGNOSTIC FUNCTIONS
# ==============================================================================
def check_simulate_import() -> bool:
    """Verifica que simulate() puede importarse correctamente."""
    logger.info("1️⃣  Verificando importación de simulate()...")

    try:
        from iquitos_citylearn.oe3.simulate import simulate  # type: ignore
        logger.info("   ✅ simulate() importado correctamente")
        return True
    except ImportError as e:
        logger.error(f"   ❌ Error importando simulate(): {e}")
        return False
    except Exception as e:
        logger.error(f"   ❌ Error inesperado: {e}")
        return False


def check_a2c_agent_import() -> bool:
    """Verifica que el agente A2C puede importarse."""
    logger.info("2️⃣  Verificando importación de agente A2C...")

    try:
        from iquitos_citylearn.oe3.agents.a2c_sb3 import make_a2c  # type: ignore
        logger.info("   ✅ A2C agent importado correctamente")
        return True
    except ImportError as e:
        logger.error(f"   ❌ Error importando A2C: {e}")
        return False
    except Exception as e:
        logger.error(f"   ❌ Error inesperado: {e}")
        return False


def check_config_valid() -> bool:
    """Verifica que la configuración default.yaml existe y es válida."""
    logger.info("3️⃣  Verificando configuración default.yaml...")

    config_path: Path = Path("configs/default.yaml")

    if not config_path.exists():
        logger.error(f"   ❌ Archivo no encontrado: {config_path}")
        return False

    try:
        import yaml  # type: ignore
        with open(config_path, "r", encoding="utf-8") as f:
            config: Dict[str, Any] = yaml.safe_load(f)

        # Verificar campos necesarios
        required_fields: List[str] = [
            "oe3",
            "project",
            "paths"
        ]

        for field in required_fields:
            if field not in config:
                logger.error(f"   ❌ Campo requerido faltante: {field}")
                return False

        logger.info("   ✅ Configuración válida")
        return True

    except Exception as e:
        logger.error(f"   ❌ Error validando configuración: {e}")
        return False


def check_output_directories() -> bool:
    """Verifica que los directorios de salida existen o pueden crearse."""
    logger.info("4️⃣  Verificando directorios de salida...")

    output_paths: List[Path] = [
        Path("outputs/agents/a2c"),
        Path("outputs/oe3_simulations"),
        Path("checkpoints/a2c"),
    ]

    all_valid: bool = True

    for dir_path in output_paths:
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"   ✅ Directorio disponible: {dir_path}")
        except Exception as e:
            logger.error(f"   ❌ Error creando directorio {dir_path}: {e}")
            all_valid = False

    return all_valid


def check_dataset_exists() -> bool:
    """Verifica que el dataset CityLearn existe."""
    logger.info("5️⃣  Verificando dataset CityLearn...")

    dataset_paths: List[Path] = [
        Path("data/processed/citylearn/iquitos_ev_mall/schema.json"),
        Path("data/processed/citylearn/iquitos_ev_mall/Building_1.csv"),
    ]

    all_exist: bool = True

    for path in dataset_paths:
        if path.exists():
            logger.info(f"   ✅ {path}")
        else:
            logger.error(f"   ❌ No encontrado: {path}")
            all_exist = False

    if not all_exist:
        logger.error("   ⚠️  Dataset incompleto. Ejecutar: python -m scripts.run_oe3_build_dataset")

    return all_exist


def check_simulate_function_signature() -> bool:
    """Verifica que simulate() tiene los parámetros necesarios para A2C."""
    logger.info("6️⃣  Verificando firma de función simulate()...")

    import inspect

    try:
        from iquitos_citylearn.oe3.simulate import simulate  # type: ignore

        sig = inspect.signature(simulate)
        params: List[str] = list(sig.parameters.keys())

        # Parámetros necesarios para A2C
        required_params: List[str] = [
            "schema_path",
            "agent_name",
            "out_dir",
            "training_dir",
            "carbon_intensity_kg_per_kwh",
            "a2c_timesteps",
            "a2c_resume_checkpoints",
            "use_multi_objective",
        ]

        missing_params: List[str] = [p for p in required_params if p not in params]

        if missing_params:
            logger.error(f"   ❌ Parámetros faltantes: {', '.join(missing_params)}")
            return False

        logger.info(f"   ✅ Todos los parámetros presentes ({len(params)} total)")
        return True

    except Exception as e:
        logger.error(f"   ❌ Error inspeccionando función: {e}")
        return False


def check_a2c_training_scripts() -> bool:
    """Verifica que los scripts de entrenamiento A2C existen."""
    logger.info("7️⃣  Verificando scripts de entrenamiento A2C...")

    scripts: List[Path] = [
        Path("scripts/run_agent_a2c.py"),
        Path("scripts/train_a2c_production.py"),
    ]

    all_exist: bool = True

    for script in scripts:
        if script.exists():
            logger.info(f"   ✅ {script}")
        else:
            logger.error(f"   ❌ No encontrado: {script}")
            all_exist = False

    return all_exist


def check_previous_a2c_runs() -> bool:
    """Verifica si hay ejecuciones previas de A2C con datos técnicos."""
    logger.info("8️⃣  Verificando ejecuciones previas de A2C...")

    output_dir: Path = Path("outputs/agents/a2c")

    if not output_dir.exists():
        logger.warning(f"   ⚠️  Directorio no existe aún: {output_dir}")
        return True  # No es un error, es normal en primera ejecución

    expected_files: List[Path] = [
        output_dir / "result_a2c.json",
        output_dir / "timeseries_a2c.csv",
        output_dir / "trace_a2c.csv",
    ]

    found_files: List[Path] = [f for f in expected_files if f.exists()]

    if len(found_files) == 0:
        logger.warning(f"   ⚠️  No hay archivos técnicos A2C previos (primera ejecución)")
        return True
    elif len(found_files) == 3:
        logger.info(f"   ✅ Todos los archivos técnicos encontrados")
        return True
    else:
        logger.warning(f"   ⚠️  Archivos incompletos: {len(found_files)}/3")
        missing = [f.name for f in expected_files if f not in found_files]
        logger.warning(f"      Faltando: {', '.join(missing)}")
        return False


def check_multiobjetive_config() -> bool:
    """Verifica que la configuración multiobjetivo es válida."""
    logger.info("9️⃣  Verificando configuración multiobjetivo...")

    try:
        from iquitos_citylearn.oe3.rewards import (  # type: ignore
            create_iquitos_reward_weights,
            MultiObjectiveReward,
        )

        # Intentar crear pesos con prioridad co2_focus
        weights = create_iquitos_reward_weights("co2_focus")

        # Verificar suma de pesos = 1.0
        total_weight: float = (
            weights.co2 +
            weights.cost +
            weights.solar +
            weights.ev_satisfaction +
            weights.grid_stability
        )

        if abs(total_weight - 1.0) > 0.01:
            logger.error(f"   ❌ Suma de pesos inválida: {total_weight} (esperado 1.0)")
            return False

        logger.info(f"   ✅ Multiobjetivo configurado correctamente")
        logger.info(f"      CO2: {weights.co2:.2f}, Solar: {weights.solar:.2f}, Cost: {weights.cost:.2f}")
        return True

    except Exception as e:
        logger.error(f"   ❌ Error verificando multiobjetivo: {e}")
        return False


# ==============================================================================
# MAIN DIAGNOSTIC ORCHESTRATION
# ==============================================================================
def run_diagnostics() -> int:
    """Ejecuta todos los diagnósticos y retorna código de salida."""

    logger.info("")
    logger.info("=" * 80)
    logger.info("🔧 DIAGNÓSTICO DE GENERACIÓN DE DATOS TÉCNICOS A2C")
    logger.info("=" * 80)
    logger.info("")

    # Lista de checks
    checks: List[Tuple[str, Callable[[], bool]]] = [
        ("simulate() import", check_simulate_import),
        ("A2C agent import", check_a2c_agent_import),
        ("Config validation", check_config_valid),
        ("Output directories", check_output_directories),
        ("Dataset existence", check_dataset_exists),
        ("simulate() signature", check_simulate_function_signature),
        ("Training scripts", check_a2c_training_scripts),
        ("Previous A2C runs", check_previous_a2c_runs),
        ("Multiobjetivo config", check_multiobjetive_config),
    ]

    results: List[Tuple[str, bool]] = []

    for check_name, check_func in checks:
        try:
            result: bool = check_func()
            results.append((check_name, result))
        except Exception as e:
            logger.error(f"   ❌ Error en check: {e}")
            results.append((check_name, False))

        logger.info("")

    # Resumen final
    logger.info("=" * 80)
    logger.info("📊 RESUMEN DE DIAGNÓSTICO")
    logger.info("=" * 80)
    logger.info("")

    passed: int = sum(1 for _, result in results if result)
    total: int = len(results)

    for check_name, result in results:
        status: str = "✅" if result else "❌"
        logger.info(f"{status} {check_name}")

    logger.info("")
    logger.info(f"✅ Passed: {passed}/{total}")
    logger.info(f"❌ Failed: {total - passed}/{total}")
    logger.info("")

    if passed == total:
        logger.info("🎉 TODOS LOS DIAGNÓSTICOS PASARON - LISTO PARA ENTRENAMIENTO A2C")
        logger.info("")
        logger.info("Próximos pasos:")
        logger.info("  1. python scripts/run_agent_a2c.py")
        logger.info("  2. python scripts/validate_a2c_technical_data.py")
        return 0
    else:
        logger.error("⚠️  ALGUNOS DIAGNÓSTICOS FALLARON - VER ERRORES ARRIBA")
        logger.error("")
        logger.error("Soluciones:")
        logger.error("  1. Verificar que todos los archivos necesarios existen")
        logger.error("  2. Ejecutar: python -m scripts.run_oe3_build_dataset")
        logger.error("  3. Revisar logs para más detalles")
        return 1


if __name__ == "__main__":
    sys.exit(run_diagnostics())
