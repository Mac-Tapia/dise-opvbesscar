from __future__ import annotations
import json, pandas as pd, numpy as np
from pathlib import Path

ROOT = Path("d:/diseñopvbesscar")
agents = ["sac", "ppo", "a2c"]

F0 = 7_053_691   # kg CO2/año sin solar/BESS/RL
F1 = 5_777_812   # kg CO2/año con solar+BESS, sin RL
SEP = "=" * 70

# Cargar datos
data = {}
for ag in agents:
    j = json.loads((ROOT / f"outputs/{ag}_training/result_{ag}.json").read_text(encoding="utf-8"))
    csv = ROOT / f"outputs/{ag}_training/{ag}_convergencia_episodios.csv"
    r = pd.read_csv(csv)["reward"].values if csv.exists() else np.array([])
    ev = j.get("training_evolution", {})
    data[ag] = {
        "j": j, "r": r, "ev": ev,
        "co2":  np.array(ev.get("hist_co2_neta_kg", [])),
        "red":  np.array(ev.get("hist_reduccion_pct", [])),
        "grid": np.array(ev.get("hist_grid_import_kwh", [])),
        "bess": np.array(ev.get("hist_bess_discharge_kwh", [])),
        "solar_sc": np.array(ev.get("hist_solar_selfcons_kwh", [])),
        "ev_motos": np.array(ev.get("hist_ev_motos_kwh", [])),
        "ev_moto2": np.array(ev.get("hist_ev_mototaxis_kwh", [])),
        "cost":     np.array(ev.get("hist_cost_soles", [])),
    }

print(SEP)
print("  ANALISIS OE3: SELECCION DEL MEJOR AGENTE RL")
print("  Objetivo: minimizar CO2 + cumplir carga EV + usar BESS + reducir costo")
print(SEP)

# ── 1. CO2 TOTAL (promedio de últimos 10 ep — más representativo que solo ep50)
print("\n[1] EMISION CO2 NETA — últimos 10 episodios (kg/año)\n")
co2_scores = []
for ag in agents:
    co2 = data[ag]["co2"]
    if len(co2) >= 10:
        co2_last10 = co2[-10:].mean()
        co2_best   = co2.min()
        ep_best    = int(co2.argmin()) + 1
        red_vs_F0  = (F0 - co2_last10) / F0 * 100
        red_vs_F1  = (F1 - co2_last10) / F1 * 100
        co2_scores.append((ag, co2_last10, co2_best, ep_best, red_vs_F0, red_vs_F1))
        print(f"  {ag.upper():4s}  CO2 media(ep41-50): {co2_last10:>12,.0f} kg/año"
              f"  | -{red_vs_F0:.1f}% vs F0  | -{red_vs_F1:.1f}% vs F1"
              f"  | mejor ep{ep_best}: {co2_best:,.0f}")

co2_scores.sort(key=lambda x: x[1])
print(f"\n  RANKING CO2: {' > '.join(x[0].upper() for x in co2_scores)}")
winner_co2 = co2_scores[0][0]

# ── 2. REWARD (consistencia en convergencia)
print("\n[2] REWARD CONVERGENCIA — últimos 10 episodios\n")
rew_scores = []
for ag in agents:
    r = data[ag]["r"]
    if len(r) >= 10:
        r_late  = r[-10:].mean()
        r_std   = r[-10:].std()
        r_best  = r.max()
        rew_scores.append((ag, r_late, r_std, r_best))
        print(f"  {ag.upper():4s}  reward media(ep41-50): {r_late:>10.2f}"
              f"  std: {r_std:.4f}  best: {r_best:.4f}")

rew_scores.sort(key=lambda x: -x[1])  # mayor reward = mejor
print(f"\n  RANKING REWARD: {' > '.join(x[0].upper() for x in rew_scores)}")

# ── 3. CARGA EV (si disponible)
print("\n[3] CARGA EV — últimos 10 episodios (kWh/año)\n")
ev_scores = []
for ag in agents:
    m = data[ag]["ev_motos"]
    t = data[ag]["ev_moto2"]
    if len(m) >= 10 and len(t) >= 10:
        ev_total = (m[-10:] + t[-10:]).mean()
        ev_scores.append((ag, ev_total))
        print(f"  {ag.upper():4s}  EV carga total: {ev_total:>10,.0f} kWh/año"
              f"  (motos: {m[-10:].mean():,.0f} + mototaxis: {t[-10:].mean():,.0f})")
    else:
        print(f"  {ag.upper():4s}  EV carga: sin datos desagregados")

if ev_scores:
    ev_scores.sort(key=lambda x: -x[1])
    print(f"\n  RANKING EV CARGA: {' > '.join(x[0].upper() for x in ev_scores)}")

# ── 4. USO BESS
print("\n[4] DESCARGA BESS — últimos 10 episodios (kWh/año)\n")
bess_scores = []
for ag in agents:
    b = data[ag]["bess"]
    if len(b) >= 10:
        b_late = b[-10:].mean()
        bess_scores.append((ag, b_late))
        print(f"  {ag.upper():4s}  BESS descarga media: {b_late:>10,.0f} kWh/año")

if bess_scores:
    bess_scores.sort(key=lambda x: -x[1])
    print(f"\n  RANKING BESS USO: {' > '.join(x[0].upper() for x in bess_scores)}")

# ── 5. REDUCCION IMPORTACION RED
print("\n[5] IMPORTACION RED — últimos 10 episodios (kWh/año)\n")
grid_scores = []
for ag in agents:
    g = data[ag]["grid"]
    if len(g) >= 10:
        g_late = g[-10:].mean()
        grid_scores.append((ag, g_late))
        print(f"  {ag.upper():4s}  Grid import media: {g_late:>12,.0f} kWh/año")

if grid_scores:
    grid_scores.sort(key=lambda x: x[1])  # menor = mejor
    print(f"\n  RANKING GRID (menor = mejor): {' > '.join(x[0].upper() for x in grid_scores)}")

# ── 6. COSTO OSINERGMIN
print("\n[6] COSTO TARIFARIO — últimos 10 episodios (S/./año)\n")
cost_scores = []
for ag in agents:
    c = data[ag]["cost"]
    if len(c) >= 10:
        c_late = c[-10:].mean()
        cost_scores.append((ag, c_late))
        print(f"  {ag.upper():4s}  Costo medio: {c_late:>12,.0f} S/./año")
    else:
        print(f"  {ag.upper():4s}  Costo: sin datos")

if cost_scores:
    cost_scores.sort(key=lambda x: x[1])
    print(f"\n  RANKING COSTO (menor = mejor): {' > '.join(x[0].upper() for x in cost_scores)}")

# ── 7. TABLA DE PUNTUACION GLOBAL (criterios ponderados OE3)
print("\n" + SEP)
print("  TABLA DE CRITERIOS OE3 — PUNTUACION PONDERADA")
print(SEP)
print(f"\n  Criterio           Peso    SAC    PPO    A2C")
print("  " + "-" * 55)

# Normalizar rankings a puntos (3=mejor, 1=peor)
def rank_to_pts(ranking_list):
    pts = {}
    for i, (ag, *_) in enumerate(ranking_list):
        pts[ag] = 3 - i
    return pts

criteria = []
if len(co2_scores) == 3:
    pts = rank_to_pts(co2_scores)
    criteria.append(("CO2 reduccion",     0.40, pts))
if len(rew_scores) == 3:
    pts = rank_to_pts(rew_scores)
    criteria.append(("Convergencia",      0.20, pts))
if len(grid_scores) == 3:
    pts = rank_to_pts(grid_scores)
    criteria.append(("Grid import bajo",  0.20, pts))
if len(bess_scores) == 3:
    pts = rank_to_pts(bess_scores)
    criteria.append(("BESS uso",          0.10, pts))
if len(ev_scores) == 3:
    pts = rank_to_pts(ev_scores)
    criteria.append(("EV carga max",      0.10, pts))

total = {"sac": 0.0, "ppo": 0.0, "a2c": 0.0}
for name, w, pts in criteria:
    row = f"  {name:<20s}  {w:.0%}"
    for ag in agents:
        p = pts.get(ag, 0)
        row += f"    {p}"
        total[ag] += w * p
    print(row)

print("  " + "-" * 55)
row = f"  {'PUNTUACION TOTAL':<20s}  100%"
for ag in agents:
    row += f"  {total[ag]:.2f}"
print(row)

# Ganador
best_ag = max(total, key=lambda x: total[x])
print(f"\n  *** AGENTE SELECCIONADO OE3: {best_ag.upper()} ***")
d_best = data[best_ag]
co2_best_mean = d_best["co2"][-10:].mean() if len(d_best["co2"]) >= 10 else 0
red_F0 = (F0 - co2_best_mean) / F0 * 100
red_F1 = (F1 - co2_best_mean) / F1 * 100
print(f"\n  CO2 promedio ultimos 10 ep : {co2_best_mean:,.0f} kg/año")
print(f"  Reduccion vs F0            : {red_F0:.1f}%  (F0 = {F0:,.0f} kg/año)")
print(f"  Reduccion vs F1            : {red_F1:.1f}%  (F1 = {F1:,.0f} kg/año)")
print(f"  Reward convergido          : {d_best['r'][-10:].mean():.4f}  (std={d_best['r'][-10:].std():.4f})")
print(SEP)
