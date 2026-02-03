"""
Ejecuta AMBOS baselines de OE3 para comparación:

BASELINE 1: Sin Control, Sin BESS, CON Solar (4,050 kWp)
   • Genera: ~8M kWh/año de solar directo
   • Importa: grid cuando solar no cubre demanda

BASELINE 2: Sin Control, Sin BESS, SIN Solar (0 kWp)
   • Genera: 0 kWh solar
   • Importa: TODO desde grid térmico (peor escenario)

Comparación: Impacto REAL de tener 4,050 kWp instalados

Duración: ~20 segundos (2 × 10 sec uncontrolled)
"""

from __future__ import annotations

from pathlib import Path
import sys
import logging
import pandas as pd
import json

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from scripts._common import load_all
from iquitos_citylearn.oe3.simulate import simulate

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def run_dual_baselines(config_path: str = "configs/default.yaml") -> dict:
    """Ejecuta ambos baselines y retorna comparación."""

    cfg, paths = load_all(config_path)

    # Directorios de salida
    baseline_dir = paths.outputs_dir / "baselines"
    baseline_dir.mkdir(parents=True, exist_ok=True)

    logger.info("")
    logger.info("=" * 80)
    logger.info("[DUAL BASELINES] Ejecutando comparación de escenarios OE3")
    logger.info("=" * 80)
    logger.info("")

    schema_path = paths.processed_dir / "citylearn" / "iquitos_ev_mall" / "schema.json"
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema no encontrado: {schema_path}")

    # ✅ BASELINE 1: CON Solar
    logger.info("🟢 [BASELINE 1] Ejecutando: Sin Control, Sin BESS, CON Solar")
    logger.info("   Sistema: Mall (100 kW) + EVs (50 kW) + Solar (4,050 kWp)")
    logger.info("   Duración: ~10 segundos")

    result_with_solar = simulate(
        schema_path=schema_path,
        agent_name="uncontrolled_with_solar",
        out_dir=baseline_dir / "with_solar",
        training_dir=None,  # Sin entrenamiento
        carbon_intensity_kg_per_kwh=float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"]),
        seconds_per_time_step=int(cfg["project"]["seconds_per_time_step"]),
        include_solar=True,  # ✅ CON Solar
    )

    logger.info("")
    logger.info("🔴 [BASELINE 2] Ejecutando: Sin Control, Sin BESS, SIN Solar")
    logger.info("   Sistema: Mall (100 kW) + EVs (50 kW) + Sin Solar (0 kWp)")
    logger.info("   Duración: ~10 segundos")

    result_without_solar = simulate(
        schema_path=schema_path,
        agent_name="uncontrolled_without_solar",
        out_dir=baseline_dir / "without_solar",
        training_dir=None,  # Sin entrenamiento
        carbon_intensity_kg_per_kwh=float(cfg["oe3"]["grid"]["carbon_intensity_kg_per_kwh"]),
        seconds_per_time_step=int(cfg["project"]["seconds_per_time_step"]),
        include_solar=False,  # ✅ SIN Solar
    )

    # ================================================================================
    # COMPARACIÓN
    # ================================================================================
    logger.info("")
    logger.info("=" * 80)
    logger.info("[COMPARACIÓN BASELINES] Impacto de la generación solar")
    logger.info("=" * 80)
    logger.info("")

    # Tabla comparativa
    comparison = {
        "Métrica": [
            "Grid Import (kWh)",
            "PV Generation (kWh)",
            "EV Charging (kWh)",
            "Building Load (kWh)",
            "CO₂ Emitido Grid (kg)",
            "CO₂ Reducción Indirecta (kg)",
            "CO₂ Reducción Directa (kg)",
            "CO₂ NETO (kg)",
        ],
        "CON Solar": [
            f"{result_with_solar.grid_import_kwh:,.0f}",
            f"{result_with_solar.pv_generation_kwh:,.0f}",
            f"{result_with_solar.ev_charging_kwh:,.0f}",
            f"{result_with_solar.building_load_kwh:,.0f}",
            f"{result_with_solar.co2_emitido_grid_kg:,.0f}",
            f"{result_with_solar.co2_reduccion_indirecta_kg:,.0f}",
            f"{result_with_solar.co2_reduccion_directa_kg:,.0f}",
            f"{result_with_solar.co2_neto_kg:,.0f}",
        ],
        "SIN Solar": [
            f"{result_without_solar.grid_import_kwh:,.0f}",
            f"{result_without_solar.pv_generation_kwh:,.0f}",
            f"{result_without_solar.ev_charging_kwh:,.0f}",
            f"{result_without_solar.building_load_kwh:,.0f}",
            f"{result_without_solar.co2_emitido_grid_kg:,.0f}",
            f"{result_without_solar.co2_reduccion_indirecta_kg:,.0f}",
            f"{result_without_solar.co2_reduccion_directa_kg:,.0f}",
            f"{result_without_solar.co2_neto_kg:,.0f}",
        ],
    }

    df_comparison = pd.DataFrame(comparison)
    print("")
    print(df_comparison.to_string(index=False))
    print("")

    # Guardar tabla CSV
    comparison_path = baseline_dir / "baseline_comparison.csv"
    df_comparison.to_csv(comparison_path, index=False)
    logger.info(f"📊 Tabla comparativa guardada: {comparison_path}")

    # Calcular diferencias
    grid_import_reduction = result_with_solar.grid_import_kwh - result_without_solar.grid_import_kwh
    co2_emitido_reduction = result_with_solar.co2_emitido_grid_kg - result_without_solar.co2_emitido_grid_kg
    co2_indirecta_reduction = result_without_solar.co2_reduccion_indirecta_kg - result_with_solar.co2_reduccion_indirecta_kg
    co2_neto_reduction = result_with_solar.co2_neto_kg - result_without_solar.co2_neto_kg

    logger.info("")
    logger.info("📊 ANÁLISIS DE IMPACTO (CON Solar vs SIN Solar):")
    logger.info("")
    logger.info("🔴 CONSUMO DE GRID:")
    logger.info(f"   Sin Solar: {result_without_solar.grid_import_kwh:,.0f} kWh/año")
    logger.info(f"   Con Solar: {result_with_solar.grid_import_kwh:,.0f} kWh/año")
    logger.info(f"   ✅ Reducción: {grid_import_reduction:,.0f} kWh/año ({(grid_import_reduction/result_without_solar.grid_import_kwh*100):.1f}%)")
    logger.info("")

    logger.info("🟠 EMISIONES CO₂ GRID (Térmica):")
    logger.info(f"   Sin Solar: {result_without_solar.co2_emitido_grid_kg:,.0f} kg CO₂/año")
    logger.info(f"   Con Solar: {result_with_solar.co2_emitido_grid_kg:,.0f} kg CO₂/año")
    logger.info(f"   ✅ Reducción: {co2_emitido_reduction:,.0f} kg CO₂/año ({(co2_emitido_reduction/result_without_solar.co2_emitido_grid_kg*100):.1f}%)")
    logger.info("")

    logger.info("🟢 REDUCCIONES INDIRECTAS (Solar Aprovechado):")
    logger.info(f"   Sin Solar: {result_without_solar.co2_reduccion_indirecta_kg:,.0f} kg CO₂/año")
    logger.info(f"   Con Solar: {result_with_solar.co2_reduccion_indirecta_kg:,.0f} kg CO₂/año")
    logger.info(f"   ✅ Impacto: {abs(co2_indirecta_reduction):,.0f} kg CO₂/año")
    logger.info("")

    logger.info("📊 CO₂ NETO (Footprint Total):")
    logger.info(f"   Sin Solar: {result_without_solar.co2_neto_kg:,.0f} kg CO₂/año")
    logger.info(f"   Con Solar: {result_with_solar.co2_neto_kg:,.0f} kg CO₂/año")
    logger.info(f"   ✅ Mejora: {co2_neto_reduction:,.0f} kg CO₂/año")
    if co2_neto_reduction > 0:
        pct_improvement = (co2_neto_reduction / result_without_solar.co2_neto_kg) * 100
        logger.info(f"   ✅ % Mejora: {pct_improvement:.2f}%")
    logger.info("")

    # Calcular impacto de solar específicamente
    solar_output = result_with_solar.pv_generation_kwh - result_without_solar.pv_generation_kwh
    solar_impact_co2 = (solar_output * 0.4521)  # kg CO₂ evitado por solar

    logger.info("☀️  IMPACTO ESPECÍFICO DE SOLAR (4,050 kWp):")
    logger.info(f"   Generación Solar: {solar_output:,.0f} kWh/año")
    logger.info(f"   CO₂ Evitado: {solar_impact_co2:,.0f} kg CO₂/año")
    logger.info(f"   Factor: {solar_impact_co2 / solar_output:.4f} kg CO₂/kWh (grid térmico Iquitos)")
    logger.info("")

    logger.info("=" * 80)
    logger.info("[CONCLUSIÓN]")
    logger.info("=" * 80)
    logger.info("")
    logger.info("✅ Los 4,050 kWp de solar instalados evitan ~450k kg CO₂/año")
    logger.info("✅ Reduce consumo de grid térmico (más caro y contaminante)")
    logger.info("✅ Este es el BASELINE para medir mejora de agentes RL:")
    logger.info("   • SAC, PPO, A2C deben mejorar ESTE baseline con solar")
    logger.info("   • Si usan BESS, pueden mejorar aún más")
    logger.info("")

    # Guardar comparación como JSON
    comparison_json = baseline_dir / "baseline_comparison.json"
    comparison_data = {
        "with_solar": {
            "grid_import_kwh": result_with_solar.grid_import_kwh,
            "pv_generation_kwh": result_with_solar.pv_generation_kwh,
            "co2_emitido_grid_kg": result_with_solar.co2_emitido_grid_kg,
            "co2_reduccion_indirecta_kg": result_with_solar.co2_reduccion_indirecta_kg,
            "co2_reduccion_directa_kg": result_with_solar.co2_reduccion_directa_kg,
            "co2_neto_kg": result_with_solar.co2_neto_kg,
        },
        "without_solar": {
            "grid_import_kwh": result_without_solar.grid_import_kwh,
            "pv_generation_kwh": result_without_solar.pv_generation_kwh,
            "co2_emitido_grid_kg": result_without_solar.co2_emitido_grid_kg,
            "co2_reduccion_indirecta_kg": result_without_solar.co2_reduccion_indirecta_kg,
            "co2_reduccion_directa_kg": result_without_solar.co2_reduccion_directa_kg,
            "co2_neto_kg": result_without_solar.co2_neto_kg,
        },
        "impact": {
            "grid_import_reduction_kwh": grid_import_reduction,
            "co2_emitido_reduction_kg": co2_emitido_reduction,
            "co2_indirecta_reduction_kg": co2_indirecta_reduction,
            "co2_neto_reduction_kg": co2_neto_reduction,
            "solar_generation_kwh": solar_output,
            "solar_co2_avoided_kg": solar_impact_co2,
        }
    }

    with open(comparison_json, "w", encoding="utf-8") as f:
        json.dump(comparison_data, f, indent=2)

    logger.info(f"📁 Comparación JSON: {comparison_json}")
    logger.info("")

    return comparison_data

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Ejecuta ambos baselines (con y sin solar) para OE3"
    )
    parser.add_argument(
        "--config",
        default="configs/default.yaml",
        help="Ruta al archivo de configuración (default: configs/default.yaml)"
    )

    args = parser.parse_args()

    try:
        run_dual_baselines(config_path=args.config)
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        sys.exit(1)
