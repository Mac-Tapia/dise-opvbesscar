#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CANONICAL_REPORT = ROOT / "reports" / "oe3" / "AGENTES_RL_COMPARATIVA_CANONICA.md"
CURRENT_DOCX = ROOT / "outputs" / "docx" / "INFORME_OE3_SELECCION_AGENTE_RL_v12.docx"


def main() -> None:
    print("Insercion historica de graficas Word deshabilitada.")
    print(f"Use el informe canonico: {CANONICAL_REPORT.relative_to(ROOT)}")
    print(f"Use el DOCX vigente: {CURRENT_DOCX.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
