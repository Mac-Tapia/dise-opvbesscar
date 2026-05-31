#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CANONICAL_JSON = ROOT / "reports" / "oe3" / "agents_comparison_canonical.json"


def main() -> None:
    print("Analisis estadistico historico deshabilitado.")
    print(f"Use el JSON canonico: {CANONICAL_JSON.relative_to(ROOT)}")
    print("Contiene Shapiro-Wilk, Kruskal-Wallis, Mann-Whitney U y Wilcoxon actualizados.")


if __name__ == "__main__":
    main()
