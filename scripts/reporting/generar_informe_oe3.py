#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CANONICAL_REPORT = ROOT / "reports" / "oe3" / "AGENTES_RL_COMPARATIVA_CANONICA.md"
CANONICAL_JSON = ROOT / "reports" / "oe3" / "agents_comparison_canonical.json"


def main() -> None:
    print("Generador historico de informe OE3 deshabilitado.")
    print(f"Informe canonico: {CANONICAL_REPORT.relative_to(ROOT)}")
    print(f"Datos estructurados: {CANONICAL_JSON.relative_to(ROOT)}")
    print("Agente OE3 vigente: PPO")


if __name__ == "__main__":
    main()
