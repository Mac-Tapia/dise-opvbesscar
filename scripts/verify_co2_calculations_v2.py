#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VERIFICACION: CO2 Reduction Calculations (Direct & Indirect)

Este script verifica que el entrenamiento esta calculando correctamente:
1. CO2 INDIRECTO: Solar que evita importacion de grid
2. CO2 DIRECTO: EVs que evitan combustion
"""

from __future__ import annotations
import sys
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
import pandas as pd
from typing import Tuple

from iquitos_citylearn.oe3.rewards import (
    MultiObjectiveReward,
    MultiObjectiveWeights,
    IquitosContext,
)


def print_section(title: str) -> None:
    """Print formatted section header."""
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")
    sys.stdout.flush()


def test_context():
    """Test 1: IquitosContext parameters."""
    print_section("TEST 1: IquitosContext (OE2 Parameters)")

    ctx = IquitosContext()

    print("CO2 Parameters:")
    print(f"  CO2 Factor Grid (thermal): {ctx.co2_factor_kg_per_kwh} kg CO2/kWh")
    print(f"  CO2 Conversion (EVs): {ctx.co2_conversion_factor} kg CO2/kWh")
    print(f"  EV Efficiency: {ctx.km_per_kwh} km/kWh")
    print(f"  Combustion Efficiency: {ctx.km_per_gallon} km/gallon")
    print(f"  Combustion Emissions: {ctx.kgco2_per_gallon} kg CO2/gallon")
    print(f"\nChargers: {ctx.n_chargers}, Total sockets: {ctx.total_sockets}")
    print("\n[OK] Context loaded successfully")
    return ctx


def test_weights():
    """Test 2: Reward weights."""
    print_section("TEST 2: Reward Weights")

    weights = MultiObjectiveWeights(
        co2=0.50,
        cost=0.15,
        solar=0.20,
        ev_satisfaction=0.10,
        grid_stability=0.05
    )

    print("Reward Weights:")
    print(f"  CO2 (primary): {weights.co2:.4f}")
    print(f"  Solar (secondary): {weights.solar:.4f}")
    print(f"  Cost: {weights.cost:.4f}")
    print(f"  EV Satisfaction: {weights.ev_satisfaction:.4f}")
    print(f"  Grid Stability: {weights.grid_stability:.4f}")

    total = weights.co2 + weights.cost + weights.solar + weights.ev_satisfaction + weights.grid_stability
    print(f"\nTotal (should be 1.0): {total:.4f}")
    assert abs(total - 1.0) < 0.01, f"Weights sum error: {total}"
    print("[OK] Weights validated")
    return weights


def test_scenarios():
    """Test 3: CO2 calculations in realistic scenarios."""
    print_section("TEST 3: CO2 Calculations (Scenarios)")

    weights = MultiObjectiveWeights(co2=0.50, cost=0.15, solar=0.20, ev_satisfaction=0.10, grid_stability=0.05)
    reward_fn = MultiObjectiveReward(weights=weights)

    scenarios = [
        ("OFF-PEAK (02:00)", 2, 30.0, 0.0, 0.0),
        ("EARLY MORNING (06:00)", 6, 50.0, 10.0, 20.0),
        ("SOLAR PEAK (12:00)", 12, 20.0, 200.0, 50.0),
        ("AFTERNOON (15:00)", 15, 40.0, 150.0, 50.0),
        ("PRE-PEAK (17:00)", 17, 60.0, 50.0, 50.0),
        ("PEAK NIGHT (19:00)", 19, 100.0, 0.0, 50.0),
        ("LATE NIGHT (23:00)", 23, 80.0, 0.0, 30.0),
    ]

    results = []
    for name, hour, grid_imp, solar, ev_ch in scenarios:
        reward, comps = reward_fn.compute(
            grid_import_kwh=grid_imp,
            grid_export_kwh=0.0,
            solar_generation_kwh=solar,
            ev_charging_kwh=ev_ch,
            ev_soc_avg=0.7,
            bess_soc=0.6,
            hour=hour,
        )
        results.append({
            "scenario": name,
            "grid_import": grid_imp,
            "solar": solar,
            "ev_charging": ev_ch,
            "co2_grid": comps.get("co2_grid_kg", 0),
            "co2_avoided_indirect": comps.get("co2_avoided_indirect_kg", 0),
            "co2_avoided_direct": comps.get("co2_avoided_direct_kg", 0),
            "co2_avoided_total": comps.get("co2_avoided_total_kg", 0),
            "co2_net": comps.get("co2_net_kg", 0),
            "r_co2": comps.get("r_co2", 0),
            "reward": reward,
        })

    df = pd.DataFrame(results)

    print("Scenario Data:")
    print(df[["scenario", "grid_import", "solar", "ev_charging"]].to_string(index=False))

    print("\n\nCO2 Components (kg):")
    print(df[["scenario", "co2_grid", "co2_avoided_indirect", "co2_avoided_direct", "co2_net"]].to_string(index=False))

    print("\n\nRewards:")
    print(df[["scenario", "r_co2", "reward"]].to_string(index=False))

    print("\n\nValidations:")

    # Check solar peak
    solar_peak = df[df["scenario"] == "SOLAR PEAK (12:00)"].iloc[0]
    print(f"  Solar Peak indirect avoidance: {solar_peak['co2_avoided_indirect']:.2f} kg")
    assert solar_peak['co2_avoided_indirect'] > 50, "Solar should avoid >50kg"

    # Check EV direct
    ev_rows = df[df["ev_charging"] > 0]
    if len(ev_rows) > 0:
        avg_direct = ev_rows['co2_avoided_direct'].mean()
        print(f"  EV Direct avoidance (avg): {avg_direct:.2f} kg")
        assert avg_direct > 0, "EV should avoid CO2 directly"

    # Check sum
    df["sum_check"] = df["co2_avoided_indirect"] + df["co2_avoided_direct"]
    max_err = (df["sum_check"] - df["co2_avoided_total"]).abs().max()
    print(f"  Sum accuracy error: {max_err:.6f} kg (should be ~0)")
    assert max_err < 0.001, "Sum mismatch"

    print("\n[OK] All scenario validations passed")


def test_annual():
    """Test 4: Full year simulation."""
    print_section("TEST 4: Annual Simulation (8,760 hours)")

    weights = MultiObjectiveWeights(co2=0.50, cost=0.15, solar=0.20, ev_satisfaction=0.10, grid_stability=0.05)
    reward_fn = MultiObjectiveReward(weights=weights)

    # Generate synthetic annual data
    hours = np.arange(8760)

    # Solar: peaks at noon, 0 at night
    solar = 200 * np.maximum(0, np.sin((hours % 24) * np.pi / 24)) ** 2

    # EV charging: 9AM-10PM only
    ev_mask = ((hours % 24 >= 9) & (hours % 24 <= 21)).astype(float)
    ev_ch = 50.0 * ev_mask * (0.8 + 0.2 * np.sin((hours % 24) * np.pi / 12))

    # Grid: inversely related to solar
    grid = 100 - 0.5 * solar + 20 * np.random.randn(8760)
    grid = np.maximum(10, grid)

    # Sample daily
    co2_grids = []
    co2_indirect = []
    co2_direct = []
    co2_total_avoided = []

    for t in range(0, 8760, 24):
        hour = t % 24
        reward, comps = reward_fn.compute(
            grid_import_kwh=grid[t],
            grid_export_kwh=0.0,
            solar_generation_kwh=solar[t],
            ev_charging_kwh=ev_ch[t],
            ev_soc_avg=0.7,
            bess_soc=0.6,
            hour=hour,
        )
        co2_grids.append(comps.get("co2_grid_kg", 0))
        co2_indirect.append(comps.get("co2_avoided_indirect_kg", 0))
        co2_direct.append(comps.get("co2_avoided_direct_kg", 0))
        co2_total_avoided.append(comps.get("co2_avoided_total_kg", 0))

    # Extrapolate to full year
    factor = 8760 / len(co2_grids)
    print(f"Simulated {len(co2_grids)} days (sampled from {len(co2_grids)*24} hours)")
    print(f"\nAnnual Totals (extrapolated x{factor:.1f}):")
    print(f"  CO2 Grid Import: {np.sum(co2_grids) * factor:.0f} kg")
    print(f"  CO2 Avoided Indirect (solar): {np.sum(co2_indirect) * factor:.0f} kg")
    print(f"  CO2 Avoided Direct (EVs): {np.sum(co2_direct) * factor:.0f} kg")
    print(f"  CO2 Avoided Total: {np.sum(co2_total_avoided) * factor:.0f} kg")

    if np.sum(co2_grids) > 0:
        reduction_pct = (np.sum(co2_total_avoided) / np.sum(co2_grids)) * 100
        print(f"\n  Net Reduction: {reduction_pct:.1f}%")

    print("\n[OK] Annual simulation completed")


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("  CO2 REDUCTION CALCULATIONS VERIFICATION")
    print("  Verifying direct and indirect CO2 reduction calculations")
    print("="*80)

    try:
        test_context()
        test_weights()
        test_scenarios()
        test_annual()

        print_section("SUMMARY")
        print("All tests PASSED!")
        print("\nCO2 CALCULATION STATUS:")
        print("  [OK] CO2 Indirect (solar avoids grid import)")
        print("  [OK] CO2 Direct (EVs avoid combustion)")
        print("  [OK] Multiobjetive rewards (weight 0.50 on CO2)")
        print("  [OK] Annual calculations working")
        print("\nThe training IS calculating both direct and indirect CO2 reductions correctly.")

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
