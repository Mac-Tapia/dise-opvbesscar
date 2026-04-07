"""training_metrics.py — Métricas de Entrenamiento por Agente RL (pvbesscar OE3)

Genera por cada agente (A2C, SAC, PPO):
  - Curva de convergencia con banda ±1σ y media móvil
  - Curva de varianza por episodio (robustez estocástica)
  - Tabla de métricas estadísticas en la misma figura
  - episode_stats_{agent}.csv — datos por episodio (rolling mean, std, variance)
  - training_stats_{agent}.json — resumen estadístico completo

Uso (al final de cada train_*.py):
    from training_metrics import generate_all_training_metrics
    generate_all_training_metrics('A2C', callback.episode_rewards, OUTPUT_DIR)
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")  # headless — sin GUI
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import pandas as pd
from scipy import stats

# ---------------------------------------------------------------------------
# Paleta de colores por agente (usada también en compare_agents_training.py)
# ---------------------------------------------------------------------------
AGENT_COLORS: dict[str, str] = {
    "A2C": "#1565C0",   # Azul
    "SAC": "#6A1B9A",   # Violeta
    "PPO": "#E65100",   # Naranja
}

# ---------------------------------------------------------------------------
# Funciones internas
# ---------------------------------------------------------------------------

def _rolling_stats(
    arr: np.ndarray, window: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Rolling mean, std y variance con min_periods=1."""
    s = pd.Series(arr)
    rm = s.rolling(window, min_periods=1).mean().values
    rs = s.rolling(window, min_periods=1).std(ddof=1).fillna(0.0).values
    rv = rs ** 2
    return rm, rs, rv


def _convergence_episode(rewards: np.ndarray, threshold: float = 0.90) -> int:
    """Primer episodio donde la media móvil supera 90 % del máximo alcanzado."""
    if len(rewards) < 2:
        return 0
    w = max(2, len(rewards) // 5)
    rm, _, _ = _rolling_stats(rewards, w)
    target = threshold * float(np.max(rm))
    idx = int(np.argmax(rm >= target))
    return idx


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def compute_robustness_stats(
    agent_name: str, episode_rewards: list[float]
) -> dict:
    """Calcula estadísticos de robustez estocástica para un agente.

    Returns un dict con todas las métricas — también guardado como JSON.
    """
    if not episode_rewards:
        return {"agent": agent_name, "n_episodes": 0, "error": "no episode data"}

    arr = np.array(episode_rewards, dtype=float)
    n = len(arr)
    w = max(2, min(5, n // 2))
    rm, rs, rv = _rolling_stats(arr, w)

    # Tendencia lineal
    x = np.arange(n, dtype=float)
    slope, intercept, r_value, p_value, _ = stats.linregress(x, arr)

    # Media "convergida" — últimos 30 % de episodios
    tail_n = max(1, int(n * 0.30))
    tail_mean = float(np.mean(arr[-tail_n:]))
    tail_std = float(np.std(arr[-tail_n:], ddof=1)) if tail_n > 1 else 0.0

    # Índice de estabilidad: 1 – CV(últimos 30%), rango [0, 1]
    denom = abs(tail_mean) if abs(tail_mean) > 1e-9 else 1.0
    cv_tail = tail_std / denom
    stability_index = float(max(0.0, 1.0 - min(1.0, cv_tail)))

    q25, q50, q75 = map(float, np.percentile(arr, [25, 50, 75]))
    mean_rew = float(np.mean(arr))
    std_rew = float(np.std(arr, ddof=1)) if n > 1 else 0.0
    cv_rew = std_rew / abs(mean_rew) if abs(mean_rew) > 1e-9 else 0.0

    return {
        "agent": agent_name,
        "n_episodes": n,
        # Tendencia central
        "mean_reward": mean_rew,
        "std_reward": std_rew,
        "cv_reward": float(cv_rew),              # Coef. variación global
        "min_reward": float(np.min(arr)),
        "max_reward": float(np.max(arr)),
        "q25_reward": q25,
        "median_reward": q50,
        "q75_reward": q75,
        "iqr_reward": float(q75 - q25),
        # Mejor episodio
        "best_episode": int(np.argmax(arr)),
        "best_reward": float(np.max(arr)),
        # Estabilidad al final del entrenamiento
        "final_mean_reward": tail_mean,
        "final_std_reward": tail_std,
        "final_n_episodes_used": tail_n,
        "stability_index": stability_index,      # 0–1, > 0.70 es estable
        # Tendencia de aprendizaje
        "trend_slope": float(slope),             # > 0 = mejorando con episodios
        "trend_intercept": float(intercept),
        "trend_r2": float(r_value ** 2),
        "trend_p_value": float(p_value),
        "trend_improving": bool(slope > 0),
        # Convergencia
        "convergence_episode": _convergence_episode(arr),
        # Varianza
        "mean_variance": float(np.mean(rv)),
        "max_variance": float(np.max(rv)),
    }


def plot_convergence_curve(
    agent_name: str,
    episode_rewards: list[float],
    output_dir: Path,
    window: int | None = None,
) -> Path:
    """Genera la figura de convergencia + varianza + tabla de robustez.

    Salida: convergence_curve_{agent_name}.png (dpi=150, 14×11 in)
    """
    out_path = output_dir / f"convergence_curve_{agent_name}.png"

    if not episode_rewards:
        print(f"  [SKIP] convergence_curve_{agent_name}.png — sin datos de episodio")
        return out_path

    arr = np.array(episode_rewards, dtype=float)
    n = len(arr)
    w = window or max(2, min(5, n // 2))
    rm, rs, rv = _rolling_stats(arr, w)
    color = AGENT_COLORS.get(agent_name, "#333333")
    episodes = np.arange(1, n + 1)
    robust = compute_robustness_stats(agent_name, episode_rewards)
    tail_n = robust["final_n_episodes_used"]

    # ── Figura con 3 paneles ──────────────────────────────────────────────
    fig = plt.figure(figsize=(14, 11))
    gs = gridspec.GridSpec(3, 1, hspace=0.50, figure=fig,
                           height_ratios=[2.2, 1.3, 1.5])

    # Panel 1 — Curva de recompensa + media móvil + banda de incertidumbre
    ax1 = fig.add_subplot(gs[0])
    ax1.scatter(episodes, arr, color=color, alpha=0.40, s=20, zorder=2,
                label="Recompensa por episodio")
    ax1.plot(episodes, rm, color=color, lw=2.2, zorder=3,
             label=f"Media móvil (ventana={w})")
    ax1.fill_between(episodes, rm - rs, rm + rs,
                     color=color, alpha=0.18,
                     label=f"±1 Desv. Estándar (ventana={w})")
    ax1.axhline(robust["final_mean_reward"], color="black", lw=1.3, ls=":",
                label=f"Media convergida (últ. {tail_n} ep): "
                      f"{robust['final_mean_reward']:.3f}")

    best_idx = robust["best_episode"]
    ax1.annotate(
        f"Mejor\nep {best_idx + 1}\n({arr[best_idx]:.2f})",
        xy=(best_idx + 1, arr[best_idx]),
        xytext=(best_idx + 1 + max(1, n * 0.06), arr[best_idx]),
        fontsize=7.5, color="darkgray",
        arrowprops=dict(arrowstyle="->", color="darkgray", lw=0.9),
    )
    ax1.set_title(
        f"[{agent_name}] Curva de Convergencia — Recompensas Acumuladas por Episodio",
        fontsize=12, fontweight="bold",
    )
    ax1.set_xlabel("Episodio de entrenamiento")
    ax1.set_ylabel("Recompensa acumulada (suma ponderada)")
    ax1.legend(fontsize=8, loc="lower right")
    ax1.grid(True, alpha=0.28)

    # Panel 2 — Varianza por episodio (robustez estocástica)
    ax2 = fig.add_subplot(gs[1])
    ax2.plot(episodes, rv, color=color, lw=1.6, alpha=0.85,
             label=f"Varianza rolling (ventana={w})")
    ax2.fill_between(episodes, 0, rv, color=color, alpha=0.14)
    ax2.set_title(
        f"[{agent_name}] Varianza por Episodio — Análisis de Robustez Estocástica",
        fontsize=11,
    )
    ax2.set_xlabel("Episodio")
    ax2.set_ylabel("Varianza")
    ax2.legend(fontsize=8, loc="upper right")
    ax2.grid(True, alpha=0.28)

    # Panel 3 — Tabla de métricas de robustez
    ax3 = fig.add_subplot(gs[2])
    ax3.axis("off")

    rows = [
        ["N episodios entrenados", f"{n}", ""],
        ["Media ± Desv. Est.", f"{robust['mean_reward']:.4f} ± {robust['std_reward']:.4f}", ""],
        ["Coef. Variación (CV)", f"{robust['cv_reward']:.4f}",
         "< 0.10 = muy estable; < 0.25 = aceptable"],
        ["Mínimo / Máximo", f"{robust['min_reward']:.3f} / {robust['max_reward']:.3f}", ""],
        ["Mediana (Q50)", f"{robust['median_reward']:.4f}", ""],
        ["IQR (Q75 − Q25)", f"{robust['iqr_reward']:.4f}", "dispersión del 50 % central"],
        ["Mejor episodio", f"ep {best_idx + 1}  ({robust['best_reward']:.4f})", ""],
        ["Episodio de convergencia",
         f"ep {robust['convergence_episode'] + 1}", "1er ep ≥ 90 % del máximo"],
        ["Pendiente de tendencia", f"{robust['trend_slope']:.5f}",
         "> 0 = aprendiendo continuamente"],
        ["R² de tendencia lineal", f"{robust['trend_r2']:.4f}",
         "ajuste de la regresión lineal"],
        ["Índice de estabilidad", f"{robust['stability_index']:.4f}",
         "0–1; > 0.70 = entrenamiento estable"],
        ["Media convergida (final)", f"{robust['final_mean_reward']:.4f}",
         f"promedio de los últimos {tail_n} episodios"],
    ]
    col_labels = ["Métrica", "Valor", "Referencia / Interpretación"]
    col_widths = [0.32, 0.24, 0.44]

    tbl = ax3.table(
        cellText=rows,
        colLabels=col_labels,
        colWidths=col_widths,
        loc="upper center",
        cellLoc="center",
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(8.5)
    tbl.scale(1.0, 1.38)

    # Estilo encabezado
    for j in range(3):
        tbl[0, j].set_facecolor(color)
        tbl[0, j].set_text_props(color="white", fontweight="bold")
    # Filas alternas
    for row_i in range(1, len(rows) + 1):
        fc = "#E8EAF6" if row_i % 2 == 0 else "white"
        for j in range(3):
            tbl[row_i, j].set_facecolor(fc)

    ax3.set_title(
        f"[{agent_name}] Métricas de Robustez Estocástica y Estadísticos de Convergencia",
        fontsize=10.5, pad=6,
    )

    fig.suptitle(
        f"Análisis de Entrenamiento — Agente {agent_name} | pvbesscar OE3 | Iquitos, Perú",
        fontsize=13, fontweight="bold", y=0.995,
    )

    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] convergence_curve_{agent_name}.png  =>  {out_path}")
    return out_path


def save_episode_stats(
    agent_name: str,
    episode_rewards: list[float],
    output_dir: Path,
) -> Path:
    """Guarda CSV con estadísticos rolling por episodio."""
    out_path = output_dir / f"episode_stats_{agent_name}.csv"
    if not episode_rewards:
        return out_path

    arr = np.array(episode_rewards, dtype=float)
    n = len(arr)
    w = max(2, min(5, n // 2))
    rm, rs, rv = _rolling_stats(arr, w)

    df = pd.DataFrame({
        "episode":          np.arange(1, n + 1),
        "reward":           arr,
        "rolling_mean":     rm,
        "rolling_std":      rs,
        "rolling_variance": rv,
        "cumulative_mean":  np.cumsum(arr) / np.arange(1, n + 1, dtype=float),
        "reward_z_score":   (arr - arr.mean()) / (arr.std(ddof=1) + 1e-12),
    })
    df.to_csv(out_path, index=False, encoding="utf-8")
    print(f"  [OK] episode_stats_{agent_name}.csv  ({n} episodios)  =>  {out_path}")
    return out_path


def save_training_stats_json(
    agent_name: str,
    episode_rewards: list[float],
    output_dir: Path,
    extra: dict | None = None,
) -> Path:
    """Guarda JSON con todos los estadísticos de robustez."""
    robust = compute_robustness_stats(agent_name, episode_rewards)
    if extra:
        robust.update(extra)
    out_path = output_dir / f"training_stats_{agent_name}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(robust, f, indent=2, ensure_ascii=False, default=str)
    print(f"  [OK] training_stats_{agent_name}.json  =>  {out_path}")
    return out_path


def generate_all_training_metrics(
    agent_name: str,
    episode_rewards: list[float],
    output_dir: Path,
    extra_stats: dict | None = None,
    window: int | None = None,
) -> None:
    """Punto de entrada principal — llamar al final de cada entrenamiento.

    Genera los 3 archivos:
      convergence_curve_{agent}.png
      episode_stats_{agent}.csv
      training_stats_{agent}.json
    """
    if not episode_rewards:
        print(f"  [WARN] training_metrics: sin episode_rewards para {agent_name}, saltando.")
        return

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*70}")
    print(f"  METRICAS DE CONVERGENCIA Y ROBUSTEZ — Agente {agent_name}")
    print(f"{'='*70}")
    plot_convergence_curve(agent_name, episode_rewards, output_dir, window=window)
    save_episode_stats(agent_name, episode_rewards, output_dir)
    save_training_stats_json(agent_name, episode_rewards, output_dir, extra=extra_stats)
    print(f"  3 archivos generados en: {output_dir}")
    print(f"{'='*70}\n")
