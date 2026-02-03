#!/usr/bin/env python3
"""
================================================================================
🚀 PIPELINE PPO - PRODUCCIÓN
================================================================================
Entrenamiento optimizado de PPO para Iquitos EV + Solar + BESS.

Características:
- Visualización en tiempo real del progreso
- Checkpoints automáticos cada 1000 steps
- Detección automática de GPU (CUDA/MPS/CPU)
- Resumen de métricas CO₂ al finalizar
- Sincronización con dataset OE3 generado
- GAE (Generalized Advantage Estimation) para mejor policy gradient
- KL Divergence adaptativo para estabilidad

Uso:
    # Entrenamiento completo (100k timesteps por defecto)
    python -m scripts.train_ppo_production

    # Entrenamiento extendido (500k timesteps)
    python -m scripts.train_ppo_production --timesteps 500000

    # Entrenamiento rápido para testing (10k timesteps)
    python -m scripts.train_ppo_production --timesteps 10000

    # Continuar desde checkpoint
    python -m scripts.train_ppo_production --resume

    # Solo evaluación (sin entrenamiento)
    python -m scripts.train_ppo_production --eval-only

================================================================================
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np


# Configurar logging con colores
class ColorFormatter(logging.Formatter):
    """Formatter con colores para terminal."""

    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m',
    }

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        record.levelname = f"{color}{record.levelname}{reset}"
        return super().format(record)


# Setup logging
handler = logging.StreamHandler()
handler.setFormatter(ColorFormatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"))
logging.basicConfig(level=logging.INFO, handlers=[handler])
logger = logging.getLogger(__name__)


def print_banner():
    """Imprime banner de inicio."""
    print()
    print("=" * 80)
    print("  🚀 PPO TRAINING PIPELINE - PRODUCCIÓN")
    print("=" * 80)
    print("  Proyecto: pvbesscar (Iquitos EV + Solar + BESS)")
    print("  Agente: Proximal Policy Optimization (On-Policy)")
    print("  Objetivo: Minimizar CO₂ con control inteligente")
    print("=" * 80)
    print()


def print_config_summary(cfg: Dict[str, Any], checkpoint_dir: Path, out_dir: Path, timesteps: int):
    """Imprime resumen de configuración."""
    print("📋 CONFIGURACIÓN:")
    print(f"   Dataset: iquitos_ev_mall (8,760 horas)")
    print(f"   Carbon Intensity: {cfg['oe3']['grid']['carbon_intensity_kg_per_kwh']} kg CO₂/kWh")
    print(f"   Timestep: {cfg['project']['seconds_per_time_step']}s (1 hora)")
    print()
    print("🔧 HIPERPARÁMETROS PPO:")
    print(f"   Timesteps Totales: {timesteps:,}")
    print(f"   N-Steps: 2,048 (rollout buffer)")
    print(f"   Batch Size: 256")
    print(f"   N-Epochs: 10")
    print(f"   Learning Rate: 1e-4 (linear decay)")
    print(f"   Gamma: 0.99")
    print(f"   GAE Lambda: 0.98")
    print(f"   Clip Range: 0.2")
    print(f"   Entropy Coef: 0.01 (decaying)")
    print(f"   Hidden Layers: (256, 256)")
    print()
    print("📁 DIRECTORIOS:")
    print(f"   Checkpoints: {checkpoint_dir}")
    print(f"   Output: {out_dir}")
    print()


def detect_gpu() -> Dict[str, Any]:
    """Detecta GPU disponible y retorna info."""
    info: Dict[str, Any] = {"device": "cpu", "name": "CPU", "memory_gb": 0.0}
    try:
        import torch  # type: ignore
        if torch.cuda.is_available():
            info["device"] = "cuda"
            info["name"] = str(torch.cuda.get_device_name(0))
            info["memory_gb"] = round(float(torch.cuda.get_device_properties(0).total_memory) / 1e9, 2)
            cuda_ver = torch.version.cuda
            if cuda_ver is not None:
                info["cuda_version"] = str(cuda_ver)
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            info["device"] = "mps"
            info["name"] = "Apple Silicon (MPS)"
    except (ImportError, AttributeError, RuntimeError):
        pass
    return info


def validate_dataset(schema_path: Path) -> bool:
    """Valida que el dataset existe y tiene 128 chargers."""
    if not schema_path.exists():
        logger.error(f"❌ Schema no encontrado: {schema_path}")
        return False

    dataset_dir = schema_path.parent
    charger_files = list(dataset_dir.glob("charger_simulation_*.csv"))

    if len(charger_files) != 128:
        logger.error(f"❌ Chargers incompletos: {len(charger_files)}/128")
        return False

    logger.info(f"✅ Dataset validado: {len(charger_files)} chargers, schema OK")
    return True


def run_training(
    config_path: Path,
    timesteps: int = 100000,
    resume: bool = False,
    eval_only: bool = False,
) -> Dict[str, Any]:
    """Ejecuta entrenamiento PPO.

    Args:
        config_path: Ruta al archivo de configuración
        timesteps: Total de timesteps para entrenar
        resume: Si True, continúa desde último checkpoint
        eval_only: Si True, solo evalúa sin entrenar

    Returns:
        Dict con resultados y métricas
    """
    from scripts._common import load_all
    from iquitos_citylearn.oe3.simulate import simulate

    # Cargar configuración
    cfg, paths = load_all(str(config_path))
    logger.info(f"✅ Configuración cargada: {config_path}")

    # Rutas
    schema_path = paths.processed_dir / "citylearn" / "iquitos_ev_mall" / "schema.json"
    checkpoint_dir = paths.checkpoints_dir / "ppo"
    out_dir = Path("outputs/agents/ppo")

    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Validar dataset
    if not validate_dataset(schema_path):
        raise RuntimeError("Dataset inválido. Ejecuta: python -m scripts.run_oe3_build_dataset")

    # Detectar GPU
    gpu_info = detect_gpu()

    # Imprimir configuración
    print_config_summary(cfg, checkpoint_dir, out_dir, timesteps)

    print("🖥️  DISPOSITIVO:")
    print(f"   GPU: {gpu_info['name']}")
    if gpu_info['device'] != 'cpu':
        print(f"   VRAM: {gpu_info['memory_gb']:.2f} GB")
        if 'cuda_version' in gpu_info:
            print(f"   CUDA: {gpu_info['cuda_version']}")
    print()

    # Modo
    if eval_only:
        print("🎯 MODO: Solo evaluación (sin entrenamiento)")
        timesteps = 8760  # 1 episodio para eval
    else:
        print(f"🎯 MODO: Entrenamiento ({timesteps:,} timesteps)")
        if resume:
            checkpoint_files = list(checkpoint_dir.glob("ppo_*.zip"))
            if checkpoint_files:
                latest = max(checkpoint_files, key=lambda p: p.stat().st_mtime)
                print(f"   📥 Resumiendo desde: {latest}")
            else:
                print("   ⚠️  No hay checkpoints, iniciando desde cero")

    print()
    print("=" * 80)
    print("  INICIANDO ENTRENAMIENTO PPO...")
    print("=" * 80)
    print()

    start_time = time.time()

    # Ejecutar simulación
    result = simulate(
        schema_path=schema_path,
        agent_name="ppo",
        out_dir=out_dir,
        training_dir=paths.checkpoints_dir,
        carbon_intensity_kg_per_kwh=float(cfg['oe3']['grid']['carbon_intensity_kg_per_kwh']),
        seconds_per_time_step=int(cfg['project']['seconds_per_time_step']),
        # PPO config
        ppo_timesteps=timesteps,
        ppo_n_steps=2048,
        ppo_batch_size=256,
        ppo_use_amp=True,
        ppo_device=gpu_info['device'],
        ppo_target_kl=0.02,
        ppo_kl_adaptive=True,
        ppo_log_interval=500,
        ppo_checkpoint_freq_steps=1000,
        ppo_resume_checkpoints=resume,
        # General
        deterministic_eval=True,
        use_multi_objective=True,
        multi_objective_priority="co2_focus",
        seed=42,
    )

    elapsed = time.time() - start_time

    # Resumen final
    print()
    print("=" * 80)
    print("  ✅ ENTRENAMIENTO PPO COMPLETADO")
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
        "agent": "PPO",
        "timestamp": datetime.now().isoformat(),
        "elapsed_seconds": elapsed,
        "timesteps": timesteps,
        "steps_executed": result.steps,
        "device": gpu_info['device'],
        "gpu_name": gpu_info.get('name', 'N/A'),
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

    summary_path = out_dir / "ppo_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    logger.info(f"📄 Resumen guardado: {summary_path}")

    return summary


def main():
    """Entry point principal."""
    parser = argparse.ArgumentParser(
        description="🚀 PPO Training Pipeline - Producción",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Entrenamiento estándar (100k timesteps)
  python -m scripts.train_ppo_production

  # Entrenamiento extendido (500k timesteps)
  python -m scripts.train_ppo_production --timesteps 500000

  # Entrenamiento rápido para testing
  python -m scripts.train_ppo_production --timesteps 10000

  # Continuar desde checkpoint
  python -m scripts.train_ppo_production --resume

  # Solo evaluación
  python -m scripts.train_ppo_production --eval-only
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
        default=100000,
        help="Total de timesteps para entrenar (default: 100000)"
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
            sys.exit(0)  # Éxito: carbono negativo
        else:
            sys.exit(0)  # Éxito pero carbono positivo

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
