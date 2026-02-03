#!/usr/bin/env python3
"""
================================================================================
BASELINE 2: SIN SOLAR (0 kWp)
================================================================================
Ejecuta simulación de baseline SIN control RL y SIN generación solar.

Muestra el impacto de NO tener los 4,050 kWp instalados.
- Mall: 100 kW constante
- EVs: 50 kW constante  
- Solar: 0 kWp (desactivado)
- BESS: Desactivado
- Control RL: NO

Uso:
    python -m scripts.run_baseline2_nosolar
    python -m scripts.run_baseline2_nosolar --config configs/default.yaml

Resultado esperado: ~640,000 kg CO₂/año
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
    parser = argparse.ArgumentParser(description="Baseline 2: Sin Solar (0 kWp)")
    parser.add_argument(
        "--config",
        type=str,
        default="configs/default.yaml",
        help="Ruta al archivo de configuración YAML",
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
    logger.info("  🌑 BASELINE 2: SIN SOLAR (0 kWp)")
    logger.info("=" * 80)
    logger.info("")

    # Cargar configuración
    cfg, rp = load_all(args.config)

    # Configurar paths
    schema_path = rp.processed_dir / "citylearn" / cfg["oe3"]["dataset"]["name"] / "schema.json"
    out_dir = rp.outputs_dir / "baselines" / "baseline2_without_solar"
    out_dir.mkdir(parents=True, exist_ok=True)

    if not schema_path.exists():
        logger.error(f"Schema no encontrado: {schema_path}")
        logger.error("Ejecuta primero: python -m scripts.run_oe3_build_dataset")
        sys.exit(1)

    logger.info(f"  Schema: {schema_path}")
    logger.info(f"  Output: {out_dir}")
    logger.info("")

    # Ejecutar simulación
    carbon_intensity = float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"])
    seconds_per_step = int(cfg["project"]["seconds_per_time_step"])

    logger.info("  Iniciando simulación baseline (SIN solar)...")
    logger.info("")

    result = simulate(
        schema_path=schema_path,
        agent_name="uncontrolled",
        out_dir=out_dir,
        training_dir=None,  # Sin entrenamiento
        carbon_intensity_kg_per_kwh=carbon_intensity,
        seconds_per_time_step=seconds_per_step,
        use_multi_objective=True,
        multi_objective_priority="co2_focus",
        include_solar=False,  # ❌ SIN SOLAR
    )

    # Guardar resumen
    summary = {
        "baseline": "baseline2_without_solar",
        "description": "Baseline SIN generación solar (0 kWp)",
        "timestamp": datetime.now().isoformat(),
        "include_solar": False,
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
    }

    summary_path = out_dir / "baseline2_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    # Mostrar resultados
    logger.info("")
    logger.info("=" * 80)
    logger.info("  ✅ BASELINE 2 COMPLETADO")
    logger.info("=" * 80)
    logger.info("")
    logger.info(f"  📊 MÉTRICAS:")
    logger.info(f"     PV Generado:         {result.pv_generation_kwh:>12,.0f} kWh (desactivado)")
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
    logger.info(f"  📁 Archivos guardados en: {out_dir}")
    logger.info("=" * 80)

    return result


if __name__ == "__main__":
    main()
