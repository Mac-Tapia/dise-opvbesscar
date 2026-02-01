#!/usr/bin/env python3
"""
Generar gráfica consolidada único con métricas de rendimiento y aprendizaje
de todos los agentes (SAC, PPO, A2C) en una sola visualización.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt  # type: ignore
import seaborn as sns  # type: ignore

sns.set_style("darkgrid")
plt.rcParams["figure.figsize"] = (22, 12)
plt.rcParams["font.size"] = 11


def load_simulation_result(agent_name: str, results_dir: Path) -> dict:  # type: ignore
    """Carga resultados de simulación de un agente."""
    json_path = results_dir / f"result_{agent_name}.json"
    if json_path.exists():
        with open(json_path) as f:
            return json.load(f)  # type: ignore
    return {}


def main():
    """Generar gráfica consolidada."""
    results_dir = Path("outputs/oe3/simulations")

    # Crear figura con subplots
    fig = plt.figure(figsize=(22, 12))
    gs = fig.add_gridspec(2, 4, hspace=0.35, wspace=0.3)

    agents = ["SAC", "PPO", "A2C"]
    colors = {"SAC": "#FF6B6B", "PPO": "#4ECDC4", "A2C": "#45B7D1"}

    # Cargar todos los datos de simulación
    simulation_results = {}

    print("[*] Cargando datos de simulación...")
    for agent in agents:
        simulation_results[agent] = load_simulation_result(agent, results_dir)
        if simulation_results[agent]:
            print(f"  OK {agent}: simulación cargada")

    # Variables para almacenar valores
    grid_values, co2_values, ev_values, solar_values = [], [], [], []
    labels = []
    colors_list = []

    for agent in agents:
        result = simulation_results[agent]
        if result and "final_metrics" in result:
            labels.append(agent)
            colors_list.append(colors[agent])
            grid_values.append(result["final_metrics"].get("grid_import_kwh", 0))
            co2_values.append(result["final_metrics"].get("co2_kg", 0))
            ev_values.append(result["final_metrics"].get("ev_charging_kwh", 0))
            solar_values.append(result["final_metrics"].get("solar_used_kwh", 0))

    # ============================================================================
    # FILA 1: RENDIMIENTO FINAL
    # ============================================================================

    # Grid Import
    ax1 = fig.add_subplot(gs[0, 0])
    bars1 = ax1.bar(labels, grid_values, color=colors_list, alpha=0.8, edgecolor="black", linewidth=2)
    ax1.set_ylabel("kWh/año", fontsize=11, fontweight="bold")
    ax1.set_title("[GRID] Importacion de Red", fontsize=12, fontweight="bold")
    for bar, val in zip(bars1, grid_values):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width() / 2, height, f"{val:,.0f}", ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax1.grid(axis="y", alpha=0.3)

    # CO2
    ax2 = fig.add_subplot(gs[0, 1])
    bars2 = ax2.bar(labels, co2_values, color=colors_list, alpha=0.8, edgecolor="black", linewidth=2)
    ax2.set_ylabel("kg/año", fontsize=11, fontweight="bold")
    ax2.set_title("[CO2] Emisiones Anuales", fontsize=12, fontweight="bold")
    for bar, val in zip(bars2, co2_values):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width() / 2, height, f"{val:,.0f}", ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax2.grid(axis="y", alpha=0.3)

    # EV Charging
    ax3 = fig.add_subplot(gs[0, 2])
    bars3 = ax3.bar(labels, ev_values, color=colors_list, alpha=0.8, edgecolor="black", linewidth=2)
    ax3.set_ylabel("kWh/año", fontsize=11, fontweight="bold")
    ax3.set_title("[EV] Carga de Vehiculos", fontsize=12, fontweight="bold")
    for bar, val in zip(bars3, ev_values):
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width() / 2, height, f"{val:,.0f}", ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax3.grid(axis="y", alpha=0.3)

    # Solar
    ax4 = fig.add_subplot(gs[0, 3])
    bars4 = ax4.bar(labels, solar_values, color=colors_list, alpha=0.8, edgecolor="black", linewidth=2)
    ax4.set_ylabel("kWh/año", fontsize=11, fontweight="bold")
    ax4.set_title("[SOLAR] Aprovechamiento", fontsize=12, fontweight="bold")
    for bar, val in zip(bars4, solar_values):
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width() / 2, height, f"{val:,.0f}", ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax4.grid(axis="y", alpha=0.3)

    # ============================================================================
    # FILA 2: MEJORAS vs BASELINE
    # ============================================================================

    baseline_result = load_simulation_result("Uncontrolled", results_dir)
    baseline_grid = baseline_result.get("final_metrics", {}).get("grid_import_kwh", 1)
    baseline_co2 = baseline_result.get("final_metrics", {}).get("co2_kg", 1)
    baseline_solar = baseline_result.get("final_metrics", {}).get("solar_used_kwh", 1)
    baseline_ev = baseline_result.get("final_metrics", {}).get("ev_charging_kwh", 1)

    # Reducción Grid
    reduction_grid = [(baseline_grid - val) / baseline_grid * 100 for val in grid_values]
    ax5 = fig.add_subplot(gs[1, 0])
    bars5 = ax5.bar(labels, reduction_grid, color=colors_list, alpha=0.8, edgecolor="black", linewidth=2)
    ax5.set_ylabel("Reduccion (%)", fontsize=11, fontweight="bold")
    ax5.set_title("[MEJORA] Reduccion Grid", fontsize=12, fontweight="bold")
    ax5.set_ylim(0, 100)
    for bar, val in zip(bars5, reduction_grid):
        height = bar.get_height()
        ax5.text(bar.get_x() + bar.get_width() / 2, height, f"{val:.1f}%", ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax5.grid(axis="y", alpha=0.3)
    ax5.axhline(y=50, color="red", linestyle="--", alpha=0.5, linewidth=2)

    # Reducción CO2
    reduction_co2 = [(baseline_co2 - val) / baseline_co2 * 100 for val in co2_values]
    ax6 = fig.add_subplot(gs[1, 1])
    bars6 = ax6.bar(labels, reduction_co2, color=colors_list, alpha=0.8, edgecolor="black", linewidth=2)
    ax6.set_ylabel("Reduccion (%)", fontsize=11, fontweight="bold")
    ax6.set_title("[MEJORA] Reduccion CO2", fontsize=12, fontweight="bold")
    ax6.set_ylim(0, 100)
    for bar, val in zip(bars6, reduction_co2):
        height = bar.get_height()
        ax6.text(bar.get_x() + bar.get_width() / 2, height, f"{val:.1f}%", ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax6.grid(axis="y", alpha=0.3)
    ax6.axhline(y=50, color="red", linestyle="--", alpha=0.5, linewidth=2)

    # Mejora Solar
    improvement_solar = [(val - baseline_solar) / baseline_solar * 100 for val in solar_values]
    ax7 = fig.add_subplot(gs[1, 2])
    bars7 = ax7.bar(labels, improvement_solar, color=colors_list, alpha=0.8, edgecolor="black", linewidth=2)
    ax7.set_ylabel("Mejora (%)", fontsize=11, fontweight="bold")
    ax7.set_title("[MEJORA] Solar", fontsize=12, fontweight="bold")
    for bar, val in zip(bars7, improvement_solar):
        height = bar.get_height()
        y_pos = height if height > 0 else 0
        va = "bottom" if height > 0 else "top"
        ax7.text(bar.get_x() + bar.get_width() / 2, y_pos, f"{val:.1f}%", ha="center", va=va, fontsize=10, fontweight="bold")
    ax7.grid(axis="y", alpha=0.3)
    ax7.axhline(y=0, color="black", linestyle="-", alpha=0.3, linewidth=1)

    # Satisfacción EV
    ev_satisfaction = [(val / baseline_ev * 100) if baseline_ev > 0 else 0 for val in ev_values]
    ax8 = fig.add_subplot(gs[1, 3])
    bars8 = ax8.bar(labels, ev_satisfaction, color=colors_list, alpha=0.8, edgecolor="black", linewidth=2)
    ax8.set_ylabel("Satisfaccion (%)", fontsize=11, fontweight="bold")
    ax8.set_title("[MEJORA] EV Satisfaction", fontsize=12, fontweight="bold")
    ax8.set_ylim(0, 120)
    for bar, val in zip(bars8, ev_satisfaction):
        height = bar.get_height()
        ax8.text(bar.get_x() + bar.get_width() / 2, height, f"{val:.1f}%", ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax8.grid(axis="y", alpha=0.3)
    ax8.axhline(y=100, color="red", linestyle="--", alpha=0.5, linewidth=2)

    # Título general
    fig.suptitle("ANALISIS CONSOLIDADO: RENDIMIENTO Y APRENDIZAJE\nSAC vs PPO vs A2C", fontsize=16, fontweight="bold", y=0.995)

    # Guardar
    output_dir = Path("analyses/oe3/training/graphics")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "consolidated_metrics_all_agents.png"

    plt.savefig(output_file, dpi=300, bbox_inches="tight", facecolor="white")
    print(f"\n✓ Grafica consolidada guardada: {output_file}")
    print(f"   Tamaño: {output_file.stat().st_size / 1024:.1f} KB")
    print(f"   Resolucion: 300 DPI")

    plt.close()

    print("\n" + "=" * 80)
    print("OK GRAFICA CONSOLIDADA GENERADA EXITOSAMENTE")
    print("=" * 80)
    print("\nMetricas incluidas en UNA SOLA grafica:")
    print("  FILA 1 - Rendimiento Final: Grid, CO2, EV, Solar")
    print("  FILA 2 - Mejoras vs Baseline: Reduccion Grid, Reduccion CO2, Mejora Solar, Satisfaccion EV")
    print("\nAgentes comparados: SAC vs PPO vs A2C")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
