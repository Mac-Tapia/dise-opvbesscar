#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CANONICAL_REPORT = ROOT / "reports" / "oe3" / "AGENTES_RL_COMPARATIVA_CANONICA.md"


def main() -> None:
    print("Generador historico de seccion 4.6.3 deshabilitado.")
    print(f"Use el informe canonico OE3: {CANONICAL_REPORT.relative_to(ROOT)}")
    print("Agente OE3 vigente: PPO")


if __name__ == "__main__":
    main()
