#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
costos_estabilidad_oe3.py — Costos tarifarios y estabilidad de red OE3

Reporta los componentes W_COST (0.02) y W_GRID_STABLE (0.02) de la funcion
multiobjetivo CO2_DUAL_FOCUS v8.1, que estan en los pesos pero no en reportes
anteriores. Calcula por episodio y agente:

  Costos (W_COST):
    - costo_total_soles     : grid_import x tarifa OSINERGMIN (S./año)
    - costo_hp_soles        : solo horas punta HP 18-23h (0.45 S./kWh)
    - costo_hfp_soles       : horas fuera de punta (0.28 S./kWh)
    - r_cost_mean           : componente reward normalizado [-1, 0]

  Estabilidad de red (W_GRID_STABLE):
    - r_grid_stable_mean    : componente reward (ya en timeseries)
    - grid_ramp_mean_kwh    : rampa media |delta grid_import| (kWh/h)
    - grid_ramp_std_kwh     : desv. est. de rampas
    - grid_cv               : CV del grid_import por episodio
    - grid_peak_kwh         : pico maximo de importacion

  Exportacion solar (r_solar / f6d):
    - solar_export_kwh      : excedente solar exportado a red Iquitos
    - solar_export_co2_kg   : CO2 desplazado en red por exportacion

Fuentes:
  outputs/{agent}_training/timeseries_{agent}.csv  (per-step, 19 cols)
  outputs/{agent}_training/{agent}_episodios_history.csv  (per-episode)
  data/iquitos_ev_mall/tariffs_osinergmin.csv
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

AGENTS = ["A2C", "PPO", "SAC"]
CO2_FACTOR           = 0.4521   # kg CO2/kWh red aislada Iquitos
MAX_GRID_IMPORT_KW   = 1500.0   # normaliz. grid_stable (W_GRID_STABLE)
TARIFA_HP_SOLES      = 0.45     # S./kWh hora punta
TARIFA_HFP_SOLES     = 0.28     # S./kWh fuera punta
MAX_COST_SOLES_H     = MAX_GRID_IMPORT_KW * TARIFA_HP_SOLES  # 675 S./h

TARIFFS_PATH = ROOT / "data" / "iquitos_ev_mall" / "tariffs_osinergmin.csv"
OUT_DIR      = ROOT / "outputs" / "estadistica_oe3"
GRAFICAS_DIR = ROOT / "outputs" / "docx" / "graficas"
REPORTS_DIR  = ROOT / "reports" / "oe3"

COLORS = {"A2C": "#2196F3", "PPO": "#FF9800", "SAC": "#4CAF50"}


# ─────────────────────────────────────────────────────────────────────────────

def load_tariffs() -> pd.DataFrame:
    """Carga tarifas OSINERGMIN (8760 filas)."""
    if not TARIFFS_PATH.exists():
        # fallback: construir desde horario HP/HFP
        hours = np.arange(8760)
        hour_of_day = hours % 24
        is_peak = ((hour_of_day >= 18) & (hour_of_day < 23)).astype(int)
        tarifa = np.where(is_peak, TARIFA_HP_SOLES, TARIFA_HFP_SOLES)
        return pd.DataFrame({"tarifa_total_soles_kwh": tarifa, "is_peak_hour": is_peak})
    df = pd.read_csv(TARIFFS_PATH)
    cols = ["tarifa_total_soles_kwh", "is_peak_hour"]
    df = df[cols].copy().reset_index(drop=True)
    if len(df) < 8760:
        df = pd.concat([df] * 10).iloc[:8760].reset_index(drop=True)
    return df.iloc[:8760]


def load_timeseries(agent: str) -> pd.DataFrame | None:
    p = ROOT / "outputs" / f"{agent.lower()}_training" / f"timeseries_{agent.lower()}.csv"
    if not p.exists():
        return None
    try:
        return pd.read_csv(p)
    except Exception:
        return None


def load_episodios(agent: str) -> pd.DataFrame | None:
    p = ROOT / "outputs" / f"{agent.lower()}_training" / f"{agent.lower()}_episodios_history.csv"
    if not p.exists():
        return None
    try:
        return pd.read_csv(p)
    except Exception:
        return None


STEPS_PER_EP = 8760  # un año = 8760 horas


def compute_episode_metrics(ts: pd.DataFrame, tariffs: pd.DataFrame) -> pd.DataFrame:
    """Agrega per-step en per-episodio: costo + estabilidad.

    Los timeseries pueden tener episode=0 para todas las filas (bug de escritura
    en los training scripts). En ese caso se reconstruye el episodio por posicion:
    episode_num = row_index // STEPS_PER_EP + 1.

    r_grid_stable siempre es 0 en el timeseries (el wrapper lo calcula pero los
    training scripts no lo propagan). Se recalcula aqui desde las rampas reales
    de grid_import_kwh usando la misma formula del wrapper.
    """
    tariff_arr  = tariffs["tarifa_total_soles_kwh"].values
    is_peak_arr = tariffs["is_peak_hour"].values

    # Reconstruir episodio si todos son 0 (o un solo valor)
    if ts["episode"].nunique() <= 1:
        ts = ts.copy()
        ts["episode"] = ts.index // STEPS_PER_EP + 1

    records = []
    for ep, grp in ts.groupby("episode"):
        grp = grp.reset_index(drop=True)
        n = len(grp)

        # Indice hora dentro del año para tarifa (0-8759)
        if "hour" in grp.columns:
            hours = grp["hour"].values.astype(int) % 8760
        else:
            hours = np.arange(n) % 8760
        hours = np.clip(hours, 0, 8759)

        tarifa_h  = tariff_arr[hours]
        is_peak_h = is_peak_arr[hours].astype(bool)
        gi        = grp["grid_import_kwh"].values

        # ── Costos ──────────────────────────────────────────────────────────
        costo_h      = gi * tarifa_h
        costo_total  = float(costo_h.sum())
        costo_hp     = float(costo_h[is_peak_h].sum())
        costo_hfp    = float(costo_h[~is_peak_h].sum())
        r_cost_steps = -np.clip(costo_h / MAX_COST_SOLES_H, 0.0, 1.0)
        r_cost_mean  = float(r_cost_steps.mean())

        # ── Estabilidad de red ───────────────────────────────────────────────
        # r_grid_stable almacenado siempre es 0 (bug training scripts).
        # Se recalcula con la misma formula del wrapper:
        #   delta = |grid_import[t] - grid_import[t-1]|
        #   r_grid_stable[t] = -clip(delta / MAX_GRID_IMPORT_KW, 0, 1)
        ramps = np.abs(np.diff(gi)) if len(gi) > 1 else np.array([0.0])
        r_grid_stable_recomputed = -np.clip(ramps / MAX_GRID_IMPORT_KW, 0.0, 1.0)
        r_grid_stable_mean = float(r_grid_stable_recomputed.mean())

        grid_ramp_mean  = float(ramps.mean())
        grid_ramp_std   = float(ramps.std())
        grid_cv         = float(gi.std() / gi.mean()) if gi.mean() > 0 else np.nan
        grid_peak_kwh   = float(gi.max())
        grid_valley_kwh = float(gi.min())
        pvr = grid_peak_kwh / grid_valley_kwh if grid_valley_kwh > 0 else np.nan

        records.append({
            "episodio":            int(ep),
            "costo_total_soles":   costo_total,
            "costo_hp_soles":      costo_hp,
            "costo_hfp_soles":     costo_hfp,
            "r_cost_mean":         r_cost_mean,
            "r_grid_stable_mean":  r_grid_stable_mean,
            "grid_ramp_mean_kwh":  grid_ramp_mean,
            "grid_ramp_std_kwh":   grid_ramp_std,
            "grid_cv":             grid_cv,
            "grid_peak_kwh":       grid_peak_kwh,
            "grid_valley_kwh":     grid_valley_kwh,
            "peak_valley_ratio":   pvr,
        })
    return pd.DataFrame(records)


# ─────────────────────────────────────────────────────────────────────────────

def _mannwhitney_row(a1: str, a2: str, x1: pd.Series, x2: pd.Series, label: str) -> str:
    if len(x1) < 2 or len(x2) < 2:
        return f"- {a1} vs {a2} [{label}]: datos insuficientes"
    stat, pval = stats.mannwhitneyu(x1, x2, alternative="two-sided")
    delta = x1.mean() - x2.mean()
    sig = "✓ sig." if pval < 0.05 else "ns"
    return (
        f"- **{a1} vs {a2}**: U={stat:.0f}, p={pval:.3e} {sig} | "
        f"Δ={delta:+,.1f} ({a1} {'menor' if delta < 0 else 'mayor'})"
    )


def build_report(all_metrics: dict[str, pd.DataFrame]) -> str:
    lines = [
        "# Reporte: Costos Tarifarios y Estabilidad de Red — OE3",
        "",
        "**Componentes del reward multiobjetivo CO2_DUAL_FOCUS v8.1:**",
        "| Componente     | Peso | Descripcion |",
        "|----------------|------|-------------|",
        "| W_DIRECT_CO2   | 0.20 | CO2 directa (ICE→EV) |",
        "| W_INDIRECT_CO2 | 0.30 | CO2 indirecta (grid import × 0.4521) |",
        "| W_EV_COMPLETE  | 0.35 | Satisfaccion EV (motos + mototaxis) |",
        "| W_BESS_SOLAR   | 0.07 | BESS carga desde solar |",
        "| W_SOLAR        | 0.04 | Autoconsumo PV |",
        "| **W_GRID_STABLE** | **0.02** | **Suavizado rampas grid_import** |",
        "| **W_COST**     | **0.02** | **Costo tarifario OSINERGMIN HP/HFP** |",
        "",
        "Tarifa HP (18-23h): **0.45 S./kWh** | Tarifa HFP: **0.28 S./kWh**",
        "Factor CO₂ red Iquitos: **0.4521 kg CO₂/kWh**",
        "",
        "---",
        "",
        "## 1. Costos Energéticos (S./año)",
        "",
    ]

    agents_ok = [a for a in AGENTS if a in all_metrics]

    def table_row(label: str, col: str, fmt: str) -> str:
        row = f"| {label:<38} |"
        for ag in AGENTS:
            if ag in all_metrics and col in all_metrics[ag].columns:
                v = all_metrics[ag][col].mean()
                row += f" {fmt.format(v):>16} |"
            else:
                row += f" {'N/D':>16} |"
        return row

    hdr = f"| {'Métrica':<38} | {'A2C':>16} | {'PPO':>16} | {'SAC':>16} |"
    sep = f"|{'-'*40}|{'-'*18}|{'-'*18}|{'-'*18}|"
    lines += [hdr, sep,
        table_row("Costo total medio (S./año)",         "costo_total_soles",  "{:,.0f}"),
        table_row("Costo HP medio 18-23h (S./año)",     "costo_hp_soles",     "{:,.0f}"),
        table_row("Costo HFP medio (S./año)",           "costo_hfp_soles",    "{:,.0f}"),
        table_row("% costo en HP",                      "costo_hp_soles",     "{:.1%}"),
        table_row("r_cost medio (reward normalizado)",  "r_cost_mean",        "{:.4f}"),
        "",
    ]

    lines += [
        "## 2. Estabilidad de Red (W_GRID_STABLE)",
        "",
        hdr, sep,
        table_row("r_grid_stable medio (reward)",        "r_grid_stable_mean",  "{:.4f}"),
        table_row("Rampa media |Δgrid_import| (kWh/h)", "grid_ramp_mean_kwh",  "{:.2f}"),
        table_row("Rampa std |Δgrid_import| (kWh/h)",   "grid_ramp_std_kwh",   "{:.2f}"),
        table_row("CV grid_import por episodio",         "grid_cv",             "{:.4f}"),
        table_row("Grid peak maximo (kWh/h)",            "grid_peak_kwh",       "{:.1f}"),
        table_row("Ratio pico/valle",                    "peak_valley_ratio",   "{:.3f}"),
        "",
    ]

    lines += [
        "## 3. Exportación Solar a Red Iquitos (F6d)",
        "",
        "| Agente | Export solar medio (kWh/año) | CO₂ desplazado (kg/año) | % generacion solar |",
        "|--------|------------------------------|------------------------|--------------------|",
    ]
    for ag in AGENTS:
        if ag not in all_metrics:
            continue
        m = all_metrics[ag]
        if "solar_export_kwh" in m.columns:
            exp_kwh = m["solar_export_kwh"].mean()
            exp_co2 = exp_kwh * CO2_FACTOR
            pct = exp_kwh / 5_819_332 * 100
            lines.append(f"| {ag} | {exp_kwh:>28,.0f} | {exp_co2:>22,.0f} | {pct:>18.1f}% |")

    lines += [
        "",
        "## 4. Pruebas estadísticas — Costo total (S./año)",
        "",
    ]
    for i, a1 in enumerate(agents_ok):
        for a2 in agents_ok[i+1:]:
            x1 = all_metrics[a1]["costo_total_soles"].dropna()
            x2 = all_metrics[a2]["costo_total_soles"].dropna()
            lines.append(_mannwhitney_row(a1, a2, x1, x2, "costo"))

    lines += [
        "",
        "## 5. Pruebas estadísticas — Estabilidad (r_grid_stable)",
        "",
    ]
    for i, a1 in enumerate(agents_ok):
        for a2 in agents_ok[i+1:]:
            x1 = all_metrics[a1]["r_grid_stable_mean"].dropna()
            x2 = all_metrics[a2]["r_grid_stable_mean"].dropna()
            if len(x1) >= 2 and len(x2) >= 2:
                lines.append(_mannwhitney_row(a1, a2, x1, x2, "r_grid_stable"))

    lines += [
        "",
        "## 6. Interpretación multiobjetivo",
        "",
        "Los pesos W_COST=0.02 y W_GRID_STABLE=0.02 actúan como restricciones blandas:",
        "",
        "- **W_COST (0.02):** Penaliza consumo de red en HP (18-23h) → desplazamiento de carga "
        "a HFP. El agente aprende a cargar BESS y EV fuera de horas punta para reducir costo.",
        "- **W_GRID_STABLE (0.02):** Penaliza rampas bruscas en grid_import → suaviza la curva "
        "de demanda a la red diesel aislada de Iquitos, reduciendo estrés en generadores.",
        "- La exportacion solar (F6d) desplaza generacion diesel en la red Iquitos para "
        "otros consumidores, multiplicando el impacto ambiental del proyecto.",
        "- Aunque con pesos menores que CO₂ (0.50) y EV (0.35), estos componentes "
        "son necesarios para la viabilidad operativa del sistema.",
    ]

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────

def make_cost_figure(all_metrics: dict) -> Path:
    agents_ok = [a for a in AGENTS if a in all_metrics and "costo_total_soles" in all_metrics[a].columns]
    fig, axes = plt.subplots(1, 3, figsize=(16, 6))
    fig.suptitle(
        "Costos Tarifarios OSINERGMIN por Agente RL — OE3\n"
        "(50 episodios/agente | HP=0.45 S./kWh 18-23h | HFP=0.28 S./kWh)",
        fontsize=12, fontweight="bold"
    )

    # Boxplot costo total
    ax = axes[0]
    data = [all_metrics[a]["costo_total_soles"].values / 1e6 for a in agents_ok]
    bp = ax.boxplot(data, labels=agents_ok, patch_artist=True,
                    medianprops=dict(color="black", linewidth=2))
    for patch, ag in zip(bp["boxes"], agents_ok):
        patch.set_facecolor(COLORS[ag]); patch.set_alpha(0.75)
    for i, ag in enumerate(agents_ok):
        mu = all_metrics[ag]["costo_total_soles"].mean() / 1e6
        ax.text(i + 1, mu + 0.002, f"μ={mu:.3f}", ha="center", fontsize=9, fontweight="bold")
    ax.set_title("Costo total energético\n(M S./año)", fontsize=10)
    ax.set_ylabel("Millones S./año")
    ax.grid(True, alpha=0.3)

    # Barras HP vs HFP
    ax2 = axes[1]
    x = np.arange(len(agents_ok))
    hp_v  = [all_metrics[a]["costo_hp_soles"].mean()  / 1e6 for a in agents_ok]
    hfp_v = [all_metrics[a]["costo_hfp_soles"].mean() / 1e6 for a in agents_ok]
    ax2.bar(x - 0.2, hp_v,  0.35, label="HP 18-23h", color="#E53935", alpha=0.82, edgecolor="white", linewidth=1.5)
    ax2.bar(x + 0.2, hfp_v, 0.35, label="HFP",       color="#1E88E5", alpha=0.82, edgecolor="white", linewidth=1.5)
    ax2.set_xticks(x); ax2.set_xticklabels(agents_ok)
    ax2.set_title("HP vs HFP (M S./año)\nDesplazamiento de carga", fontsize=10)
    ax2.set_ylabel("Millones S./año")
    ax2.legend(fontsize=9); ax2.grid(True, alpha=0.3, axis="y")

    # r_cost componente
    ax3 = axes[2]
    data3 = [all_metrics[a]["r_cost_mean"].values for a in agents_ok]
    bp3 = ax3.boxplot(data3, labels=agents_ok, patch_artist=True,
                      medianprops=dict(color="black", linewidth=2))
    for patch, ag in zip(bp3["boxes"], agents_ok):
        patch.set_facecolor(COLORS[ag]); patch.set_alpha(0.75)
    ax3.axhline(0, color="gray", linestyle="--", alpha=0.5)
    ax3.set_title("Componente r_cost\n(0=sin costo, −1=costo máx.)", fontsize=10)
    ax3.set_ylabel("r_cost (normalizado)")
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    out = GRAFICAS_DIR / "costos_tarifarios_oe3.png"
    GRAFICAS_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return out


def make_stability_figure(all_metrics: dict) -> Path:
    agents_ok = [a for a in AGENTS if a in all_metrics and "r_grid_stable_mean" in all_metrics[a].columns]
    fig, axes = plt.subplots(1, 3, figsize=(16, 6))
    fig.suptitle(
        "Estabilidad de Red — Componente W_GRID_STABLE OE3\n"
        "(Penaliza rampas bruscas de importacion | red aislada diesel Iquitos)",
        fontsize=12, fontweight="bold"
    )

    # Boxplot r_grid_stable
    ax = axes[0]
    data = [all_metrics[a]["r_grid_stable_mean"].dropna().values for a in agents_ok]
    bp = ax.boxplot(data, labels=agents_ok, patch_artist=True,
                    medianprops=dict(color="black", linewidth=2))
    for patch, ag in zip(bp["boxes"], agents_ok):
        patch.set_facecolor(COLORS[ag]); patch.set_alpha(0.75)
    ax.axhline(0, color="gray", linestyle="--", alpha=0.5, label="Máx. estable")
    ax.set_title("r_grid_stable medio\n(0=estable, −1=máx. rampa)", fontsize=10)
    ax.set_ylabel("r_grid_stable")
    ax.grid(True, alpha=0.3); ax.legend(fontsize=8)

    # Rampa media
    ax2 = axes[1]
    x = np.arange(len(agents_ok))
    ramp_v = [all_metrics[a]["grid_ramp_mean_kwh"].mean() for a in agents_ok]
    bars = ax2.bar(x, ramp_v, color=[COLORS[a] for a in agents_ok], alpha=0.82,
                   edgecolor="white", linewidth=1.5)
    for bar, v in zip(bars, ramp_v):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                 f"{v:.1f}", ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax2.set_xticks(x); ax2.set_xticklabels(agents_ok)
    ax2.set_title("Rampa media |Δgrid_import|\n(kWh/h) — menor = más estable", fontsize=10)
    ax2.set_ylabel("kWh/h"); ax2.grid(True, alpha=0.3, axis="y")

    # CV grid_import
    ax3 = axes[2]
    data3 = [all_metrics[a]["grid_cv"].dropna().values for a in agents_ok]
    bp3 = ax3.boxplot(data3, labels=agents_ok, patch_artist=True,
                      medianprops=dict(color="black", linewidth=2))
    for patch, ag in zip(bp3["boxes"], agents_ok):
        patch.set_facecolor(COLORS[ag]); patch.set_alpha(0.75)
    ax3.set_title("CV grid_import por episodio\n(Variabilidad dentro del año)", fontsize=10)
    ax3.set_ylabel("Coeficiente de variación")
    ax3.grid(True, alpha=0.3)

    plt.tight_layout()
    out = GRAFICAS_DIR / "estabilidad_red_oe3.png"
    GRAFICAS_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return out


# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("\n" + "=" * 70)
    print("COSTOS TARIFARIOS Y ESTABILIDAD DE RED — OE3")
    print("W_COST=0.02 | W_GRID_STABLE=0.02 | CO2_DUAL_FOCUS v8.1")
    print("=" * 70)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    GRAFICAS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    tariffs = load_tariffs()
    print(f"\n  Tarifas cargadas: {len(tariffs)} horas")
    tarif_hp  = float(tariffs[tariffs["is_peak_hour"] == 1]["tarifa_total_soles_kwh"].mean())
    tarif_hfp = float(tariffs[tariffs["is_peak_hour"] == 0]["tarifa_total_soles_kwh"].mean())
    print(f"  HP  (18-23h): {tarif_hp:.4f} S./kWh | HFP: {tarif_hfp:.4f} S./kWh")

    all_metrics: dict[str, pd.DataFrame] = {}

    for agent in AGENTS:
        ts = load_timeseries(agent)
        if ts is None:
            print(f"\n  [{agent}] timeseries no encontrado — omitido")
            continue

        n_ep_raw  = ts["episode"].nunique() if "episode" in ts.columns else 0
        n_ep_real = len(ts) // STEPS_PER_EP if n_ep_raw <= 1 else n_ep_raw
        print(f"\n  [{agent}] {len(ts):,} pasos | ~{n_ep_real} episodios"
              + (" (reconstruidos por posicion)" if n_ep_raw <= 1 else ""))

        metrics = compute_episode_metrics(ts, tariffs)

        # Enriquecer con episodios_history (solar export via f6d)
        ep_hist = load_episodios(agent)
        if ep_hist is not None:
            ep_col = "episodio" if "episodio" in ep_hist.columns else ep_hist.columns[0]
            merge_cols = [c for c in ["co2_f6d_kg", "co2_neta_kg", "grid_import_kwh"]
                          if c in ep_hist.columns]
            if merge_cols:
                ep_hist_sub = ep_hist[[ep_col] + merge_cols].rename(columns={ep_col: "episodio"})
                metrics = metrics.merge(ep_hist_sub, on="episodio", how="left")
                if "co2_f6d_kg" in metrics.columns:
                    metrics["solar_export_kwh"]  = metrics["co2_f6d_kg"] / CO2_FACTOR
                    metrics["solar_export_co2_kg"] = metrics["co2_f6d_kg"]

        all_metrics[agent] = metrics

        out_csv = OUT_DIR / f"costos_estabilidad_{agent.lower()}.csv"
        metrics.to_csv(out_csv, index=False)
        print(f"  → {out_csv.relative_to(ROOT)}")

        # Print summary
        c_tot  = metrics["costo_total_soles"].mean()
        c_hp   = metrics["costo_hp_soles"].mean()
        rgs    = metrics["r_grid_stable_mean"].mean()
        ramp   = metrics["grid_ramp_mean_kwh"].mean()
        pct_hp = c_hp / c_tot * 100 if c_tot > 0 else 0
        print(f"  Costo medio: {c_tot:>10,.0f} S./año  (HP: {pct_hp:.1f}%)")
        print(f"  r_grid_stable medio: {rgs:.4f} | Rampa media: {ramp:.1f} kWh/h")
        if "solar_export_kwh" in metrics.columns:
            exp = metrics["solar_export_kwh"].mean()
            print(f"  Solar export: {exp:,.0f} kWh/año ({exp/5_819_332*100:.1f}% de generacion)")

    if not all_metrics:
        print("\n  ERROR: no hay datos de ningun agente.")
        sys.exit(1)

    # Reporte markdown
    md = build_report(all_metrics)
    md_path = REPORTS_DIR / "COSTOS_ESTABILIDAD_OE3.md"
    md_path.write_text(md, encoding="utf-8")
    print(f"\n  Reporte: {md_path.relative_to(ROOT)}")

    # CSV consolidado para comparacion estadistica
    rows = []
    for ag, df in all_metrics.items():
        df_copy = df.copy()
        df_copy.insert(0, "agente", ag)
        rows.append(df_copy)
    if rows:
        consolidated = pd.concat(rows, ignore_index=True)
        csv_out = OUT_DIR / "costos_estabilidad_consolidado.csv"
        consolidated.to_csv(csv_out, index=False)
        print(f"  CSV consolidado: {csv_out.relative_to(ROOT)}")

    # Figuras
    try:
        p1 = make_cost_figure(all_metrics)
        print(f"  Figura costos: {p1.name}")
    except Exception:
        traceback.print_exc()

    try:
        p2 = make_stability_figure(all_metrics)
        print(f"  Figura estabilidad: {p2.name}")
    except Exception:
        traceback.print_exc()

    print("\n  OK — costos y estabilidad reportados")
    print("=" * 70)


if __name__ == "__main__":
    main()
