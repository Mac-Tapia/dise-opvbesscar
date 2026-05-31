from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CANONICAL = ROOT / "reports" / "oe3" / "agents_comparison_canonical.json"


def main() -> None:
    data = json.loads(CANONICAL.read_text(encoding="utf-8"))
    agents = sorted(data["agents"].items(), key=lambda item: item[1]["rank"])

    print("=" * 78)
    print("  RANKING CANONICO OE3 - SAC / PPO / A2C")
    print("=" * 78)
    print(f"  Fuente: {CANONICAL.relative_to(ROOT)}")
    print(f"  Fecha:  {data['metadata']['updated_at']}")
    print(f"  Criterio principal: {data['metadata']['selection_criterion']}")
    print()
    print(
        f"  {'Rank':>4}  {'Agente':<6} {'CO2 evitado 50ep':>18} "
        f"{'Prom/ep':>14} {'F2 minimo':>14} {'CV':>8}"
    )
    print("  " + "-" * 82)
    for agent, metrics in agents:
        selected = " *" if metrics["selected"] else ""
        print(
            f"  {metrics['rank']:>4}  {agent + selected:<6} "
            f"{metrics['co2_total_avoided_sum_50_kg']:>18,.0f} "
            f"{metrics['co2_total_avoided_mean_kg_per_episode']:>14,.0f} "
            f"{metrics['f2_min_kg_per_year']:>14,.0f} "
            f"{metrics['cv_plateau_pct']:>7.3f}%"
        )

    print()
    print(f"  >>> AGENTE SELECCIONADO OE3: {data['metadata']['selected_agent']} <<<")
    print("=" * 78)


if __name__ == "__main__":
    main()
