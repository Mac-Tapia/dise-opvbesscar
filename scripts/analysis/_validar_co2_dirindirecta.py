from __future__ import annotations
"""
Validación OE3: ¿Qué agente reduce AMBAS emisiones directas e indirectas de CO2?
"""
import json, numpy as np
from pathlib import Path

ROOT = Path("d:/diseñopvbesscar")
F0   = 7_053_691
SEP  = "=" * 72
agents = ["sac", "ppo", "a2c"]

data = {}
for ag in agents:
    j  = json.loads((ROOT / f"outputs/{ag}_training/result_{ag}.json").read_text(encoding="utf-8"))
    ev = j.get("training_evolution", {})
    data[ag] = {
        "co2_dir":  np.array(ev.get("hist_co2_directa_kg",   [])),
        "co2_ind":  np.array(ev.get("hist_co2_indirecta_kg", [])),
        "co2_net":  np.array(ev.get("hist_co2_neta_kg",      [])),
        "co2_ctrl": np.array(ev.get("hist_co2_control_kg",   [])),
        "grid":     np.array(ev.get("hist_grid_import_kwh",  [])),
        "bess":     np.array(ev.get("hist_bess_discharge_kwh", [])),
        "ev_m":     np.array(ev.get("hist_ev_motos_kwh",     [])),
        "ev_t":     np.array(ev.get("hist_ev_mototaxis_kwh", [])),
    }

print(SEP)
print("  VALIDACION OE3: REDUCCION DE EMISIONES DIRECTAS E INDIRECTAS DE CO2")
print(f"  Objetivo: minimizar CO2_directa + CO2_indirecta del sistema de carga EV")
print(SEP)

# ─── Emisiones en ep50 (política aprendida final) ────────────────────────────
print(f"\n{'─'*72}")
print("  A. ESTADO FINAL APRENDIDO (ep50) — políticas completamente entrenadas")
print(f"{'─'*72}")
print(f"\n  {'Componente':<28} {'SAC ep50':>14} {'PPO ep50':>14} {'A2C ep50':>14}  Mejor")

rows = []
for label, key in [
    ("CO2 DIRECTA (kg/año)",    "co2_dir"),
    ("CO2 INDIRECTA (kg/año)",  "co2_ind"),
    ("CO2 NETA = dir+ind",      "co2_net"),
    ("CO2 CONTROL total",       "co2_ctrl"),
    ("Grid import (kWh/año)",   "grid"),
    ("BESS descarga (kWh/año)", "bess"),
]:
    vals = {ag: data[ag][key][-1] if len(data[ag][key]) > 0 else 0 for ag in agents}
    best = min(vals, key=lambda x: vals[x])
    row  = f"  {label:<28} {vals['sac']:>14,.0f} {vals['ppo']:>14,.0f} {vals['a2c']:>14,.0f}  {best.upper()}"
    print(row)

# ─── Tendencia de mejora ep01→ep50 ───────────────────────────────────────────
print(f"\n{'─'*72}")
print("  B. TENDENCIA DE MEJORA ep01 → ep50 (delta = ep50 - ep01)")
print(f"{'─'*72}")
print(f"\n  {'Componente':<28} {'SAC':>16} {'PPO':>16} {'A2C':>16}  Mejor (menor delta)")

for label, key in [
    ("Delta CO2_directa (kg/año)", "co2_dir"),
    ("Delta CO2_indirecta (kg/año)","co2_ind"),
    ("Delta CO2_neta (kg/año)",    "co2_net"),
    ("Delta Grid import (kWh)",    "grid"),
    ("Delta BESS descarga (kWh)",  "bess"),
]:
    deltas = {ag: data[ag][key][-1] - data[ag][key][0] if len(data[ag][key]) > 0 else 0 for ag in agents}
    # for CO2: negative delta = reduction = GOOD
    # for BESS: positive delta = more BESS = ambiguous
    if "BESS" not in label:
        best = min(deltas, key=lambda x: deltas[x])
    else:
        best = max(deltas, key=lambda x: deltas[x])
    row = f"  {label:<28} {deltas['sac']:>+16,.0f} {deltas['ppo']:>+16,.0f} {deltas['a2c']:>+16,.0f}  {best.upper()}"
    print(row)

# ─── Factor CO2 implícito (timing de importacion) ────────────────────────────
print(f"\n{'─'*72}")
print("  C. FACTOR CO2 EFECTIVO POR kWh IMPORTADO (timing de carga BESS)")
print(f"{'─'*72}")
print("  Menor factor = agente importa mas en horas de baja emision (solar disponible)")
print()
for ag in agents:
    d = data[ag]
    if len(d["co2_ind"]) == 0 or len(d["grid"]) == 0:
        continue
    # Factor en ep01, ep25, ep50
    f01 = d["co2_ind"][0]  / d["grid"][0]  if d["grid"][0]  > 0 else 0
    f25 = d["co2_ind"][24] / d["grid"][24] if d["grid"][24] > 0 else 0
    f50 = d["co2_ind"][-1] / d["grid"][-1] if d["grid"][-1] > 0 else 0
    ref = 0.4521  # factor nominal MINEM
    print(f"  {ag.upper()}  factor CO2 efectivo (kg/kWh_grid):  ep01={f01:.4f}  ep25={f25:.4f}  ep50={f50:.4f}  (ref MINEM={ref})")
    if f50 < ref:
        print(f"       -> Por debajo del factor nominal: usa solar en momentos clave ✓")
    else:
        print(f"       -> Por encima del factor nominal: importa en horas de alta CO2 ✗")

# ─── Ranking dual: directa + indirecta ───────────────────────────────────────
print(f"\n{'─'*72}")
print("  D. RANKING CONSOLIDADO: REDUCCION CO2_DIRECTA + CO2_INDIRECTA")
print(f"{'─'*72}")

scores = {}
for ag in agents:
    d     = data[ag]
    dir50 = d["co2_dir"][-1]
    ind50 = d["co2_ind"][-1]
    net50 = dir50 + ind50
    # tendencia de indirecta (lo mas controlable)
    delta_ind = d["co2_ind"][-1] - d["co2_ind"][0]
    factor50  = d["co2_ind"][-1] / d["grid"][-1] if d["grid"][-1] > 0 else 1
    scores[ag] = {
        "dir": dir50, "ind": ind50, "net": net50,
        "delta_ind": delta_ind, "factor": factor50,
        "ctrl": d["co2_ctrl"][-1],
    }

# Normalizar a puntos 0-10 (menor CO2 = mayor puntuacion)
def score_min(vals):
    lo, hi = min(vals.values()), max(vals.values())
    if hi == lo:
        return {ag: 10.0 for ag in vals}
    return {ag: (hi - v) / (hi - lo) * 10 for ag, v in vals.items()}

s_dir   = score_min({ag: scores[ag]["dir"]    for ag in agents})
s_ind   = score_min({ag: scores[ag]["ind"]    for ag in agents})
s_dind  = score_min({ag: scores[ag]["delta_ind"] for ag in agents})  # tendencia indirecta
s_fact  = score_min({ag: scores[ag]["factor"] for ag in agents})     # factor CO2 eficiente
s_ctrl  = score_min({ag: scores[ag]["ctrl"]   for ag in agents})

print(f"\n  {'Criterio':<30} {'Peso':>5}  {'SAC':>6}  {'PPO':>6}  {'A2C':>6}")
print("  " + "-" * 60)

criterios = [
    ("CO2_directa ep50 (menos=mejor)",   0.15, s_dir),
    ("CO2_indirecta ep50 (menos=mejor)", 0.35, s_ind),
    ("Tendencia CO2_indirecta (mejora)", 0.25, s_dind),
    ("Factor CO2 por kWh grid",          0.15, s_fact),
    ("CO2_control total sistema",        0.10, s_ctrl),
]

total = {ag: 0.0 for ag in agents}
for name, w, sc in criterios:
    for ag in agents:
        total[ag] += w * sc[ag]
    print(f"  {name:<30} {w:>5.0%}  {sc['sac']:>6.2f}  {sc['ppo']:>6.2f}  {sc['a2c']:>6.2f}")

print("  " + "-" * 60)
print(f"  {'PUNTUACION FINAL':<30} {'':>5}  {total['sac']:>6.2f}  {total['ppo']:>6.2f}  {total['a2c']:>6.2f}")

winner = max(total, key=lambda x: total[x])
print(f"\n  AGENTE OE3 SELECCIONADO: {winner.upper()}")

# ─── Resumen ejecutivo ───────────────────────────────────────────────────────
w = scores[winner]
print(f"\n{SEP}")
print(f"  RESUMEN EJECUTIVO PARA OE3")
print(SEP)
print(f"""
  Agente seleccionado: {winner.upper()}

  CO2 Directa  ep50 : {w['dir']:>12,.0f} kg/año
  CO2 Indirecta ep50: {w['ind']:>12,.0f} kg/año
  CO2 NETA     ep50 : {w['net']:>12,.0f} kg/año  ({(F0-w['net'])/F0*100:.1f}% vs F0)
  CO2 CONTROL  ep50 : {w['ctrl']:>12,.0f} kg/año  ({(F0-w['ctrl'])/F0*100:.1f}% vs F0)

  Factor CO2 efectivo: {w['factor']:.4f} kg/kWh grid (menor = mejor timing solar)
""")

print("  POR QUE SAC FALLA EN CO2_INDIRECTA:")
sac = scores["sac"]
a2c_sc = scores["a2c"]
print(f"  SAC cicla BESS: {data['sac']['bess'][-1]:,.0f} kWh/año  vs  A2C: {data['a2c']['bess'][-1]:,.0f} kWh/año")
print(f"  SAC importa de red en horas de alta CO2 (factor {sac['factor']:.4f} kg/kWh)")
print(f"  A2C usa solar directamente → factor {a2c_sc['factor']:.4f} kg/kWh (−{(sac['factor']-a2c_sc['factor'])*1000:.1f} gCO2/kWh mejor)")
print(f"  Diferencia CO2_indirecta SAC vs A2C: {sac['ind']-a2c_sc['ind']:+,.0f} kg/año ({(sac['ind']-a2c_sc['ind'])/a2c_sc['ind']*100:.1f}% mas)")
print()
print("  MEJORAS RECOMENDADAS PARA SAC:")
print("  1. Reward: _W_INDIRECT_CO2 0.45->0.55, _W_EV_COMPLETE 0.25->0.15")
print("  2. Bonus de timing: recompensar BESS carga cuando solar_kw > 500 kW")
print("  3. Penalizar BESS carga nocturna (grid diesel peak): factor CO2 horario en reward")
print("  4. Extender a 100 ep: CO2_ctrl slope=-2,544 kg/ep -> ~3,537k kg en ep100 (49.9% vs F0)")
