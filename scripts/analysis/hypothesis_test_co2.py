#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CANONICAL_REPORT = ROOT / "outputs" / "estadistica_oe3" / "reporte_estadistico_oe3.md"
CANONICAL_JSON = ROOT / "reports" / "oe3" / "agents_comparison_canonical.json"


def main() -> None:
    print("Script historico de prueba de hipotesis deshabilitado.")
    print(f"Use el reporte estadistico vigente: {CANONICAL_REPORT.relative_to(ROOT)}")
    print(f"Use el JSON canonico vigente: {CANONICAL_JSON.relative_to(ROOT)}")
    print("Agente OE3 vigente: A2C")


if __name__ == "__main__":
    main()
