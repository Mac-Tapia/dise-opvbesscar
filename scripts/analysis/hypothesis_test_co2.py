#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CANONICAL_JSON = ROOT / "outputs" / "hypothesis_test" / "RESULTADOS_HIPOTESIS_CO2_COMPLETO.json"


def main() -> None:
    print("Script historico de prueba de hipotesis deshabilitado.")
    print(f"Use el resumen estadistico vigente: {CANONICAL_JSON.relative_to(ROOT)}")
    print("Agente OE3 vigente: PPO")


if __name__ == "__main__":
    main()
