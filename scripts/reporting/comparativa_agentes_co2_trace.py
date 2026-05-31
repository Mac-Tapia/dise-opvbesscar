#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Comparativa completa SAC vs PPO vs A2C desde trace y convergencia.

Fuentes:
  outputs/{agent}_training/trace_{agent}.csv         — CO2 por hora
  outputs/{agent}_training/{agent}_convergencia_episodios.csv — reward/CV
  outputs/{agent}_training/{agent}_episodios_history.csv      — metricas OE3

Genera figuras en: outputs/docx/graficas/
  1. co2_convergencia_reward.png        — trayectoria reward (rolling mean 10 ep)
  2. co2_indirecto_residual.png         — F2 CO2 indirecto residual por episodio
  3. co2_evitado_total_trace.png        — CO2 total evitado (directo+indirecto) por ep
  4. grid_import_episodios.png          — importacion de red por episodio (kWh)
  5. co2_comparativa_multicriterio.png  — panel 4 criterios (barras mejores episodios)
  6. sac_convergencia_estable_inferior.png — diagnostico SAC vs PPO/A2C
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "outputs" / "docx" / "graficas"
OUT_DIR.mkdir(parents=True, exist_ok=True)

AGENTS = ("PPO", "A2C", "SAC")
COLORS = {"PPO": "#E07B39", "A2C": "#2CA02C", "SAC": "#1F77B4"}
MARKERS = {"PPO": "o", "A2C": "s", "SAC": "^"}
LS = {"PPO": "-", "A2C": "-", "SAC": "--"}

F0_KG = 7_053_999
ROWS_PER_EP = 8_760
CANONICAL = ROOT / "reports" / "oe3" / "agents_comparison_canonical.json"


# ─── loaders ────────────────────────────────────────────────────────────────

def load_convergencia(agent: str) -> pd.DataFrame:
    p = ROOT / "outputs" / f"{agent.lower()}_training" / f"{agent.lower()}_convergencia_episodios.csv"
    return pd.read_csv(p)


def load_episodios(agent: str) -> pd.DataFrame:
    p = ROOT / "outputs" / f"{agent.lower()}_training" / f"{agent.lower()}_episodios_history.csv"
    return pd.read_csv(p)


def load_trace_summary() -> pd.DataFrame:
    p = ROOT / "reports" / "oe3" / "co2_trace_direct_indirect_summary.csv"
    return pd.read_csv(p)


def load_canonical() -> dict:
    return json.loads(CANONICAL.read_text(encoding="utf-8"))


# ─── helpers ────────────────────────────────────────────────────────────────

def _save(fig: plt.Figure, name: str) -> None:
    path = OUT_DIR / name
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  guardado: {path.name}")


def _add_ppo_selected_marker(ax: plt.Axes, x: float, y: float, label: str = "PPO ep49 (seleccionado)") -> None:
    ax.annotate(
        label,
        xy=(x, y),
        xytext=(x + 2, y * 1.015),
        fontsize=8,
        color="#14532D",
        arrowprops=dict(arrowstyle="->", color="#14532D", lw=1.5),
        bbox=dict(boxstyle="round,pad=0.25", facecolor="#DFF3E7", edgecolor="#14532D", alpha=0.85),
    )


# ─── figura 1: convergencia reward ──────────────────────────────────────────

def fig_convergencia_reward() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.patch.set_facecolor("#FAFAFA")

    ax_raw, ax_roll = axes

    for agent in AGENTS:
        df = load_convergencia(agent)
        eps = df["episodio"].values
        raw = df["reward"].values
        roll = df["rolling_mean"].values
        ax_raw.plot(eps, raw, color=COLORS[agent], alpha=0.45, linewidth=1.2,
                    linestyle=LS[agent], label=f"{agent}")
        ax_roll.plot(eps, roll, color=COLORS[agent], linewidth=2.5,
                     linestyle=LS[agent], marker=MARKERS[agent], markersize=3,
                     markevery=5, label=f"{agent} (rolling 10ep)")

    # Zona plateau SAC
    ax_raw.axhspan(1450, 1510, alpha=0.08, color=COLORS["SAC"], label="SAC plateau ~1480")
    ax_roll.axhspan(1450, 1510, alpha=0.08, color=COLORS["SAC"])

    for ax in axes:
        ax.axhline(0, color="gray", linestyle=":", linewidth=1, alpha=0.5)
        ax.set_xlabel("Episodio", fontsize=11)
        ax.set_ylabel("Reward", fontsize=11)
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.25, linestyle="--")
        ax.set_xlim(1, 50)

    ax_raw.set_title("Reward por episodio (raw)", fontsize=11, fontweight="bold")
    ax_roll.set_title("Reward rolling mean 10 episodios", fontsize=11, fontweight="bold")

    fig.suptitle(
        "Convergencia OE3 — SAC vs PPO vs A2C | 50 episodios × 8,760 h | reward v7.5",
        fontsize=13, fontweight="bold",
    )
    fig.text(
        0.5, -0.03,
        "SAC mejorado converge ~ep18 a plateau ≈1,480 (200 pts por debajo de PPO/A2C). PPO y A2C mejoran hasta ep49-50.",
        ha="center", fontsize=9, color="#4B5563",
    )
    plt.tight_layout()
    _save(fig, "co2_convergencia_reward.png")


# ─── figura 2: CO2 indirecto residual F2 por episodio ───────────────────────

def fig_co2_indirecto_residual() -> None:
    fig, ax = plt.subplots(figsize=(12, 6))
    fig.patch.set_facecolor("#FAFAFA")

    canonical = load_canonical()
    best_eps = {a: canonical["agents"][a]["best_episode"] for a in AGENTS}
    best_f2 = {a: canonical["agents"][a]["f2_min_kg_per_year"] for a in AGENTS}

    for agent in AGENTS:
        df = load_episodios(agent)
        eps = df["episodio"].values
        co2_ind = df["co2_indirecta_kg"].values
        ax.plot(eps, co2_ind / 1e6, color=COLORS[agent], linewidth=2.2,
                linestyle=LS[agent], marker=MARKERS[agent], markersize=3,
                markevery=5, label=f"{agent} (F2 min={best_f2[agent]/1e6:.3f} Mt ep{best_eps[agent]})")

    ax.axhline(F0_KG / 1e6, color="darkred", linestyle=":", linewidth=2, alpha=0.7,
               label=f"F0 (sin solar/BESS/RL) = {F0_KG/1e6:.3f} Mt CO₂/año")
    ax.axhline(best_f2["PPO"] / 1e6, color=COLORS["PPO"], linestyle=":", linewidth=1.5, alpha=0.6)

    ax.set_xlabel("Episodio", fontsize=12, fontweight="bold")
    ax.set_ylabel("CO₂ indirecto residual (Mt CO₂/año)", fontsize=12, fontweight="bold")
    ax.set_title(
        "CO₂ indirecto residual por episodio (F2) — SAC vs PPO vs A2C\n"
        "Criterio OE3 canónico: menor F2 = mejor control ambiental",
        fontsize=12, fontweight="bold",
    )
    ax.legend(fontsize=9, loc="upper right")
    ax.grid(True, alpha=0.25, linestyle="--")
    ax.set_xlim(1, 50)

    _add_ppo_selected_marker(
        ax, best_eps["PPO"], best_f2["PPO"] / 1e6,
        f"PPO ep{best_eps['PPO']}\n{best_f2['PPO']/1e6:.3f} Mt",
    )

    fig.text(
        0.5, -0.03,
        f"SAC: F2 mínimo = {best_f2['SAC']/1e6:.3f} Mt (+{(best_f2['SAC']-best_f2['PPO'])/1e3:.1f} kt vs PPO). "
        f"A2C: {best_f2['A2C']/1e6:.3f} Mt (+{(best_f2['A2C']-best_f2['PPO'])/1e3:.2f} kt vs PPO).",
        ha="center", fontsize=9, color="#4B5563",
    )
    plt.tight_layout()
    _save(fig, "co2_indirecto_residual.png")


# ─── figura 3: CO2 total evitado (directo+indirecto) por episodio ────────────

def fig_co2_evitado_total() -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    fig.patch.set_facecolor("#FAFAFA")

    for agent in AGENTS:
        df = load_episodios(agent)
        eps = df["episodio"].values
        co2_dir = df["co2_directa_kg"].values
        co2_ind_avoided = df["co2_indirecta_kg"].values  # este es el indirecto evitado en episodios_history
        co2_total = co2_dir + co2_ind_avoided
        ax1.plot(eps, co2_dir / 1e3, color=COLORS[agent], linewidth=2.2,
                 linestyle=LS[agent], marker=MARKERS[agent], markersize=3,
                 markevery=5, label=agent)
        ax2.plot(eps, co2_total / 1e6, color=COLORS[agent], linewidth=2.2,
                 linestyle=LS[agent], marker=MARKERS[agent], markersize=3,
                 markevery=5, label=agent)

    ax1.set_xlabel("Episodio", fontsize=11)
    ax1.set_ylabel("CO₂ directo evitado (t CO₂/año)", fontsize=11)
    ax1.set_title("CO₂ directo evitado (ICE→EV)", fontsize=11, fontweight="bold")
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.25, linestyle="--")
    ax1.set_xlim(1, 50)

    ax2.set_xlabel("Episodio", fontsize=11)
    ax2.set_ylabel("CO₂ total evitado (Mt CO₂/año)", fontsize=11)
    ax2.set_title("CO₂ total evitado (directo + indirecto)", fontsize=11, fontweight="bold")
    ax2.legend(fontsize=9)
    ax2.grid(True, alpha=0.25, linestyle="--")
    ax2.set_xlim(1, 50)

    fig.suptitle(
        "CO₂ evitado por episodio — SAC vs PPO vs A2C | Iquitos 2024",
        fontsize=13, fontweight="bold",
    )
    plt.tight_layout()
    _save(fig, "co2_evitado_total_trace.png")


# ─── figura 4: importación de red por episodio ──────────────────────────────

def fig_grid_import() -> None:
    fig, ax = plt.subplots(figsize=(12, 6))
    fig.patch.set_facecolor("#FAFAFA")

    canonical = load_canonical()
    val_imports = {a: canonical["agents"][a]["validation_mean_grid_import_kwh"] for a in AGENTS}

    for agent in AGENTS:
        df = load_episodios(agent)
        eps = df["episodio"].values
        grid = df["grid_import_kwh"].values
        ax.plot(eps, grid / 1e6, color=COLORS[agent], linewidth=2.2,
                linestyle=LS[agent], marker=MARKERS[agent], markersize=3,
                markevery=5, label=f"{agent} (val={val_imports[agent]/1e6:.2f} M kWh)")

    ax.set_xlabel("Episodio", fontsize=12, fontweight="bold")
    ax.set_ylabel("Grid import (M kWh/año)", fontsize=12, fontweight="bold")
    ax.set_title(
        "Importación de red eléctrica por episodio — SAC vs PPO vs A2C\n"
        "Iquitos: red térmica diesel 0.4521 kg CO₂/kWh — menor import = menor CO₂",
        fontsize=12, fontweight="bold",
    )
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.25, linestyle="--")
    ax.set_xlim(1, 50)

    # Anotar diferencia SAC vs PPO
    y_ppo = val_imports["PPO"] / 1e6
    y_sac = val_imports["SAC"] / 1e6
    diff_kwh = val_imports["SAC"] - val_imports["PPO"]
    diff_co2 = diff_kwh * 0.4521 / 1e3
    ax.annotate(
        f"SAC importa\n+{diff_kwh/1e3:.1f} MWh extra\n≡ +{diff_co2:.1f} t CO₂/año",
        xy=(50, y_sac),
        xytext=(42, y_sac + 0.05),
        fontsize=8.5,
        color="#991B1B",
        arrowprops=dict(arrowstyle="->", color="#991B1B", lw=1.5),
        bbox=dict(boxstyle="round,pad=0.3", facecolor="#FEF2F2", edgecolor="#991B1B", alpha=0.85),
    )

    fig.text(
        0.5, -0.03,
        f"SAC validación: {val_imports['SAC']/1e6:.3f} M kWh | "
        f"PPO validación: {val_imports['PPO']/1e6:.3f} M kWh | "
        f"A2C validación: {val_imports['A2C']/1e6:.3f} M kWh",
        ha="center", fontsize=9, color="#4B5563",
    )
    plt.tight_layout()
    _save(fig, "grid_import_episodios.png")


# ─── figura 5: comparativa multicriterio (barras) ───────────────────────────

def fig_comparativa_multicriterio() -> None:
    canonical = load_canonical()
    trace_df = load_trace_summary()

    def best_trace(criterion: str, agent: str, col: str) -> float:
        sub = trace_df[(trace_df["criterion"] == criterion) & (trace_df["agent"] == agent)]
        return float(sub[col].iloc[0]) if not sub.empty else 0.0

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.patch.set_facecolor("#FAFAFA")
    axes = axes.flatten()

    x = np.arange(3)
    width = 0.55
    labels = list(AGENTS)
    bar_colors = [COLORS[a] for a in AGENTS]

    # Panel 1: F2 minimo (menor = mejor)
    ax = axes[0]
    vals = [canonical["agents"][a]["f2_min_kg_per_year"] / 1e6 for a in AGENTS]
    bars = ax.bar(x, vals, width, color=bar_colors, alpha=0.82, edgecolor="white", linewidth=2)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=11, fontweight="bold")
    ax.set_ylabel("Mt CO₂/año", fontsize=10)
    ax.set_title("CO₂ indirecto residual mínimo (F2)\n↓ menor = mejor control ambiental",
                 fontsize=11, fontweight="bold")
    ax.grid(axis="y", alpha=0.25, linestyle="--")
    bars[0].set_edgecolor("#14532D")
    bars[0].set_linewidth(3)
    for bar, val in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2., bar.get_height() + 0.002,
                f"{val:.4f}", ha="center", va="bottom", fontsize=9.5, fontweight="bold")
    ax.text(0, vals[0] - 0.004, "★ PPO", ha="center", fontsize=9, color="#14532D", fontweight="bold")
    y_min = min(vals) * 0.994
    ax.set_ylim(y_min, max(vals) * 1.008)

    # Panel 2: CO2 total evitado máximo desde trace (mayor = mejor)
    ax = axes[1]
    vals2 = [best_trace("max_total_avoided", a, "co2_total_avoided_kg") / 1e6 for a in AGENTS]
    bars2 = ax.bar(x, vals2, width, color=bar_colors, alpha=0.82, edgecolor="white", linewidth=2)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=11, fontweight="bold")
    ax.set_ylabel("Mt CO₂ evitados/año", fontsize=10)
    ax.set_title("CO₂ total evitado máximo (directo+indirecto)\n↑ mayor = mejor sustitución",
                 fontsize=11, fontweight="bold")
    ax.grid(axis="y", alpha=0.25, linestyle="--")
    bars2[1].set_edgecolor("#14532D")
    bars2[1].set_linewidth(3)
    for bar, val in zip(bars2, vals2):
        ax.text(bar.get_x() + bar.get_width() / 2., bar.get_height() + 0.0002,
                f"{val:.4f}", ha="center", va="bottom", fontsize=9.5, fontweight="bold")
    ax.text(1, vals2[1] + 0.004, "★ A2C", ha="center", fontsize=9, color="#14532D", fontweight="bold")
    y_min2 = min(vals2) * 0.997
    ax.set_ylim(y_min2, max(vals2) * 1.012)

    # Panel 3: CO2 directo evitado máximo (mayor = mejor)
    ax = axes[2]
    vals3 = [best_trace("max_direct_avoided", a, "co2_direct_avoided_kg") / 1e3 for a in AGENTS]
    bars3 = ax.bar(x, vals3, width, color=bar_colors, alpha=0.82, edgecolor="white", linewidth=2)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=11, fontweight="bold")
    ax.set_ylabel("t CO₂ evitados/año", fontsize=10)
    ax.set_title("CO₂ directo evitado máximo (ICE→EV)\n↑ mayor = más motos/mototaxis electrificados",
                 fontsize=11, fontweight="bold")
    ax.grid(axis="y", alpha=0.25, linestyle="--")
    bars3[0].set_edgecolor("#14532D")
    bars3[0].set_linewidth(3)
    for bar, val in zip(bars3, vals3):
        ax.text(bar.get_x() + bar.get_width() / 2., bar.get_height() + 0.3,
                f"{val:.1f}", ha="center", va="bottom", fontsize=9.5, fontweight="bold")
    ax.text(0, vals3[0] + 2, "★ PPO", ha="center", fontsize=9, color="#14532D", fontweight="bold")

    # Panel 4: Grid import validación (menor = mejor)
    ax = axes[3]
    vals4 = [canonical["agents"][a]["validation_mean_grid_import_kwh"] / 1e6 for a in AGENTS]
    bars4 = ax.bar(x, vals4, width, color=bar_colors, alpha=0.82, edgecolor="white", linewidth=2)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=11, fontweight="bold")
    ax.set_ylabel("M kWh/año", fontsize=10)
    ax.set_title("Grid import validación\n↓ menor = menor dependencia red diesel",
                 fontsize=11, fontweight="bold")
    ax.grid(axis="y", alpha=0.25, linestyle="--")
    bars4[1].set_edgecolor("#14532D")
    bars4[1].set_linewidth(3)
    for bar, val in zip(bars4, vals4):
        ax.text(bar.get_x() + bar.get_width() / 2., bar.get_height() + 0.005,
                f"{val:.3f}", ha="center", va="bottom", fontsize=9.5, fontweight="bold")
    ax.text(1, vals4[1] - 0.015, "★ A2C", ha="center", fontsize=9, color="#14532D", fontweight="bold")
    y_min4 = min(vals4) * 0.996
    ax.set_ylim(y_min4, max(vals4) * 1.006)

    legend_patches = [mpatches.Patch(color=COLORS[a], label=a, alpha=0.82) for a in AGENTS]
    fig.legend(handles=legend_patches, loc="lower center", ncol=3, fontsize=10,
               bbox_to_anchor=(0.5, -0.02), framealpha=0.9)

    fig.suptitle(
        "Comparativa multicriterio OE3 — SAC vs PPO vs A2C | Iquitos 2024\n"
        "★ indica el mejor agente por criterio (borde verde)",
        fontsize=13, fontweight="bold", y=1.01,
    )
    plt.tight_layout()
    _save(fig, "co2_comparativa_multicriterio.png")


# ─── figura 6: diagnóstico SAC convergencia estable inferior ────────────────

def fig_sac_diagnostico() -> None:
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    fig.patch.set_facecolor("#FAFAFA")

    canonical = load_canonical()

    # Subplot 1: Reward rolling mean con plateau SAC
    ax = axes[0]
    for agent in AGENTS:
        df = load_convergencia(agent)
        eps = df["episodio"].values
        roll = df["rolling_mean"].values
        cv = df["rolling_cv_pct"].values
        ax.plot(eps, roll, color=COLORS[agent], linewidth=2.5,
                linestyle=LS[agent], label=f"{agent}")

    ax.axhspan(1440, 1520, alpha=0.12, color=COLORS["SAC"],
               label="SAC plateau ≈1,480 (opt. local)")
    ax.axhline(1677, color=COLORS["PPO"], linestyle=":", linewidth=1.5, alpha=0.7,
               label="PPO plateau ≈1,677")
    ax.axvline(20, color="gray", linestyle=":", linewidth=1.5, alpha=0.6, label="ep20 (SAC congela)")
    ax.set_xlabel("Episodio", fontsize=10)
    ax.set_ylabel("Reward rolling mean", fontsize=10)
    ax.set_title("SAC estabiliza ep≈20\nPPO/A2C siguen mejorando", fontsize=11, fontweight="bold")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.25, linestyle="--")
    ax.set_xlim(1, 50)

    # Subplot 2: CV plateau (variabilidad)
    ax = axes[1]
    for agent in AGENTS:
        df = load_convergencia(agent)
        eps = df["episodio"].values
        cv = df["rolling_cv_pct"].values
        ax.plot(eps, cv, color=COLORS[agent], linewidth=2.2,
                linestyle=LS[agent], label=f"{agent} CV plateau={canonical['agents'][agent]['cv_plateau_pct']:.3f}%")

    ax.axhline(1.0, color="gray", linestyle=":", linewidth=1.5, alpha=0.6,
               label="Umbral plateau 1%")
    ax.set_xlabel("Episodio", fontsize=10)
    ax.set_ylabel("CV rolling 10ep (%)", fontsize=10)
    ax.set_title("Coeficiente de variación\nCV→0: convergencia estable",
                 fontsize=11, fontweight="bold")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.25, linestyle="--")
    ax.set_xlim(1, 50)
    ax.set_ylim(0, None)

    # Subplot 3: Grid import (causa directa del CO2 de SAC)
    ax = axes[2]
    for agent in AGENTS:
        df = load_episodios(agent)
        eps = df["episodio"].values
        grid = df["grid_import_kwh"].values / 1e6
        ax.plot(eps, grid, color=COLORS[agent], linewidth=2.2,
                linestyle=LS[agent], label=f"{agent}")

    ax.set_xlabel("Episodio", fontsize=10)
    ax.set_ylabel("Grid import (M kWh/año)", fontsize=10)
    ax.set_title("SAC importa más de la red diesel\n→ causa directa del mayor CO₂",
                 fontsize=11, fontweight="bold")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.25, linestyle="--")
    ax.set_xlim(1, 50)

    fig.suptitle(
        "Diagnóstico SAC mejorado — convergencia estable a óptimo local inferior\n"
        f"SAC F2={canonical['agents']['SAC']['f2_min_kg_per_year']/1e6:.4f} Mt | "
        f"PPO F2={canonical['agents']['PPO']['f2_min_kg_per_year']/1e6:.4f} Mt | "
        f"Diferencia: {(canonical['agents']['SAC']['f2_min_kg_per_year']-canonical['agents']['PPO']['f2_min_kg_per_year'])/1e3:.1f} kt CO₂/año",
        fontsize=12, fontweight="bold",
    )
    fig.text(
        0.5, -0.04,
        "SAC estabiliza ~ep20 con ent_coef que decrece rápido → menos exploración → óptimo local inferior."
        " PPO y A2C (on-policy) continúan mejorando hasta ep49-50.",
        ha="center", fontsize=9, color="#4B5563",
    )
    plt.tight_layout()
    _save(fig, "sac_convergencia_estable_inferior.png")


# ─── main ────────────────────────────────────────────────────────────────────

def main() -> None:
    print("\n" + "=" * 70)
    print("COMPARATIVA AGENTES CO2 TRACE — SAC vs PPO vs A2C")
    print("Fuente: trace CSVs + convergencia + canonical JSON")
    print("=" * 70 + "\n")

    canonical = load_canonical()
    print(f"  Agente seleccionado: {canonical['metadata']['selected_agent']}")
    print(f"  PPO F2 mínimo: {canonical['agents']['PPO']['f2_min_kg_per_year']:,.0f} kg CO2/año (ep49)")
    print(f"  A2C F2 mínimo: {canonical['agents']['A2C']['f2_min_kg_per_year']:,.0f} kg CO2/año (ep45)")
    print(f"  SAC F2 mínimo: {canonical['agents']['SAC']['f2_min_kg_per_year']:,.0f} kg CO2/año (ep33)")
    print()

    print("[1] Convergencia reward...")
    fig_convergencia_reward()

    print("[2] CO2 indirecto residual F2 por episodio...")
    fig_co2_indirecto_residual()

    print("[3] CO2 total evitado por episodio...")
    fig_co2_evitado_total()

    print("[4] Grid import por episodio...")
    fig_grid_import()

    print("[5] Comparativa multicriterio (4 paneles)...")
    fig_comparativa_multicriterio()

    print("[6] Diagnóstico SAC convergencia estable inferior...")
    fig_sac_diagnostico()

    print("\n" + "=" * 70)
    print("FIGURAS GENERADAS:")
    names = [
        "co2_convergencia_reward.png",
        "co2_indirecto_residual.png",
        "co2_evitado_total_trace.png",
        "grid_import_episodios.png",
        "co2_comparativa_multicriterio.png",
        "sac_convergencia_estable_inferior.png",
    ]
    for name in names:
        path = OUT_DIR / name
        status = "OK" if path.exists() else "ERROR"
        print(f"  [{status}] outputs/docx/graficas/{name}")
    print("=" * 70)


if __name__ == "__main__":
    main()
