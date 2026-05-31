#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Control operativo BESS/EV/pico OE3 — patrón por hora del día.

Analiza timeseries de los mejores episodios de A2C, PPO y SAC para documentar:
  - Ciclo BESS: cuándo carga (solar) y cuándo descarga (HP, EV noche)
  - Peak shaving: grid import en HP (h18-h22) por agente
  - Carga EV: distribución horaria motos/mototaxis
  - Restricción mall: reducción EV en horario apertura (h09-h21)

Salidas:
  reports/oe3/CONTROL_OPERATIVO_BESS_EV_OE3.md
  outputs/docx/graficas/control_operativo_bess_ev_oe3.png
"""
from __future__ import annotations

import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT_MD = ROOT / "reports" / "oe3" / "CONTROL_OPERATIVO_BESS_EV_OE3.md"
OUT_PNG = ROOT / "outputs" / "docx" / "graficas" / "control_operativo_bess_ev_oe3.png"
OUT_PNG.parent.mkdir(parents=True, exist_ok=True)

BEST_EPS = {"A2C": 19, "PPO": 49, "SAC": 33}   # mejores episodios canónicos
COLORS = {"A2C": "#2CA02C", "PPO": "#E07B39", "SAC": "#1F77B4"}
HP_HOURS = set(range(18, 23))
MALL_HOURS = set(range(9, 22))
SOLAR_HOURS = set(range(6, 19))


def load_ep(agent: str, best_ep: int) -> pd.DataFrame:
    ts = pd.read_csv(ROOT / "outputs" / f"{agent.lower()}_training" / f"timeseries_{agent.lower()}.csv")
    ts["ep_calc"] = np.arange(len(ts)) // 8760 + 1
    ep = ts[ts["ep_calc"] == best_ep].copy()
    ep["hour_of_day"] = ep["hour"] % 24
    return ep


def hourly_profile(ep: pd.DataFrame) -> pd.DataFrame:
    return ep.groupby("hour_of_day").agg(
        soc_mean=("bess_soc", "mean"),
        grid_mean=("grid_import_kwh", "mean"),
        solar_mean=("solar_generation_kwh", "mean"),
        ev_mean=("ev_charging_kwh", "mean"),
        reward_mean=("reward", "mean"),
    ).reset_index()


def run() -> dict[str, pd.DataFrame]:
    profiles: dict[str, pd.DataFrame] = {}
    for agent, ep in BEST_EPS.items():
        print(f"  Cargando {agent} ep{ep}...")
        df_ep = load_ep(agent, ep)
        profiles[agent] = hourly_profile(df_ep)
    return profiles


def save_md(profiles: dict[str, pd.DataFrame]) -> None:
    lines = [
        "# OE3 — Control operativo BESS/EV/pico por hora del día",
        "",
        "**Fecha:** 2026-05-31",
        "**Episodios analizados:** A2C ep19 (mayor CO₂ evitado) | PPO ep49 (menor F2) | SAC ep33 (mejor SAC)",
        "",
        "---",
        "",
    ]
    for agent, ep in BEST_EPS.items():
        prof = profiles[agent]
        lines += [
            f"## {agent} ep{ep}",
            "",
            "| Hora | Mall | HP | SOC medio | Grid (kWh) | Solar (kWh) | EV (kWh) | Patrón |",
            "|---:|:---:|:---:|---:|---:|---:|---:|---|",
        ]
        for _, row in prof.iterrows():
            h = int(row["hour_of_day"])
            mall = "ABIERTO" if h in MALL_HOURS else "—"
            hp = "HP" if h in HP_HOURS else "—"
            solar_icon = "☀" if h in SOLAR_HOURS else " "
            soc = row["soc_mean"]
            grid = row["grid_mean"]
            ev = row["ev_mean"]
            solar = row["solar_mean"]

            if h in HP_HOURS:
                if grid > 1000:
                    pat = "⚠ pico alto"
                else:
                    pat = "✓ pico controlado"
            elif soc > 0.85 and solar > 500:
                pat = "BESS lleno (solar)"
            elif soc < 0.30:
                pat = "BESS bajo"
            elif ev > 50:
                pat = "carga EV intensa"
            elif solar > 1000:
                pat = "solar → BESS"
            else:
                pat = "—"

            lines.append(
                f"| h{h:02d} | {mall} | {hp} | {soc:.2f} | {grid:,.0f} | {solar:,.0f} | {ev:.1f} | {pat} |"
            )
        lines.append("")

    # Resumen comparativo peak shaving
    lines += [
        "---",
        "",
        "## Resumen comparativo — Peak Shaving HP (h18–h22)",
        "",
        "| Hora | A2C grid (kWh) | PPO grid (kWh) | SAC grid (kWh) | A2C SOC | PPO SOC | SAC SOC |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for h in range(18, 23):
        vals = {}
        for agent in ["A2C", "PPO", "SAC"]:
            row = profiles[agent][profiles[agent]["hour_of_day"] == h].iloc[0]
            vals[agent] = row
        lines.append(
            f"| h{h:02d} | {vals['A2C']['grid_mean']:,.0f} | {vals['PPO']['grid_mean']:,.0f} | "
            f"{vals['SAC']['grid_mean']:,.0f} | {vals['A2C']['soc_mean']:.2f} | "
            f"{vals['PPO']['soc_mean']:.2f} | {vals['SAC']['soc_mean']:.2f} |"
        )

    # Promedios HP
    hp_grid = {}
    for agent in ["A2C", "PPO", "SAC"]:
        mask = profiles[agent]["hour_of_day"].isin(HP_HOURS)
        hp_grid[agent] = profiles[agent].loc[mask, "grid_mean"].mean()

    lines += [
        "",
        f"**Grid import promedio HP:**  A2C = {hp_grid['A2C']:,.0f} kWh/h | "
        f"PPO = {hp_grid['PPO']:,.0f} kWh/h | SAC = {hp_grid['SAC']:,.0f} kWh/h",
        "",
        f"A2C reduce el pico HP en **{hp_grid['PPO']-hp_grid['A2C']:,.0f} kWh/h** vs PPO "
        f"({(hp_grid['PPO']-hp_grid['A2C'])/hp_grid['PPO']*100:.0f}% menos).",
        "",
        "---",
        "",
        "## Estrategias aprendidas",
        "",
        "### A2C — 'Carga solar tarde, EV noche, BESS lleno al HP'",
        "- BESS cargado (SOC 0.88–0.97) al entrar a HP por recarga solar vespertina",
        "- EV carga en h00–h06 usando BESS descargado de la noche anterior",
        "- EV pausa en h07–h13 para no competir con demanda apertura mall",
        "- Grid HP: **287–693 kWh/h** — pico absorbido por BESS+solar",
        "",
        "### PPO — 'BESS vacío noche, carga solar mañana, EV en HP'",
        "- BESS depleto de noche (SOC 0.19), se llena con solar en h07–h11",
        "- EV carga concentrada en HP (h18–h21: 82–86 kWh/h)",
        "- Grid HP: **1,909–2,011 kWh/h** — EV+mall crean pico alto",
        "",
        "### SAC — 'BESS temprano, EV mediodía, corte en HP'",
        "- BESS recarga en madrugada, se vacía en mediodía",
        "- EV carga en h10–h13, se detiene desde h16",
        "- Grid HP: **420–456 kWh/h** — bajo solo porque no carga EVs",
        "- No es control óptimo: evasión del pico a costa de no cargar mototaxis",
        "",
        "---",
        "",
        "*Generado: 2026-05-31 | Script: scripts/analysis/control_operativo_bess_ev_oe3.py*",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"  MD: CONTROL_OPERATIVO_BESS_EV_OE3.md")


def save_figure(profiles: dict[str, pd.DataFrame]) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(16, 11))
    fig.patch.set_facecolor("#FAFAFA")

    hours = np.arange(24)
    hp_span = [18, 23]
    mall_span = [9, 22]

    def shade(ax: plt.Axes) -> None:
        ax.axvspan(*hp_span, alpha=0.08, color="red", label="Hora punta (HP)")
        ax.axvspan(*mall_span, alpha=0.04, color="blue", label="Mall abierto")
        ax.set_xticks(range(0, 24, 2))
        ax.grid(True, alpha=0.2, linestyle="--")
        ax.set_xlabel("Hora del día", fontsize=10)

    # ── SOC BESS ──
    ax = axes[0, 0]
    for agent, prof in profiles.items():
        ax.plot(prof["hour_of_day"], prof["soc_mean"],
                color=COLORS[agent], linewidth=2.5, marker="o", markersize=4,
                markevery=3, label=f"{agent} ep{BEST_EPS[agent]}")
    ax.axhline(0.20, color="gray", linestyle=":", linewidth=1.2, alpha=0.7, label="SOC mín (20%)")
    ax.axhline(0.95, color="gray", linestyle="--", linewidth=1.2, alpha=0.5, label="SOC máx útil")
    shade(ax)
    ax.set_ylabel("SOC BESS (fracción)", fontsize=10)
    ax.set_title("Estado de carga BESS por hora\nA2C llega con SOC alto al HP", fontsize=11, fontweight="bold")
    ax.legend(fontsize=8, loc="lower left"); ax.set_ylim(0, 1.05)

    # ── Grid import ──
    ax = axes[0, 1]
    for agent, prof in profiles.items():
        ax.plot(prof["hour_of_day"], prof["grid_mean"] / 1e3,
                color=COLORS[agent], linewidth=2.5, marker="s", markersize=4,
                markevery=3, label=agent)
    shade(ax)
    ax.set_ylabel("Grid import (MWh/h media)", fontsize=10)
    ax.set_title("Importación de red por hora\nA2C tiene pico HP 3× menor que PPO", fontsize=11, fontweight="bold")
    ax.legend(fontsize=8)

    # ── EV charging ──
    ax = axes[1, 0]
    for agent, prof in profiles.items():
        ax.fill_between(prof["hour_of_day"], prof["ev_mean"],
                        color=COLORS[agent], alpha=0.35, label=agent)
        ax.plot(prof["hour_of_day"], prof["ev_mean"],
                color=COLORS[agent], linewidth=2)
    shade(ax)
    ax.set_ylabel("Carga EV media (kWh/h)", fontsize=10)
    ax.set_title("Carga EV por hora\nA2C distribuye: nocturna + vespertina", fontsize=11, fontweight="bold")
    ax.legend(fontsize=8)

    # ── Solar ──
    ax = axes[1, 1]
    solar_ref = profiles["A2C"]["solar_mean"].values
    ax.fill_between(hours, solar_ref, color="#FFD700", alpha=0.4, label="Solar (A2C ref)")
    for agent, prof in profiles.items():
        ax.plot(prof["hour_of_day"], prof["soc_mean"] * 400,
                color=COLORS[agent], linewidth=2, linestyle="--",
                label=f"SOC×400 kW {agent}")
    shade(ax)
    ax.set_ylabel("kWh/h", fontsize=10)
    ax.set_title("Solar vs potencia BESS equivalente\n(SOC×400 kW = reserva disponible)", fontsize=11, fontweight="bold")
    ax.legend(fontsize=8)

    fig.suptitle(
        "OE3 — Control operativo BESS / EV / Peak Shaving por hora del día\n"
        f"A2C ep{BEST_EPS['A2C']} | PPO ep{BEST_EPS['PPO']} | SAC ep{BEST_EPS['SAC']} — Iquitos 2024",
        fontsize=13, fontweight="bold", y=1.01,
    )
    fig.savefig(OUT_PNG, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  PNG: control_operativo_bess_ev_oe3.png")


def main() -> None:
    print("\n" + "=" * 60)
    print("CONTROL OPERATIVO BESS/EV/PICO OE3")
    print("=" * 60 + "\n")
    profiles = run()
    save_md(profiles)
    save_figure(profiles)
    print("\n  Archivos generados:")
    print(f"  - reports/oe3/CONTROL_OPERATIVO_BESS_EV_OE3.md")
    print(f"  - outputs/docx/graficas/control_operativo_bess_ev_oe3.png")


if __name__ == "__main__":
    main()
