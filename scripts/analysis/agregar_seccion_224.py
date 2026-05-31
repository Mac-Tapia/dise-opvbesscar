#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CANONICAL_REPORT = ROOT / "reports" / "oe3" / "AGENTES_RL_COMPARATIVA_CANONICA.md"


def main() -> None:
    print("Generador Word historico de seccion 2.2.4 deshabilitado.")
    print(f"Use las fuentes vigentes documentadas en: {CANONICAL_REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
