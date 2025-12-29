from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import pandas as pd


def load_metric_curves(train_dir: Path) -> Dict[str, Tuple[pd.Series, pd.Series]]:
    """Carga curvas de entrenamiento (mean_reward vs step) para cada agente."""
    curves: Dict[str, Tuple[pd.Series, pd.Series]] = {}
    for csv_path in train_dir.glob("*_training_metrics.csv"):
        agent = csv_path.stem.replace("_training_metrics", "")
        df = pd.read_csv(csv_path)
        if {"step", "mean_reward"} <= set(df.columns) and not df.empty:
            curves[agent] = (df["step"], df["mean_reward"])
    return curves


def load_episode_curves(progress_dir: Path) -> Dict[str, Tuple[pd.Series, pd.Series]]:
    """Carga recompensas por episodio desde progress/*.csv."""
    curves: Dict[str, Tuple[pd.Series, pd.Series]] = {}
    if not progress_dir.exists():
        return curves
    for csv_path in progress_dir.glob("*_progress.csv"):
        agent = csv_path.stem.replace("_progress", "")
        df = pd.read_csv(csv_path)
        if {"episode", "episode_reward"} <= set(df.columns) and not df.empty:
            curves[agent] = (df["episode"], df["episode_reward"])
    return curves


def plot_curves(curves: Dict[str, Tuple[pd.Series, pd.Series]], xlabel: str, ylabel: str, title: str) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(10, 5))
    for agent, (x, y) in sorted(curves.items()):
        ax.plot(x, y, label=agent)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    if curves:
        ax.legend()
    fig.tight_layout()
    return fig


def main() -> None:
    ap = argparse.ArgumentParser(description="Grafica comparativa de entrenamiento OE3 (SAC/PPO/A2C)")
    ap.add_argument("--config", default="configs/default.yaml", help="(No usado, solo compatibilidad de CLI)")
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    train_dir = repo_root / "analyses" / "oe3" / "training"
    progress_dir = train_dir / "progress"

    metric_curves = load_metric_curves(train_dir)
    episode_curves = load_episode_curves(progress_dir)

    if not metric_curves and not episode_curves:
        print("No se encontraron curvas de entrenamiento en analyses/oe3/training/.")
        return

    plots: List[Tuple[plt.Figure, Path]] = []

    if metric_curves:
        fig1 = plot_curves(
            metric_curves,
            xlabel="step",
            ylabel="mean_reward",
            title="OE3 - Entrenamiento (mean_reward vs step)",
        )
        plots.append((fig1, train_dir / "training_comparison.png"))

    if episode_curves:
        fig2 = plot_curves(
            episode_curves,
            xlabel="episodio",
            ylabel="episode_reward",
            title="OE3 - Recompensa por episodio",
        )
        plots.append((fig2, train_dir / "training_comparison_episode_reward.png"))

    for fig, path in plots:
        fig.savefig(path, dpi=150, bbox_inches="tight")
        print(f"OK guardado: {path}")
        plt.close(fig)


if __name__ == "__main__":
    main()
