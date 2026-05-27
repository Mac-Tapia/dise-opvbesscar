"""scripts/analysis/analyse_energy_flows.py — Diagnostic: energy flows and CO2 for one full episode."""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from src.core import load_site_config
from src.rl import UniversalPVBESSEnv
from src.core.reward import RewardWeights

# -- Load data -----------------------------------------------------------------
solar = pd.read_csv(_ROOT / "data/oe2/Generacionsolar/pv_generation_citylearn2024.csv")
chargers = pd.read_csv(_ROOT / "data/oe2/chargers/chargers_ev_ano_2024_v3.csv")
mall = pd.read_csv(_ROOT / "data/oe2/demandamallkwh/demandamallhorakwh.csv")
ev_dfs = {
    "moto":     chargers["ev_energia_motos_kwh"],
    "mototaxi": chargers["ev_energia_mototaxis_kwh"],
}

pv_annual = solar["potencia_kw"].sum()
ev_moto_annual = ev_dfs["moto"].sum()
ev_moto_max = ev_dfs["moto"].max()
ev_taxi_annual = ev_dfs["mototaxi"].sum()
ev_total_annual = ev_moto_annual + ev_taxi_annual
mall_annual = mall["mall_demand_kwh"].sum()

print("=" * 60)
print("  ESTADISTICAS DE DATOS OE2 (series temporales)")
print("=" * 60)
print(f"  PV anual total    : {pv_annual:>12,.0f} kWh/anio")
print(f"  PV pico           : {solar['potencia_kw'].max():>12.1f} kW")
print(f"  PV horas activas  : {(solar['potencia_kw'] > 0).sum():>12d} h/anio")
print(f"  EV motos anual    : {ev_moto_annual:>12,.0f} kWh/anio")
print(f"  EV motos max/h    : {ev_moto_max:>12.2f} kWh/h")
print(f"  EV mototaxi anual : {ev_taxi_annual:>12,.0f} kWh/anio")
print(f"  EV total anual    : {ev_total_annual:>12,.0f} kWh/anio")
print(f"  Mall anual        : {mall_annual:>12,.0f} kWh/anio")
print(f"  CARGA TOTAL OE2   : {ev_total_annual + mall_annual:>12,.0f} kWh/anio")
print(f"  Ratio PV/carga    : {pv_annual / (ev_total_annual + mall_annual) * 100:.1f}%")

# -- Build env ----------------------------------------------------------------
site = load_site_config(_ROOT / "configs/sites/iquitos_bess_mall.yaml")
env = UniversalPVBESSEnv.from_dataframes(
    site=site, building_idx=0,
    solar_df=solar, ev_dfs=ev_dfs, fixed_load_df=mall,
    reward_weights=RewardWeights.co2_dual_focus(), seed=42,
)

# -- Full deterministic zero action (discharge BESS, serve 100% EV) ----------
def run_policy(label, bess_a, ev_frac):
    env.reset()
    totals = dict(co2=0.0, pv=0.0, grid=0.0, ev_served=dict(moto=0.0, mototaxi=0.0),
                  ev_demand=dict(moto=0.0, mototaxi=0.0), reward=0.0)
    action = np.array([bess_a, ev_frac, ev_frac], dtype=np.float32)
    for _ in range(8760):
        _, reward, done, _, info = env.step(action)
        totals["co2"] += info["co2_avoided_kg"]
        totals["pv"]  += info["pv_kwh"]
        totals["grid"] += info["grid_import_kwh"]
        totals["reward"] += reward
        if done:
            break
    return totals, info["ev_satisfaction"]

print()
print("=" * 60)
print("  SIMULACION DE POLITICAS (agente fijo, 8760 pasos)")
print("=" * 60)

policies = [
    ("PV-pass + EV-100%  (bess=0, ev=1.0)",  0.0, 1.0),
    ("Descarga BESS + EV-100% (bess=-1, ev=1.0)", -1.0, 1.0),
    ("Carga BESS + EV-0%  (bess=+1, ev=0.0)", 1.0, 0.0),
]

for label, bess_a, ev_frac in policies:
    t, ev_sat = run_policy(label, bess_a, ev_frac)
    co2_pct = t["co2"] / 7_054_000 * 100
    print(f"\n  [{label}]")
    print(f"    CO2 evitado : {t['co2']/1e3:>8.1f} t/anio  ({co2_pct:.1f}% de F0)")
    print(f"    PV usada    : {t['pv']:>12,.0f} kWh/anio")
    print(f"    Grid import : {t['grid']:>12,.0f} kWh/anio")
    print(f"    EV sat      : moto={ev_sat[0]:.3f}  mototaxi={ev_sat[1]:.3f}")
    print(f"    Reward total: {t['reward']:>10.1f}")

# -- CO2 budget breakdown at ev=1.0, bess=0 -----------------------------------
print()
print("=" * 60)
print("  BALANCE CO2 TEORICO (politica: bess=0, ev=1.0)")
print("=" * 60)
moto_kappa   = 0.87
taxi_kappa   = 0.54
alpha_grid   = 0.4521
co2_direct_moto = ev_moto_annual * moto_kappa
co2_direct_taxi = ev_taxi_annual * taxi_kappa
co2_indirect = pv_annual * alpha_grid
print(f"  Direct CO2 motos    : {co2_direct_moto/1e3:>8.1f} t/anio  ({ev_moto_annual:.0f} kWh x {moto_kappa} kg/kWh)")
print(f"  Direct CO2 mototaxis: {co2_direct_taxi/1e3:>8.1f} t/anio  ({ev_taxi_annual:.0f} kWh x {taxi_kappa} kg/kWh)")
print(f"  Indirect CO2 (PV)   : {co2_indirect/1e3:>8.1f} t/anio  ({pv_annual:.0f} kWh x {alpha_grid} kg/kWh)")
print(f"  CO2 EVITADO TOTAL   : {(co2_direct_moto + co2_direct_taxi + co2_indirect)/1e3:>8.1f} t/anio")
print(f"  F0 baseline         : {7054.0:>8.1f} t/anio")
print(f"  Reduccion teorica   : {(co2_direct_moto + co2_direct_taxi + co2_indirect)/7_054_000*100:.1f}%")
print()
print("  Nota: F2 SAC ep48 validado = 2,622 t CO2/anio EMITIDO (no evitado)")
print("  La metrica 'co2_avoided' suma savings directas + indirectas por hora")
