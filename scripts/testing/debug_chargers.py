"""
Debug chargers y EVs en CityLearn
"""
import os
from pathlib import Path

os.chdir("data/processed/citylearn/iquitos_ev_mall")
from citylearn.citylearn import CityLearnEnv

env = CityLearnEnv(schema="schema.json", render_mode=None)

print("=== VERIFICAR CHARGERS Y EVs ===")
b = env.buildings[0]

print(f"Total chargers en building: {len(b.electric_vehicle_chargers)}")
print(f"Total EVs en env: {len(env.electric_vehicles)}")

# Verificar estado de los primeros chargers
print("\nEstado de primeros 5 chargers:")
for i, charger in enumerate(b.electric_vehicle_chargers[:5]):
    print(f"  Charger {i+1} ({charger.charger_id}):")
    print(f"    - connected_electric_vehicle: {charger.connected_electric_vehicle}")
    print(f"    - incoming_electric_vehicle: {charger.incoming_electric_vehicle}")
    print(f"    - max_charging_power: {charger.max_charging_power}")
    print(f"    - efficiency: {charger.efficiency}")

# Reset y ejecutar steps
print("\nReset y ejecutar steps...")
obs, info = env.reset()

# Mostrar action space
print(f"\nAction space type: {type(env.action_space)}")
if hasattr(env.action_space, "shape"):
    print(f"Action space shape: {env.action_space.shape}")

# Ejecutar 15 steps (hasta hora 15, bien dentro del horario de carga 9-22)
print("\nEjecutando 15 steps...")
for t in range(15):
    # Preparar acciones
    if isinstance(env.action_space, list):
        actions = [[0.8] * sum(sp.shape[0] if hasattr(sp, "shape") else 1 for sp in env.action_space)]
    else:
        n_actions = env.action_space.shape[0] if hasattr(env.action_space, "shape") else 129
        actions = [[0.8] * n_actions]

    obs, reward, terminated, truncated, info = env.step(actions)

    # Verificar consumo
    charging = b.chargers_electricity_consumption[-1] if len(b.chargers_electricity_consumption) > 0 else 0
    print(f"Step {t+1}: chargers_consumption={charging:.2f} kWh")

    # En step 10 (hora 10), verificar chargers conectados
    if t == 10:
        print("\n  === Estado de chargers en hora 10 ===")
        connected = sum(1 for ch in b.electric_vehicle_chargers if ch.connected_electric_vehicle is not None)
        incoming = sum(1 for ch in b.electric_vehicle_chargers if ch.incoming_electric_vehicle is not None)
        print(f"  Chargers con EV conectado: {connected}/128")
        print(f"  Chargers con EV incoming: {incoming}/128")

        if connected > 0:
            for ch in b.electric_vehicle_chargers:
                if ch.connected_electric_vehicle is not None:
                    ev = ch.connected_electric_vehicle
                    ev_name = ev.name if hasattr(ev, "name") else "EV"
                    ev_soc = "N/A"
                    if hasattr(ev, "battery") and hasattr(ev.battery, "soc"):
                        if len(ev.battery.soc) > 0:
                            ev_soc = ev.battery.soc[-1]
                    print(f"  Ejemplo EV conectado: {ev_name}, SOC={ev_soc}")
                    break

        # Verificar incoming EVs
        if incoming > 0:
            for ch in b.electric_vehicle_chargers:
                if ch.incoming_electric_vehicle is not None:
                    ev = ch.incoming_electric_vehicle
                    ev_name = ev.name if hasattr(ev, "name") else "EV"
                    print(f"  Ejemplo EV incoming: {ev_name}")
                    break

print("\n=== FIN ===")
