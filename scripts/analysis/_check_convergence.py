from __future__ import annotations
import json, pandas as pd, numpy as np
from pathlib import Path

ROOT = Path("d:/diseñopvbesscar")

agents = ["sac", "ppo", "a2c"]
for ag in agents:
    j = json.loads((ROOT / f"outputs/{ag}_training/result_{ag}.json").read_text(encoding="utf-8"))
    ev = j.get("training_evolution", {})
    rewards_json = ev.get("episode_rewards", [])
    csv_path = ROOT / f"outputs/{ag}_training/{ag}_convergencia_episodios.csv"
    rewards_csv = pd.read_csv(csv_path)["reward"].values if csv_path.exists() else np.array([])

    r    = np.array(rewards_json) if len(rewards_json) > 0 else rewards_csv
    co2  = np.array(ev.get("hist_co2_neta_kg", []))
    grid = np.array(ev.get("hist_grid_import_kwh", []))
    red  = np.array(ev.get("hist_reduccion_pct", []))
    bess = np.array(ev.get("hist_bess_discharge_kwh", []))

    n_ep = j.get("total_episodes", len(r))
    ts   = j.get("total_timesteps", "?")

    print(f"=== {ag.upper()} ===")
    print(f"  Episodios completados   : {n_ep}")
    print(f"  Total timesteps         : {ts}")

    if len(r) > 0:
        print(f"  Rewards  min/mean/max   : {r.min():.4f} / {r.mean():.4f} / {r.max():.4f}")
        if len(r) >= 10:
            f10 = r[:10].mean()
            l10 = r[-10:].mean()
            trend = ((l10 - f10) / abs(f10)) * 100 if f10 != 0 else 0
            print(f"  Rewards  ep01-10 mean   : {f10:.4f}")
            print(f"  Rewards  ep41-50 mean   : {l10:.4f}")
            print(f"  Mejora rewards (%)      : {trend:+.1f}%")
    else:
        print("  Rewards: SIN DATOS")

    if len(co2) > 0:
        print(f"  CO2 neta ep01 / ep50    : {co2[0]:,.0f} / {co2[-1]:,.0f} kg/año")
        print(f"  CO2 neta  min / mean    : {co2.min():,.0f} / {co2.mean():,.0f} kg/año")
    if len(red) > 0:
        print(f"  Reduccion %  ep01/ep50  : {red[0]:.1f}% / {red[-1]:.1f}%")
        print(f"  Reduccion %  max        : {red.max():.1f}%")
    if len(grid) > 0:
        print(f"  Grid import  ep01/ep50  : {grid[0]:,.0f} / {grid[-1]:,.0f} kWh/año")
    if len(bess) > 0:
        print(f"  BESS disch   ep01/ep50  : {bess[0]:,.0f} / {bess[-1]:,.0f} kWh/año")
    print()
