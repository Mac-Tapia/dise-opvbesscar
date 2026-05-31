#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wrapper de compatibilidad para graficas OE3.

El paquete de graficas ampliadas anterior mezclaba criterios obsoletos de
seleccion. La fuente vigente de comparacion SAC/PPO/A2C es:

- reports/oe3/AGENTES_RL_COMPARATIVA_CANONICA.md
- reports/oe3/agents_comparison_canonical.json
- reports/oe3/agents_comparison_canonical.csv

Este wrapper conserva el punto de entrada historico y delega en el generador
de tablas canonicas.
"""

from __future__ import annotations

import runpy
from pathlib import Path


BASE = Path(__file__).resolve().parents[2]
CANONICAL_SCRIPT = BASE / "scripts" / "reporting" / "generar_tablas_oe3.py"


def main() -> None:
    print("OE3 canonical: A2C seleccionado por score multiobjetivo. Generando tablas canonicas...")
    runpy.run_path(str(CANONICAL_SCRIPT), run_name="__main__")


if __name__ == "__main__":
    main()
