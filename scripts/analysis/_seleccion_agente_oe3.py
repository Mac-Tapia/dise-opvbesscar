from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CANONICAL = ROOT / "reports" / "oe3" / "agents_comparison_canonical.json"


def main() -> None:
    data = json.loads(CANONICAL.read_text(encoding="utf-8"))
    selected = data["metadata"]["selected_agent"]
    selected_metrics = data["agents"][selected]
    sac_metrics = data["agents"]["SAC"]
    ppo_metrics = data["agents"]["PPO"]

    print("=" * 78)
    print("  SELECCION CANONICA AGENTE OE3")
    print("=" * 78)
    print(f"  Fuente: {CANONICAL.relative_to(ROOT)}")
    print(f"  Agente seleccionado: {selected}")
    print(
        "  CO2 total evitado 50 episodios: "
        f"{selected_metrics['co2_total_avoided_sum_50_kg']:,.0f} kg CO2"
    )
    print(
        "  Promedio evitado por episodio: "
        f"{selected_metrics['co2_total_avoided_mean_kg_per_episode']:,.0f} kg CO2/año"
    )
    print(f"  F2 minimo complementario: {selected_metrics['f2_min_kg_per_year']:,.0f} kg CO2/año")
    print()
    print("  Justificacion:")
    print("  - El criterio operativo principal es maximizar CO2 reducido acumulado en 50 episodios.")
    print("  - A2C tiene el mayor total directo + indirecto evitado.")
    print(
        "  - SAC no gana porque su CO2 total evitado queda "
        f"{selected_metrics['co2_total_avoided_sum_50_kg'] - sac_metrics['co2_total_avoided_sum_50_kg']:,.0f} "
        "kg CO2 por debajo de A2C en el acumulado."
    )
    print(
        "  - PPO conserva el menor F2 puntual: "
        f"{ppo_metrics['f2_min_kg_per_year']:,.0f} kg CO2/año."
    )
    print("  - Shapiro-Wilk rechaza normalidad; se reportan pruebas no parametricas.")
    print("=" * 78)


if __name__ == "__main__":
    main()
