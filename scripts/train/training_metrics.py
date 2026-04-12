"""training_metrics.py — Curvas de Aprendizaje y Métricas RL (pvbesscar OE3)
   Nivel: Tesis Doctoral / Artículo Científico

   Genera por agente (SAC / PPO / A2C):
   ├─ fig1_learning_curve_{agent}.png     — Convergencia + varianza + tabla [Ref 1,4]
   ├─ fig2_co2_reduction_{agent}.png      — Reducción CO₂ directa e indirecta [Ref 5,6]
   ├─ fig3_energy_management_{agent}.png  — Solar, red, BESS, EV por episodio [Ref 5,7]
   ├─ fig4_reward_components_{agent}.png  — Descomposición multi-objetivo [Ref 7]
   ├─ fig5_agent_diagnostics_{agent}.png  — Diagnósticos del algoritmo [Ref 1,2,3]
   ├─ fig6_phd_dashboard_{agent}.png      — Dashboard integral 3×3 [Ref 4]
   ├─ episode_stats_{agent}.csv           — Estadísticos rolling por episodio
   └─ training_stats_{agent}.json         — Resumen estadístico completo

   Referencias:
   [1] Haarnoja et al. (2018) Soft Actor-Critic. ICML.
   [2] Schulman et al. (2017) PPO. arXiv:1707.06347.
   [3] Mnih et al. (2016) A3C. ICML.
   [4] Henderson et al. (2018) Deep RL That Matters. AAAI.
   [5] Pigott et al. (2022) CityLearn 2022 Challenge.
   [6] Vázquez-Canteli & Nagy (2019) RL for demand response. Appl. Energy.
   [7] Liu et al. (2021) Multi-objective RL for energy management. Energy.

Uso (al final de cada train_*.py):
    from training_metrics import generate_all_training_metrics
    generate_all_training_metrics(
        agent_name='SAC',
        episode_rewards=cb.episode_rewards,
        output_dir=OUTPUT_DIR,
        episode_co2_direct=cb.episode_co2_avoided_direct,
        episode_co2_indirect=cb.episode_co2_avoided_indirect,
        episode_solar_kwh=cb.episode_solar_kwh,
        episode_grid_import=cb.episode_grid_import,
        episode_bess_discharge=cb.episode_bess_discharge_kwh,
        episode_bess_charge=cb.episode_bess_charge_kwh,
        episode_cost_usd=cb.episode_cost_usd,
        episode_ev_peak_kwh=cb.episode_ev_charging_peak,
        episode_ev_offpeak_kwh=cb.episode_ev_charging_offpeak,
        reward_components={'CO2': cb.episode_r_co2, 'Solar': cb.episode_r_solar, ...},
        agent_diagnostics={'actor_loss': mcb.actor_loss_history, ...},
    )
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
    rm = np.asarray(s.rolling(window, min_periods=1).mean().values, dtype=np.float64)
    rs = np.asarray(s.rolling(window, min_periods=1).std(ddof=1).fillna(0.0).values, dtype=np.float64)
    rv = np.asarray((rs ** 2), dtype=np.float64)
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


def _smooth(data: list[float], window: int = 5) -> np.ndarray:
    """Rolling mean para suavizar curvas de update-step (ventanas >5)."""
    if not data:
        return np.array([])
    s = pd.Series(data)
    return np.asarray(s.rolling(window, min_periods=1).mean().values, dtype=np.float64)


# ---------------------------------------------------------------------------
# Figura 2: Reducción de CO₂ por episodio
# Ref: Pigott et al. (2022) CityLearn; Vázquez-Canteli & Nagy (2019)
# ---------------------------------------------------------------------------

def _fig2_co2_reduction(
    agent_name: str,
    co2_direct: np.ndarray,
    co2_indirect: np.ndarray,
    output_dir: Path,
    color: str,
) -> None:
    """Figura 2 — Reducción CO₂ directa, indirecta y acumulada por episodio."""
    n = max(len(co2_direct), len(co2_indirect))
    if n < 2:
        return
    eps = np.arange(1, n + 1)

    # Rellenar arrays de desigual longitud
    d = np.array(co2_direct,   dtype=float) if len(co2_direct)   >= n else np.pad(co2_direct,   (0, n - len(co2_direct)),   constant_values=np.nan)
    i = np.array(co2_indirect, dtype=float) if len(co2_indirect) >= n else np.pad(co2_indirect, (0, n - len(co2_indirect)), constant_values=np.nan)
    total = np.where(~np.isnan(d) & ~np.isnan(i), d + i,
            np.where(~np.isnan(d), d, np.where(~np.isnan(i), i, np.nan)))

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle(
        f"[{agent_name}] Reducción de CO₂ por Episodio — pvbesscar OE3\n"
        f"Ref: Pigott et al. (2022) CityLearn; Vázquez-Canteli & Nagy (2019) Appl. Energy",
        fontsize=12, fontweight="bold",
    )

    datasets = [
        (d, "CO₂ Directo evitado\n(combustión vehicular)", "#388E3C"),
        (i, "CO₂ Indirecto evitado\n(importación red × 0.4521 kg/kWh)", "#1565C0"),
        (total, "CO₂ Total evitado\n(directo + indirecto)", color),
    ]

    for ax, (arr, label, c) in zip(axes, datasets):
        valid = ~np.isnan(arr)
        if valid.sum() < 2:
            ax.set_visible(False)
            continue
        w = max(2, min(5, valid.sum() // 2))
        rm, _, _ = _rolling_stats(arr[valid].tolist(), w)
        ep_valid = eps[valid]

        ax.bar(ep_valid, arr[valid], color=c, alpha=0.35, width=0.8, label="Por episodio")
        ax.plot(ep_valid, rm, color=c, lw=2.2, label=f"Media móvil (w={w})")

        # Área acumulada (eje derecho)
        ax2 = ax.twinx()
        ax2.plot(ep_valid, np.cumsum(arr[valid]), color="gray", lw=1.4, ls="--",
                 alpha=0.7, label="Acumulado")
        ax2.set_ylabel("CO₂ Acumulado (kg)", fontsize=8, color="gray")
        ax2.tick_params(axis="y", labelcolor="gray", labelsize=7)

        ax.set_xlabel("Episodio", fontsize=9)
        ax.set_ylabel("kg CO₂ evitado / episodio", fontsize=9)
        ax.set_title(label, fontsize=10)
        ax.legend(fontsize=7, loc="upper left")
        ax.grid(True, alpha=0.28)

    plt.tight_layout()
    out = output_dir / f"fig2_co2_reduction_{agent_name}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] fig2_co2_reduction_{agent_name}.png")


# ---------------------------------------------------------------------------
# Figura 3: Gestión energética por episodio
# Ref: Pigott et al. (2022); Siano et al. (2021) EV Smart Charging; Liu et al. (2021)
# ---------------------------------------------------------------------------

def _fig3_energy_management(
    agent_name: str,
    solar_kwh: list[float],
    grid_import: list[float],
    bess_discharge: list[float],
    bess_charge: list[float],
    ev_peak: list[float],
    ev_offpeak: list[float],
    co2_direct: list[float],
    output_dir: Path,
    color: str,
) -> None:
    """Figura 3 — Solar, red, BESS, EV y CO₂ directo por episodio."""
    n = len(solar_kwh) or len(grid_import) or len(bess_discharge)
    if n < 2:
        return
    eps = np.arange(1, n + 1)

    def _arr(lst: list[float]) -> np.ndarray:
        a = np.array(lst[:n], dtype=float)
        if len(a) < n:
            a = np.pad(a, (0, n - len(a)), constant_values=np.nan)
        return a

    sol = _arr(solar_kwh)
    grid = _arr(grid_import)
    bd = _arr(bess_discharge)
    bc = _arr(bess_charge)
    bess_net = bd - bc  # >0 descargando, <0 cargando
    ep_v = _arr(ev_peak)
    ep_o = _arr(ev_offpeak)
    co2_dir = _arr(co2_direct)
    ev_total = np.where(~np.isnan(ep_v) & ~np.isnan(ep_o), ep_v + ep_o, np.nan)
    ev_pct = np.where(ev_total > 1e-3, ep_v / ev_total * 100, np.nan)

    w = max(2, min(5, n // 2))

    fig, axes = plt.subplots(2, 3, figsize=(18, 11))
    fig.suptitle(
        f"[{agent_name}] Gestión Energética por Episodio — pvbesscar OE3\n"
        f"Ref: Pigott et al. (2022) CityLearn; Liu et al. (2021) Energy; "
        f"Siano et al. (2021) EV Smart Charging",
        fontsize=11, fontweight="bold",
    )

    panels = [
        (sol,      "Solar Utilizada (kWh/episodio)",          "#F9A825", False),
        (grid,     "Importación de Red (kWh/episodio)",       "#D32F2F", False),
        (bess_net, "BESS Neto (kWh/episodio)\n>0=descarga, <0=carga", "#4A148C", True),
        (ev_pct,   "% EV en Hora Pico (9–22 h)",              "#00796B", False),
        (co2_dir,  "CO₂ Directo Evitado (kg/episodio)\n(combustón vehicular evitada)  [↑ mayor = mejor]", "#2E7D32", False),
        (ev_total, "Total Energía EV Cargada (kWh/episodio)", color,     False),
    ]

    for ax, (arr, label, c, zero_line) in zip(axes.flat, panels):
        valid = ~np.isnan(arr)
        if valid.sum() < 2:
            ax.axis("off")
            continue
        ep_v2 = eps[valid]
        arr_v = arr[valid]
        rm, _, _ = _rolling_stats(arr_v.tolist(), w)

        ax.bar(ep_v2, arr_v, color=c, alpha=0.30, width=0.8)
        ax.plot(ep_v2, rm, color=c, lw=2.2, label=f"Media móvil (w={w})")

        if zero_line:
            ax.axhline(0, color="black", lw=0.9, ls="--")

        # Tendencia lineal
        if len(ep_v2) > 3:
            z = np.polyfit(ep_v2, arr_v, 1)
            ax.plot(ep_v2, np.poly1d(z)(ep_v2), "k--", lw=1.0, alpha=0.55,
                    label=f"Tendencia (slope={z[0]:.1f})")

        ax.set_xlabel("Episodio", fontsize=8)
        ax.set_ylabel(label, fontsize=8)
        ax.set_title(label.split("\n")[0], fontsize=9, fontweight="bold")
        ax.legend(fontsize=7)
        ax.grid(True, alpha=0.25)

    plt.tight_layout()
    out = output_dir / f"fig3_energy_management_{agent_name}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] fig3_energy_management_{agent_name}.png")


# ---------------------------------------------------------------------------
# Figura 4: Descomposición multi-objetivo del reward
# Ref: Liu et al. (2021) Multi-objective RL; Schulman et al. (2017)
# ---------------------------------------------------------------------------

def _fig4_reward_components(
    agent_name: str,
    components: dict[str, list[float]],
    output_dir: Path,
    color: str,
) -> None:
    """Figura 4 — Evolución de cada componente de reward por episodio."""
    if not components:
        return
    data = {k: np.array(v, dtype=float) for k, v in components.items() if v}
    if not data:
        return

    n = max(len(v) for v in data.values())
    if n < 2:
        return
    eps = np.arange(1, n + 1)
    nc = len(data)
    w = max(2, min(5, n // 2))

    # Paleta multi-objetivo
    palette = ["#E53935", "#F9A825", "#43A047", "#1E88E5",
               "#8E24AA", "#00ACC1", "#FB8C00", "#6D4C41"]

    fig, axes = plt.subplots(nc, 1, figsize=(14, 2.8 * nc), squeeze=False)
    fig.suptitle(
        f"[{agent_name}] Descomposición Multi-Objetivo del Reward por Episodio\n"
        f"Ref: Liu et al. (2021) Energy; Schulman et al. (2017) PPO arXiv:1707.06347",
        fontsize=12, fontweight="bold",
    )

    for idx, (name, arr) in enumerate(data.items()):
        ax = axes[idx, 0]
        c = palette[idx % len(palette)]

        # Padding si hay longitudes distintas
        if len(arr) < n:
            arr = np.pad(arr, (0, n - len(arr)), constant_values=np.nan)

        valid = ~np.isnan(arr)
        if valid.sum() < 2:
            ax.axis("off")
            continue

        ep_v = eps[valid]
        arr_v = arr[valid]
        rm, rs, _ = _rolling_stats(arr_v.tolist(), w)

        ax.fill_between(ep_v, rm - rs, rm + rs, color=c, alpha=0.18)
        ax.plot(ep_v, arr_v, color=c, alpha=0.35, lw=0.7)
        ax.plot(ep_v, rm, color=c, lw=2.2, label=f"{name} — media móvil (w={w})")
        ax.axhline(0, color="black", lw=0.7, ls=":")

        mean_val = float(np.nanmean(arr_v))
        ax.axhline(mean_val, color=c, lw=1.0, ls="--", alpha=0.6,
                   label=f"Media global: {mean_val:.4f}")

        ax.set_ylabel(name, fontsize=8)
        ax.legend(fontsize=7, loc="upper right")
        ax.grid(True, alpha=0.25)
        if idx == nc - 1:
            ax.set_xlabel("Episodio de entrenamiento", fontsize=9)

    plt.tight_layout()
    out = output_dir / f"fig4_reward_components_{agent_name}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] fig4_reward_components_{agent_name}.png")


# ---------------------------------------------------------------------------
# Figura 5: Diagnósticos del agente (algoritmo-específicos)
# Ref: Haarnoja (2018) SAC; Schulman (2017) PPO; Mnih (2016) A3C
# ---------------------------------------------------------------------------

# Configuración de cada métrica de diagnóstico por agente
_DIAG_META: dict[str, tuple[str, str, float | None, float | None, bool]] = {
    # key: (label_display, color, warn_low, warn_high, lower_is_better)
    "actor_loss":    ("Actor Loss (SAC)",      "#6A1B9A", None, None,   True),
    "critic_loss":   ("Critic Loss (SAC)",     "#AD1457", None, 1000.0, True),
    "entropy":       ("Entropía / ent_coef",   "#00796B", 0.01, None,   False),
    "kl_divergence": ("KL Divergence (PPO)",   "#E65100", None, 0.05,   True),
    "clip_fraction": ("Clip Fraction (PPO)",   "#FF8F00", None, 0.30,   True),
    "policy_loss":   ("Policy Loss",           "#283593", None, None,   True),
    "value_loss":    ("Value Loss",            "#B71C1C", None, None,   True),
    "explained_var": ("Explained Variance",    "#1B5E20", 0.0,  None,   False),
    "grad_norm":     ("Grad Norm",             "#4E342E", None, None,   True),
}

_DIAG_REFS: dict[str, str] = {
    "SAC": "Haarnoja et al. (2018) SAC ICML",
    "PPO": "Schulman et al. (2017) PPO arXiv:1707.06347",
    "A2C": "Mnih et al. (2016) A3C ICML",
}


def _fig5_agent_diagnostics(
    agent_name: str,
    diagnostics: dict[str, list[float]],
    output_dir: Path,
) -> None:
    """Figura 5 — Evolución de métricas internas del algoritmo (por update/rollout)."""
    valid_diags = {k: v for k, v in diagnostics.items() if v and len(v) >= 2}
    if not valid_diags:
        return

    nc = len(valid_diags)
    ncols = min(2, nc)
    nrows = (nc + ncols - 1) // ncols
    w_smooth = max(5, min(30, len(next(iter(valid_diags.values()))) // 20))

    fig, axes = plt.subplots(nrows, ncols, figsize=(14, 3.5 * nrows), squeeze=False)
    ref = _DIAG_REFS.get(agent_name, "Schulman et al. (2017)")
    fig.suptitle(
        f"[{agent_name}] Diagnósticos del Algoritmo — Métricas por Update/Rollout\n"
        f"Ref: {ref}",
        fontsize=12, fontweight="bold",
    )

    for idx, (key, values) in enumerate(valid_diags.items()):
        row, col = divmod(idx, ncols)
        ax = axes[row, col]
        arr = np.array(values, dtype=float)
        n = len(arr)
        steps = np.arange(1, n + 1)
        sm = _smooth(values, w_smooth)

        meta = _DIAG_META.get(key, (key, "#333333", None, None, True))
        label, c, warn_low, warn_high, lower_better = meta

        ax.plot(steps, arr, color=c, alpha=0.25, lw=0.6, label="Raw")
        ax.plot(steps, sm, color=c, lw=2.2, label=f"Suavizado (w={w_smooth})")

        if warn_high is not None:
            ax.axhline(warn_high, color="red", ls="--", lw=1.1, alpha=0.7,
                       label=f"Umbral alto ({warn_high})")
        if warn_low is not None:
            ax.axhline(warn_low, color="orange", ls="--", lw=1.1, alpha=0.7,
                       label=f"Umbral bajo ({warn_low})")

        direction = "↓ menor = mejor" if lower_better else "↑ mayor = mejor"
        ax.set_title(f"{label}  ({direction})", fontsize=9, fontweight="bold")
        ax.set_xlabel(f"Update step (total: {n:,})", fontsize=8)
        ax.set_ylabel(label, fontsize=8)
        ax.legend(fontsize=7, loc="upper right")
        ax.grid(True, alpha=0.25)

        # Anotación estadística
        mean_v = float(np.mean(arr))
        final_v = float(arr[-1])
        ax.annotate(
            f"μ={mean_v:.4f}  final={final_v:.4f}",
            xy=(0.02, 0.06), xycoords="axes fraction",
            fontsize=7, color="gray",
        )

    # Ocultar ejes vacíos
    for idx2 in range(nc, nrows * ncols):
        row, col = divmod(idx2, ncols)
        axes[row, col].set_visible(False)

    plt.tight_layout()
    out = output_dir / f"fig5_agent_diagnostics_{agent_name}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] fig5_agent_diagnostics_{agent_name}.png")


# ---------------------------------------------------------------------------
# Figura 6: Dashboard PhD integral 3×3
# Ref: Henderson et al. (2018) "Deep RL That Matters"; Schulman (2017)
# ---------------------------------------------------------------------------

def _fig6_phd_dashboard(
    agent_name: str,
    rewards: np.ndarray,
    co2_direct: np.ndarray | None,
    co2_indirect: np.ndarray | None,
    solar_kwh: np.ndarray | None,
    grid_import: np.ndarray | None,
    bess_net: np.ndarray | None,
    ev_pct: np.ndarray | None,
    cost_usd: np.ndarray | None,
    diag_primary: tuple[str, np.ndarray] | None,
    diag_secondary: tuple[str, np.ndarray] | None,
    output_dir: Path,
    color: str,
) -> None:
    """Figura 6 — Dashboard PhD 3×3 con las métricas más relevantes."""
    n = len(rewards)
    if n < 2:
        return
    eps = np.arange(1, n + 1)
    w = max(2, min(5, n // 2))

    co2_total = None
    if co2_direct is not None and co2_indirect is not None:
        valid_d = len(co2_direct) >= n
        valid_i = len(co2_indirect) >= n
        if valid_d and valid_i:
            co2_total = np.array(co2_direct[:n]) + np.array(co2_indirect[:n])

    rm_rew, rs_rew, rv_rew = _rolling_stats(rewards.tolist(), w)

    fig, axes = plt.subplots(3, 3, figsize=(18, 14))
    fig.suptitle(
        f"Dashboard PhD — Agente {agent_name} | pvbesscar OE3 | Iquitos, Perú\n"
        f"Ref: Henderson et al. (2018) Deep RL That Matters AAAI; "
        f"Pigott et al. (2022) CityLearn",
        fontsize=13, fontweight="bold", y=1.005,
    )

    def _plot_series(ax: plt.Axes, data: np.ndarray | None, title: str,
                     ylabel: str, c: str, w_in: int) -> None:
        if data is None or len(data) < 2:
            ax.text(0.5, 0.5, "Sin datos", ha="center", va="center",
                    transform=ax.transAxes, fontsize=10, color="gray")
            ax.set_title(title, fontsize=9)
            return
        n_d = len(data)
        ep_d = np.arange(1, n_d + 1)
        w_d = max(2, min(w_in, n_d // 2))
        rm_d, _, _ = _rolling_stats(data.tolist(), w_d)
        ax.bar(ep_d, data, color=c, alpha=0.25, width=0.8)
        ax.plot(ep_d, rm_d, color=c, lw=2.0)
        ax.set_title(title, fontsize=9, fontweight="bold")
        ax.set_xlabel("Episodio", fontsize=7)
        ax.set_ylabel(ylabel, fontsize=7)
        ax.grid(True, alpha=0.22)
        ax.tick_params(labelsize=7)

    # (0,0) Curva de aprendizaje — reward
    ax = axes[0, 0]
    ax.scatter(eps, rewards, color=color, alpha=0.4, s=18, zorder=2)
    ax.plot(eps, rm_rew, color=color, lw=2.2, label="Media móvil")
    ax.fill_between(eps, rm_rew - rs_rew, rm_rew + rs_rew, color=color, alpha=0.15,
                    label="±1σ")
    ax.set_title("Recompensa por Episodio\n(Media ± 1σ) [Henderson 2018]",
                 fontsize=9, fontweight="bold")
    ax.set_xlabel("Episodio", fontsize=7)
    ax.set_ylabel("Reward acumulado", fontsize=7)
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.22)
    ax.tick_params(labelsize=7)

    # (0,1) Varianza del reward
    ax = axes[0, 1]
    ax.fill_between(eps, 0, rv_rew, color=color, alpha=0.3)
    ax.plot(eps, rv_rew, color=color, lw=1.8)
    ax.set_title("Varianza del Reward por Episodio\n(Robustez Estocástica) [Henderson 2018]",
                 fontsize=9, fontweight="bold")
    ax.set_xlabel("Episodio", fontsize=7)
    ax.set_ylabel("Varianza", fontsize=7)
    ax.grid(True, alpha=0.22)
    ax.tick_params(labelsize=7)

    # (0,2) CO2 total
    _plot_series(axes[0, 2], co2_total,
                 "CO₂ Total Evitado (kg/episodio)\n[Pigott 2022; Vázquez-Canteli 2019]",
                 "kg CO₂", "#2E7D32", w)

    # (1,0) Solar utilización
    sol = np.array(solar_kwh[:n], dtype=float) if solar_kwh and len(solar_kwh) >= 2 else None
    _plot_series(axes[1, 0], sol,
                 "Energía Solar Aprovechada\n(kWh/episodio) [Liu 2021]",
                 "kWh", "#F9A825", w)

    # (1,1) Grid import
    grd = np.array(grid_import[:n], dtype=float) if grid_import and len(grid_import) >= 2 else None
    _plot_series(axes[1, 1], grd,
                 "Importación de Red (kWh/episodio)\n↓ menor = menos emisiones",
                 "kWh", "#D32F2F", w)

    # (1,2) BESS net
    _plot_series(axes[1, 2], bess_net,
                 "BESS Neto (kWh/episodio)\n>0=descarga, <0=carga [Liu 2021]",
                 "kWh neto", "#4A148C", w)

    # (2,0) EV peak ratio
    ev_arr = np.array(ev_pct[:n], dtype=float) if ev_pct and len(ev_pct) >= 2 else None
    _plot_series(axes[2, 0], ev_arr,
                 "% EV Cargado en Hora Pico\n(9–22 h) [Siano 2021]",
                 "%", "#00796B", w)

    # (2,1) CO₂ Directo Evitado — el principal indicador OE3
    co2_dir_arr = np.array(co2_direct[:n], dtype=float) if co2_direct is not None and len(co2_direct) >= 2 else None
    _plot_series(axes[2, 1], co2_dir_arr,
                 "CO₂ Directo Evitado (kg/episodio)\n(combustón vehicular evitada) [↑ mayor = mejor]",
                 "kg CO₂", "#2E7D32", w)

    # (2,2) Diagnóstico primario del agente
    if diag_primary is not None:
        key_d, arr_d = diag_primary
        meta = _DIAG_META.get(key_d, (key_d, "#333333", None, None, True))
        ax = axes[2, 2]
        w_diag = max(5, min(30, len(arr_d) // 20))
        sm_d = _smooth(arr_d.tolist(), w_diag)
        steps_d = np.arange(1, len(arr_d) + 1)
        ax.plot(steps_d, arr_d, color=meta[1], alpha=0.25, lw=0.6)
        ax.plot(steps_d, sm_d, color=meta[1], lw=2.2)
        ax.set_title(f"Diagnóstico: {meta[0]}\n(update steps)", fontsize=9, fontweight="bold")
        ax.set_xlabel("Update step", fontsize=7)
        ax.set_ylabel(meta[0], fontsize=7)
        ax.grid(True, alpha=0.22)
        ax.tick_params(labelsize=7)
    else:
        axes[2, 2].axis("off")

    plt.tight_layout()
    out = output_dir / f"fig6_phd_dashboard_{agent_name}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  [OK] fig6_phd_dashboard_{agent_name}.png")


# ---------------------------------------------------------------------------
# API pública principal
# ---------------------------------------------------------------------------

def generate_all_training_metrics(
    agent_name: str,
    episode_rewards: list[float],
    output_dir: Path,
    *,
    # ── KPIs ambientales (por episodio) ──────────────────────────────────
    episode_co2_direct: list[float] | None = None,
    episode_co2_indirect: list[float] | None = None,
    episode_solar_kwh: list[float] | None = None,
    episode_grid_import: list[float] | None = None,
    episode_bess_discharge: list[float] | None = None,
    episode_bess_charge: list[float] | None = None,
    episode_cost_usd: list[float] | None = None,
    episode_ev_peak_kwh: list[float] | None = None,
    episode_ev_offpeak_kwh: list[float] | None = None,
    # ── Componentes del reward (por episodio) ────────────────────────────
    reward_components: dict[str, list[float]] | None = None,
    # ── Diagnósticos del algoritmo (por update/rollout) ──────────────────
    agent_diagnostics: dict[str, list[float]] | None = None,
    # ── Opcionales ───────────────────────────────────────────────────────
    extra_stats: dict | None = None,
    window: int | None = None,
) -> None:
    """Punto de entrada principal. Genera hasta 6 figuras + CSV + JSON por agente.

    Parámetros mínimos requeridos: agent_name, episode_rewards, output_dir.
    Todos los demás parámetros son opcionales; las figuras correspondientes se
    omiten (con aviso) si los datos no están disponibles.

    Referencias científicas usando estas curvas:
    - [1] Haarnoja et al. (2018) SAC — ICML
    - [2] Schulman et al. (2017) PPO — arXiv:1707.06347
    - [3] Mnih et al. (2016) A3C — ICML
    - [4] Henderson et al. (2018) Deep RL That Matters — AAAI
    - [5] Pigott et al. (2022) CityLearn 2022
    - [6] Vázquez-Canteli & Nagy (2019) — Appl. Energy
    - [7] Liu et al. (2021) Multi-obj RL — Energy
    """
    if not episode_rewards:
        print(f"  [WARN] training_metrics: sin episode_rewards para {agent_name}.")
        return

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    color = AGENT_COLORS.get(agent_name, "#333333")

    print(f"\n{'='*72}")
    print(f"  CURVAS DE APRENDIZAJE — Agente {agent_name}  (nivel tesis doctoral)")
    print(f"{'='*72}")

    # ── F1: Curva de aprendizaje + varianza + tabla [Henderson 2018] ──────
    plot_convergence_curve(agent_name, episode_rewards, output_dir, window=window)

    # ── F2: Reducción CO₂ [Pigott 2022; Vázquez-Canteli 2019] ────────────
    if episode_co2_direct or episode_co2_indirect:
        _fig2_co2_reduction(
            agent_name,
            episode_co2_direct or [],
            episode_co2_indirect or [],
            output_dir, color,
        )
    else:
        print(f"  [SKIP] fig2_co2_reduction — sin datos CO₂")

    # ── F3: Gestión energética [Liu 2021; Siano 2021] ─────────────────────
    if any([episode_solar_kwh, episode_grid_import, episode_bess_discharge]):
        _fig3_energy_management(
            agent_name,
            episode_solar_kwh or [],
            episode_grid_import or [],
            episode_bess_discharge or [],
            episode_bess_charge or [],
            episode_ev_peak_kwh or [],
            episode_ev_offpeak_kwh or [],
            episode_co2_direct or [],
            output_dir, color,
        )
    else:
        print(f"  [SKIP] fig3_energy_management — sin datos energéticos")

    # ── F4: Descomposición multi-objetivo [Liu 2021] ──────────────────────
    if reward_components:
        _fig4_reward_components(agent_name, reward_components, output_dir, color)
    else:
        print(f"  [SKIP] fig4_reward_components — sin datos de componentes")

    # ── F5: Diagnósticos del agente [Haarnoja 2018; Schulman 2017] ────────
    if agent_diagnostics:
        _fig5_agent_diagnostics(agent_name, agent_diagnostics, output_dir)
    else:
        print(f"  [SKIP] fig5_agent_diagnostics — sin datos de diagnóstico")

    # ── F6: Dashboard PhD 3×3 [Henderson 2018] ───────────────────────────
    arr_rew = np.array(episode_rewards, dtype=float)

    # Preparar BESS net para el dashboard
    bess_net_arr = None
    if episode_bess_discharge and episode_bess_charge:
        n_ep = len(episode_rewards)
        bd = np.array(episode_bess_discharge[:n_ep], dtype=float)
        bc = np.array(episode_bess_charge[:n_ep], dtype=float)
        if len(bd) == len(bc) and len(bd) >= 2:
            bess_net_arr = bd - bc

    # Preparar EV peak ratio
    ev_pct_arr = None
    if episode_ev_peak_kwh and episode_ev_offpeak_kwh:
        n_ep = len(episode_rewards)
        epk = np.array(episode_ev_peak_kwh[:n_ep], dtype=float)
        eop = np.array(episode_ev_offpeak_kwh[:n_ep], dtype=float)
        total_ev = epk + eop
        ev_pct_arr = np.where(total_ev > 1e-3, epk / total_ev * 100, np.nan).tolist()

    # Diagnóstico primario y secundario del agente
    diag_primary = None
    if agent_diagnostics:
        # SAC → actor_loss; PPO → kl_divergence; A2C → entropy
        pref_order = ["actor_loss", "kl_divergence", "entropy", "policy_loss"]
        for key in pref_order:
            if key in agent_diagnostics and len(agent_diagnostics[key]) >= 2:
                diag_primary = (key, np.array(agent_diagnostics[key], dtype=float))
                break

    _fig6_phd_dashboard(
        agent_name=agent_name,
        rewards=arr_rew,
        co2_direct=np.array(episode_co2_direct, dtype=float) if episode_co2_direct else None,
        co2_indirect=np.array(episode_co2_indirect, dtype=float) if episode_co2_indirect else None,
        solar_kwh=episode_solar_kwh,
        grid_import=episode_grid_import,
        bess_net=bess_net_arr,
        ev_pct=ev_pct_arr,
        cost_usd=episode_cost_usd,
        diag_primary=diag_primary,
        diag_secondary=None,
        output_dir=output_dir,
        color=color,
    )

    # ── CSV y JSON ────────────────────────────────────────────────────────
    save_episode_stats(agent_name, episode_rewards, output_dir)
    save_training_stats_json(agent_name, episode_rewards, output_dir, extra=extra_stats)

    n_figs = 6 - sum([
        not (episode_co2_direct or episode_co2_indirect),
        not any([episode_solar_kwh, episode_grid_import, episode_bess_discharge]),
        not reward_components,
        not agent_diagnostics,
    ])
    print(f"  {n_figs} figuras + CSV + JSON generados en: {output_dir}")
    print(f"{'='*72}\n")

