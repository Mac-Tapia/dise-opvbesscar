from __future__ import annotations
"""
Selección del mejor agente OE3 bajo criterio dual:
  50% Consistencia Operativa + 50% Reducción CO2
"""
import json, pandas as pd, numpy as np
from pathlib import Path

ROOT  = Path("d:/diseñopvbesscar")
F0    = 7_053_691   # kg CO2/año — sin solar/BESS/RL
F1    = 5_777_812   # kg CO2/año — con solar+BESS, sin RL
SEP   = "=" * 72
agents = ["sac", "ppo", "a2c"]

# ── carga de datos ────────────────────────────────────────────────────────────
data = {}
for ag in agents:
    j   = json.loads((ROOT / f"outputs/{ag}_training/result_{ag}.json").read_text(encoding="utf-8"))
    rob = json.loads((ROOT / f"outputs/{ag}_training/{ag}_robustez_estocastica.json").read_text(encoding="utf-8"))
    csv = ROOT / f"outputs/{ag}_training/{ag}_convergencia_episodios.csv"
    r   = pd.read_csv(csv)["reward"].values if csv.exists() else np.array([])
    ev  = j.get("training_evolution", {})
    data[ag] = {
        "r": r, "ev": ev, "rob": rob,
        "co2":   np.array(ev.get("hist_co2_neta_kg", [])),
        "red":   np.array(ev.get("hist_reduccion_pct", [])),
        "grid":  np.array(ev.get("hist_grid_import_kwh", [])),
        "bess":  np.array(ev.get("hist_bess_discharge_kwh", [])),
        "motos": np.array(ev.get("hist_ev_motos_kwh", [])),
        "moto2": np.array(ev.get("hist_ev_mototaxis_kwh", [])),
    }

print(SEP)
print("  SELECCION AGENTE OE3: CONSISTENCIA OPERATIVA + REDUCCION CO2")
print(SEP)

# ═══════════════════════════════════════════════════════════════════════════════
# BLOQUE A — REDUCCION CO2  (peso 50%)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "─" * 72)
print("  BLOQUE A — REDUCCION CO2  (50%)")
print("─" * 72)

co2_stats = {}
for ag in agents:
    co2 = data[ag]["co2"]
    n   = len(co2)
    co2_late  = co2[-10:].mean() if n >= 10 else co2.mean()
    co2_best  = co2.min()
    ep_best   = int(co2.argmin()) + 1
    # tendencia lineal (pendiente negativa = mejora sostenida)
    slope = np.polyfit(np.arange(n), co2, 1)[0] if n > 2 else 0.0
    red_F0 = (F0 - co2_late) / F0 * 100
    red_F1 = (F1 - co2_late) / F1 * 100
    # monotonía: cuántos episodios sucesivos mejoran CO2
    diffs = np.diff(co2)
    pct_mejora = (diffs < 0).sum() / len(diffs) * 100 if len(diffs) > 0 else 0
    co2_stats[ag] = {
        "co2_late": co2_late, "co2_best": co2_best, "ep_best": ep_best,
        "slope": slope, "red_F0": red_F0, "red_F1": red_F1,
        "pct_ep_mejoran": pct_mejora,
    }
    print(f"\n  {ag.upper()}")
    print(f"    CO2 media ep41-50     : {co2_late:>12,.0f} kg/año")
    print(f"    CO2 mejor episodio    : {co2_best:>12,.0f} kg/año  (ep{ep_best})")
    print(f"    Reduccion vs F0       : {red_F0:>8.2f}%")
    print(f"    Reduccion vs F1       : {red_F1:>8.2f}%")
    print(f"    Tendencia (slope/ep)  : {slope:>+10,.0f} kg/año por episodio")
    print(f"    % episodios mejoran   : {pct_mejora:>8.1f}%")

# ═══════════════════════════════════════════════════════════════════════════════
# BLOQUE B — CONSISTENCIA OPERATIVA  (peso 50%)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "─" * 72)
print("  BLOQUE B — CONSISTENCIA OPERATIVA  (50%)")
print("─" * 72)
print("  (stability_index, volatilidad final, trend_r2, BESS uso, EV completado)\n")

cons_stats = {}
for ag in agents:
    rob  = data[ag]["rob"]
    r    = data[ag]["r"]
    bess = data[ag]["bess"]
    m    = data[ag]["motos"]
    t    = data[ag]["moto2"]

    stab      = rob.get("stability_index", 0)         # 1 = perfectamente estable
    cv_final  = rob.get("final_cv_pct", 100)          # CV% en últimos 10 ep (menor = mejor)
    trend_r2  = rob.get("trend_r2", 0)                # R² ajuste lineal (mayor = tendencia clara)
    improving = rob.get("trend_improving", False)
    std_late  = rob.get("final_std_reward", 9999)

    bess_late = bess[-10:].mean() if len(bess) >= 10 else 0
    ev_late   = (m[-10:] + t[-10:]).mean() if len(m) >= 10 else 0
    ev_motos  = m[-10:].mean() if len(m) >= 10 else 0
    ev_moto2  = t[-10:].mean() if len(t) >= 10 else 0

    # grid import variance (baja varianza = operacion predecible)
    grid = data[ag]["grid"]
    grid_cv = (grid[-10:].std() / grid[-10:].mean() * 100) if len(grid) >= 10 and grid[-10:].mean() != 0 else 100

    cons_stats[ag] = {
        "stab": stab, "cv_final": cv_final, "std_late": std_late,
        "trend_r2": trend_r2, "improving": improving,
        "bess_late": bess_late, "ev_late": ev_late,
        "ev_motos": ev_motos, "ev_moto2": ev_moto2,
        "grid_cv": grid_cv,
    }
    print(f"  {ag.upper()}")
    print(f"    Stability index       : {stab:.6f}  (1.0 = perfecto)")
    print(f"    CV reward ep41-50     : {cv_final:.4f}%  (menor = más consistente)")
    print(f"    Std reward ep41-50    : {std_late:.4f}")
    print(f"    R² tendencia reward   : {trend_r2:.4f}  (mayor = mejora más lineal)")
    print(f"    Tendencia mejorando   : {'SI' if improving else 'NO'}")
    print(f"    BESS descarga ep41-50 : {bess_late:>10,.0f} kWh/año")
    print(f"    EV carga total ep41-50: {ev_late:>10,.0f} kWh/año")
    print(f"      motos               : {ev_motos:>10,.0f} kWh/año")
    print(f"      mototaxis           : {ev_moto2:>10,.0f} kWh/año")
    print(f"    CV grid import        : {grid_cv:.2f}%  (menor = más predecible)")
    print()

# ═══════════════════════════════════════════════════════════════════════════════
# PUNTUACION PONDERADA (0–10 por sub-criterio, normalizado al rango observado)
# ═══════════════════════════════════════════════════════════════════════════════
def score_minbest(vals: dict, invert=False) -> dict:
    """Normaliza dict{ag:val} a [0,10]. invert=True si menor es mejor."""
    lo, hi = min(vals.values()), max(vals.values())
    if hi == lo:
        return {ag: 10.0 for ag in vals}
    if invert:
        return {ag: (hi - v) / (hi - lo) * 10 for ag, v in vals.items()}
    else:
        return {ag: (v - lo) / (hi - lo) * 10 for ag, v in vals.items()}

# Sub-criterios CO2 (50% total)
co2_late_s  = score_minbest({ag: co2_stats[ag]["co2_late"]   for ag in agents}, invert=True)
co2_best_s  = score_minbest({ag: co2_stats[ag]["co2_best"]   for ag in agents}, invert=True)
slope_s     = score_minbest({ag: co2_stats[ag]["slope"]      for ag in agents}, invert=True)
pct_mej_s   = score_minbest({ag: co2_stats[ag]["pct_ep_mejoran"] for ag in agents})

# Sub-criterios Consistencia (50% total)
stab_s      = score_minbest({ag: cons_stats[ag]["stab"]      for ag in agents})
cv_s        = score_minbest({ag: cons_stats[ag]["cv_final"]  for ag in agents}, invert=True)
r2_s        = score_minbest({ag: cons_stats[ag]["trend_r2"]  for ag in agents})
bess_s      = score_minbest({ag: cons_stats[ag]["bess_late"] for ag in agents})
ev_s        = score_minbest({ag: cons_stats[ag]["ev_late"]   for ag in agents})
gcv_s       = score_minbest({ag: cons_stats[ag]["grid_cv"]   for ag in agents}, invert=True)

# Pesos dentro de cada bloque
W_CO2 = {
    "CO2 media ep41-50 (kg)":     (0.50, co2_late_s),
    "CO2 mejor episodio":         (0.25, co2_best_s),
    "Tendencia decreciente":      (0.15, slope_s),
    "% episodios mejoran CO2":    (0.10, pct_mej_s),
}
W_CONS = {
    "Stability index":            (0.30, stab_s),
    "CV reward final (%)":        (0.25, cv_s),
    "R² tendencia reward":        (0.15, r2_s),
    "BESS uso ep41-50":           (0.15, bess_s),
    "EV carga ep41-50":           (0.10, ev_s),
    "CV grid import":             (0.05, gcv_s),
}

score_co2  = {ag: 0.0 for ag in agents}
score_cons = {ag: 0.0 for ag in agents}

print("\n" + SEP)
print("  PUNTUACION NORMALIZADA (0–10 por sub-criterio)")
print(SEP)

print(f"\n  {'Sub-criterio':<35s} {'Peso':>5s}  {'SAC':>6s}  {'PPO':>6s}  {'A2C':>6s}")
print("  " + "-" * 60)
print("  BLOQUE A — CO2 (peso total 50%)")
for name, (w, sc) in W_CO2.items():
    for ag in agents:
        score_co2[ag] += w * sc[ag]
    print(f"  {name:<35s} {w:>5.0%}  {sc['sac']:>6.2f}  {sc['ppo']:>6.2f}  {sc['a2c']:>6.2f}")

print(f"  {'  SUBTOTAL CO2':<35s} {'':>5s}  {score_co2['sac']:>6.2f}  {score_co2['ppo']:>6.2f}  {score_co2['a2c']:>6.2f}")

print("\n  BLOQUE B — CONSISTENCIA OPERATIVA (peso total 50%)")
for name, (w, sc) in W_CONS.items():
    for ag in agents:
        score_cons[ag] += w * sc[ag]
    print(f"  {name:<35s} {w:>5.0%}  {sc['sac']:>6.2f}  {sc['ppo']:>6.2f}  {sc['a2c']:>6.2f}")

print(f"  {'  SUBTOTAL CONSISTENCIA':<35s} {'':>5s}  {score_cons['sac']:>6.2f}  {score_cons['ppo']:>6.2f}  {score_cons['a2c']:>6.2f}")

# TOTAL: 50% CO2 + 50% Consistencia
total_score = {ag: 0.50 * score_co2[ag] + 0.50 * score_cons[ag] for ag in agents}
print("\n" + SEP)
print(f"  {'PUNTUACION FINAL (50% CO2 + 50% Consistencia)':<50s}")
print("  " + "-" * 60)
print(f"  {'SAC':<10s}: {total_score['sac']:>6.2f}/10")
print(f"  {'PPO':<10s}: {total_score['ppo']:>6.2f}/10")
print(f"  {'A2C':<10s}: {total_score['a2c']:>6.2f}/10")

winner = max(total_score, key=lambda x: total_score[x])
print(SEP)
print(f"\n  >>> AGENTE SELECCIONADO OE3: {winner.upper()} <<<")
cs = co2_stats[winner]
ks = cons_stats[winner]
rob = data[winner]["rob"]
print(f"\n  CO2 media ep41-50       : {cs['co2_late']:>12,.0f} kg/año")
print(f"  Reduccion vs F0         : {cs['red_F0']:>8.2f}%")
print(f"  Reduccion vs F1         : {cs['red_F1']:>8.2f}%")
print(f"  Stability index         : {ks['stab']:.6f}")
print(f"  CV reward final         : {ks['cv_final']:.4f}%")
print(f"  Std reward ep41-50      : {ks['std_late']:.4f}")
print(f"  Tendencia mejorando     : {'SI' if ks['improving'] else 'NO'}")
print(f"  BESS descarga ep41-50   : {ks['bess_late']:>10,.0f} kWh/año")
print(f"  EV carga ep41-50        : {ks['ev_late']:>10,.0f} kWh/año")
print(SEP)
