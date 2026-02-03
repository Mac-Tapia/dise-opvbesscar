#!/usr/bin/env python3
"""
================================================================================
TABLA COMPARATIVA: Baselines vs Agentes RL
================================================================================
Genera tabla comparativa final de todos los resultados.

Lee los archivos JSON de resumen generados por cada pipeline individual
y genera una tabla comparativa con métricas clave.

Uso:
    python -m scripts.compare_all_results
    python -m scripts.compare_all_results --format markdown
    python -m scripts.compare_all_results --format csv
    python -m scripts.compare_all_results --format json

Requiere haber ejecutado previamente:
    1. python -m scripts.run_baseline1_solar
    2. python -m scripts.run_baseline2_nosolar
    3. python -m scripts.run_agent_sac
    4. python -m scripts.run_agent_ppo
    5. python -m scripts.run_agent_a2c
================================================================================
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def load_summary(path: Path) -> Optional[Dict[str, Any]]:
    """Carga un archivo JSON de resumen."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning(f"Error cargando {path}: {e}")
        return None


def calculate_improvement(baseline_co2: float, agent_co2: float) -> float:
    """Calcula mejora porcentual vs baseline."""
    if baseline_co2 == 0:
        return 0.0
    return ((baseline_co2 - agent_co2) / abs(baseline_co2)) * 100


def main():
    parser = argparse.ArgumentParser(description="Tabla Comparativa de Resultados")
    parser.add_argument(
        "--config",
        type=str,
        default="configs/default.yaml",
        help="Ruta al archivo de configuración YAML",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["table", "markdown", "csv", "json"],
        default="table",
        help="Formato de salida",
    )
    args = parser.parse_args()

    # Importar después de argparse para mejor UX
    try:
        from scripts._common import load_all
    except ImportError as e:
        logger.error(f"Error importando módulos: {e}")
        sys.exit(1)

    logger.info("")
    logger.info("=" * 80)
    logger.info("  📊 TABLA COMPARATIVA: Baselines vs Agentes RL")
    logger.info("=" * 80)
    logger.info("")

    # Cargar configuración
    cfg, rp = load_all(args.config)

    # Definir rutas de resultados
    results_paths = {
        "baseline1_solar": rp.outputs_dir / "baselines" / "baseline1_with_solar" / "baseline1_summary.json",
        "baseline2_nosolar": rp.outputs_dir / "baselines" / "baseline2_without_solar" / "baseline2_summary.json",
        "sac": rp.outputs_dir / "agents" / "sac" / "sac_summary.json",
        "ppo": rp.outputs_dir / "agents" / "ppo" / "ppo_summary.json",
        "a2c": rp.outputs_dir / "agents" / "a2c" / "a2c_summary.json",
    }

    # Cargar todos los resultados
    results: Dict[str, Optional[Dict[str, Any]]] = {}
    for name, path in results_paths.items():
        results[name] = load_summary(path)
        status = "✓" if results[name] else "✗"
        logger.info(f"  {status} {name}: {path}")

    logger.info("")

    # Verificar que hay al menos un resultado
    available = {k: v for k, v in results.items() if v is not None}
    if not available:
        logger.error("No hay resultados disponibles. Ejecuta primero los pipelines individuales:")
        logger.error("  1. python -m scripts.run_baseline1_solar")
        logger.error("  2. python -m scripts.run_baseline2_nosolar")
        logger.error("  3. python -m scripts.run_agent_sac")
        logger.error("  4. python -m scripts.run_agent_ppo")
        logger.error("  5. python -m scripts.run_agent_a2c")
        sys.exit(1)

    # Obtener CO₂ de baseline1 para comparativas
    baseline1_co2 = None
    if results["baseline1_solar"]:
        baseline1_co2 = results["baseline1_solar"]["metrics"]["co2_neto_kg"]

    # Construir tabla de datos
    table_data: List[Dict[str, Any]] = []
    
    # Orden de filas
    row_order = [
        ("baseline1_solar", "🔆 Baseline 1 (Con Solar)", "baseline"),
        ("baseline2_nosolar", "🌑 Baseline 2 (Sin Solar)", "baseline"),
        ("sac", "🤖 SAC (Soft Actor-Critic)", "agent"),
        ("ppo", "🤖 PPO (Proximal Policy Opt.)", "agent"),
        ("a2c", "🤖 A2C (Advantage Actor-Critic)", "agent"),
    ]

    for key, display_name, category in row_order:
        r = results.get(key)
        if r is None:
            row = {
                "name": display_name,
                "category": category,
                "co2_emitido_kg": "N/A",
                "co2_reduccion_ind_kg": "N/A",
                "co2_reduccion_dir_kg": "N/A",
                "co2_neto_kg": "N/A",
                "grid_import_kwh": "N/A",
                "pv_generation_kwh": "N/A",
                "mejora_vs_baseline1": "N/A",
            }
        else:
            m = r["metrics"]
            co2_neto = m["co2_neto_kg"]
            mejora = calculate_improvement(baseline1_co2, co2_neto) if baseline1_co2 else 0.0
            
            row = {
                "name": display_name,
                "category": category,
                "co2_emitido_kg": m["co2_emitido_grid_kg"],
                "co2_reduccion_ind_kg": m["co2_reduccion_indirecta_kg"],
                "co2_reduccion_dir_kg": m["co2_reduccion_directa_kg"],
                "co2_neto_kg": co2_neto,
                "grid_import_kwh": m["grid_import_kwh"],
                "pv_generation_kwh": m["pv_generation_kwh"],
                "mejora_vs_baseline1": mejora,
            }
        table_data.append(row)

    # Mostrar según formato
    if args.format == "json":
        output = {
            "timestamp": datetime.now().isoformat(),
            "comparison_baseline": "baseline1_solar",
            "results": table_data,
        }
        print(json.dumps(output, indent=2, ensure_ascii=False))
    
    elif args.format == "csv":
        import csv
        import io
        output = io.StringIO()
        fieldnames = list(table_data[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(table_data)
        print(output.getvalue())

    elif args.format == "markdown":
        # Generar tabla Markdown
        print("\n## Tabla Comparativa: Baselines vs Agentes RL\n")
        print("| Escenario | CO₂ Emitido (kg) | CO₂ Red. Ind. (kg) | CO₂ Red. Dir. (kg) | **CO₂ NETO (kg)** | Mejora vs B1 |")
        print("|-----------|------------------|--------------------|--------------------|-------------------|--------------|")
        for row in table_data:
            if row["co2_neto_kg"] == "N/A":
                print(f"| {row['name']} | N/A | N/A | N/A | **N/A** | N/A |")
            else:
                mejora_str = f"{row['mejora_vs_baseline1']:+.1f}%" if isinstance(row['mejora_vs_baseline1'], float) else "N/A"
                print(f"| {row['name']} | {row['co2_emitido_kg']:,.0f} | {row['co2_reduccion_ind_kg']:,.0f} | {row['co2_reduccion_dir_kg']:,.0f} | **{row['co2_neto_kg']:,.0f}** | {mejora_str} |")
        print("")

    else:  # table (default)
        # Tabla formateada en consola
        logger.info("=" * 100)
        logger.info(f"  {'ESCENARIO':<35} {'CO₂ Emitido':>14} {'Red. Ind.':>12} {'Red. Dir.':>12} {'CO₂ NETO':>14} {'Mejora':>10}")
        logger.info(f"  {'':<35} {'(kg)':>14} {'(kg)':>12} {'(kg)':>12} {'(kg)':>14} {'vs B1':>10}")
        logger.info("=" * 100)

        for row in table_data:
            if row["co2_neto_kg"] == "N/A":
                logger.info(f"  {row['name']:<35} {'N/A':>14} {'N/A':>12} {'N/A':>12} {'N/A':>14} {'N/A':>10}")
            else:
                mejora_str = f"{row['mejora_vs_baseline1']:+.1f}%" if isinstance(row['mejora_vs_baseline1'], float) else "N/A"
                logger.info(
                    f"  {row['name']:<35} "
                    f"{row['co2_emitido_kg']:>14,.0f} "
                    f"{row['co2_reduccion_ind_kg']:>12,.0f} "
                    f"{row['co2_reduccion_dir_kg']:>12,.0f} "
                    f"{row['co2_neto_kg']:>14,.0f} "
                    f"{mejora_str:>10}"
                )

            # Separador entre baselines y agentes
            if row["category"] == "baseline" and row == table_data[1]:
                logger.info("-" * 100)

        logger.info("=" * 100)
        logger.info("")
        logger.info("  📝 LEYENDA:")
        logger.info("     CO₂ Emitido:    Emisiones por importación de grid (0.4521 kg/kWh)")
        logger.info("     Red. Ind.:      Reducción indirecta (solar + BESS evita grid)")
        logger.info("     Red. Dir.:      Reducción directa (EV evita gasolina)")
        logger.info("     CO₂ NETO:       Emitido - Red.Ind. - Red.Dir. (< 0 = carbono-negativo)")
        logger.info("     Mejora vs B1:   % reducción vs Baseline 1 (con solar)")
        logger.info("")

    # Guardar resumen comparativo
    comparison_path = rp.outputs_dir / "comparison_summary.json"
    comparison_data = {
        "timestamp": datetime.now().isoformat(),
        "comparison_baseline": "baseline1_solar",
        "baseline1_co2_neto_kg": baseline1_co2,
        "results": table_data,
    }
    comparison_path.write_text(json.dumps(comparison_data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"  📁 Resumen guardado en: {comparison_path}")
    logger.info("")

    # Mostrar mejor agente
    agents_available = [r for r in table_data if r["category"] == "agent" and r["co2_neto_kg"] != "N/A"]
    if agents_available:
        best_agent = min(agents_available, key=lambda x: x["co2_neto_kg"])
        logger.info(f"  🏆 MEJOR AGENTE: {best_agent['name']}")
        logger.info(f"     CO₂ Neto: {best_agent['co2_neto_kg']:,.0f} kg")
        if isinstance(best_agent['mejora_vs_baseline1'], float):
            logger.info(f"     Mejora vs Baseline 1: {best_agent['mejora_vs_baseline1']:+.1f}%")
        logger.info("")

    return table_data


if __name__ == "__main__":
    main()
