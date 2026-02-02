"""
TEST COMPLETO: Validar que el dataset CityLearn está funcionando correctamente
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import pandas as pd

def main():
    print("=" * 80)
    print("VALIDACION COMPLETA DEL DATASET CITYLEARN")
    print("=" * 80)

    # 1. Verificar schema.json
    schema_path = Path("data/processed/citylearn/iquitos_ev_mall/schema.json")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    print("\n[1] ELECTRIC_VEHICLES_DEF en schema:")
    ev_def = schema.get("electric_vehicles_def", {})
    print(f"   Total EVs definidos: {len(ev_def)}")

    if ev_def:
        ev1 = ev_def.get("EV_Mall_1", {})
        ev113 = ev_def.get("EV_Mall_113", {})
        bat1 = ev1.get("battery", {}).get("attributes", {})
        bat113 = ev113.get("battery", {}).get("attributes", {})

        cap1 = bat1.get("capacity", "N/A")
        pow1 = bat1.get("nominal_power", "N/A")
        soc1 = bat1.get("initial_soc", "N/A")

        cap113 = bat113.get("capacity", "N/A")
        pow113 = bat113.get("nominal_power", "N/A")
        soc113 = bat113.get("initial_soc", "N/A")

        print(f"   EV_Mall_1 (moto): cap={cap1} kWh, pow={pow1} kW, initial_soc={soc1}")
        print(f"   EV_Mall_113 (mototaxi): cap={cap113} kWh, pow={pow113} kW, initial_soc={soc113}")
    else:
        print("   [ERROR] No hay electric_vehicles_def!")

    # 2. Verificar chargers en schema
    print("\n[2] CHARGERS en schema (Mall_Iquitos):")
    mall = schema.get("buildings", {}).get("Mall_Iquitos", {})
    chargers = mall.get("chargers", {})
    print(f"   Total chargers: {len(chargers)}")

    # 3. Verificar CSV de chargers
    print("\n[3] CSVs DE CHARGERS (formato SOC):")
    dataset_dir = Path("data/processed/citylearn/iquitos_ev_mall")
    csv1 = dataset_dir / "charger_simulation_001.csv"
    df1 = pd.read_csv(csv1)
    soc_arr1 = df1["electric_vehicle_estimated_soc_arrival"].iloc[9]
    soc_dep1 = df1["electric_vehicle_required_soc_departure"].iloc[9]
    print(f"   charger_001 (hora 9): arrival_soc={soc_arr1}, departure_soc={soc_dep1}")

    if soc_arr1 > 1.0:
        print("   [ERROR] SOC en formato PORCENTAJE - debe ser FRACCION!")
    else:
        print("   [OK] SOC en formato FRACCION correcto")

    # 4. Test de carga con CityLearn
    print("\n[4] TEST DE CARGA CON CITYLEARN:")

    os.chdir(str(dataset_dir.resolve()))
    from citylearn.citylearn import CityLearnEnv

    env = CityLearnEnv(schema="schema.json", render_mode=None)
    print(f"   EVs cargados: {len(env.electric_vehicles)}")

    # Los chargers están en env.chargers (no en buildings)
    total_chargers = len(env.chargers) if hasattr(env, 'chargers') else 0
    print(f"   Chargers cargados: {total_chargers}")

    # Reset y avanzar hasta hora 9
    obs, info = env.reset()
    for t in range(9):
        actions = [[0.5] * 129]
        obs, reward, _, _, _ = env.step(actions)

    print("   Ejecutando 10 steps de carga (hora 9-19)...")
    total_charging = 0.0
    for t in range(10):
        actions = [[0.8] * 129]
        obs, reward, _, _, _ = env.step(actions)
        step_charging = 0.0
        for b in env.buildings:
            if hasattr(b, "chargers_electricity_consumption") and len(b.chargers_electricity_consumption) > 0:
                step_charging = b.chargers_electricity_consumption[-1]
        total_charging += max(0, step_charging)

    print(f"   CONSUMO TOTAL 10 steps: {total_charging:.2f} kWh")

    if total_charging > 0:
        print("\n[OK] DATASET FUNCIONANDO - Chargers consumiendo energia")
    else:
        print("\n[ERROR] CHARGERS NO CONSUMEN ENERGIA")

    print("=" * 80)


if __name__ == "__main__":
    main()
