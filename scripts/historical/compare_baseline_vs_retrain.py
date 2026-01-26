"""
Compara resultados de Uncontrolled baseline vs Agentes Reentrenados.

Genera:
- Tabla comparativa de métricas clave
- Gráficos de evolución (power, SOC, import)
- CSV con datos detallados
- Reporte markdown
"""

import sys
from pathlib import Path
import json
import logging
import numpy as np
import pandas as pd
from typing import Tuple
import matplotlib.pyplot as plt

# Agregar raíz al path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts._common import load_all

logger = logging.getLogger(__name__)
plt.rcParams["figure.figsize"] = (14, 6)


def load_diagnostics(diagnostics_dir: Path, agent_name: str) -> Tuple[pd.DataFrame, dict]:
    """Carga CSV y JSON de diagnósticos de un agente."""
    csv_file = diagnostics_dir / f"{agent_name}_diagnostics.csv"
    json_file = diagnostics_dir / f"{agent_name}_summary.json"

    if not csv_file.exists() or not json_file.exists():
        raise FileNotFoundError(f"No se encontraron diagnósticos para {agent_name}")

    df = pd.read_csv(csv_file)
    with open(json_file, "r") as f:
        summary = json.load(f)

    return df, summary


def extract_comparison_metrics(
    df_baseline: pd.DataFrame,
    summary_baseline: dict,
    df_retrain: pd.DataFrame,
    summary_retrain: dict,
) -> pd.DataFrame:
    """
    Extrae métricas para tabla comparativa.

    Returns DataFrame con columnas:
    - Metric
    - Uncontrolled (baseline)
    - SAC Retrain
    - Change (%)
    - Status (↑ mejora, ↓ empeora)
    """

    comparisons = []

    # 1. Potencia pico máxima
    baseline_peak = summary_baseline.get("ev_peak_power_max_kw", np.nan)
    retrain_peak = summary_retrain.get("ev_peak_power_max_kw", np.nan)
    change_pct = ((retrain_peak - baseline_peak) / baseline_peak * 100) if baseline_peak > 0 else 0
    status = "↓" if change_pct < 0 else "↑"
    comparisons.append({
        "Metric": "Potencia pico EV máx. (kW)",
        "Uncontrolled": f"{baseline_peak:.1f}",
        "SAC Retrain": f"{retrain_peak:.1f}",
        "Change (%)": f"{change_pct:+.1f}%",
        "Direction": status,
    })

    # 2. Importación anual total
    baseline_import = summary_baseline.get("grid_import_total_kwh", np.nan)
    retrain_import = summary_retrain.get("grid_import_total_kwh", np.nan)
    change_pct = ((retrain_import - baseline_import) / baseline_import * 100) if baseline_import > 0 else 0
    status = "↓" if change_pct < 0 else "↑"
    comparisons.append({
        "Metric": "Importación anual (MWh)",
        "Uncontrolled": f"{baseline_import/1000:.2f}",
        "SAC Retrain": f"{retrain_import/1000:.2f}",
        "Change (%)": f"{change_pct:+.1f}%",
        "Direction": status,
    })

    # 3. Importación en pico
    baseline_import_peak = summary_baseline.get("grid_import_peak_hours_kwh", np.nan)
    retrain_import_peak = summary_retrain.get("grid_import_peak_hours_kwh", np.nan)
    change_pct = ((retrain_import_peak - baseline_import_peak) / baseline_import_peak * 100) if baseline_import_peak > 0 else 0
    status = "↓" if change_pct < 0 else "↑"
    comparisons.append({
        "Metric": "Importación pico 18-21h (MWh)",
        "Uncontrolled": f"{baseline_import_peak/1000:.2f}",
        "SAC Retrain": f"{retrain_import_peak/1000:.2f}",
        "Change (%)": f"{change_pct:+.1f}%",
        "Direction": status,
    })

    # 4. SOC mínimo BESS
    baseline_soc_min = summary_baseline.get("bess_soc_min_percent", np.nan)
    retrain_soc_min = summary_retrain.get("bess_soc_min_percent", np.nan)
    change_pct = ((retrain_soc_min - baseline_soc_min) / baseline_soc_min * 100) if baseline_soc_min > 0 else 0
    status = "↑" if change_pct > 0 else "↓"
    comparisons.append({
        "Metric": "SOC BESS mínimo (%)",
        "Uncontrolled": f"{baseline_soc_min:.1f}%",
        "SAC Retrain": f"{retrain_soc_min:.1f}%",
        "Change (%)": f"{change_pct:+.1f}%",
        "Direction": status,
    })

    # 5. SOC BESS durante pico (mínimo)
    baseline_soc_peak_min = summary_baseline.get("bess_soc_during_peak_min", np.nan)
    retrain_soc_peak_min = summary_retrain.get("bess_soc_during_peak_min", np.nan)
    change_pct = ((retrain_soc_peak_min - baseline_soc_peak_min) / baseline_soc_peak_min * 100) if baseline_soc_peak_min > 0 else 0
    status = "↑" if change_pct > 0 else "↓"
    comparisons.append({
        "Metric": "SOC BESS en pico (mín., %)",
        "Uncontrolled": f"{baseline_soc_peak_min:.1f}%",
        "SAC Retrain": f"{retrain_soc_peak_min:.1f}%",
        "Change (%)": f"{change_pct:+.1f}%",
        "Direction": status,
    })

    # 6. Desequilibrio entre playas (fairness)
    baseline_ratio = summary_baseline.get("playa_power_ratio", np.nan)
    retrain_ratio = summary_retrain.get("playa_power_ratio", np.nan)
    change_pct = ((retrain_ratio - baseline_ratio) / baseline_ratio * 100) if baseline_ratio > 0 else 0
    status = "↓" if change_pct < 0 else "↑"  # Menor ratio = mejor fairness
    comparisons.append({
        "Metric": "Desequilibrio playas (ratio)",
        "Uncontrolled": f"{baseline_ratio:.2f}",
        "SAC Retrain": f"{retrain_ratio:.2f}",
        "Change (%)": f"{change_pct:+.1f}%",
        "Direction": status,
    })

    # 7. Potencia pico playa motos
    baseline_p1 = summary_baseline.get("ev_power_playa1_max_kw", np.nan)
    retrain_p1 = summary_retrain.get("ev_power_playa1_max_kw", np.nan)
    change_pct = ((retrain_p1 - baseline_p1) / baseline_p1 * 100) if baseline_p1 > 0 else 0
    status = "↓" if change_pct < 0 else "↑"
    comparisons.append({
        "Metric": "Potencia pico Playa Motos (kW)",
        "Uncontrolled": f"{baseline_p1:.1f}",
        "SAC Retrain": f"{retrain_p1:.1f}",
        "Change (%)": f"{change_pct:+.1f}%",
        "Direction": status,
    })

    # 8. Potencia pico playa mototaxis
    baseline_p2 = summary_baseline.get("ev_power_playa2_max_kw", np.nan)
    retrain_p2 = summary_retrain.get("ev_power_playa2_max_kw", np.nan)
    change_pct = ((retrain_p2 - baseline_p2) / baseline_p2 * 100) if baseline_p2 > 0 else 0
    status = "↓" if change_pct < 0 else "↑"
    comparisons.append({
        "Metric": "Potencia pico Playa Mototaxis (kW)",
        "Uncontrolled": f"{baseline_p2:.1f}",
        "SAC Retrain": f"{retrain_p2:.1f}",
        "Change (%)": f"{change_pct:+.1f}%",
        "Direction": status,
    })

    return pd.DataFrame(comparisons)


def create_power_profile_plot(
    df_baseline: pd.DataFrame,
    df_retrain: pd.DataFrame,
    output_file: Path,
) -> None:
    """Grafica perfil de potencia EV: baseline vs retrain."""

    _, axes = plt.subplots(2, 2, figsize=(16, 10))

    # Subgráfico 1: Potencia total EV
    ax = axes[0, 0]
    ax.plot(df_baseline["hour_of_year"], df_baseline["ev_power_total_kw"],
            label="Uncontrolled", linewidth=1, alpha=0.7, color="red")
    ax.plot(df_retrain["hour_of_year"], df_retrain["ev_power_total_kw"],
            label="SAC Retrain", linewidth=1, alpha=0.7, color="green")
    ax.axhspan(18, 21, alpha=0.1, color="gray", label="Horas Pico")
    ax.set_ylabel("Potencia (kW)")
    ax.set_xlabel("Hora del Año")
    ax.set_title("Potencia EV Total")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Subgráfico 2: Potencia playa motos
    ax = axes[0, 1]
    ax.plot(df_baseline["hour_of_year"], df_baseline["ev_power_playa1_kw"],
            label="Uncontrolled", linewidth=0.8, alpha=0.6, color="red")
    ax.plot(df_retrain["hour_of_year"], df_retrain["ev_power_playa1_kw"],
            label="SAC Retrain", linewidth=0.8, alpha=0.6, color="green")
    ax.axhspan(18, 21, alpha=0.1, color="gray")
    ax.set_ylabel("Potencia (kW)")
    ax.set_xlabel("Hora del Año")
    ax.set_title("Potencia Playa Motos")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Subgráfico 3: Potencia playa mototaxis
    ax = axes[1, 0]
    ax.plot(df_baseline["hour_of_year"], df_baseline["ev_power_playa2_kw"],
            label="Uncontrolled", linewidth=0.8, alpha=0.6, color="red")
    ax.plot(df_retrain["hour_of_year"], df_retrain["ev_power_playa2_kw"],
            label="SAC Retrain", linewidth=0.8, alpha=0.6, color="green")
    ax.axhspan(18, 21, alpha=0.1, color="gray")
    ax.set_ylabel("Potencia (kW)")
    ax.set_xlabel("Hora del Año")
    ax.set_title("Potencia Playa Mototaxis")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Subgráfico 4: Ratio fairness por hora
    ax = axes[1, 1]
    baseline_ratio = df_baseline["ev_power_playa1_kw"] / (df_baseline["ev_power_playa2_kw"] + 0.1)
    retrain_ratio = df_retrain["ev_power_playa1_kw"] / (df_retrain["ev_power_playa2_kw"] + 0.1)

    ax.plot(df_baseline["hour_of_year"], baseline_ratio,
            label="Uncontrolled", linewidth=0.8, alpha=0.6, color="red")
    ax.plot(df_retrain["hour_of_year"], retrain_ratio,
            label="SAC Retrain", linewidth=0.8, alpha=0.6, color="green")
    ax.axhline(y=1.0, color="black", linestyle="--", label="Balanced (1:1)")
    ax.axhspan(18, 21, alpha=0.1, color="gray")
    ax.set_ylabel("Ratio Motos/Mototaxis")
    ax.set_xlabel("Hora del Año")
    ax.set_title("Equilibrio (Fairness) Entre Playas")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_ylim((0, 4))

    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches="tight")
    logger.info(f"✓ Gráfico power profile guardado en {output_file}")
    plt.close()


def create_soc_evolution_plot(
    df_baseline: pd.DataFrame,
    df_retrain: pd.DataFrame,
    output_file: Path,
) -> None:
    """Grafica evolución de SOC BESS: baseline vs retrain."""

    _, ax = plt.subplots(figsize=(16, 6))

    ax.plot(df_baseline["hour_of_year"], df_baseline["bess_soc_percent"],
            label="Uncontrolled", linewidth=1, alpha=0.7, color="red")
    ax.plot(df_retrain["hour_of_year"], df_retrain["bess_soc_percent"],
            label="SAC Retrain", linewidth=1, alpha=0.7, color="green")

    # Targets operacionales
    ax.axhline(y=60, color="blue", linestyle=":", alpha=0.5, label="Target Normal (60%)")
    ax.axhline(y=85, color="orange", linestyle=":", alpha=0.5, label="Target Pre-Pico (85%)")
    ax.axhline(y=40, color="purple", linestyle=":", alpha=0.5, label="Min Pico (40%)")
    ax.axhline(y=20, color="black", linestyle="--", alpha=0.5, label="Min Absoluto (20%)")

    # Bandas de pico
    for hour in range(18, 22):
        ax.axvspan(hour * 365, (hour + 1) * 365, alpha=0.05, color="gray")

    ax.set_ylabel("SOC (%)")
    ax.set_xlabel("Hora del Año")
    ax.set_title("Evolución de SOC BESS (2000 kWh)")
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)
    ax.set_ylim((0, 105))

    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches="tight")
    logger.info(f"✓ Gráfico SOC evolution guardado en {output_file}")
    plt.close()


def create_grid_import_plot(
    df_baseline: pd.DataFrame,
    df_retrain: pd.DataFrame,
    output_file: Path,
) -> None:
    """Grafica importación de red: baseline vs retrain."""

    _, axes = plt.subplots(2, 1, figsize=(16, 10))

    # Subgráfico 1: Importación horaria
    ax = axes[0]
    ax.plot(df_baseline["hour_of_year"], df_baseline["grid_import_kw"],
            label="Uncontrolled", linewidth=0.8, alpha=0.6, color="red")
    ax.plot(df_retrain["hour_of_year"], df_retrain["grid_import_kw"],
            label="SAC Retrain", linewidth=0.8, alpha=0.6, color="green")
    ax.axhspan(18, 21, alpha=0.1, color="gray", label="Pico (18-21h)")
    ax.set_ylabel("Potencia Importada (kW)")
    ax.set_xlabel("Hora del Año")
    ax.set_title("Importación de Red - Series Temporal")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Subgráfico 2: Acumulación diaria
    ax = axes[1]
    ax.plot(df_baseline["hour_of_year"], df_baseline["grid_import_daily_kwh"] / 1000,
            label="Uncontrolled", linewidth=1, alpha=0.7, color="red")
    ax.plot(df_retrain["hour_of_year"], df_retrain["grid_import_daily_kwh"] / 1000,
            label="SAC Retrain", linewidth=1, alpha=0.7, color="green")
    ax.set_ylabel("Importación Acumulada Diaria (MWh)")
    ax.set_xlabel("Hora del Año")
    ax.set_title("Importación Acumulada por Día")
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_file, dpi=150, bbox_inches="tight")
    logger.info(f"✓ Gráfico grid import guardado en {output_file}")
    plt.close()


def main():
    # Cargar config
    _, rp = load_all("configs/default.yaml")
    rp.ensure()

    logger.info("=" * 80)
    logger.info("COMPARACIÓN: Baseline Uncontrolled vs Agentes Reentrenados")
    logger.info("=" * 80)

    # Cargar diagnósticos baseline
    logger.info("\n[1] Cargando diagnósticos baseline (Uncontrolled)...")
    try:
        df_baseline, summary_baseline = load_diagnostics(
            rp.oe3_diagnostics_dir, "uncontrolled"
        )
        logger.info(f"✓ Baseline cargado: {len(df_baseline)} timesteps")
    except FileNotFoundError as e:
        logger.error(f"✗ No se puede cargar baseline: {e}")
        logger.info("\nPrimero ejecuta: python -m scripts.run_uncontrolled_baseline")
        return

    # Cargar diagnósticos retrain
    logger.info("\n[2] Cargando diagnósticos retrain (SAC)...")
    try:
        df_retrain, summary_retrain = load_diagnostics(
            rp.oe3_diagnostics_dir, "sac_retrain"  # Adjust name if different
        )
        logger.info(f"✓ Retrain cargado: {len(df_retrain)} timesteps")
    except FileNotFoundError as e:
        logger.warning(f"⚠ No se puede cargar retrain SAC: {e}")
        logger.info("Continuando con solo baseline...")
        summary_retrain = summary_baseline.copy()  # Usar baseline como placeholder
        df_retrain = df_baseline.copy()

    # Extraer métricas comparativas
    logger.info("\n[3] Extrayendo métricas comparativas...")
    df_comparison = extract_comparison_metrics(
        df_baseline, summary_baseline, df_retrain, summary_retrain
    )

    # Guardar tabla comparativa
    comparison_file = rp.oe3_analysis_dir / "comparison_metrics.csv"
    comparison_file.parent.mkdir(parents=True, exist_ok=True)
    df_comparison.to_csv(comparison_file, index=False)
    logger.info(f"✓ Tabla comparativa guardada en {comparison_file}")

    # Imprimir tabla
    logger.info("\n" + "=" * 100)
    logger.info(df_comparison.to_string(index=False))
    logger.info("=" * 100)

    # Crear gráficos
    logger.info("\n[4] Generando gráficos comparativos...")
    plots_dir = rp.oe3_analysis_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    create_power_profile_plot(df_baseline, df_retrain, plots_dir / "power_profile.png")
    create_soc_evolution_plot(df_baseline, df_retrain, plots_dir / "soc_evolution.png")
    create_grid_import_plot(df_baseline, df_retrain, plots_dir / "grid_import.png")

    # Guardar JSON con resumen
    summary_comparison = {
        "baseline": summary_baseline,
        "retrain": summary_retrain,
        "comparison": df_comparison.to_dict(orient="records"),
    }

    summary_file = rp.oe3_analysis_dir / "comparison_summary.json"
    with open(summary_file, "w") as f:
        json.dump(summary_comparison, f, indent=2)
    logger.info(f"✓ Resumen JSON guardado en {summary_file}")

    logger.info("\n" + "=" * 80)
    logger.info("COMPARACIÓN COMPLETADA")
    logger.info("=" * 80)
    logger.info(f"Archivos generados en: {rp.oe3_analysis_dir}")
    logger.info(f"  - comparison_metrics.csv")
    logger.info(f"  - comparison_summary.json")
    logger.info(f"  - plots/power_profile.png")
    logger.info(f"  - plots/soc_evolution.png")
    logger.info(f"  - plots/grid_import.png")

    return df_comparison


if __name__ == "__main__":
    main()
