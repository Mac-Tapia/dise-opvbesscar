"""
Test completo de carga de chargers con acciones correctas
"""
import os
import numpy as np
os.chdir("data/processed/citylearn/iquitos_ev_mall")
from citylearn.citylearn import CityLearnEnv

env = CityLearnEnv(schema="schema.json", render_mode=None)

print("=" * 80)
print("TEST COMPLETO DE CARGA DE CHARGERS")
print("=" * 80)

b = env.buildings[0]

print(f"\nAction space: {env.action_space[0].shape}")
print(f"  Action 0: BESS (electrical_storage)")
print(f"  Actions 1-128: Chargers (electric_vehicle_storage)")
print(f"Total EVs: {len(env.electric_vehicles)}")
print(f"Total chargers: {len(b.electric_vehicle_chargers)}")

obs, info = env.reset()

# Ejecutar 24 horas con acciones de carga
print("\n=== EJECUTANDO 24 HORAS ===")
total_charging = 0.0

for hour in range(24):
    # Crear acciones: 0.0 para BESS, 0.8 para todos los chargers
    actions = np.zeros(129, dtype=np.float32)
    actions[0] = 0.0  # BESS: no action
    actions[1:] = 0.8  # Chargers: cargar al 80%

    # Step
    obs, reward, terminated, truncated, info = env.step([actions])

    # Extraer consumo de chargers - usar la suma de todos los chargers individuales
    step_charging = 0.0
    for ch in b.electric_vehicle_chargers:
        if len(ch.electricity_consumption) > hour:
            step_charging += max(0, ch.electricity_consumption[hour])

    total_charging += max(0, step_charging)

    # Contar EVs conectados
    connected = sum(1 for ch in b.electric_vehicle_chargers if ch.connected_electric_vehicle is not None)

    # Mostrar info cada 3 horas
    if hour % 3 == 0 or step_charging > 0:
        print(f"Hora {hour:2d}: consumo={step_charging:7.2f} kWh, EVs conectados={connected:3d}, acum={total_charging:10.2f} kWh")

print(f"\n=== RESULTADO ===")
print(f"Consumo total chargers (24h): {total_charging:.2f} kWh")

if total_charging > 0:
    print("\n[OK] ✓ CHARGERS FUNCIONANDO CORRECTAMENTE")
else:
    print("\n[ERROR] ✗ CHARGERS NO CONSUMEN ENERGIA")

    # Debug adicional
    print("\n=== DEBUG: Estado de chargers en hora 12 ===")
    ch = b.electric_vehicle_chargers[0]
    print(f"  Charger 1:")
    print(f"    connected_electric_vehicle: {ch.connected_electric_vehicle}")
    print(f"    electricity_consumption: {list(ch.electricity_consumption[:15])}")

    if ch.connected_electric_vehicle:
        ev = ch.connected_electric_vehicle
        print(f"  EV conectado:")
        if hasattr(ev, "battery"):
            print(f"    battery.soc: {list(ev.battery.soc[:15])}")
            print(f"    battery.energy_balance: {list(ev.battery.energy_balance[:15])}")

print("=" * 80)
