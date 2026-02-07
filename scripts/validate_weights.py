#!/usr/bin/env python3
"""Validate weight synchronization across all configuration files."""

from src.rewards.rewards import create_iquitos_reward_weights
import inspect
from src.citylearnv2.metric.dispatcher import EnergyDispatcher
import yaml
import json

print("=== VERIFICACION PESOS MULTIOBJETIVO ===\n")

# 1. rewards.py
w = create_iquitos_reward_weights("co2_focus")
sum1 = w.co2 + w.solar + w.ev_satisfaction + w.cost + w.grid_stability
print(f"rewards.py (co2_focus):")
print(f"  CO2={w.co2:.2f} Solar={w.solar:.2f} EV={w.ev_satisfaction:.2f} Cost={w.cost:.2f} Grid={w.grid_stability:.2f}")
print(f"  Suma={sum1:.2f} {'[OK]' if abs(sum1-1.0)<0.01 else '[ERROR]'}\n")

# 2. dispatcher.py
sig = inspect.signature(EnergyDispatcher.dispatch)
defaults = {k: v.default for k, v in sig.parameters.items() if v.default is not inspect.Parameter.empty}
print(f"dispatcher.py dispatch() defaults:")
for k, v in defaults.items():
    print(f"  {k}={v}")
sum_d = defaults.get("co2_weight", 0) + defaults.get("solar_weight", 0) + defaults.get("ev_weight", 0) + defaults.get("cost_weight", 0) + defaults.get("grid_weight", 0)
print(f"  Suma={sum_d:.2f} {'[OK]' if abs(sum_d-1.0)<0.01 else '[ERROR]'}\n")

# 3. default.yaml
with open("configs/default.yaml", "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)
r = cfg.get("oe3", {}).get("rewards", {})
co2_y = r.get("co2_weight", 0)
solar_y = r.get("solar_weight", 0)
ev_y = r.get("ev_satisfaction_weight", 0)
cost_y = r.get("cost_weight", 0)
grid_y = r.get("grid_stability_weight", 0)
sum_y = co2_y + solar_y + ev_y + cost_y + grid_y
print(f"default.yaml (oe3.rewards):")
print(f"  CO2={co2_y} Solar={solar_y} EV={ev_y} Cost={cost_y} Grid={grid_y}")
print(f"  Suma={sum_y:.2f} {'[OK]' if abs(sum_y-1.0)<0.01 else '[ERROR]'}\n")

# 4. sac_optimized.json
with open("configs/sac_optimized.json", "r") as f:
    jcfg = json.load(f)
rj = jcfg.get("rewards", {})
co2_j = rj.get("co2_weight", 0)
solar_j = rj.get("solar_weight", 0)
ev_j = rj.get("ev_satisfaction_weight", 0)
cost_j = rj.get("cost_weight", 0)
grid_j = rj.get("grid_stability_weight", 0)
sum_j = co2_j + solar_j + ev_j + cost_j + grid_j
print(f"sac_optimized.json:")
print(f"  CO2={co2_j} Solar={solar_j} EV={ev_j} Cost={cost_j} Grid={grid_j}")
print(f"  Suma={sum_j:.2f} {'[OK]' if abs(sum_j-1.0)<0.01 else '[ERROR]'}\n")

# Summary table
print("=" * 70)
print("| Archivo              | CO2  | Solar | EV   | Cost | Grid | Suma |")
print("|" + "-"*22 + "|" + "-"*6 + "|" + "-"*7 + "|" + "-"*6 + "|" + "-"*6 + "|" + "-"*6 + "|" + "-"*6 + "|")
print(f"| rewards.py           | {w.co2:.2f} | {w.solar:.2f}  | {w.ev_satisfaction:.2f} | {w.cost:.2f} | {w.grid_stability:.2f} | {sum1:.2f} |")
print(f"| dispatcher.py        | {defaults.get('co2_weight', 0):.2f} | {defaults.get('solar_weight', 0):.2f}  | {defaults.get('ev_weight', 0):.2f} | {defaults.get('cost_weight', 0):.2f} | {defaults.get('grid_weight', 0):.2f} | {sum_d:.2f} |")
print(f"| default.yaml         | {co2_y:.2f} | {solar_y:.2f}  | {ev_y:.2f} | {cost_y:.2f} | {grid_y:.2f} | {sum_y:.2f} |")
print(f"| sac_optimized.json   | {co2_j:.2f} | {solar_j:.2f}  | {ev_j:.2f} | {cost_j:.2f} | {grid_j:.2f} | {sum_j:.2f} |")
print("=" * 70)

all_ok = all([
    abs(sum1-1.0) < 0.01,
    abs(sum_d-1.0) < 0.01,
    abs(sum_y-1.0) < 0.01,
    abs(sum_j-1.0) < 0.01,
])
print(f"\n{'[OK] TODOS LOS PESOS SINCRONIZADOS CORRECTAMENTE' if all_ok else '[ERROR] HAY ERRORES DE SINCRONIZACION'}")
