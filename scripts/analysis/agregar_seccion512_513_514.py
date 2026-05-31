#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OE2_REPORT = ROOT / "docs" / "REPORTE_FINAL_VERIFICACION_CORRECCIONES_OE2_v52.md"
OE3_REPORT = ROOT / "reports" / "oe3" / "AGENTES_RL_COMPARATIVA_CANONICA.md"


def main() -> None:
    print("Generador historico de secciones 5.1.2-5.1.4 deshabilitado.")
    print(f"Use OE2 vigente: {OE2_REPORT.relative_to(ROOT)}")
    print(f"Use OE3 vigente: {OE3_REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
