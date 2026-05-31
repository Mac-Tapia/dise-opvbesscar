#!/usr/bin/env python3
from __future__ import annotations

import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

"""
Genera tablas PNG de OE3 desde la fuente canonica versionada en reports/oe3.

Salida:
  - outputs/docx/graficas/tabla_criterios_seleccion_oe3.png
  - outputs/docx/graficas/tabla_co2_componentes_ppo_ep49.png
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[2]
CANONICAL = ROOT / "reports" / "oe3" / "agents_comparison_canonical.json"
OUT_DIR = ROOT / "outputs" / "docx" / "graficas"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def _fmt_int(value: float) -> str:
    return f"{value:,.0f}"


def _load() -> dict:
    return json.loads(CANONICAL.read_text(encoding="utf-8"))


def _save_table(filename: str, title: str, columns: list[str], rows: list[list[str]], selected_row: int | None = None) -> Path:
    fig_height = max(3.5, 1.0 + 0.55 * len(rows))
    fig, ax = plt.subplots(figsize=(14, fig_height))
    ax.axis("off")
    fig.patch.set_facecolor("#FAFAFA")

    table = ax.table(cellText=rows, colLabels=columns, loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(9.5)
    table.scale(1, 1.55)

    for col in range(len(columns)):
        cell = table[0, col]
        cell.set_facecolor("#17476F")
        cell.set_text_props(color="white", fontweight="bold")
        cell.set_edgecolor("white")

    for row_idx in range(len(rows)):
        for col_idx in range(len(columns)):
            cell = table[row_idx + 1, col_idx]
            cell.set_edgecolor("#D1D5DB")
            if selected_row is not None and row_idx == selected_row:
                cell.set_facecolor("#DFF3E7")
                cell.set_text_props(fontweight="bold", color="#14532D")
            elif row_idx % 2 == 0:
                cell.set_facecolor("#F8FBFF")
            else:
                cell.set_facecolor("white")

    ax.set_title(title, fontsize=12, fontweight="bold", color="#12324F", pad=18)
    ax.text(
        0.99,
        -0.04,
        f"Fuente: {CANONICAL.relative_to(ROOT)}",
        transform=ax.transAxes,
        ha="right",
        fontsize=8.5,
        color="#4B5563",
    )

    path = OUT_DIR / filename
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return path


def generate_selection_table(data: dict) -> Path:
    agents = sorted(data["agents"].items(), key=lambda item: item[1]["rank"])
    selected_agent = data["metadata"]["selected_agent"]
    columns = [
        "Rank",
        "Agente",
        "CO2 total evitado\n50 ep kg",
        "Promedio\nkg/ep",
        "CO2 directo\n50 ep kg",
        "CO2 indirecto\n50 ep kg",
        "F2 minimo\nkg/año",
        "CV plateau",
    ]
    rows = []
    selected_row = None
    for idx, (agent, metrics) in enumerate(agents):
        if metrics["selected"]:
            selected_row = idx
        rows.append(
            [
                str(metrics["rank"]),
                agent,
                _fmt_int(metrics["co2_total_avoided_sum_50_kg"]),
                _fmt_int(metrics["co2_total_avoided_mean_kg_per_episode"]),
                _fmt_int(metrics["co2_direct_avoided_sum_50_kg"]),
                _fmt_int(metrics["co2_indirect_avoided_sum_50_kg"]),
                _fmt_int(metrics["f2_min_kg_per_year"]),
                f"{metrics['cv_plateau_pct']:.3f}%",
            ]
        )

    return _save_table(
        "tabla_criterios_seleccion_oe3.png",
        f"OE3 - Comparativa canonica de agentes RL ({selected_agent} seleccionado)",
        columns,
        rows,
        selected_row=selected_row,
    )


def generate_co2_summary_table(data: dict) -> Path:
    system = data["system"]
    selected_agent = data["metadata"]["selected_agent"]
    selected = data["agents"][selected_agent]
    sac = data["agents"]["SAC"]
    a2c = data["agents"]["A2C"]
    ppo = data["agents"]["PPO"]
    columns = ["Concepto", "Valor", "Unidad", "Nota"]
    rows = [
        ["Agente seleccionado", selected_agent, "-", "Mayor CO2 evitado acumulado"],
        ["F0 referencia", _fmt_int(system["f0_reference_kg_co2_year"]), "kg CO2/año", "Sin solar/BESS/RL"],
        [f"CO2 total evitado {selected_agent}", _fmt_int(selected["co2_total_avoided_sum_50_kg"]), "kg CO2/50 ep", "Directo + indirecto"],
        [f"Promedio evitado {selected_agent}", _fmt_int(selected["co2_total_avoided_mean_kg_per_episode"]), "kg CO2/ep", "Media anual por episodio"],
        ["F2 PPO vs A2C", _fmt_int(a2c["f2_min_kg_per_year"] - ppo["f2_min_kg_per_year"]), "kg CO2/año", "PPO menor F2 puntual"],
        ["F2 PPO vs SAC", _fmt_int(sac["f2_min_kg_per_year"] - ppo["f2_min_kg_per_year"]), "kg CO2/año", "PPO menor F2 puntual"],
        ["Solar PV DC", _fmt_int(system["solar_kwp_dc_pvwatts"]), "kWp DC", "PVWatts pdc0 OE2 (Jinko Tiger Neo)"],
        ["BESS", _fmt_int(system["bess_kwh"]), "kWh", "400 kW"],
    ]
    return _save_table(
        "tabla_co2_componentes_ppo_ep49.png",
        f"OE3 - Resumen CO2 canonico multiobjetivo para {selected_agent}",
        columns,
        rows,
        selected_row=2,
    )


def main() -> None:
    data = _load()
    path1 = generate_selection_table(data)
    path2 = generate_co2_summary_table(data)
    print(f"Tabla 1 guardada: {path1}")
    print(f"Tabla 2 guardada: {path2}")
    print(f"Agente OE3 seleccionado: {data['metadata']['selected_agent']}")


if __name__ == "__main__":
    main()
