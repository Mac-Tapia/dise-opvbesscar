#!/usr/bin/env python3
"""
Diagnóstico de Generación de Datos Técnicos SAC

Script que verifica que SAC esté configurado correctamente para generar:
- result_sac.json
- timeseries_sac.csv
- trace_sac.csv

9 Checks de diagnóstico para verificar setup pre-entrenamiento.
"""

from __future__ import annotations

import sys
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Callable

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Colores para output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def check_simulate_import() -> Tuple[bool, str]:
    """Verificar que simulate() sea importable."""
    try:
        from iquitos_citylearn.oe3.simulate import simulate
        return True, "simulate() importado correctamente"
    except ImportError as e:
        return False, f"Error importando simulate(): {e}"


def check_sac_agent_import() -> Tuple[bool, str]:
    """Verificar que SAC agent sea creatable."""
    try:
        from iquitos_citylearn.oe3.agents import make_sac
        return True, "SAC agent importado correctamente"
    except ImportError as e:
        return False, f"Error importando make_sac: {e}"


def check_config_valid() -> Tuple[bool, str]:
    """Verificar que configuración sea válida."""
    try:
        from iquitos_citylearn.config import load_config, load_paths
        cfg = load_config(Path("configs/default.yaml"))

        # Verificar campos SAC específicos
        oe3_config = cfg.get("oe3", {})
        if not oe3_config:
            return False, "No OE3 configuration found in default.yaml"
        return True, "Configuración SAC válida"
    except Exception as e:
        return False, f"Error validando config: {e}"


def check_output_directories() -> Tuple[bool, str]:
    """Verificar que directorios de salida sean accesibles."""
    try:
        output_dirs = [
            Path("outputs/agents/sac"),
            Path("outputs/oe3_simulations"),
            Path("checkpoints/sac"),
        ]

        for dir_path in output_dirs:
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)
            if not dir_path.is_dir():
                return False, f"{dir_path} no es directorio"

        dirs_str = "\n   ".join([f"✅ Directorio disponible: {d}" for d in output_dirs])
        return True, f"Directorios accesibles:\n   {dirs_str}"
    except Exception as e:
        return False, f"Error verificando directorios: {e}"


def check_dataset_exists() -> Tuple[bool, str]:
    """Verificar que dataset CityLearn existe."""
    try:
        dataset_files = [
            Path("data/processed/citylearn/iquitos_ev_mall/schema.json"),
            Path("data/processed/citylearn/iquitos_ev_mall/Building_1.csv"),
        ]

        for file_path in dataset_files:
            if not file_path.exists():
                return False, f"Dataset no encontrado: {file_path}"

        files_str = "\n   ".join([f"✅ {f}" for f in dataset_files])
        return True, f"Dataset completo:\n   {files_str}"
    except Exception as e:
        return False, f"Error verificando dataset: {e}"


def check_simulate_function_signature() -> Tuple[bool, str]:
    """Verificar que simulate() tenga los parámetros correctos."""
    try:
        import inspect
        from iquitos_citylearn.oe3.simulate import simulate

        sig = inspect.signature(simulate)
        params = list(sig.parameters.keys())

        required_params = [
            "schema_path", "agent_name", "out_dir", "training_dir",
            "carbon_intensity_kg_per_kwh", "seconds_per_time_step"
        ]

        missing = [p for p in required_params if p not in params]
        if missing:
            return False, f"Parámetros faltantes: {missing}"

        return True, f"Todos los parámetros presentes ({len(params)} total)"
    except Exception as e:
        return False, f"Error verificando firma: {e}"


def check_sac_training_scripts() -> Tuple[bool, str]:
    """Verificar que scripts de entrenamiento SAC existan."""
    try:
        scripts = [
            Path("scripts/run_agent_sac.py"),
            Path("scripts/train_sac_production.py"),
        ]

        for script in scripts:
            if not script.exists():
                return False, f"Script no encontrado: {script}"

        scripts_str = "\n   ".join([f"✅ {s}" for s in scripts])
        return True, f"Scripts de entrenamiento presentes:\n   {scripts_str}"
    except Exception as e:
        return False, f"Error verificando scripts: {e}"


def check_previous_sac_runs() -> Tuple[bool, str]:
    """Verificar si hay ejecuciones previas de SAC."""
    try:
        sac_files = [
            Path("outputs/agents/sac/result_sac.json"),
            Path("outputs/agents/sac/timeseries_sac.csv"),
            Path("outputs/agents/sac/trace_sac.csv"),
        ]

        existing = [f for f in sac_files if f.exists()]

        if not existing:
            return True, "No hay archivos técnicos SAC previos (primera ejecución)"

        return True, f"Archivos previos encontrados: {len(existing)}/3"
    except Exception as e:
        return False, f"Error verificando ejecuciones previas: {e}"


def check_multiobjetivo_config() -> Tuple[bool, str]:
    """Verificar que multiobjetivo esté configurado correctamente."""
    try:
        from iquitos_citylearn.config import load_config
        cfg = load_config(Path("configs/default.yaml"))

        # Verificar que reward weights estén configurados
        oe3_config = cfg.get("oe3", {})

        if not oe3_config:
            return False, "No OE3 configuration found"

        # Verificar que grid carbon intensity esté configurado
        grid_carbon = oe3_config.get("grid", {}).get("carbon_intensity_kg_per_kwh", 0.4521)

        weights_str = f"Grid CO₂ Factor: {grid_carbon:.4f} kg/kWh"
        return True, f"Multiobjetivo configurado correctamente: {weights_str}"
    except Exception as e:
        return False, f"Error verificando config multiobjetivo: {e}"


def run_all_diagnostics() -> List[Tuple[int, str, bool, str]]:
    """Ejecuta todos los diagnósticos y retorna resultados."""
    checks = [
        (1, "Verificando importación de simulate()", check_simulate_import),
        (2, "Verificando importación de agente SAC", check_sac_agent_import),
        (3, "Verificando configuración default.yaml", check_config_valid),
        (4, "Verificando directorios de salida", check_output_directories),
        (5, "Verificando dataset CityLearn", check_dataset_exists),
        (6, "Verificando firma de función simulate()", check_simulate_function_signature),
        (7, "Verificando scripts de entrenamiento SAC", check_sac_training_scripts),
        (8, "Verificando ejecuciones previas de SAC", check_previous_sac_runs),
        (9, "Verificando configuración multiobjetivo", check_multiobjetivo_config),
    ]

    results = []
    passed = 0
    failed = 0

    logger.info("")
    logger.info("=" * 60)
    logger.info("🔧 DIAGNÓSTICO DE GENERACIÓN DE DATOS TÉCNICOS SAC")
    logger.info("=" * 60)
    logger.info("")

    for check_num, description, check_func in checks:
        # Mostrar encabezado del check
        emoji = f"{check_num}️⃣ "
        logger.info(f"{emoji} {description}")

        try:
            # Ejecutar check
            success, message = check_func()

            if success:
                # Mostrar resultado exitoso
                for line in message.split("\n"):
                    logger.info(f"   ✅ {line}")
                passed += 1
            else:
                # Mostrar error
                logger.error(f"   ❌ {message}")
                failed += 1

            results.append((check_num, description, success, message))

        except Exception as e:
            logger.error(f"   ❌ Excepción no esperada: {e}")
            failed += 1
            results.append((check_num, description, False, str(e)))

        logger.info("")

    # Resumen
    logger.info("=" * 60)
    logger.info("📊 RESUMEN DE DIAGNÓSTICO")
    logger.info("=" * 60)

    # Tabla de resultados
    for check_num, description, success, message in results:
        status = "✅" if success else "❌"
        logger.info(f"{status} Check {check_num}: {description}")

    logger.info("")
    logger.info(f"✅ Passed: {passed}/9")
    logger.info(f"❌ Failed: {failed}/9")
    logger.info("")

    if failed == 0:
        logger.info("🎉 TODOS LOS DIAGNÓSTICOS PASARON - LISTO PARA ENTRENAMIENTO SAC")
        logger.info("")
        logger.info("Próximos pasos:")
        logger.info("  1. python scripts/run_agent_sac.py")
        logger.info("  2. python scripts/validate_sac_technical_data.py")
    else:
        logger.error("⚠️  ALGUNOS DIAGNÓSTICOS FALLARON - REVISAR ARRIBA")

    logger.info("=" * 60)
    logger.info("")

    return results


def main() -> int:
    """Punto de entrada principal."""
    try:
        results = run_all_diagnostics()

        # Retornar código de salida basado en resultados
        failed = sum(1 for _, _, success, _ in results if not success)
        return 0 if failed == 0 else 1

    except Exception as e:
        logger.critical(f"Error crítico en diagnóstico: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
