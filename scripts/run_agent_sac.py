#!/usr/bin/env python3
"""
================================================================================
AGENTE SAC: Soft Actor-Critic
================================================================================
Ejecuta evaluación del agente SAC entrenado.

Este script:
1. Carga el checkpoint más reciente de SAC (si existe)
2. Ejecuta evaluación (1 año = 8760 horas)
3. Guarda métricas y timeseries

Uso:
    python -m scripts.run_agent_sac
    python -m scripts.run_agent_sac --train          # Entrenar desde cero
    python -m scripts.run_agent_sac --resume         # Continuar entrenamiento
    python -m scripts.run_agent_sac --eval-only      # Solo evaluación (default)

Checkpoints: checkpoints/sac/sac_final.zip
================================================================================
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Agente SAC - Evaluación/Entrenamiento")
    parser.add_argument(
        "--config",
        type=str,
        default="configs/default.yaml",
        help="Ruta al archivo de configuración YAML",
    )
    parser.add_argument(
        "--train",
        action="store_true",
        help="Entrenar agente (si no existe checkpoint)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Continuar entrenamiento desde último checkpoint",
    )
    parser.add_argument(
        "--eval-only",
        action="store_true",
        default=True,
        help="Solo evaluación usando checkpoint existente (default)",
    )
    parser.add_argument(
        "--episodes",
        type=int,
        default=3,
        help="Número de episodios de entrenamiento",
    )
    args = parser.parse_args()

    # Importar después de argparse para mejor UX
    try:
        from scripts._common import load_all
        from iquitos_citylearn.oe3.simulate import simulate
    except ImportError as e:
        logger.error(f"Error importando módulos: {e}")
        logger.error("Asegúrate de estar en el directorio raíz del proyecto")
        sys.exit(1)

    logger.info("")
    logger.info("=" * 80)
    logger.info("  🤖 AGENTE SAC (Soft Actor-Critic)")
    logger.info("=" * 80)
    logger.info("")

    # Cargar configuración
    cfg, rp = load_all(args.config)

    # Configurar paths
    schema_path = rp.processed_dir / "citylearn" / cfg["oe3"]["dataset"]["name"] / "schema.json"
    out_dir = rp.outputs_dir / "agents" / "sac"
    out_dir.mkdir(parents=True, exist_ok=True)

    checkpoint_dir = rp.checkpoints_dir / "sac"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    if not schema_path.exists():
        logger.error(f"Schema no encontrado: {schema_path}")
        logger.error("Ejecuta primero: python -m scripts.run_oe3_build_dataset")
        sys.exit(1)

    # Verificar checkpoint existente
    checkpoint_path = checkpoint_dir / "sac_final.zip"
    has_checkpoint = checkpoint_path.exists()

    logger.info(f"  Schema: {schema_path}")
    logger.info(f"  Output: {out_dir}")
    logger.info(f"  Checkpoint: {checkpoint_path} ({'✓ existe' if has_checkpoint else '✗ no existe'})")
    logger.info("")

    # Determinar modo de operación
    if args.train or args.resume:
        mode = "train"
        episodes = args.episodes
        resume = args.resume and has_checkpoint
        logger.info(f"  Modo: ENTRENAMIENTO ({episodes} episodios)")
        if resume:
            logger.info(f"  Resumiendo desde checkpoint existente")
    else:
        mode = "eval"
        episodes = 0  # No entrenar, solo evaluar
        resume = has_checkpoint
        if not has_checkpoint:
            logger.warning("  ⚠️  No hay checkpoint - ejecutará sin agente entrenado")
            logger.warning("     Para entrenar: python -m scripts.run_agent_sac --train")
        else:
            logger.info(f"  Modo: EVALUACIÓN (usando checkpoint existente)")
    logger.info("")

    # Ejecutar simulación
    carbon_intensity = float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"])
    seconds_per_step = int(cfg["project"]["seconds_per_time_step"])

    logger.info("  Iniciando agente SAC...")
    logger.info("")

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
        # SAC específico
        sac_episodes=episodes if mode == "train" else 0,
        sac_resume_checkpoints=resume,
        sac_batch_size=512,
        sac_learning_rate=5e-5,
        sac_checkpoint_freq_steps=1000,
    )

    # Guardar resumen
    summary = {
        "agent": "sac",
        "description": "Soft Actor-Critic (off-policy)",
        "timestamp": datetime.now().isoformat(),
        "mode": mode,
        "checkpoint_used": str(checkpoint_path) if has_checkpoint else None,
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

    # Mostrar resultados
    logger.info("")
    logger.info("=" * 80)
    logger.info("  ✅ AGENTE SAC COMPLETADO")
    logger.info("=" * 80)
    logger.info("")
    logger.info(f"  📊 MÉTRICAS:")
    logger.info(f"     PV Generado:         {result.pv_generation_kwh:>12,.0f} kWh")
    logger.info(f"     Grid Import:         {result.grid_import_kwh:>12,.0f} kWh")
    logger.info(f"     Grid Export:         {result.grid_export_kwh:>12,.0f} kWh")
    logger.info(f"     Demanda EV:          {result.ev_charging_kwh:>12,.0f} kWh")
    logger.info(f"     Demanda Mall:        {result.building_load_kwh:>12,.0f} kWh")
    logger.info("")
    logger.info(f"  🌍 CO₂ (3 COMPONENTES):")
    logger.info(f"     CO₂ Emitido Grid:    {result.co2_emitido_grid_kg:>12,.0f} kg")
    logger.info(f"     CO₂ Reducción Ind:   {result.co2_reduccion_indirecta_kg:>12,.0f} kg")
    logger.info(f"     CO₂ Reducción Dir:   {result.co2_reduccion_directa_kg:>12,.0f} kg")
    logger.info(f"     ─────────────────────────────────────")
    logger.info(f"     CO₂ NETO:            {result.co2_neto_kg:>12,.0f} kg")
    logger.info("")
    logger.info(f"  🎯 MULTI-OBJETIVO:")
    logger.info(f"     Reward Total Mean:   {result.reward_total_mean:>12.4f}")
    logger.info(f"     Reward CO₂ Mean:     {result.reward_co2_mean:>12.4f}")
    logger.info(f"     Reward Solar Mean:   {result.reward_solar_mean:>12.4f}")
    logger.info("")
    logger.info(f"  📁 Archivos guardados en: {out_dir}")
    logger.info("=" * 80)

    return result


if __name__ == "__main__":
    main()
