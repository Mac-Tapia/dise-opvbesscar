from __future__ import annotations
"""Diagnóstico profundo SAC: por qué el reward sube pero CO2 sube."""
import json, numpy as np, pandas as pd
from pathlib import Path

ROOT = Path("d:/diseñopvbesscar")

agents = ["sac", "ppo", "a2c"]
SEP = "=" * 72

for ag in agents:
    j   = json.loads((ROOT / f"outputs/{ag}_training/result_{ag}.json").read_text(encoding="utf-8"))
    ev  = j.get("training_evolution", {})
    csv = ROOT / f"outputs/{ag}_training/{ag}_convergencia_episodios.csv"
    r   = pd.read_csv(csv)["reward"].values

    co2_dir  = np.array(ev.get("hist_co2_directa_kg", []))
    co2_ind  = np.array(ev.get("hist_co2_indirecta_kg", []))
    co2_net  = np.array(ev.get("hist_co2_neta_kg", []))
    co2_base = np.array(ev.get("hist_co2_baseline_kg", []))
    co2_ctrl = np.array(ev.get("hist_co2_control_kg", []))
    grid     = np.array(ev.get("hist_grid_import_kwh", []))
    bess     = np.array(ev.get("hist_bess_discharge_kwh", []))
    ev_m     = np.array(ev.get("hist_ev_motos_kwh", []))
    ev_t     = np.array(ev.get("hist_ev_mototaxis_kwh", []))
    red      = np.array(ev.get("hist_reduccion_pct", []))

    print(f"\n{SEP}")
    print(f"  {ag.upper()} — DESCOMPOSICION CO2")
    print(SEP)

    print(f"\n  {'Métrica':<30} {'ep01':>14} {'ep10':>14} {'ep25':>14} {'ep50':>14}")
    print("  " + "-" * 72)
    for label, arr in [
        ("CO2 directa (kg/año)",    co2_dir),
        ("CO2 indirecta (kg/año)",  co2_ind),
        ("CO2 control (kg/año)",    co2_ctrl),
        ("CO2 neta (kg/año)",       co2_net),
        ("CO2 baseline (kg/año)",   co2_base),
        ("Reduccion %",             red),
        ("Grid import (kWh/año)",   grid),
        ("BESS descarga (kWh/año)", bess),
        ("EV motos (kWh/año)",      ev_m),
        ("EV mototaxis (kWh/año)",  ev_t),
        ("Reward",                  r),
    ]:
        if len(arr) < 50:
            continue
        vals = [arr[0], arr[9], arr[24], arr[49]]
        if label == "Reduccion %" or label == "Reward":
            row = f"  {label:<30} " + "  ".join(f"{v:>14.2f}" for v in vals)
        else:
            row = f"  {label:<30} " + "  ".join(f"{v:>14,.0f}" for v in vals)
        print(row)

    # Correlaciones claves
    print()
    if len(co2_net) == 50 and len(r) == 50:
        print(f"  Correlacion reward <-> CO2_neta      : {np.corrcoef(r, co2_net)[0,1]:>+.4f}")
    if len(co2_dir) == 50:
        print(f"  Correlacion reward <-> CO2_directa   : {np.corrcoef(r, co2_dir)[0,1]:>+.4f}")
    if len(co2_ind) == 50:
        print(f"  Correlacion reward <-> CO2_indirecta : {np.corrcoef(r, co2_ind)[0,1]:>+.4f}")
    if len(grid) == 50:
        print(f"  Correlacion reward <-> Grid import   : {np.corrcoef(r, grid)[0,1]:>+.4f}")
    if len(bess) == 50:
        print(f"  Correlacion reward <-> BESS descarga : {np.corrcoef(r, bess)[0,1]:>+.4f}")

    # Verificar: CO2_neta = CO2_ctrl - CO2_baseline ?
    if len(co2_net) > 0 and len(co2_ctrl) > 0 and len(co2_base) > 0:
        diff = co2_net - (co2_ctrl - co2_base)
        print(f"\n  CHECK co2_neta == co2_ctrl - co2_base: diff max={diff.max():+.0f} min={diff.min():+.0f}")
    if len(co2_net) > 0 and len(co2_ctrl) > 0:
        diff2 = co2_net - co2_ctrl
        print(f"  CHECK co2_neta == co2_ctrl:             diff max={diff2.max():+.0f} min={diff2.min():+.0f}")

# Resumen: tabla comparativa de reduccion real vs F0
print(f"\n{SEP}")
print("  RESUMEN: CO2 REAL DEL SISTEMA CONTROLADO")
print(SEP)
F0 = 7_053_691
F1 = 5_777_812
print(f"\n  {'Agente':<8} {'CO2_ctrl ep50':>16} {'CO2_neta ep50':>16} {'Red vs F0':>10} {'co2_baseline ep1':>18}")
for ag in agents:
    j  = json.loads((ROOT / f"outputs/{ag}_training/result_{ag}.json").read_text(encoding="utf-8"))
    ev = j.get("training_evolution", {})
    ctrl = np.array(ev.get("hist_co2_control_kg", []))
    net  = np.array(ev.get("hist_co2_neta_kg", []))
    base = np.array(ev.get("hist_co2_baseline_kg", []))
    c50  = ctrl[-1] if len(ctrl) > 0 else 0
    n50  = net[-1]  if len(net)  > 0 else 0
    b0   = base[0]  if len(base) > 0 else 0
    red  = (F0 - c50) / F0 * 100 if c50 > 0 else 0
    print(f"  {ag.upper():<8} {c50:>16,.0f} {n50:>16,.0f} {red:>9.1f}% {b0:>18,.0f}")

print(f"\n  F0 (referencia sin RL): {F0:,.0f} kg/año")
print(f"  F1 (solar+BESS sin RL): {F1:,.0f} kg/año")
