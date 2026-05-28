from __future__ import annotations
import json, numpy as np, pandas as pd
from pathlib import Path

ROOT = Path("d:/diseñopvbesscar")
j = json.loads((ROOT / "outputs/sac_training/result_sac.json").read_text(encoding="utf-8"))
ev = j.get("training_evolution", {})

print("Keys en training_evolution:")
for k, v in ev.items():
    if isinstance(v, list):
        tipo = type(v[0]).__name__ if v else "empty"
        print(f"  {k}: n={len(v)}, tipo={tipo}")
    else:
        print(f"  {k}: {v}")
print()

co2  = np.array(ev.get("hist_co2_neta_kg", []))
grid = np.array(ev.get("hist_grid_import_kwh", []))
bess = np.array(ev.get("hist_bess_discharge_kwh", []))
solar_sc = np.array(ev.get("hist_solar_selfcons_kwh", []))
ev_m = np.array(ev.get("hist_ev_motos_kwh", []))
ev_t = np.array(ev.get("hist_ev_mototaxis_kwh", []))
red  = np.array(ev.get("hist_reduccion_pct", []))

csv = ROOT / "outputs/sac_training/sac_convergencia_episodios.csv"
r   = pd.read_csv(csv)["reward"].values

corr_r_co2  = np.corrcoef(r, co2)[0, 1]
corr_r_grid = np.corrcoef(r, grid)[0, 1] if len(grid) == len(r) else float("nan")
corr_r_bess = np.corrcoef(r, bess)[0, 1] if len(bess) == len(r) else float("nan")

print(f"Correlacion reward <-> CO2  : {corr_r_co2:.4f}  (negativo = reward sube, CO2 sube TAMBIEN -> desacoplados)")
print(f"Correlacion reward <-> grid : {corr_r_grid:.4f}")
print(f"Correlacion reward <-> BESS : {corr_r_bess:.4f}")
print()

print("Evolucion por bloque de 10 episodios:")
print(f"{'Bloque':<12} {'Reward':>10} {'CO2 kg':>14} {'Grid kWh':>14} {'BESS kWh':>12} {'Reduc%':>8}")
for i in range(5):
    s, e = i * 10, (i + 1) * 10
    rm  = r[s:e].mean()
    cm  = co2[s:e].mean()  if len(co2)  >= e else 0
    gm  = grid[s:e].mean() if len(grid) >= e else 0
    bm  = bess[s:e].mean() if len(bess) >= e else 0
    rm2 = red[s:e].mean()  if len(red)  >= e else 0
    print(f"ep{s+1:02d}-{e:02d}       {rm:>10.2f} {cm:>14,.0f} {gm:>14,.0f} {bm:>12,.0f} {rm2:>8.1f}%")
print()

# Comportamiento BESS: cuanto mas descarga, mas CO2 deberia bajar
# Si sube CO2 y sube BESS -> BESS descarga energia que viene de red, no de solar
print("ANALISIS BESS vs SOLAR vs CO2:")
print(f"  BESS descarga ep01-10 mean : {bess[:10].mean():>12,.0f} kWh/año")
print(f"  BESS descarga ep41-50 mean : {bess[-10:].mean():>12,.0f} kWh/año")
print(f"  Delta BESS                 : {bess[-10:].mean()-bess[:10].mean():>+12,.0f} kWh/año (+ = mas uso)")
if len(solar_sc) > 0:
    print(f"  Solar self-cons ep01-10    : {solar_sc[:10].mean():>12,.0f} kWh/año")
    print(f"  Solar self-cons ep41-50    : {solar_sc[-10:].mean():>12,.0f} kWh/año")
print(f"  Grid import ep01-10 mean   : {grid[:10].mean():>12,.0f} kWh/año")
print(f"  Grid import ep41-50 mean   : {grid[-10:].mean():>12,.0f} kWh/año")
print(f"  Delta grid import          : {grid[-10:].mean()-grid[:10].mean():>+12,.0f} kWh/año (- = aprende)")
print()

# Hypothesis: SAC learns to charge BESS FROM GRID during off-peak, then discharge
# This increases grid import but could be "smart" economically (lower tariff)
# But increases CO2 if grid factor is high

# CO2 neta vs grid*factor
factor = 0.4521
co2_estimada = grid * factor
print("VERIFICACION: CO2 estimada = grid_import * 0.4521 vs CO2 neta real:")
for i in [0, 9, 24, 39, 49]:
    if i < len(co2) and i < len(grid):
        est = grid[i] * factor
        real = co2[i]
        diff = real - est
        print(f"  ep{i+1:02d}: CO2_est={est:,.0f}  CO2_real={real:,.0f}  diff={diff:+,.0f} kg")
print()

# EV charging trend
print("CARGA EV:")
print(f"  Motos    ep01-10: {ev_m[:10].mean():>10,.0f}  ep41-50: {ev_m[-10:].mean():>10,.0f}  delta: {ev_m[-10:].mean()-ev_m[:10].mean():>+10,.0f}")
print(f"  Mototaxis ep01-10:{ev_t[:10].mean():>10,.0f}  ep41-50: {ev_t[-10:].mean():>10,.0f}  delta: {ev_t[-10:].mean()-ev_t[:10].mean():>+10,.0f}")
