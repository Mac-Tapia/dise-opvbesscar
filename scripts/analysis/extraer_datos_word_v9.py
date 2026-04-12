"""
Extracción consolidada de datos para el Word v9 - Tesis OE3 pvbesscar
Datos reales de checkpoints y CSVs generados el 11-12/04/2026
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from scipy import stats

# ── Cargar historiales de episodios ──────────────────────────────────────────
sac = pd.read_csv("outputs/sac_training/sac_episodios_history.csv")
ppo = pd.read_csv("outputs/ppo_training/ppo_episodios_history.csv")
a2c = pd.read_csv("outputs/a2c_training/a2c_episodios_history.csv")

F0 = 7_054_000  # kg CO2/anio sin solar, BESS ni RL
F1 = sac["co2_baseline_kg"].mean()  # con solar+BESS, sin RL (promedio SAC)

# ── Episodio óptimo ───────────────────────────────────────────────────────────
def mejor_episodio(df, nombre):
    idx = df["co2_control_kg"].idxmin()
    r = df.loc[idx]
    return {
        "agente": nombre,
        "episodio": int(r.episodio),
        "F2": int(r.co2_control_kg),
        "directa": int(r.co2_directa_kg),
        "indirecta": int(r.co2_indirecta_kg),
        "neta": int(r.co2_neta_kg),
        "reduccion_pct": round(r.reduccion_pct, 1),
        "solar_kwh": int(r.solar_kwh),
        "bess_kwh": int(r.bess_discharge_kwh),
        "grid_kwh": int(r.grid_import_kwh),
        "ev_motos_kwh": int(r.ev_motos_kwh),
        "ev_taxis_kwh": int(r.ev_mototaxis_kwh),
        "violations": int(r.debt_violations),
        "F2_vs_F0_pct": round((F0 - int(r.co2_control_kg)) / F0 * 100, 1),
        "F2_vs_F1_pct": round((F1 - int(r.co2_control_kg)) / F1 * 100, 1),
    }

sac_best = mejor_episodio(sac, "SAC")
ppo_best = mejor_episodio(ppo, "PPO")
a2c_best = mejor_episodio(a2c, "A2C")

print("=" * 70)
print("EPISODIOS ÓPTIMOS")
print("=" * 70)
for b in [sac_best, ppo_best, a2c_best]:
    print(f"\n{b['agente']} — Episodio {b['episodio']}")
    print(f"  F2 = {b['F2']:,} kg CO2/año")
    print(f"  Reducción vs F0 = {b['F2_vs_F0_pct']}%  |  vs F1 = {b['F2_vs_F1_pct']}%")
    print(f"  CO2 directa = {b['directa']:,} kg  |  indirecta = {b['indirecta']:,} kg  |  neta = {b['neta']:,} kg")
    print(f"  Solar = {b['solar_kwh']:,} kWh  |  BESS = {b['bess_kwh']:,} kWh  |  Grid = {b['grid_kwh']:,} kWh")
    print(f"  EV motos = {b['ev_motos_kwh']:,} kWh  |  EV taxis = {b['ev_taxis_kwh']:,} kWh")
    print(f"  Debt violations = {b['violations']}")

# ── Estadísticas descriptivas 50 eps ─────────────────────────────────────────
print("\n" + "=" * 70)
print("ESTADÍSTICAS DESCRIPTIVAS 50 EPISODIOS (F2 = co2_control_kg)")
print("=" * 70)
for nombre, df in [("SAC", sac), ("PPO", ppo), ("A2C", a2c)]:
    s = df["co2_control_kg"]
    print(f"\n{nombre}: media={s.mean():.0f} | std={s.std():.0f} | min={s.min():.0f} | max={s.max():.0f} | mediana={s.median():.0f} | CV={s.std()/s.mean()*100:.3f}%")

# ── Plateau (últimos 15 eps) ──────────────────────────────────────────────────
print("\n" + "=" * 70)
print("PLATEAU — eps 36 a 50 (convergencia tardía)")
print("=" * 70)
for nombre, df in [("SAC", sac), ("PPO", ppo), ("A2C", a2c)]:
    pl = df[df.episodio >= 36]["co2_control_kg"]
    cv = pl.std() / pl.mean() * 100
    print(f"{nombre}: media={pl.mean():.0f}  std={pl.std():.0f}  CV={cv:.4f}%  n={len(pl)}")

# ── Convergencia ep1→ep50 ─────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("CONVERGENCIA ep1 → ep50")
print("=" * 70)
for nombre, df in [("SAC", sac), ("PPO", ppo), ("A2C", a2c)]:
    ep1 = df[df.episodio == 1]["co2_control_kg"].values[0]
    ep50 = df[df.episodio == 50]["co2_control_kg"].values[0]
    mejora = (ep1 - ep50) / ep1 * 100
    print(f"{nombre}: ep1={ep1:.0f}  ep50={ep50:.0f}  mejora={mejora:.2f}%")

# ── Pruebas estadísticas ──────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("PRUEBAS ESTADÍSTICAS")
print("=" * 70)

# Kruskal-Wallis
H, p_kw = stats.kruskal(sac["co2_control_kg"], ppo["co2_control_kg"], a2c["co2_control_kg"])
print(f"\nKruskal-Wallis: H={H:.4f}  p={p_kw:.4e}  (α=0.001 → {'RECHAZA H0' if p_kw < 0.001 else 'No rechaza'})")

# Wilcoxon (F1 vs cada F2)
for nombre, df in [("SAC", sac), ("PPO", ppo), ("A2C", a2c)]:
    T, p_w = stats.wilcoxon(df["co2_baseline_kg"], df["co2_control_kg"])
    print(f"Wilcoxon F1>F2 {nombre}: T={T:.1f}  p={p_w:.4e}")

# Mann-Whitney pairwise
pairs = [("SAC", sac), ("PPO", ppo), ("A2C", a2c)]
print()
for i, (n1, d1) in enumerate(pairs):
    for j, (n2, d2) in enumerate(pairs):
        if i < j:
            U, p_mw = stats.mannwhitneyu(d1["co2_control_kg"], d2["co2_control_kg"], alternative="less")
            n_total = len(d1) + len(d2)
            r_effect = 1 - (2 * U) / (len(d1) * len(d2))
            print(f"Mann-Whitney {n1}<{n2}: U={U:.0f}  p={p_mw:.4e}  r_effect={r_effect:.4f}")

# Shapiro-Wilk plateau
print("\nShapiro-Wilk (plateau eps 36-50):")
for nombre, df in [("SAC", sac), ("PPO", ppo), ("A2C", a2c)]:
    pl = df[df.episodio >= 36]["co2_control_kg"]
    W, p_sw = stats.shapiro(pl)
    print(f"  {nombre}: W={W:.4f}  p={p_sw:.4f}  ({'NORMAL' if p_sw > 0.05 else 'no normal'})")

# Correlación BESS↔CO2
print("\nCorrelación Pearson r(BESS, CO2):")
for nombre, df in [("SAC", sac), ("PPO", ppo), ("A2C", a2c)]:
    r, p_r = stats.pearsonr(df["bess_discharge_kwh"], df["co2_control_kg"])
    print(f"  {nombre}: r={r:.4f}  p={p_r:.4e}")

# ── Baselines (F0, F1) ────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("BASELINES")
print("=" * 70)
F1_mean = (sac["co2_baseline_kg"].mean() + ppo["co2_baseline_kg"].mean() + a2c["co2_baseline_kg"].mean()) / 3
print(f"F0 (sin solar, BESS, RL) = {F0:,} kg CO2/año")
print(f"F1 (con solar+BESS, sin RL) = {F1_mean:,.0f} kg CO2/año")
print(f"ΔF0→F1 = {F0-F1_mean:,.0f} kg ({(F0-F1_mean)/F0*100:.1f}% reducción por solar+BESS)")

sac_F2 = sac_best["F2"]
print(f"\nF2 SAC (RL óptimo) = {sac_F2:,} kg CO2/año")
print(f"ΔF1→F2 SAC = {F1_mean-sac_F2:,.0f} kg ({(F1_mean-sac_F2)/F1_mean*100:.1f}% aporte exclusivo RL)")
print(f"ΔF0→F2 SAC = {F0-sac_F2:,.0f} kg ({(F0-sac_F2)/F0*100:.1f}% reducción total)")

# ── Checkpoints ──────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("ARQUEOLOGÍA DE CHECKPOINTS (50 eps = 438,000 pasos)")
print("=" * 70)
import os, glob
for agent_dir in ["SAC_CityLearn", "PPO_CityLearn", "A2C_CityLearn"]:
    path = f"checkpoints/{agent_dir}"
    if os.path.exists(path):
        files = glob.glob(f"{path}/*.zip")
        sizes = [os.path.getsize(f) / 1024 for f in files]
        last = max((os.path.getmtime(f) for f in files), default=0)
        import datetime
        dt = datetime.datetime.fromtimestamp(last).strftime("%d/%m/%Y %H:%M")
        print(f"{agent_dir}: {len(files)} checkpoints ZIP  |  último={dt}  |  máx={max(sizes,default=0):.0f} KB")
    else:
        # Buscar variantes
        alts = glob.glob(f"checkpoints/{agent_dir[:3]}*")
        print(f"{agent_dir}: no encontrado  |  alternativas: {alts}")

print("\n✓ Extracción completa.")
