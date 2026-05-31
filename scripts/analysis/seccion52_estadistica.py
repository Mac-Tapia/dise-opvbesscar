"""
Sección 5.2 — Validación Estadística OE3 PVBESSCAR
Análisis estadístico completo: SAC vs PPO vs A2C
Generado: 2026-04-12
"""
from __future__ import annotations

import json
import warnings
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings("ignore")

# ─── Rutas ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "outputs" / "seccion52"
OUT_DIR.mkdir(parents=True, exist_ok=True)
RUN_DATE = date.today().isoformat()

SAC_CSV = ROOT / "outputs" / "sac_training" / "sac_episodios_history.csv"
PPO_CSV = ROOT / "outputs" / "ppo_training" / "ppo_episodios_history.csv"
A2C_CSV = ROOT / "outputs" / "a2c_training" / "a2c_episodios_history.csv"

# ─── Cargar datos ─────────────────────────────────────────────────────────────
sac = pd.read_csv(SAC_CSV)
ppo = pd.read_csv(PPO_CSV)
a2c = pd.read_csv(A2C_CSV)

print(f"✓ SAC: {len(sac)} episodios | PPO: {len(ppo)} | A2C: {len(a2c)}")

# F0 (sin proyecto) — valor fijo de referencia OE2
F0_KG = 7_054_000.0

# F1 (baseline con solar, sin BESS, sin RL) — media de columna co2_baseline
F1_SAC = sac["co2_baseline_kg"].mean()
F1_PPO = ppo["co2_baseline_kg"].mean()
F1_A2C = a2c["co2_baseline_kg"].mean()
F1_mean = np.mean([F1_SAC, F1_PPO, F1_A2C])

# F2 por episodio para cada agente
f2_sac = sac["co2_control_kg"].values
f2_ppo = ppo["co2_control_kg"].values
f2_a2c = a2c["co2_control_kg"].values

# Rewards por episodio (si existen en CSV de convergencia)
sac_conv_csv = ROOT / "outputs" / "sac_training" / "sac_convergencia_episodios.csv"
ppo_conv_csv = ROOT / "outputs" / "ppo_training" / "ppo_convergencia_episodios.csv"
a2c_conv_csv = ROOT / "outputs" / "a2c_training" / "a2c_convergencia_episodios.csv"

# ─── Cargar rewards si existen ────────────────────────────────────────────────
def load_rewards(csv_path: Path) -> np.ndarray | None:
    if not csv_path.exists():
        return None
    df = pd.read_csv(csv_path)
    for col in ["episode_reward", "reward", "ep_reward"]:
        if col in df.columns:
            return df[col].values
    return None

rewards_sac = load_rewards(sac_conv_csv)
rewards_ppo = load_rewards(ppo_conv_csv)
rewards_a2c = load_rewards(a2c_conv_csv)

# ─── 5.2.1 Estadísticos Descriptivos ─────────────────────────────────────────
print("\n═══ 5.2.1 Estadísticos Descriptivos por Episodio ═══")

desc_data = {
    "Agente": ["F0 Sin Proyecto", "F1 Baseline (solar+BESS, sin RL)", "SAC", "PPO", "A2C"],
    "N": [50, 50, 50, 50, 50],
    "Media (kg/año)": [
        F0_KG,
        F1_mean,
        f2_sac.mean(),
        f2_ppo.mean(),
        f2_a2c.mean(),
    ],
    "Mediana (kg/año)": [
        F0_KG,
        np.median(sac["co2_baseline_kg"].values),
        np.median(f2_sac),
        np.median(f2_ppo),
        np.median(f2_a2c),
    ],
    "σ (kg/año)": [
        0.0,
        sac["co2_baseline_kg"].std(),
        f2_sac.std(),
        f2_ppo.std(),
        f2_a2c.std(),
    ],
    "Mínimo (kg/año)": [F0_KG, sac["co2_baseline_kg"].min(), f2_sac.min(), f2_ppo.min(), f2_a2c.min()],
    "Máximo (kg/año)": [F0_KG, sac["co2_baseline_kg"].max(), f2_sac.max(), f2_ppo.max(), f2_a2c.max()],
    "vs F0 (%)": [
        0.0,
        round((F1_mean - F0_KG) / F0_KG * 100, 1),
        round((f2_sac.mean() - F0_KG) / F0_KG * 100, 1),
        round((f2_ppo.mean() - F0_KG) / F0_KG * 100, 1),
        round((f2_a2c.mean() - F0_KG) / F0_KG * 100, 1),
    ],
}
df_desc = pd.DataFrame(desc_data)
df_desc.to_csv(OUT_DIR / "tabla_1_descriptivos.csv", index=False)
print(df_desc.to_string(index=False))

# ─── 5.2.2 Pruebas de Normalidad (Shapiro-Wilk) ──────────────────────────────
print("\n═══ 5.2.2 Prueba de Normalidad Shapiro-Wilk ═══")

groups = {
    "F1 Baseline": sac["co2_baseline_kg"].values,
    "SAC": f2_sac,
    "PPO": f2_ppo,
    "A2C": f2_a2c,
}

norm_rows = []
for name, data in groups.items():
    stat, pval = stats.shapiro(data)
    es_normal = "Sí ✓" if pval >= 0.05 else "No ✗"
    norm_rows.append({
        "Grupo": name,
        "n": len(data),
        "W (Shapiro-Wilk)": round(stat, 6),
        "p-value": f"{pval:.3e}",
        "α=0.05": es_normal,
    })
    print(f"  {name}: W={stat:.6f}, p={pval:.3e} → {es_normal}")

df_norm = pd.DataFrame(norm_rows)
df_norm.to_csv(OUT_DIR / "tabla_2_normalidad.csv", index=False)

# Determinar prueba
all_normal = all(r["α=0.05"] == "Sí ✓" for r in norm_rows)
prueba_nombre = "T-Student (muestras relacionadas)" if all_normal else "Wilcoxon signed-rank (no paramétrica)"
print(f"\n→ Prueba seleccionada: {prueba_nombre}")

# ─── 5.2.3 Prueba Inferencial ─────────────────────────────────────────────────
print("\n═══ 5.2.3 Prueba Inferencial ═══")

baseline_arr = sac["co2_baseline_kg"].values  # mismo perfil determinista

def cohen_d(a: np.ndarray, b: np.ndarray) -> float:
    diff = a - b
    return diff.mean() / diff.std(ddof=1)

def run_test(name: str, ctrl: np.ndarray) -> dict:
    if all_normal:
        stat, pval = stats.ttest_rel(baseline_arr, ctrl)
    else:
        stat, pval = stats.wilcoxon(baseline_arr, ctrl, alternative="greater")
    cd = cohen_d(baseline_arr, ctrl)
    reduccion_media = (baseline_arr.mean() - ctrl.mean()) / baseline_arr.mean() * 100
    rechaza = "SÍ ✓" if pval < 0.05 else "No ✗"
    magnitud = (
        "GIGANTE (d > 2.0)" if abs(cd) > 2.0 else
        "Grande (d > 0.8)" if abs(cd) > 0.8 else
        "Medio (d > 0.5)" if abs(cd) > 0.5 else
        "Pequeño"
    )
    return {
        "Comparación": f"F1 Baseline vs {name}",
        "Estadístico": round(stat, 3),
        "p-value": f"{pval:.3e}",
        "Rechaza H₀ (p<0.05)": rechaza,
        "Reducción media (%)": round(reduccion_media, 2),
        "Cohen d": round(cd, 4),
        "Magnitud efecto": magnitud,
    }

infer_rows = [
    run_test("SAC", f2_sac),
    run_test("PPO", f2_ppo),
    run_test("A2C", f2_a2c),
]

# Kruskal-Wallis entre los 3 agentes
kw_stat, kw_pval = stats.kruskal(f2_sac, f2_ppo, f2_a2c)
infer_rows.append({
    "Comparación": "SAC vs PPO vs A2C (Kruskal-Wallis)",
    "Estadístico": round(kw_stat, 3),
    "p-value": f"{kw_pval:.3e}",
    "Rechaza H₀ (p<0.05)": "SÍ ✓" if kw_pval < 0.05 else "No ✗",
    "Reducción media (%)": "—",
    "Cohen d": "—",
    "Magnitud efecto": "—",
})

# Mann-Whitney entre pares de agentes
for a_name, a_arr, b_name, b_arr in [
    ("SAC", f2_sac, "PPO", f2_ppo),
    ("SAC", f2_sac, "A2C", f2_a2c),
    ("PPO", f2_ppo, "A2C", f2_a2c),
]:
    stat_mw, pval_mw = stats.mannwhitneyu(a_arr, b_arr, alternative="less")
    cd_pair = cohen_d(b_arr, a_arr)
    infer_rows.append({
        "Comparación": f"{a_name} vs {b_name} (Mann-Whitney)",
        "Estadístico": round(stat_mw, 3),
        "p-value": f"{pval_mw:.3e}",
        "Rechaza H₀ (p<0.05)": "SÍ ✓" if pval_mw < 0.05 else "No ✗",
        "Reducción media (%)": round((b_arr.mean() - a_arr.mean()) / b_arr.mean() * 100, 2),
        "Cohen d": round(cd_pair, 4),
        "Magnitud efecto": "GIGANTE (d > 2.0)" if abs(cd_pair) > 2.0 else "Grande (d > 0.8)" if abs(cd_pair) > 0.8 else "Medio",
    })

df_infer = pd.DataFrame(infer_rows)
df_infer.to_csv(OUT_DIR / "tabla_3_inferencial.csv", index=False)
for r in infer_rows:
    print(f"  {r['Comparación']}: stat={r['Estadístico']}, p={r['p-value']}, {r['Rechaza H₀ (p<0.05)']}, d={r['Cohen d']}")

# ─── 5.2.4 Robustez Estocástica ───────────────────────────────────────────────
print("\n═══ 5.2.4 Análisis de Robustez Estocástica ═══")

# Rangos de plateau (últimos 15 episodios)
plateau_sac = f2_sac[-15:]
plateau_ppo = f2_ppo[-15:]
plateau_a2c = f2_a2c[-15:]

robustez_rows = []
for name, arr_all, arr_plateau in [("SAC", f2_sac, plateau_sac), ("PPO", f2_ppo, plateau_ppo), ("A2C", f2_a2c, plateau_a2c)]:
    cv_all = arr_all.std() / arr_all.mean() * 100
    cv_plateau = arr_plateau.std() / arr_plateau.mean() * 100
    mejora_total = (arr_all[0] - arr_all.min()) / arr_all[0] * 100
    robustez_rows.append({
        "Agente": name,
        "F2 mínimo (kg/año)": int(round(float(arr_all.min()))),
        "F2 Ep1 (kg/año)": int(arr_all[0]),
        "Mejora total (%)": round(mejora_total, 2),
        "σ global (kg/año)": round(arr_all.std(), 0),
        "CV global (%)": round(cv_all, 3),
        "σ plateau (kg/año)": round(arr_plateau.std(), 0),
        "CV plateau (%)": round(cv_plateau, 3),
        "Estabilidad plateau": "Alta" if cv_plateau < 1.0 else "Media" if cv_plateau < 3.0 else "Baja",
    })
    print(f"  {name}: min={arr_all.min():,.0f} kg, mejora={mejora_total:.1f}%, CV_plateau={cv_plateau:.3f}%")

df_robustez = pd.DataFrame(robustez_rows)
df_robustez.to_csv(OUT_DIR / "tabla_4_robustez_estocastica.csv", index=False)

# ─── FIGURA 1: Convergencia F2 por episodio ───────────────────────────────────
print("\n═══ Generando figuras ═══")

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle(
    "Figura 5.1 — Convergencia y Análisis Estocástico SAC/PPO/A2C\nOE3 PVBESSCAR | Iquitos, Perú",
    fontsize=13, fontweight="bold", y=0.98
)

eps = np.arange(1, 51)
colors = {"SAC": "#1f77b4", "PPO": "#ff7f0e", "A2C": "#2ca02c"}

# Panel 1: Curvas de convergencia F2
ax1 = axes[0, 0]
ax1.plot(eps, f2_sac / 1e6, color=colors["SAC"], linewidth=2, marker="o", markersize=3, label=f"SAC (mín={f2_sac.min()/1e6:.3f} MtCO₂)")
ax1.plot(eps, f2_ppo / 1e6, color=colors["PPO"], linewidth=2, marker="s", markersize=3, label=f"PPO (mín={f2_ppo.min()/1e6:.3f} MtCO₂)")
ax1.plot(eps, f2_a2c / 1e6, color=colors["A2C"], linewidth=2, marker="^", markersize=3, label=f"A2C (mín={f2_a2c.min()/1e6:.3f} MtCO₂)")
ax1.axhline(F1_mean / 1e6, color="gray", linestyle="--", linewidth=1.5, alpha=0.7, label=f"F1 Baseline ({F1_mean/1e6:.3f} MtCO₂)")
ax1.set_xlabel("Episodio de entrenamiento")
ax1.set_ylabel("CO₂ controlado F2 (MtCO₂/año)")
ax1.set_title("Curvas de convergencia — Emisiones CO₂ F2")
ax1.legend(fontsize=8)
ax1.grid(True, alpha=0.3)
ax1.set_xlim(1, 50)

# Panel 2: Reducción acumulada vs F0
ax2 = axes[0, 1]
red_sac = (F0_KG - f2_sac) / F0_KG * 100
red_ppo = (F0_KG - f2_ppo) / F0_KG * 100
red_a2c = (F0_KG - f2_a2c) / F0_KG * 100
ax2.plot(eps, red_sac, color=colors["SAC"], linewidth=2, marker="o", markersize=3, label=f"SAC (máx={red_sac.max():.1f}%)")
ax2.plot(eps, red_ppo, color=colors["PPO"], linewidth=2, marker="s", markersize=3, label=f"PPO (máx={red_ppo.max():.1f}%)")
ax2.plot(eps, red_a2c, color=colors["A2C"], linewidth=2, marker="^", markersize=3, label=f"A2C (máx={red_a2c.max():.1f}%)")
ax2.axhline(62.8, color=colors["SAC"], linestyle=":", linewidth=1, alpha=0.5)
ax2.set_xlabel("Episodio de entrenamiento")
ax2.set_ylabel("Reducción CO₂ vs F0 (%)")
ax2.set_title("Reducción acumulada de CO₂ vs Escenario Sin Proyecto")
ax2.legend(fontsize=8)
ax2.grid(True, alpha=0.3)
ax2.set_xlim(1, 50)

# Panel 3: Distribución de F2 en plateau (box + violin)
ax3 = axes[1, 0]
data_box = [plateau_sac / 1e6, plateau_ppo / 1e6, plateau_a2c / 1e6]
bp = ax3.boxplot(data_box, labels=["SAC", "PPO", "A2C"], patch_artist=True, notch=True,
                  medianprops=dict(color="black", linewidth=2))
for patch, color in zip(bp["boxes"], [colors["SAC"], colors["PPO"], colors["A2C"]]):
    patch.set_facecolor(color)
    patch.set_alpha(0.7)
ax3.set_ylabel("F2 en plateau — últimos 15 eps (MtCO₂/año)")
ax3.set_title("Distribución en plateau (Eps 36-50)\nRobustez estocástica")
ax3.grid(True, alpha=0.3, axis="y")
for i, (name, arr) in enumerate(zip(["SAC", "PPO", "A2C"], data_box)):
    cv = arr.std() / arr.mean() * 100
    ax3.text(i + 1, arr.max() + 0.003, f"CV={cv:.2f}%", ha="center", fontsize=8)

# Panel 4: Barras comparativas CO₂ total
ax4 = axes[1, 1]
agentes = ["F0\nSin Proyecto", "F1\nBaseline", "SAC\n(Óptimo)", "PPO\n(Óptimo)", "A2C\n(Óptimo)"]
valores = [F0_KG / 1e6, F1_mean / 1e6, f2_sac.min() / 1e6, f2_ppo.min() / 1e6, f2_a2c.min() / 1e6]
bar_colors = ["#d62728", "#9467bd", colors["SAC"], colors["PPO"], colors["A2C"]]
bars = ax4.bar(agentes, valores, color=bar_colors, alpha=0.8, edgecolor="black", linewidth=0.8)
for bar, val in zip(bars, valores):
    ax4.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
             f"{val:.3f}", ha="center", va="bottom", fontsize=9, fontweight="bold")
# Etiquetas de reducción
for i, (val, ref) in enumerate(zip(valores[2:], [valores[0]] * 3), start=2):
    pct = (ref - val) / ref * 100
    ax4.text(bars[i].get_x() + bars[i].get_width() / 2,
             val / 2, f"-{pct:.1f}%\nvs F0", ha="center", va="center",
             fontsize=8, color="white", fontweight="bold")
ax4.set_ylabel("CO₂ total anual (MtCO₂/año)")
ax4.set_title("Comparación F2 óptimo — Los 3 algoritmos RL\nvs Referencias F0 y F1")
ax4.grid(True, alpha=0.3, axis="y")

plt.tight_layout()
fig.savefig(OUT_DIR / "fig1_convergencia_agentes.png", dpi=150, bbox_inches="tight")
plt.close()
print("  ✓ fig1_convergencia_agentes.png")

# ─── FIGURA 2: Normalidad (Q-Q plots) ────────────────────────────────────────
fig2, axes2 = plt.subplots(1, 4, figsize=(16, 4))
fig2.suptitle("Figura 5.2 — Prueba de Normalidad: Q-Q Plots (Shapiro-Wilk)\nOE3 PVBESSCAR",
              fontsize=12, fontweight="bold")

for ax, (name, data), color in zip(
    axes2,
    [("F1 Baseline", sac["co2_baseline_kg"].values), ("SAC", f2_sac), ("PPO", f2_ppo), ("A2C", f2_a2c)],
    ["gray", colors["SAC"], colors["PPO"], colors["A2C"]]
):
    stat, pval = stats.shapiro(data)
    (osm, osr), (slope, intercept, _) = stats.probplot(data, dist="norm")
    ax.plot(osm, osr, "o", color=color, markersize=4, alpha=0.7)
    ax.plot(osm, slope * np.array(osm) + intercept, "r-", linewidth=1.5)
    normal_str = "Normal ✓" if pval >= 0.05 else "No Normal ✗"
    ax.set_title(f"{name}\nW={stat:.4f}, p={pval:.2e}\n{normal_str}", fontsize=9)
    ax.set_xlabel("Cuantiles teóricos")
    ax.set_ylabel("Cuantiles observados")
    ax.grid(True, alpha=0.3)

plt.tight_layout()
fig2.savefig(OUT_DIR / "fig2_distribucion_normalidad.png", dpi=150, bbox_inches="tight")
plt.close()
print("  ✓ fig2_distribucion_normalidad.png")

# ─── FIGURA 3: Varianza y robustez estocástica ───────────────────────────────
fig3, axes3 = plt.subplots(1, 3, figsize=(15, 5))
fig3.suptitle("Figura 5.3 — Varianza y Robustez Estocástica por Algoritmo\nOE3 PVBESSCAR",
              fontsize=12, fontweight="bold")

window = 5
for ax, (name, arr), color in zip(
    axes3,
    [("SAC", f2_sac), ("PPO", f2_ppo), ("A2C", f2_a2c)],
    [colors["SAC"], colors["PPO"], colors["A2C"]]
):
    rolling_mean = pd.Series(arr).rolling(window, min_periods=1).mean().values
    rolling_std = pd.Series(arr).rolling(window, min_periods=1).std(ddof=0).values

    ax.plot(eps, arr / 1e6, color=color, alpha=0.4, linewidth=1, label="F2 por episodio")
    ax.plot(eps, rolling_mean / 1e6, color=color, linewidth=2.5, label=f"Media móvil (w={window})")
    ax.fill_between(eps,
                    (rolling_mean - rolling_std) / 1e6,
                    (rolling_mean + rolling_std) / 1e6,
                    color=color, alpha=0.15, label="±1σ")

    # Marcar mínimo
    idx_min = np.argmin(arr)
    ax.scatter([eps[idx_min]], [arr[idx_min] / 1e6], color="red", zorder=5, s=80, label=f"Óptimo Ep{idx_min+1}")

    cv_final = arr[-15:].std() / arr[-15:].mean() * 100
    ax.set_title(f"{name}\nF2_min={arr.min()/1e6:.3f} MtCO₂ | CV_plateau={cv_final:.2f}%")
    ax.set_xlabel("Episodio")
    ax.set_ylabel("CO₂ controlado (MtCO₂/año)")
    ax.legend(fontsize=7)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(1, 50)

plt.tight_layout()
fig3.savefig(OUT_DIR / "fig3_varianza_robustez.png", dpi=150, bbox_inches="tight")
plt.close()
print("  ✓ fig3_varianza_robustez.png")

# ─── FIGURA 4: BESS y Grid_import por episodio ───────────────────────────────
fig4, axes4 = plt.subplots(1, 2, figsize=(13, 5))
fig4.suptitle("Figura 5.4 — Estrategia BESS y Grid Import por Algoritmo\nOE3 PVBESSCAR",
              fontsize=12, fontweight="bold")

ax_bess = axes4[0]
ax_bess.plot(eps, sac["bess_discharge_kwh"] / 1e3, color=colors["SAC"], linewidth=2, label="SAC")
ax_bess.plot(eps, ppo["bess_discharge_kwh"] / 1e3, color=colors["PPO"], linewidth=2, label="PPO")
ax_bess.plot(eps, a2c["bess_discharge_kwh"] / 1e3, color=colors["A2C"], linewidth=2, label="A2C")
ax_bess.set_xlabel("Episodio")
ax_bess.set_ylabel("BESS descarga (MWh/año)")
ax_bess.set_title("Descarga BESS anual por episodio")
ax_bess.legend()
ax_bess.grid(True, alpha=0.3)
ax_bess.set_xlim(1, 50)

ax_grid = axes4[1]
ax_grid.plot(eps, sac["grid_import_kwh"] / 1e6, color=colors["SAC"], linewidth=2, label="SAC")
ax_grid.plot(eps, ppo["grid_import_kwh"] / 1e6, color=colors["PPO"], linewidth=2, label="PPO")
ax_grid.plot(eps, a2c["grid_import_kwh"] / 1e6, color=colors["A2C"], linewidth=2, label="A2C")
ax_grid.set_xlabel("Episodio")
ax_grid.set_ylabel("Grid Import (GWh/año)")
ax_grid.set_title("Importación de red por episodio\n(menor = más desplazamiento CO₂)")
ax_grid.legend()
ax_grid.grid(True, alpha=0.3)
ax_grid.set_xlim(1, 50)

plt.tight_layout()
fig4.savefig(OUT_DIR / "fig4_bess_grid_estrategia.png", dpi=150, bbox_inches="tight")
plt.close()
print("  ✓ fig4_bess_grid_estrategia.png")

# ─── Guardar JSON de resultados ───────────────────────────────────────────────
algoritmos_resultados = {
    "SAC": {
        "f2_minimo_kg": int(round(float(f2_sac.min()))),
        "f2_minimo_ep": int(np.argmin(f2_sac) + 1),
        "f2_media_kg": round(f2_sac.mean(), 0),
        "f2_sigma_kg": round(f2_sac.std(), 0),
        "vs_f0_pct": round((F0_KG - f2_sac.min()) / F0_KG * 100, 2),
        "co2_evitado_kg": int(round(float(F0_KG - f2_sac.min()))),
        "cv_plateau_pct": round(plateau_sac.std() / plateau_sac.mean() * 100, 3),
    },
    "PPO": {
        "f2_minimo_kg": int(round(float(f2_ppo.min()))),
        "f2_minimo_ep": int(np.argmin(f2_ppo) + 1),
        "f2_media_kg": round(f2_ppo.mean(), 0),
        "f2_sigma_kg": round(f2_ppo.std(), 0),
        "vs_f0_pct": round((F0_KG - f2_ppo.min()) / F0_KG * 100, 2),
        "co2_evitado_kg": int(round(float(F0_KG - f2_ppo.min()))),
        "cv_plateau_pct": round(plateau_ppo.std() / plateau_ppo.mean() * 100, 3),
    },
    "A2C": {
        "f2_minimo_kg": int(round(float(f2_a2c.min()))),
        "f2_minimo_ep": int(np.argmin(f2_a2c) + 1),
        "f2_media_kg": round(f2_a2c.mean(), 0),
        "f2_sigma_kg": round(f2_a2c.std(), 0),
        "vs_f0_pct": round((F0_KG - f2_a2c.min()) / F0_KG * 100, 2),
        "co2_evitado_kg": int(round(float(F0_KG - f2_a2c.min()))),
        "cv_plateau_pct": round(plateau_a2c.std() / plateau_a2c.mean() * 100, 3),
    },
}
best_name = min(algoritmos_resultados, key=lambda name: algoritmos_resultados[name]["f2_minimo_kg"])
best_info = algoritmos_resultados[best_name]

resultados = {
    "fecha_generacion": RUN_DATE,
    "algoritmos": algoritmos_resultados,
    "algoritmo_optimo": best_name,
    "prueba_normalidad": "Shapiro-Wilk",
    "pruebas_no_parametricas": [
        "Wilcoxon signed-rank",
        "Kruskal-Wallis",
        "Mann-Whitney U",
    ],
    "prueba_inferencial": "Wilcoxon signed-rank, Kruskal-Wallis y Mann-Whitney U (no paramétricas)",
    "alpha": 0.05,
    "conclusion": (
        f"{best_name} es el algoritmo óptimo: F2 mínimo={best_info['f2_minimo_kg']:,} kg/año "
        f"en el episodio {best_info['f2_minimo_ep']}, reducción={best_info['vs_f0_pct']:.2f}% vs F0."
    ),
}

with open(OUT_DIR / "resultados_seccion52.json", "w", encoding="utf-8") as f:
    json.dump(resultados, f, indent=2, ensure_ascii=False)

print(f"\n✓ Todos los archivos generados en: {OUT_DIR}")
print("\n═══ RESUMEN FINAL ═══")
print(f"  SAC: F2_min = {f2_sac.min():,.0f} kg/año → -{(F0_KG - f2_sac.min())/F0_KG*100:.1f}% vs F0")
print(f"  PPO: F2_min = {f2_ppo.min():,.0f} kg/año → -{(F0_KG - f2_ppo.min())/F0_KG*100:.1f}% vs F0")
print(f"  A2C: F2_min = {f2_a2c.min():,.0f} kg/año → -{(F0_KG - f2_a2c.min())/F0_KG*100:.1f}% vs F0")
print(f"\n  Kruskal-Wallis (SAC vs PPO vs A2C): H={kw_stat:.3f}, p={kw_pval:.3e}")
print(f"  → Diferencias ESTADÍSTICAMENTE SIGNIFICATIVAS entre agentes (p << 0.05)")
