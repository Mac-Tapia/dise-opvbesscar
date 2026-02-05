from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, Iterable
import logging

logger = logging.getLogger(__name__)

def append_progress_row(path: Path, row: Dict[str, Any], headers: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(headers))
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def render_progress_plot(progress_csv: Path, png_path: Path, title: str, metric_col: str = "mean_reward") -> None:
    """Genera/actualiza una gráfica rápida de progreso desde un CSV de métricas.

    CORREGIDO: Filtra filas con valores NaN/vacíos en la columna de métricas
    para evitar gráficas incorrectas.
    """
    if not progress_csv.exists():
        return
    try:
        import pandas as pd  # type: ignore[import]
        import matplotlib.pyplot as plt  # type: ignore[import]
    except Exception:  # pylint: disable=broad-except
        logger.debug("Plotting dependencies no disponibles, omitiendo plot.")
        return

    try:
        df = pd.read_csv(progress_csv)
        if metric_col not in df.columns:
            # buscar alguna columna compatible
            for c in ("episode_reward", "reward", "mean_reward"):
                if c in df.columns:
                    metric_col = c
                    break
            else:
                return

        # CRITICAL FIX: Filtrar solo filas con valores válidos en metric_col
        df_valid = df[df[metric_col].notna()].copy()
        if df_valid.empty:
            logger.debug("No hay datos válidos para graficar en %s", progress_csv)
            return

        x = df_valid["global_step"] if "global_step" in df_valid.columns else df_valid.index
        y = df_valid[metric_col]

        plt.figure(figsize=(10, 5))
        plt.plot(x, y, color="steelblue", linewidth=2, marker='o', markersize=6)
        plt.xlabel("Global Steps", fontsize=11)
        plt.ylabel(metric_col.replace("_", " ").title(), fontsize=11)
        plt.title(title, fontsize=13, fontweight='bold')
        plt.grid(True, alpha=0.3)

        # Añadir anotaciones con valores
        for xi, yi in zip(x, y):
            plt.annotate(f'{yi:.0f}', (xi, yi), textcoords='offset points',
                        xytext=(0, 8), ha='center', fontsize=9)

        plt.tight_layout()
        png_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(png_path, dpi=150, bbox_inches="tight")
        plt.close()
        logger.info("Gráfica guardada: %s (%d puntos)", png_path, len(df_valid))
    except Exception:  # pylint: disable=broad-except
        logger.debug("No se pudo renderizar plot de progreso")
