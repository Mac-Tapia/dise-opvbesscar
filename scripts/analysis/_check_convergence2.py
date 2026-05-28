from __future__ import annotations
import json, pandas as pd, numpy as np
from pathlib import Path

ROOT = Path("d:/diseñopvbesscar")
agents = ["sac", "ppo", "a2c"]

print("=== VERIFICACION DE APRENDIZAJE Y CONVERGENCIA ===\n")

for ag in agents:
    j = json.loads((ROOT / f"outputs/{ag}_training/result_{ag}.json").read_text(encoding="utf-8"))
    ev = j.get("training_evolution", {})

    csv_path = ROOT / f"outputs/{ag}_training/{ag}_convergencia_episodios.csv"
    r = pd.read_csv(csv_path)["reward"].values if csv_path.exists() else np.array([])

    red  = np.array(ev.get("hist_reduccion_pct", []))
    co2  = np.array(ev.get("hist_co2_neta_kg", []))
    bess = np.array(ev.get("hist_bess_discharge_kwh", []))
    grid = np.array(ev.get("hist_grid_import_kwh", []))

    n_ep = j.get("total_episodes", len(r))

    # Estabilidad: comparar std en primeros 10 vs ultimos 10
    r_std_early = float(r[:10].std()) if len(r) >= 10 else 0.0
    r_std_late  = float(r[-10:].std()) if len(r) >= 10 else 0.0
    estable = "SI (se estabilizo)" if r_std_late < r_std_early else "NO (sigue oscilando)"

    # Mejora global de reward
    r_mean_early = float(r[:10].mean()) if len(r) >= 10 else 0.0
    r_mean_late  = float(r[-10:].mean()) if len(r) >= 10 else 0.0
    mejora_pct   = ((r_mean_late - r_mean_early) / abs(r_mean_early) * 100) if r_mean_early != 0 else 0.0

    # Tendencia BESS y grid
    bess_trend = float(bess[-10:].mean() - bess[:10].mean()) if len(bess) >= 10 else 0.0
    grid_trend = float(grid[-10:].mean() - grid[:10].mean()) if len(grid) >= 10 else 0.0

    print(f"--- {ag.upper()} ---")
    ok = "[OK]" if n_ep == 50 else "[!!]"
    print(f"  {ok} Episodios completados   : {n_ep} / 50")
    if len(r) > 0:
        print(f"  Reward ep01             : {r[0]:.4f}")
        print(f"  Reward ep50             : {r[-1]:.4f}")
        print(f"  Reward medio ep01-10    : {r_mean_early:.4f}")
        print(f"  Reward medio ep41-50    : {r_mean_late:.4f}")
        print(f"  Mejora en reward (%)    : {mejora_pct:+.1f}%")
        print(f"  Volatilidad std(early)  : {r_std_early:.4f}")
        print(f"  Volatilidad std(late)   : {r_std_late:.4f}")
        print(f"  Estabilizacion         : {estable}")
    if len(red) > 0:
        print(f"  CO2 reduccion media     : {red.mean():.1f}%")
        print(f"  CO2 reduccion ep50      : {red[-1]:.1f}%")
    if len(co2) > 0:
        print(f"  CO2 neta final ep50     : {co2[-1]:,.0f} kg/año")
        print(f"  CO2 neta mejor episodio : {co2.min():,.0f} kg/año (ep{int(co2.argmin())+1})")
    print(f"  BESS uso ep01-10 mean   : {bess[:10].mean():,.0f} kWh/año" if len(bess)>=10 else "  BESS: sin datos")
    print(f"  BESS uso ep41-50 mean   : {bess[-10:].mean():,.0f} kWh/año" if len(bess)>=10 else "")
    print(f"  BESS trend (+ = aprendio usar): {bess_trend:+,.0f} kWh/año")
    print(f"  Grid trend (- = redujo import): {grid_trend:+,.0f} kWh/año")

    # Diagnostico final
    if mejora_pct > 20:
        diag = f"CONVERGENCIA BUENA (+{mejora_pct:.1f}% reward, aprende bien)"
    elif mejora_pct > 10:
        diag = f"CONVERGENCIA MODERADA (+{mejora_pct:.1f}% reward)"
    elif mejora_pct > 0:
        diag = f"MEJORA LEVE (+{mejora_pct:.1f}% reward) — posible plateau prematuro"
    else:
        diag = f"NO CONVERGE / ESTANCADO ({mejora_pct:+.1f}%)"
    print(f"\n  *** DIAGNOSTICO: {diag} ***\n")

# Ranking final por CO2 ep50
print("=== RANKING FINAL (CO2 kg/año en ep50) ===")
ranking = []
for ag in agents:
    j = json.loads((ROOT / f"outputs/{ag}_training/result_{ag}.json").read_text(encoding="utf-8"))
    ev = j.get("training_evolution", {})
    co2 = np.array(ev.get("hist_co2_neta_kg", []))
    red = np.array(ev.get("hist_reduccion_pct", []))
    if len(co2) > 0:
        ranking.append((ag.upper(), co2[-1], red[-1] if len(red) > 0 else 0))

ranking.sort(key=lambda x: x[1])
F0 = 7_053_691
for i, (ag, co2_val, red_val) in enumerate(ranking, 1):
    print(f"  #{i} {ag}: {co2_val:,.0f} kg/año  ({red_val:.1f}% vs F0={F0:,.0f})")
