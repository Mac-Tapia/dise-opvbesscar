#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CANONICAL_REPORT = ROOT / "reports" / "oe3" / "AGENTES_RL_COMPARATIVA_CANONICA.md"


def main() -> None:
    print("Generador historico de informe OE3 completo deshabilitado.")
    print(f"Use el informe canonico: {CANONICAL_REPORT.relative_to(ROOT)}")
    print("Para tablas PNG actualizadas ejecute: python scripts/reporting/generar_tablas_oe3.py")


if __name__ == "__main__":
    main()
