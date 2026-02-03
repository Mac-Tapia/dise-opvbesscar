#!/usr/bin/env python3
"""
================================================================================
🚀 PIPELINE SAC - PRODUCCIÓN
================================================================================
Entrenamiento optimizado de SAC para Iquitos EV + Solar + BESS.

Características:
- Visualización en tiempo real del progreso
- Checkpoints automáticos cada 1000 steps
- Detección automática de GPU (CUDA/MPS/CPU)
- Resumen de métricas CO₂ al finalizar
- Sincronización con dataset OE3 generado

Uso:
    # Entrenamiento completo (3 episodios = 26,280 steps)
    python -m scripts.train_sac_production

    # Entrenamiento rápido (1 episodio = 8,760 steps)
    python -m scripts.train_sac_production --episodes 1

    # Continuar desde checkpoint
    python -m scripts.train_sac_production --resume

    # Solo evaluación (sin entrenamiento)
    python -m scripts.train_sac_production --eval-only

================================================================================
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime
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
    print("  🚀 SAC TRAINING PIPELINE - PRODUCCIÓN")
    print("=" * 80)
    print("  Proyecto: pvbesscar (Iquitos EV + Solar + BESS)")
    print("  Agente: Soft Actor-Critic (Off-Policy)")
    print("  Objetivo: Minimizar CO₂ con control inteligente")
    print("=" * 80)
    print()


def print_config_summary(cfg: Dict[str, Any], checkpoint_dir: Path, out_dir: Path):
    """Imprime resumen de configuración."""
    print("📋 CONFIGURACIÓN:")
    print(f"   Dataset: iquitos_ev_mall (8,760 horas)")
    print(f"   Carbon Intensity: {cfg['oe3']['grid']['carbon_intensity_kg_per_kwh']} kg CO₂/kWh")
    print(f"   Timestep: {cfg['project']['seconds_per_time_step']}s (1 hora)")
    print()
    print("🔧 HIPERPARÁMETROS SAC:")
    print(f"   Batch Size: 512")
    print(f"   Learning Rate: 5e-5")
    print(f"   Gamma: 0.995")
    print(f"   Buffer Size: 200,000")
    print(f"   Hidden Layers: (256, 256)")
    print()
    print("📁 DIRECTORIOS:")
    print(f"   Checkpoints: {checkpoint_dir}")
    print(f"   Output: {out_dir}")
    print()


def detect_gpu() -> Dict[str, Any]:
    """Detecta GPU disponible y retorna información."""
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


def print_gpu_info(gpu_info: Dict[str, Any]):
    """Imprime información de GPU."""
    print("🖥️  DISPOSITIVO:")
    if gpu_info["device"] == "cuda":
        print(f"   GPU: {gpu_info['name']}")
        print(f"   VRAM: {gpu_info['memory_gb']} GB")
        print(f"   CUDA: {gpu_info.get('cuda_version', 'N/A')}")
    elif gpu_info["device"] == "mps":
        print(f"   GPU: {gpu_info['name']}")
    else:
        print(f"   CPU: Entrenamiento en CPU (más lento)")
    print()


def format_time(seconds: float) -> str:
    """Formatea segundos a formato legible."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"


def print_progress_bar(current: int, total: int, prefix: str = "", suffix: str = "", length: int = 40):
    """Imprime barra de progreso."""
    percent = current / total if total > 0 else 0
    filled = int(length * percent)
    bar = "█" * filled + "░" * (length - filled)
    print(f"\r{prefix} |{bar}| {percent*100:.1f}% {suffix}", end="", flush=True)


class ProgressTracker:
    """Tracker de progreso para entrenamiento SAC."""

    def __init__(self, total_steps: int, log_interval: int = 500):
        self.total_steps = total_steps
        self.log_interval = log_interval
        self.start_time = time.time()
        self.current_step = 0
        self.rewards: list[float] = []
        self.losses: list[float] = []

    def update(self, step: int, reward: float = 0.0, loss: float = 0.0):
        """Actualiza el progreso."""
        self.current_step = step
        if reward != 0.0:
            self.rewards.append(reward)
        if loss != 0.0:
            self.losses.append(loss)

    def get_eta(self) -> str:
        """Calcula tiempo restante estimado."""
        if self.current_step == 0:
            return "Calculando..."

        elapsed = time.time() - self.start_time
        rate = self.current_step / elapsed
        remaining = (self.total_steps - self.current_step) / rate if rate > 0 else 0
        return format_time(remaining)

    def get_summary(self) -> Dict[str, Any]:
        """Retorna resumen de métricas."""
        elapsed = time.time() - self.start_time
        return {
            "total_steps": self.current_step,
            "elapsed_time": format_time(elapsed),
            "steps_per_sec": self.current_step / elapsed if elapsed > 0 else 0,
            "mean_reward": np.mean(self.rewards) if self.rewards else 0.0,
            "std_reward": np.std(self.rewards) if self.rewards else 0.0,
            "mean_loss": np.mean(self.losses) if self.losses else 0.0,
        }


def validate_dataset(schema_path: Path) -> bool:
    """Valida que el dataset está listo."""
    if not schema_path.exists():
        logger.error(f"❌ Schema no encontrado: {schema_path}")
        logger.error("   Ejecuta primero: python -m scripts.run_oe3_build_dataset")
        return False

    # Verificar archivos de chargers
    dataset_dir = schema_path.parent
    charger_files = list(dataset_dir.glob("charger_simulation_*.csv"))

    if len(charger_files) < 128:
        logger.error(f"❌ Solo {len(charger_files)}/128 archivos de chargers encontrados")
        logger.error("   Regenera el dataset: python -m scripts.run_oe3_build_dataset")
        return False

    logger.info(f"✅ Dataset validado: 128 chargers, schema OK")
    return True


def run_training(
    cfg: Dict[str, Any],
    rp: Any,
    episodes: int = 3,
    resume: bool = False,
    eval_only: bool = False,
) -> Optional[Any]:
    """Ejecuta entrenamiento SAC."""
    from iquitos_citylearn.oe3.simulate import simulate

    # Configurar paths
    schema_path = rp.processed_dir / "citylearn" / cfg["oe3"]["dataset"]["name"] / "schema.json"
    out_dir = rp.outputs_dir / "agents" / "sac"
    out_dir.mkdir(parents=True, exist_ok=True)

    checkpoint_dir = rp.checkpoints_dir / "sac"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    # Validar dataset
    if not validate_dataset(schema_path):
        return None

    # Verificar checkpoint existente
    checkpoint_path = checkpoint_dir / "sac_final.zip"
    has_checkpoint = checkpoint_path.exists()

    # Mostrar configuración
    print_config_summary(cfg, checkpoint_dir, out_dir)

    # Detectar GPU
    gpu_info = detect_gpu()
    print_gpu_info(gpu_info)

    # Determinar modo
    if eval_only:
        mode = "eval"
        train_episodes = 0
        print("🎯 MODO: Evaluación (sin entrenamiento)")
        if not has_checkpoint:
            logger.warning("⚠️  No hay checkpoint - resultados sin agente entrenado")
    else:
        mode = "train"
        train_episodes = episodes
        total_steps = episodes * 8760
        print(f"🎯 MODO: Entrenamiento ({episodes} episodios = {total_steps:,} steps)")
        if resume and has_checkpoint:
            print(f"   📥 Resumiendo desde: {checkpoint_path}")

    print()
    print("=" * 80)
    print("  INICIANDO ENTRENAMIENTO SAC...")
    print("=" * 80)
    print()

    # Crear tracker de progreso
    tracker = ProgressTracker(total_steps=train_episodes * 8760)
    start_time = time.time()

    # Ejecutar simulación/entrenamiento
    carbon_intensity = float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"])
    seconds_per_step = int(cfg["project"]["seconds_per_time_step"])

    try:
        result = simulate(
            schema_path=schema_path,
            agent_name="sac",
            out_dir=out_dir,
            training_dir=rp.checkpoints_dir if mode == "train" else None,
            carbon_intensity_kg_per_kwh=carbon_intensity,
            seconds_per_time_step=seconds_per_step,
            use_multi_objective=True,
            multi_objective_priority="co2_focus",
            include_solar=True,
            # SAC hiperparámetros optimizados
            sac_episodes=train_episodes,
            sac_resume_checkpoints=resume and has_checkpoint,
            sac_batch_size=512,
            sac_learning_rate=5e-5,
            sac_checkpoint_freq_steps=1000,
            sac_log_interval=500,
            sac_use_amp=gpu_info["device"] == "cuda",
            sac_device=gpu_info["device"],
        )
    except Exception as e:
        logger.error(f"❌ Error durante entrenamiento: {e}")
        import traceback
        traceback.print_exc()
        return None

    elapsed_time = time.time() - start_time

    # Guardar resumen
    summary = {
        "agent": "sac",
        "description": "Soft Actor-Critic (Off-Policy) - Producción",
        "timestamp": datetime.now().isoformat(),
        "mode": mode,
        "episodes": train_episodes,
        "elapsed_time_seconds": elapsed_time,
        "elapsed_time_formatted": format_time(elapsed_time),
        "device": gpu_info["device"],
        "gpu_name": gpu_info.get("name", "N/A"),
        "checkpoint_path": str(checkpoint_path) if has_checkpoint or mode == "train" else None,
        "metrics": {
            "steps": result.steps,
            "grid_import_kwh": result.grid_import_kwh,
            "grid_export_kwh": result.grid_export_kwh,
            "pv_generation_kwh": result.pv_generation_kwh,
            "ev_charging_kwh": result.ev_charging_kwh,
            "building_load_kwh": result.building_load_kwh,
            "co2_emitido_grid_kg": result.co2_emitido_grid_kg,
            "co2_reduccion_indirecta_kg": result.co2_reduccion_indirecta_kg,
            "co2_reduccion_directa_kg": result.co2_reduccion_directa_kg,
            "co2_neto_kg": result.co2_neto_kg,
        },
        "multi_objective": {
            "priority": result.multi_objective_priority,
            "reward_co2_mean": result.reward_co2_mean,
            "reward_solar_mean": result.reward_solar_mean,
            "reward_total_mean": result.reward_total_mean,
        },
    }

    summary_path = out_dir / "sac_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    # Mostrar resultados finales
    print()
    print("=" * 80)
    print("  ✅ SAC ENTRENAMIENTO COMPLETADO")
    print("=" * 80)
    print()
    print("📊 MÉTRICAS DE ENERGÍA:")
    print(f"   PV Generado:         {result.pv_generation_kwh:>12,.0f} kWh")
    print(f"   Grid Import:         {result.grid_import_kwh:>12,.0f} kWh")
    print(f"   Grid Export:         {result.grid_export_kwh:>12,.0f} kWh")
    print(f"   Demanda EV:          {result.ev_charging_kwh:>12,.0f} kWh")
    print(f"   Demanda Mall:        {result.building_load_kwh:>12,.0f} kWh")
    print()
    print("🌍 CO₂ (3 COMPONENTES):")
    print(f"   CO₂ Emitido Grid:    {result.co2_emitido_grid_kg:>12,.0f} kg")
    print(f"   CO₂ Reducción Ind:   {result.co2_reduccion_indirecta_kg:>12,.0f} kg")
    print(f"   CO₂ Reducción Dir:   {result.co2_reduccion_directa_kg:>12,.0f} kg")
    print(f"   {'─' * 45}")
    print(f"   CO₂ NETO:            {result.co2_neto_kg:>12,.0f} kg")

    if result.co2_neto_kg < 0:
        print(f"   ✅ CARBONO-NEGATIVO: El sistema reduce más CO₂ del que emite")

    print()
    print("🎯 MULTI-OBJETIVO:")
    print(f"   Reward Total Mean:   {result.reward_total_mean:>12.4f}")
    print(f"   Reward CO₂ Mean:     {result.reward_co2_mean:>12.4f}")
    print(f"   Reward Solar Mean:   {result.reward_solar_mean:>12.4f}")
    print()
    print("⏱️  TIEMPO:")
    print(f"   Duración Total:      {format_time(elapsed_time)}")
    print(f"   Steps/segundo:       {result.steps / elapsed_time:.1f}")
    print()
    print("📁 ARCHIVOS GENERADOS:")
    print(f"   Resumen: {summary_path}")
    print(f"   Timeseries: {out_dir / 'timeseries_sac.csv'}")
    if mode == "train":
        print(f"   Checkpoint: {checkpoint_path}")
    print()
    print("=" * 80)

    return result


def main():
    """Entry point principal."""
    parser = argparse.ArgumentParser(
        description="🚀 SAC Training Pipeline - Producción",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Entrenamiento completo (3 episodios)
  python -m scripts.train_sac_production

  # Entrenamiento rápido (1 episodio)
  python -m scripts.train_sac_production --episodes 1

  # Continuar desde checkpoint
  python -m scripts.train_sac_production --resume

  # Solo evaluación
  python -m scripts.train_sac_production --eval-only
        """
    )
    parser.add_argument(
        "--config",
        type=str,
        default="configs/default.yaml",
        help="Ruta al archivo de configuración YAML",
    )
    parser.add_argument(
        "--episodes",
        type=int,
        default=3,
        help="Número de episodios de entrenamiento (default: 3 = 26,280 steps)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Continuar entrenamiento desde último checkpoint",
    )
    parser.add_argument(
        "--eval-only",
        action="store_true",
        help="Solo evaluación usando checkpoint existente (sin entrenar)",
    )
    args = parser.parse_args()

    # Banner
    print_banner()

    # Importar después de argparse
    try:
        from scripts._common import load_all
    except ImportError as e:
        logger.error(f"Error importando módulos: {e}")
        logger.error("Asegúrate de estar en el directorio raíz del proyecto")
        sys.exit(1)

    # Cargar configuración
    try:
        cfg, rp = load_all(args.config)
        logger.info(f"✅ Configuración cargada: {args.config}")
    except Exception as e:
        logger.error(f"❌ Error cargando configuración: {e}")
        sys.exit(1)

    # Ejecutar entrenamiento
    result = run_training(
        cfg=cfg,
        rp=rp,
        episodes=args.episodes,
        resume=args.resume,
        eval_only=args.eval_only,
    )

    if result is None:
        logger.error("❌ Entrenamiento falló")
        sys.exit(1)

    logger.info("✅ Pipeline SAC completado exitosamente")
    return result


if __name__ == "__main__":
    main()
