"""Script rápido para verificar el dataset antes del entrenamiento."""
import pandas as pd  # type: ignore
import json
from pathlib import Path

def main():
    base = Path("data/processed/citylearn/iquitos_ev_mall")

    print("=" * 60)
    print("VERIFICACIÓN RÁPIDA DATASET ENTRENAMIENTO")
    print("=" * 60)

    # 1. Building_1.csv
    b1 = pd.read_csv(base / "Building_1.csv")
    solar_sum = b1["solar_generation"].sum()
    load_sum = b1["non_shiftable_load"].sum()
    print(f"\n1. Building_1.csv ({len(b1)} filas)")
    print(f"   solar_generation sum: {solar_sum:,.2f} (normalizado W/kWp)")
    print(f"   non_shiftable_load sum: {load_sum:,.0f} kWh/año")

    # 2. Schema PV config
    with open(base / "schema.json") as f:
        schema = json.load(f)

    pv_cfg = schema["buildings"]["Building_1"].get("pv", {})
    nominal_pv = pv_cfg.get("nominal_power", 0)
    print(f"\n2. Schema PV:")
    print(f"   nominal_power: {nominal_pv} kW")

    # 3. Cálculo energía solar
    expected_kwh = solar_sum * nominal_pv
    print(f"\n3. ENERGÍA SOLAR CALCULADA:")
    print(f"   {solar_sum:,.2f} × {nominal_pv} kW = {expected_kwh:,.0f} kWh/año")

    if expected_kwh > 7_000_000:
        print("   ✓ CORRECTO (esperado ~8M kWh)")
    else:
        print("   ✗ ERROR - MUY BAJO (esperado ~8M kWh)")

    # 4. Chargers
    ch1 = pd.read_csv(base / "charger_simulation_001.csv")
    charger_demand = ch1["electric_vehicle_charger_demand"].sum()
    print(f"\n4. Charger 001:")
    print(f"   Demanda total: {charger_demand:,.2f} kWh/año")

    # 5. Verificar reward function weights
    print(f"\n5. REWARD FUNCTION WEIGHTS (hardcoded en simulate.py):")
    print(f"   CO2: 0.50 (primary)")
    print(f"   Solar: 0.20 (secondary)")
    print(f"   Cost: 0.15")
    print(f"   EV: 0.10")
    print(f"   Grid: 0.05")

    # 6. CO2 factor
    print(f"\n6. CO2 Factor: 0.4521 kg CO₂/kWh (Iquitos térmico)")

    # 7. Baselines en reward function
    print(f"\n7. BASELINES REWARD (en rewards.py):")
    print(f"   co2_baseline_offpeak: 130 kWh/h")
    print(f"   co2_baseline_peak: 250 kWh/h (18-21h)")
    print(f"   peak_demand_limit_kw: 200 kW")

    # Validación final
    print("\n" + "=" * 60)
    all_ok = expected_kwh > 7_000_000 and nominal_pv > 4000
    if all_ok:
        print("✓ DATASET VALIDADO - LISTO PARA ENTRENAMIENTO")
    else:
        print("✗ HAY ERRORES EN EL DATASET")
    print("=" * 60)

if __name__ == "__main__":
    main()
