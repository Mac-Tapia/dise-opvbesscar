"""
Debug SOC flow during reset and steps
"""
import os
os.chdir("data/processed/citylearn/iquitos_ev_mall")
from citylearn.citylearn import CityLearnEnv

env = CityLearnEnv(schema="schema.json", render_mode=None)

# ANTES de reset
print("=== ANTES DE RESET ===")
ev = env.electric_vehicles[0]
print(f"EV Battery SOC[0]: {ev.battery.soc[0]}")
print(f"EV Battery initial_soc: {ev.battery.initial_soc}")

# Despues de reset
obs, info = env.reset()
print()
print("=== DESPUES DE RESET ===")
ev = env.electric_vehicles[0]
soc_list = list(ev.battery.soc[:5])
print(f"EV Battery SOC: primeros 5 = {soc_list}")
last_soc = ev.battery.soc[-1] if len(ev.battery.soc) > 0 else "empty"
print(f"EV Battery SOC[-1]: {last_soc}")
print(f"EV time_step: {ev.time_step}")

# Despues de step 0
actions = [[0.8] * 129]
obs, r, d, t, info = env.step(actions)
print()
print("=== DESPUES DE STEP 1 ===")
soc_list = list(ev.battery.soc[:5])
print(f"EV Battery SOC: primeros 5 = {soc_list}")
print(f"EV Battery SOC[-1]: {ev.battery.soc[-1]}")
print(f"EV time_step: {ev.time_step}")

# Ejecutar hasta hora 9
for i in range(8):
    actions = [[0.8] * 129]
    obs, r, d, t, info = env.step(actions)

print()
print("=== DESPUES DE HORA 9 (step 9) ===")
soc_list = list(ev.battery.soc[:12])
print(f"EV Battery SOC: primeros 12 = {soc_list}")
print(f"EV Battery SOC[-1]: {ev.battery.soc[-1]}")
print(f"EV time_step: {ev.time_step}")

# Verificar charger
b = env.buildings[0]
ch = b.electric_vehicle_chargers[0]
print()
print("=== CHARGER 1 ===")
print(f"connected_electric_vehicle: {ch.connected_electric_vehicle}")
if ch.connected_electric_vehicle:
    cev = ch.connected_electric_vehicle
    print(f"Connected EV battery SOC[-1]: {cev.battery.soc[-1]}")

# Verificar charger_simulation data
print()
print("=== CHARGER SIMULATION DATA ===")
cs = ch.charger_simulation
print(f"charger_simulation type: {type(cs)}")
# Ver atributos
for attr in sorted(dir(cs)):
    if not attr.startswith("_") and not callable(getattr(cs, attr, None)):
        val = getattr(cs, attr, None)
        if hasattr(val, "__len__") and not isinstance(val, str):
            if len(val) > 10:
                print(f"  {attr}: len={len(val)}, first5={list(val[:5])}")
            else:
                print(f"  {attr}: {list(val)}")
        else:
            print(f"  {attr}: {val}")
