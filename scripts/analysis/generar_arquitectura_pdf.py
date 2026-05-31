#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARCH_HTML = ROOT / "reports" / "ARQUITECTURA_v2026.html"


def main() -> None:
    print("Generador PDF historico deshabilitado.")
    print(f"Use la arquitectura HTML vigente: {ARCH_HTML.relative_to(ROOT)}")
    print("Los PDF antiguos fueron retirados para evitar resultados desactualizados.")


if __name__ == "__main__":
    main()
