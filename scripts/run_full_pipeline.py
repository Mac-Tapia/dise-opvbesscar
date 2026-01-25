"""
Pipeline Completo: Dataset → Baseline → Entrenamiento → Comparación
Ejecuta todo el flujo de forma secuencial con manejo robusto de errores.
VERSIÓN 2.0 - Mejorado para ejecución autónoma
"""

import sys
from pathlib import Path
import subprocess
import logging
import time
import json
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)
logger = logging.getLogger(__name__)


def run_script(script_name, description, timeout_seconds=3600):
    """Ejecutar un script Python con manejo robusto de errores."""
    logger.info("\n" + "=" * 80)
    logger.info(f"▶️  {description}")
    logger.info("=" * 80)

    script_path = PROJECT_ROOT / "scripts" / script_name

    if not script_path.exists():
        logger.error(f"❌ Script no encontrado: {script_path}")
        return 1, None

    try:
        logger.info(f"Ejecutando: {script_name}")
        logger.info(f"Timeout: {timeout_seconds}s\n")

        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=PROJECT_ROOT,
            timeout=timeout_seconds,
            capture_output=True,
            text=True
        )

        # Log output
        if result.stdout:
            logger.info(result.stdout)
        if result.stderr:
            logger.warning(result.stderr)

        if result.returncode == 0:
            logger.info(f"✅ {description} - EXITOSO\n")
        else:
            logger.error(f"❌ {description} - FALLÓ (exit code: {result.returncode})\n")

        return result.returncode, result

    except subprocess.TimeoutExpired:
        logger.error(f"❌ TIMEOUT ({timeout_seconds}s) en {script_name}")
        logger.error("   Pipeline abortado - tiempo de ejecución excedido\n")
        return 1, None

    except Exception as e:
        logger.error(f"❌ ERROR CRÍTICO ejecutando {script_name}: {e}")
        import traceback
        traceback.print_exc()
        logger.error("")
        return 1, None


def main():
    logger.info("=" * 80)
    logger.info("🚀 PIPELINE COMPLETO: DATASET → BASELINE → TRAINING → COMPARACIÓN")
    logger.info("=" * 80)

    start_time = time.time()
    pipeline_results = {
        "timestamp": datetime.now().isoformat(),
        "steps": {}
    }

    # Paso 1: Construir Dataset (desde OE2)
    logger.info("\n📍 PASO 1/4: Construcción de Dataset (desde artefactos OE2)")
    logger.info("   - Solar generation: PVGIS/pvlib normalizados")
    logger.info("   - Chargers: 128 sockets (32 chargers × 4)")
    logger.info("   - BESS: 2 MWh / 1.2 MW")

    rc1, result1 = run_script(
        "build_dataset.py",
        "Dataset: Construcción desde artefactos OE2",
        timeout_seconds=300
    )

    pipeline_results["steps"]["dataset"] = {
        "status": "success" if rc1 == 0 else "failed",
        "exit_code": rc1
    }

    if rc1 != 0:
        logger.error("❌ Construcción de dataset falló. Abortando pipeline.")
        return 1

    # Paso 2: Calcular Baseline (con datos construidos)
    logger.info("\n📍 PASO 2/4: Cálculo de Baseline (en base a datos construidos)")
    logger.info("   - Carga: perfil actual de chargers desde dataset")
    logger.info("   - Energía: suma real de demanda de los 128 sockets")
    logger.info("   - CO2: based on dataset energy consumption")

    rc2, result2 = run_script(
        "baseline_robust.py",
        "Baseline: Referencia de 8,760 timesteps sin control",
        timeout_seconds=120
    )

    pipeline_results["steps"]["baseline"] = {
        "status": "success" if rc2 == 0 else "failed",
        "exit_code": rc2
    }

    if rc2 != 0:
        logger.error("❌ Cálculo de baseline falló. Abortando pipeline.")
        return 1

    # Paso 3: Entrenar Agentes en serie
    logger.info("\n📍 PASO 3/4: Entrenamiento REAL de Agentes (PPO → SAC → A2C)")
    logger.info("   - 3 agentes entrenados en serie con CityLearn")
    logger.info("   - Cada agente: episodios reales de 8,760 timesteps")
    logger.info("   - Rewards calculados desde ambiente real")
    logger.info("   - DURACIÓN ESTIMADA: 15-30 min (CPU) o 5-10 min (GPU)\n")

    rc3, result3 = run_script(
        "train_agents_real_v2.py",
        "Training: Entrenamiento REAL serial de 3 agentes",
        timeout_seconds=3600  # 1 hora max
    )

    pipeline_results["steps"]["training"] = {
        "status": "success" if rc3 == 0 else "failed",
        "exit_code": rc3
    }

    if rc3 != 0:
        logger.error("⚠️  Entrenamiento falló. Continuando con comparación...")

    # Paso 4: Comparación (opcional)
    logger.info("\n📍 PASO 4/4: Comparación de Resultados")

    rc4, result4 = run_script(
        "compare_baseline_vs_agents.py",
        "Comparison: Análisis baseline vs agents",
        timeout_seconds=60
    )

    pipeline_results["steps"]["comparison"] = {
        "status": "success" if rc4 == 0 else "failed",
        "exit_code": rc4
    }

    if rc4 != 0:
        logger.warning("⚠️  Comparación no disponible. Pero pipeline continúa.")

    # Resumen final
    elapsed = time.time() - start_time

    logger.info("\n" + "=" * 80)
    logger.info("✅ PIPELINE COMPLETADO")
    logger.info("=" * 80)

    logger.info(f"\n⏱️  TIEMPO TOTAL: {elapsed:.1f}s ({elapsed/60:.1f} min)")

    # Verificar archivos creados
    output_dir = PROJECT_ROOT / "outputs" / "oe3_simulations"
    logger.info(f"\n📁 ARCHIVOS GENERADOS en {output_dir}:")

    if (output_dir / "baseline_reference.json").exists():
        logger.info("   ✓ baseline_reference.json")
        try:
            with open(output_dir / "baseline_reference.json") as f:
                baseline = json.load(f)
                logger.info(f"     - Chargers: {baseline.get('num_chargers', '?')}")
                logger.info(f"     - Energía: {baseline.get('energy_kwh', 0):,.0f} kWh/año")
                logger.info(f"     - CO₂: {baseline.get('co2_total_kg', 0):,.0f} kg/año")
        except:
            pass

    # Buscar training summary más reciente
    training_files = list(output_dir.glob("training_summary_*.json"))
    if training_files:
        latest_training = sorted(training_files)[-1]
        logger.info(f"   ✓ {latest_training.name}")
        try:
            with open(latest_training) as f:
                training = json.load(f)
                for agent in ["ppo", "sac", "a2c"]:
                    if agent in training and training[agent]:
                        agent_data = training[agent]
                        if agent_data.get("success"):
                            logger.info(f"     - {agent.upper()}: {agent_data.get('mean_reward', 0):,.2f} reward")
                        elif agent_data.get("error"):
                            logger.info(f"     - {agent.upper()}: Error - {agent_data.get('error', 'Unknown')}")
        except:
            pass

    comparison_files = list(output_dir.glob("comparison*.json"))
    if comparison_files:
        logger.info(f"   ✓ {comparison_files[0].name}")

    # Guardar resumen de pipeline
    pipeline_file = output_dir / f"pipeline_summary_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(pipeline_file, 'w') as f:
        json.dump(pipeline_results, f, indent=2)

    logger.info(f"\n📋 Resumen guardado: {pipeline_file.name}")
    logger.info("")

    # Resultado final
    success = rc1 == 0 and rc2 == 0 and rc3 == 0
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
