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
    """Genera/actualiza una gráfica rápida de progreso desde un CSV de métricas."""
    if not progress_csv.exists():
        return
    try:
        import pandas as pd
        import matplotlib.pyplot as plt
    except Exception as exc:
        logger.debug("Plotting dependencies no disponibles (%s), omitiendo plot.", exc)
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
        x = df["global_step"] if "global_step" in df.columns else df.index
        y = df[metric_col]

        plt.figure(figsize=(8, 3))
        plt.plot(x, y, color="steelblue", linewidth=1.3)
        plt.xlabel("step")
        plt.ylabel(metric_col)
        plt.title(title)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        png_path.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(png_path, dpi=120, bbox_inches="tight")
        plt.close()
    except Exception as exc:
        logger.debug("No se pudo renderizar plot de progreso (%s)", exc)
