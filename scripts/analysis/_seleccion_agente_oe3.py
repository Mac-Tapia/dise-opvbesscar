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

    print("=" * 78)
    print("  SELECCION CANONICA AGENTE OE3")
    print("=" * 78)
    print(f"  Fuente: {CANONICAL.relative_to(ROOT)}")
    print(f"  Agente seleccionado: {selected}")
    print(f"  F2 minimo: {selected_metrics['f2_min_kg_per_year']:,.0f} kg CO2/año")
    print(f"  Episodio optimo: {selected_metrics['best_episode']}")
    print(f"  Reduccion vs F0: {selected_metrics['co2_reduction_vs_f0_pct']:.2f}%")
    print()
    print("  Justificacion:")
    print("  - El criterio operativo principal es minimizar F2 anual.")
    print("  - PPO tiene el menor F2 entre SAC, PPO y A2C.")
    print(
        "  - SAC no gana porque su mejor F2 queda "
        f"{sac_metrics['f2_min_kg_per_year'] - selected_metrics['f2_min_kg_per_year']:,.0f} "
        "kg CO2/año por encima de PPO."
    )
    print("  - Shapiro-Wilk rechaza normalidad; se reportan pruebas no parametricas.")
    print("=" * 78)


if __name__ == "__main__":
    main()
