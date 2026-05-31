#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CANONICAL_REPORT = ROOT / "reports" / "oe3" / "AGENTES_RL_COMPARATIVA_CANONICA.md"


def main() -> None:
    print("Insercion historica de graficas Word deshabilitada.")
    print(f"Use el informe canonico: {CANONICAL_REPORT.relative_to(ROOT)}")
    print("Los DOCX v10/v11 fueron retirados del repositorio.")


if __name__ == "__main__":
    main()
