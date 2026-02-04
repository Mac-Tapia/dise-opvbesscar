#!/usr/bin/env python3
"""
================================================================================
🚀 A2C PRODUCTION TRAINING - ENTRENAMIENTO ROBUSTO LISTO PARA PRODUCCIÓN
================================================================================
Script de entrenamiento A2C optimizado para RTX 4060 con:
- 500,000 timesteps (escalable a 1M+)
- n_steps=2048 (captura variación anual: 8,760 ÷ 4 = 2,190 ≈ 2,048 pasos)
- Entropy decay (0.01 → 0.001) - SINCRONIZADO CON SAC/PPO
- Multiobjetivo sincronizado (rewards.py)
- GPU auto-detection
- Checkpoints cada 1,000 steps
- Resume-capable

CARACTERÍSTICAS A2C (Advantage Actor-Critic):
- Actualizaciones síncronas (más estable que A3C asíncrono)
- GAE (Generalized Advantage Estimation) para reducción de varianza
- On-policy (más data-efficient que SAC offline)
- Más rápido que PPO (wall-clock) en entrenamiento

USO:
    python scripts/train_a2c_production.py
    python scripts/train_a2c_production.py --resume
    python scripts/train_a2c_production.py --timesteps 1000000 --priority co2_focus

MONITOREO:
    tail -f logs/a2c_training.log
    tensorboard --logdir outputs/a2c_logs

HIPERPARÁMETROS:
- n_steps: 2048 (see year variation)
- learning_rate: 1e-4 (linear decay)
- gae_lambda: 0.95 (GAE for variance reduction)
- ent_coef_schedule: linear (0.01 → 0.001)
- reward_scale: 0.1 (prevent Q-explosion)
- use_huber_loss: True (robust VF)

@author: pvbesscar-system
@date: 2026-02-04
@version: 2.0.0 (SYNCHRONIZED WITH SAC/PPO)
================================================================================
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from datetime import datetime

# Set up logging
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("logs/a2c_training.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict


# ==============================================================================
# LOGGING SETUP
# ==============================================================================
class ColorFormatter(logging.Formatter):
    """Formatter con colores para terminal."""

    COLORS = {
        logging.DEBUG: "\033[36m",     # Cyan
        logging.INFO: "\033[32m",      # Green
        logging.WARNING: "\033[33m",   # Yellow
        logging.ERROR: "\033[31m",     # Red
        logging.CRITICAL: "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelno, "")
        record.levelname = f"{color}{record.levelname}{self.RESET}"
        return super().format(record)


# Setup logging
handler = logging.StreamHandler()
handler.setFormatter(ColorFormatter("%(levelname)s | %(message)s"))
logging.basicConfig(level=logging.INFO, handlers=[handler])
logger = logging.getLogger(__name__)


# ==============================================================================
# VISUAL BANNERS
# ==============================================================================
def print_banner():
    """Imprime banner de inicio A2C."""
    banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                                                                              ║
║   █████╗ ██████╗  ██████╗    ████████╗██████╗  █████╗ ██╗███╗   ██╗██╗███╗   ║
║  ██╔══██╗╚════██╗██╔════╝    ╚══██╔══╝██╔══██╗██╔══██╗██║████╗  ██║██║████╗  ║
║  ███████║ █████╔╝██║            ██║   ██████╔╝███████║██║██╔██╗ ██║██║██╔██╗ ║
║  ██╔══██║██╔═══╝ ██║            ██║   ██╔══██╗██╔══██║██║██║╚██╗██║██║██║╚██╗║
║  ██║  ██║███████╗╚██████╗       ██║   ██║  ██║██║  ██║██║██║ ╚████║██║██║ ╚██║
║  ╚═╝  ╚═╝╚══════╝ ╚═════╝       ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝╚═╝╚═╝  ╚═║
║                                                                              ║
║  🔋 Advantage Actor-Critic - Iquitos EV/Solar/BESS Optimization 🌴          ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
    print(banner)
    print(f"  📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  🐍 Python: {sys.version.split()[0]}")
    print()


def print_config_summary(
    timesteps: int,
    device: str,
    gpu_info: Dict[str, Any],
    schema_path: Path,
    checkpoint_dir: Path,
):
    """Imprime resumen de configuración A2C."""
    print()
    print("=" * 80)
    print("  ⚙️  CONFIGURACIÓN A2C")
    print("=" * 80)
    print()
    print("  📊 ENTRENAMIENTO:")
    print(f"     • Timesteps totales: {timesteps:,}")
    print(f"     • N-Steps (rollout): 2,048")
    print(f"     • Learning Rate: 1e-4 (linear decay)")
    print(f"     • Gamma (discount): 0.99")
    print(f"     • GAE Lambda: 0.95")
    print(f"     • Entropy Coef: 0.01 → 0.001 (decaying)")
    print(f"     • Value Coef: 0.5")
    print(f"     • Max Grad Norm: 0.5")
    print()
    print("  🖥️  HARDWARE:")
    print(f"     • Device: {device}")
    if gpu_info.get('cuda_available'):
        print(f"     • GPU: {gpu_info.get('name', 'N/A')}")
        print(f"     • VRAM: {gpu_info.get('vram_gb', 0):.2f} GB")
    print()
    print("  📁 RUTAS:")
    print(f"     • Schema: {schema_path}")
    print(f"     • Checkpoints: {checkpoint_dir}")
    print()
    print("  🎯 MULTI-OBJETIVO (CO₂ Focus):")
    print(f"     • CO₂ Weight: 0.50 (primary)")
    print(f"     • Solar Weight: 0.20")
    print(f"     • Cost Weight: 0.15")
    print(f"     • EV Weight: 0.10")
    print(f"     • Grid Weight: 0.05")
    print()


# ==============================================================================
# GPU DETECTION
# ==============================================================================
def detect_gpu() -> Dict[str, Any]:
    """Detecta GPU disponible y retorna info."""
    result = {
        'device': 'cpu',
        'cuda_available': False,
        'mps_available': False,
        'name': 'CPU',
        'vram_gb': 0.0,
    }

    try:
        import torch

        if torch.cuda.is_available():
            result['cuda_available'] = True
            result['device'] = 'cuda'
            result['name'] = torch.cuda.get_device_name(0)
            result['vram_gb'] = torch.cuda.get_device_properties(0).total_memory / (1024**3)
            logger.info(f"🎮 GPU detectada: {result['name']} ({result['vram_gb']:.2f} GB)")
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            result['mps_available'] = True
            result['device'] = 'mps'
            result['name'] = 'Apple MPS'
            logger.info("🍎 Apple MPS detectado")
        else:
            logger.warning("⚠️  No se detectó GPU, usando CPU")

    except ImportError:
        logger.warning("⚠️  PyTorch no instalado, usando CPU")

    return result


# ==============================================================================
# DATASET VALIDATION
# ==============================================================================
def validate_dataset(schema_path: Path) -> bool:
    """Valida que el dataset tenga los 128 chargers requeridos."""
    if not schema_path.exists():
        logger.error(f"❌ Schema no encontrado: {schema_path}")
        return False

    try:
        import json
        schema = json.loads(schema_path.read_text(encoding="utf-8"))

        # Verificar chargers
        buildings = schema.get("buildings", {})
        total_chargers = 0

        for _, bdata in buildings.items():
            chargers = bdata.get("chargers", {})
            if isinstance(chargers, dict):
                total_chargers += len(chargers)

        if total_chargers != 128:
            logger.error(f"❌ Dataset tiene {total_chargers} chargers, se requieren 128")
            return False

        logger.info(f"✅ Dataset validado: {total_chargers} chargers detectados")
        return True

    except Exception as e:
        logger.error(f"❌ Error validando dataset: {e}")
        return False


# ==============================================================================
# MAIN TRAINING FUNCTION
# ==============================================================================
def run_training(
    config_path: Path,
    timesteps: int,
    resume: bool = False,
    eval_only: bool = False,
) -> Dict[str, Any]:
    """Ejecuta entrenamiento A2C de producción.

    Args:
        config_path: Ruta al archivo de configuración YAML
        timesteps: Total de timesteps para entrenar
        resume: Si True, continua desde último checkpoint
        eval_only: Si True, solo evalúa sin entrenar

    Returns:
        Dict con resumen de entrenamiento y métricas
    """
    # Importar aquí para evitar imports innecesarios si hay errores de args
    from scripts._common import load_all
    from iquitos_citylearn.oe3.simulate import simulate

    # Cargar configuración
    cfg, paths = load_all(str(config_path))

    # Detectar GPU
    gpu_info = detect_gpu()

    # Rutas
    schema_path = paths.processed_dir / "citylearn" / "iquitos_ev_mall" / "schema.json"
    out_dir = paths.oe3_simulations_dir / "a2c"
    out_dir.mkdir(parents=True, exist_ok=True)

    checkpoint_dir = paths.checkpoints_dir / "a2c"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    # Validar dataset
    if not validate_dataset(schema_path):
        raise ValueError(f"Dataset inválido: {schema_path}")

    # Mostrar configuración
    print_config_summary(
        timesteps=timesteps,
        device=gpu_info['device'],
        gpu_info=gpu_info,
        schema_path=schema_path,
        checkpoint_dir=checkpoint_dir,
    )

    # Modo de ejecución
    if eval_only:
        print("🎯 MODO: Solo evaluación (sin entrenamiento)")
        timesteps = 8760  # 1 episodio para eval
    else:
        print(f"🎯 MODO: Entrenamiento ({timesteps:,} timesteps)")
        if resume:
            checkpoint_files = list(checkpoint_dir.glob("a2c_*.zip"))
            if checkpoint_files:
                latest = max(checkpoint_files, key=lambda p: p.stat().st_mtime)
                print(f"   📥 Resumiendo desde: {latest}")
            else:
                print("   ⚠️  No hay checkpoints, iniciando desde cero")

    print()
    print("=" * 80)
    print("  INICIANDO ENTRENAMIENTO A2C...")
    print("=" * 80)
    print()

    start_time = time.time()

    # Ejecutar simulación con A2C
    result = simulate(
        schema_path=schema_path,
        agent_name="a2c",
        out_dir=out_dir,
        training_dir=paths.checkpoints_dir,
        carbon_intensity_kg_per_kwh=float(cfg['oe3']['grid']['carbon_intensity_kg_per_kwh']),
        seconds_per_time_step=int(cfg['project']['seconds_per_time_step']),
        # A2C config - sincronizado con a2c_sb3.py defaults
        a2c_timesteps=timesteps,
        a2c_n_steps=2048,
        a2c_learning_rate=1e-4,
        a2c_entropy_coef=0.01,
        a2c_gamma=0.99,
        a2c_gae_lambda=0.95,
        a2c_vf_coef=0.5,
        a2c_log_interval=500,
        a2c_checkpoint_freq_steps=1000,
        a2c_resume_checkpoints=resume,
        a2c_device=gpu_info['device'],
        # General
        deterministic_eval=True,
        use_multi_objective=True,
        multi_objective_priority=cfg["oe3"]["multi_objective"]["multi_objective_priority"],
        seed=42,
    )

    elapsed = time.time() - start_time

    # Resumen final
    print()
    print("=" * 80)
    print("  ✅ ENTRENAMIENTO A2C COMPLETADO")
    print("=" * 80)
    print()
    print(f"⏱️  Tiempo total: {timedelta(seconds=int(elapsed))}")
    print(f"📊 Steps ejecutados: {result.steps:,}")
    print()
    print("📈 MÉTRICAS DE ENERGÍA:")
    print(f"   Grid Import: {result.grid_import_kwh:,.0f} kWh")
    print(f"   Grid Export: {result.grid_export_kwh:,.0f} kWh")
    print(f"   PV Generation: {result.pv_generation_kwh:,.0f} kWh")
    print(f"   EV Charging: {result.ev_charging_kwh:,.0f} kWh")
    print(f"   Building Load: {result.building_load_kwh:,.0f} kWh")
    print()
    print("🌍 MÉTRICAS CO₂ (3-Component):")
    print(f"   CO₂ Emitido (Grid): {result.co2_emitido_grid_kg:,.0f} kg")
    print(f"   CO₂ Reducción Indirecta: {result.co2_reduccion_indirecta_kg:,.0f} kg")
    print(f"   CO₂ Reducción Directa: {result.co2_reduccion_directa_kg:,.0f} kg")
    print(f"   CO₂ NETO: {result.co2_neto_kg:,.0f} kg")

    if result.co2_neto_kg < 0:
        print()
        print("   🎉 ¡CARBONO-NEGATIVO! El sistema reduce más CO₂ del que emite")

    print()
    print("📁 ARCHIVOS GENERADOS:")
    print(f"   Results: {result.results_path}")
    print(f"   Timeseries: {result.timeseries_path}")
    print(f"   Checkpoints: {checkpoint_dir}")
    print()

    # Guardar resumen
    summary = {
        "agent": "A2C",
        "timestamp": datetime.now().isoformat(),
        "elapsed_seconds": elapsed,
        "timesteps": timesteps,
        "steps_executed": result.steps,
        "device": gpu_info['device'],
        "gpu_name": gpu_info.get('name', 'N/A'),
        "hyperparameters": {
            "n_steps": 2048,
            "learning_rate": 1e-4,
            "gamma": 0.99,
            "gae_lambda": 0.95,
            "ent_coef": 0.01,
            "vf_coef": 0.5,
            "max_grad_norm": 0.5,
        },
        "energy_metrics": {
            "grid_import_kwh": result.grid_import_kwh,
            "grid_export_kwh": result.grid_export_kwh,
            "pv_generation_kwh": result.pv_generation_kwh,
            "ev_charging_kwh": result.ev_charging_kwh,
            "building_load_kwh": result.building_load_kwh,
        },
        "co2_metrics": {
            "co2_emitido_grid_kg": result.co2_emitido_grid_kg,
            "co2_reduccion_indirecta_kg": result.co2_reduccion_indirecta_kg,
            "co2_reduccion_directa_kg": result.co2_reduccion_directa_kg,
            "co2_neto_kg": result.co2_neto_kg,
            "carbon_negative": result.co2_neto_kg < 0,
        },
        "multi_objective": {
            "priority": result.multi_objective_priority,
            "reward_co2_mean": result.reward_co2_mean,
            "reward_solar_mean": result.reward_solar_mean,
            "reward_total_mean": result.reward_total_mean,
        },
        "files": {
            "results": result.results_path,
            "timeseries": result.timeseries_path,
            "checkpoints": str(checkpoint_dir),
        }
    }

    summary_path = out_dir / "a2c_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    logger.info(f"📄 Resumen guardado: {summary_path}")

    return summary


# ==============================================================================
# CLI MAIN
# ==============================================================================
def main():
    """Entry point principal."""
    parser = argparse.ArgumentParser(
        description="🚀 A2C Training Pipeline - Producción",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Entrenamiento estándar (500k timesteps)
  python -m scripts.train_a2c_production

  # Entrenamiento rápido para testing
  python -m scripts.train_a2c_production --timesteps 50000

  # Entrenamiento extendido (1M timesteps)
  python -m scripts.train_a2c_production --timesteps 1000000

  # Continuar desde checkpoint
  python -m scripts.train_a2c_production --resume

  # Solo evaluación
  python -m scripts.train_a2c_production --eval-only

Comparativa de Agentes:
  ┌─────────┬────────────────┬───────────────┬───────────────┐
  │ Agente  │ Sample Effic.  │ Wall-Clock    │ Estabilidad   │
  ├─────────┼────────────────┼───────────────┼───────────────┤
  │ A2C     │ ★★☆☆☆ (bajo)   │ ★★★★★ (rápido)│ ★★★☆☆ (medio) │
  │ PPO     │ ★★★★☆ (alto)   │ ★★★☆☆ (medio) │ ★★★★★ (alto)  │
  │ SAC     │ ★★★★★ (mejor)  │ ★★☆☆☆ (lento) │ ★★★★☆ (alto)  │
  └─────────┴────────────────┴───────────────┴───────────────┘

  A2C es ideal para:
  - Pruebas rápidas de concepto
  - Cuando el tiempo de entrenamiento es crítico
  - Problemas con observaciones simples
        """
    )

    parser.add_argument(
        "--config",
        type=str,
        default="configs/default.yaml",
        help="Ruta al archivo de configuración (default: configs/default.yaml)"
    )
    parser.add_argument(
        "--timesteps",
        type=int,
        default=500000,
        help="Total de timesteps para entrenar (default: 500000)"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Continuar desde último checkpoint"
    )
    parser.add_argument(
        "--eval-only",
        action="store_true",
        help="Solo evaluar sin entrenar"
    )

    args = parser.parse_args()

    print_banner()

    try:
        result = run_training(
            config_path=Path(args.config),
            timesteps=args.timesteps,
            resume=args.resume,
            eval_only=args.eval_only,
        )

        # Exit code basado en CO₂ neto
        if result["co2_metrics"]["carbon_negative"]:
            print("🏆 ¡Objetivo logrado: Sistema Carbono-Negativo!")
            sys.exit(0)
        else:
            print("📊 Entrenamiento completado (carbono positivo)")
            sys.exit(0)

    except KeyboardInterrupt:
        print("\n\n⚠️  Entrenamiento interrumpido por usuario")
        print("   Los checkpoints guardados pueden usarse con --resume")
        sys.exit(130)
    except Exception as e:
        logger.error(f"❌ Error durante entrenamiento: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
