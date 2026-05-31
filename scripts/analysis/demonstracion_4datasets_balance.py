#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OE2_REPORT = ROOT / "docs" / "REPORTE_FINAL_VERIFICACION_CORRECCIONES_OE2_v52.md"


def main() -> None:
    print("Demostracion historica de balance deshabilitada.")
    print(f"Use el reporte OE2 vigente: {OE2_REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
