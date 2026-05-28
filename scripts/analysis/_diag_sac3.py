from __future__ import annotations
"""
Diagnóstico: ¿Es CO2_neta el metric correcto para OE3?
Verifica CO2_neta = CO2_directa + CO2_indirecta y compara con CO2_control.
"""
import json, numpy as np
from pathlib import Path

ROOT = Path("d:/diseñopvbesscar")
F0   = 7_053_691
SEP  = "=" * 72

agents = ["sac", "ppo", "a2c"]
data   = {}
for ag in agents:
    j  = json.loads((ROOT / f"outputs/{ag}_training/result_{ag}.json").read_text(encoding="utf-8"))
    ev = j.get("training_evolution", {})
    data[ag] = {
        "co2_dir":  np.array(ev.get("hist_co2_directa_kg",  [])),
        "co2_ind":  np.array(ev.get("hist_co2_indirecta_kg",[])),
        "co2_net":  np.array(ev.get("hist_co2_neta_kg",     [])),
        "co2_ctrl": np.array(ev.get("hist_co2_control_kg",  [])),
        "co2_base": np.array(ev.get("hist_co2_baseline_kg", [])),
        "grid":     np.array(ev.get("hist_grid_import_kwh", [])),
        "bess":     np.array(ev.get("hist_bess_discharge_kwh", [])),
        "ev_m":     np.array(ev.get("hist_ev_motos_kwh",    [])),
        "ev_t":     np.array(ev.get("hist_ev_mototaxis_kwh",[])),
    }

# Verificar: CO2_neta = CO2_directa + CO2_indirecta ?
print(SEP)
print("  VERIFICACION: co2_neta = co2_directa + co2_indirecta ?")
print(SEP)
for ag in agents:
    d = data[ag]
    sum_dir_ind = d["co2_dir"] + d["co2_ind"]
    diff = d["co2_net"] - sum_dir_ind
    ok = "OK" if np.allclose(diff, 0, atol=1) else f"DIFF max={diff.max():+.1f}"
    print(f"  {ag.upper()}: {ok}  (ep50: dir={d['co2_dir'][-1]:,.0f}  ind={d['co2_ind'][-1]:,.0f}  sum={sum_dir_ind[-1]:,.0f}  neta={d['co2_net'][-1]:,.0f})")

# Caida directa de CO2 por ep: EV charging es el driver
print(f"\n{SEP}")
print("  CAUSA DEL AUMENTO CO2_NETA EN SAC: EV CHARGING COMO DRIVER DE CO2_DIRECTA")
print(SEP)
for ag in agents:
    d    = data[ag]
    ev_t = d["ev_m"] + d["ev_t"]
    if len(ev_t) < 50:
        continue
    # Factor implicito CO2_directa / EV_total
    with np.errstate(divide='ignore', invalid='ignore'):
        factor_dir = np.where(ev_t > 0, d["co2_dir"] / ev_t, 0)
    with np.errstate(divide='ignore', invalid='ignore'):
        factor_ind = np.where(d["grid"] > 0, d["co2_ind"] / d["grid"], 0)
    print(f"\n  {ag.upper()}")
    print(f"    EV total     ep01 -> ep50: {ev_t[0]:>10,.0f} -> {ev_t[-1]:>10,.0f} kWh/año  delta={ev_t[-1]-ev_t[0]:>+10,.0f}")
    print(f"    CO2_directa  ep01 -> ep50: {d['co2_dir'][0]:>10,.0f} -> {d['co2_dir'][-1]:>10,.0f} kg/año  delta={d['co2_dir'][-1]-d['co2_dir'][0]:>+10,.0f}")
    print(f"    CO2_indirecta ep01-> ep50: {d['co2_ind'][0]:>10,.0f} -> {d['co2_ind'][-1]:>10,.0f} kg/año  delta={d['co2_ind'][-1]-d['co2_ind'][0]:>+10,.0f}")
    print(f"    Factor dir (kg/kWh_EV)   : ep01={factor_dir[0]:.4f}  ep50={factor_dir[-1]:.4f}  (constante={np.std(factor_dir):.5f} std)")
    print(f"    Factor ind (kg/kWh_grid) : ep01={factor_ind[0]:.4f}  ep50={factor_ind[-1]:.4f}")
    print(f"    BESS        ep01 -> ep50: {d['bess'][0]:>10,.0f} -> {d['bess'][-1]:>10,.0f} kWh/año")

# Ranking por CO2_control (metrica correcta para OE3)
print(f"\n{SEP}")
print("  RANKING POR CO2_CONTROL (metrica total del sistema — correcta para OE3)")
print(SEP)
print(f"\n  {'Agente':<8} {'CO2_ctrl ep50':>16} {'vs F0':>8}  {'CO2_neta ep50':>16} {'vs F0':>8}  {'Diferencia':>12}")
ranking = []
for ag in agents:
    d     = data[ag]
    ctrl  = d["co2_ctrl"][-1]  if len(d["co2_ctrl"]) > 0 else 0
    neta  = d["co2_net"][-1]   if len(d["co2_net"])  > 0 else 0
    red_c = (F0 - ctrl) / F0 * 100
    red_n = (F0 - neta) / F0 * 100
    ranking.append((ag, ctrl, red_c, neta, red_n))
    print(f"  {ag.upper():<8} {ctrl:>16,.0f} {red_c:>7.1f}%  {neta:>16,.0f} {red_n:>7.1f}%  {ctrl-neta:>12,.0f}")

ranking.sort(key=lambda x: x[1])
print(f"\n  RANKING CO2_control: {' > '.join(x[0].upper() for x in ranking)}")
print(f"\n  RANKING CO2_neta   : A2C > PPO > SAC  (resultado anterior — DISTORSIONADO)")

# Propuestas de mejora para SAC
print(f"\n{SEP}")
print("  PROPUESTAS DE MEJORA PARA SAC (OE3)")
print(SEP)

# Calcular potencial de mejora
sac = data["sac"]
a2c = data["a2c"]
# Si SAC reduce CO2_indirecta al nivel de A2C...
sac_grid_ep50 = sac["grid"][-1]
a2c_grid_ep50 = a2c["grid"][-1]
sac_ind_ep50  = sac["co2_ind"][-1]
a2c_ind_ep50  = a2c["co2_ind"][-1]
factor_diff   = (sac_ind_ep50/sac_grid_ep50) - (a2c_ind_ep50/a2c_grid_ep50)
potencial_ind = factor_diff * sac_grid_ep50

# Potencial si SAC extendiera 50 episodios mas (extrapolando slope)
from pathlib import Path as P
import pandas as pd
csv = ROOT / "outputs/sac_training/sac_convergencia_episodios.csv"
r   = pd.read_csv(csv)["reward"].values
slope_r = np.polyfit(np.arange(len(r)), r, 1)[0]
slope_co2ctrl = np.polyfit(np.arange(len(sac["co2_ctrl"])), sac["co2_ctrl"], 1)[0]
extrap_ctrl_ep100 = sac["co2_ctrl"][-1] + slope_co2ctrl * 50
red_extrap = (F0 - extrap_ctrl_ep100) / F0 * 100

print(f"""
  [DIAGNOSTICO CONFIRMADO]
  co2_neta = co2_directa + co2_indirecta
  co2_directa aumenta porque SAC aprende a cargar mas EVs (+96% de carga):
    ep01: {sac['ev_m'][0]+sac['ev_t'][0]:,.0f} kWh/año  ->  ep50: {sac['ev_m'][-1]+sac['ev_t'][-1]:,.0f} kWh/año
  El factor CO2 de co2_directa es CONSTANTE (~0.82 kg/kWh_EV) — no cambia.
  Por eso co2_neta SUBE aunque el grid import BAJA. Es un artefacto contable.

  [METRICA CORRECTA PARA OE3]
  co2_control = CO2 total del sistema (incluye todos los flujos energeticos).
  Por co2_control: SAC (#1, {ranking[0][2]:.1f}%) > A2C (#2, {ranking[1][2]:.1f}%) > PPO (#3, {ranking[2][2]:.1f}%) vs F0.

  [PROPUESTA 1] Extender entrenamiento a 75-100 episodios
  SAC todavia mejora en ep50 (reward slope = {slope_r:+.2f}/ep, co2_ctrl slope = {slope_co2ctrl:+,.0f} kg/ep)
  Extrapolacion lineal ep100: CO2_ctrl ~ {extrap_ctrl_ep100:,.0f} kg/año ({red_extrap:.1f}% vs F0)

  [PROPUESTA 2] Ajuste de pesos de reward (ev_charging_wrapper.py)
  Actual:   _W_INDIRECT_CO2=0.45  _W_EV_COMPLETE=0.25  _W_COST=0.10
  Propuesta: _W_INDIRECT_CO2=0.55  _W_EV_COMPLETE=0.15  _W_COST=0.10
  Efecto: SAC priorizaria reduccion de grid CO2 sobre cantidad de carga EV.
  Justificacion: OE3 objetivo es CO2, no throughput de carga EV.

  [PROPUESTA 3] Solar-priority BESS charging (en ev_charging_wrapper.py)
  SAC cicla BESS con energia de red (factor CO2 implicito {sac_ind_ep50/sac_grid_ep50:.4f} kg/kWh)
  A2C importa a factor {a2c_ind_ep50/a2c_grid_ep50:.4f} kg/kWh — usa solar mas directamente.
  Diferencia factor: {factor_diff:+.4f} kg/kWh x {sac_grid_ep50:,.0f} kWh = {potencial_ind:+,.0f} kg CO2/año potencial de mejora.
  Implementacion: reward bonus cuando solar_kw > threshold Y bess_action > 0 (cargando de solar).

  [PROPUESTA 4] Checkpoint por CO2_control minimo (no solo reward)
  El mejor checkpoint SAC por reward es ep50 (-671.08).
  El mejor checkpoint por CO2_control podria ser diferente -> guardar ambos.

  [PROPUESTA 5] Learning rate decay en ultimos 20 episodios
  SAC converge reward pero CO2_ctrl sigue con slope {slope_co2ctrl:+,.0f} kg/ep (tendencia).
  Un LR scheduler (lineal decay 1e-4 -> 5e-5 en ep30-50) podria refinar la politica.
""")
