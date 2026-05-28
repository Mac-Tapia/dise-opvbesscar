#!/usr/bin/env python3
"""bess_optimal_sizing.py — Dimensionamiento óptimo BESS con despacho dinámico.

Evalúa combinaciones (capacidad_kWh x potencia_kW) y determina el diseño óptimo
considerando: cobertura EV, peak shaving mall, reducción CO₂ y ROI.

Usa la simulación dinámica de simulate_bess_arbitrage_hp_hfp() que ya integra:
  - Prioridad 1: BESS → EV (siempre que PV < EV)
  - Prioridad 2: BESS → peak shaving mall (cuando demanda neta > 1900 kW)
  - Carga dinámica desde PV excedente (hora de cruce varía cada día)
"""
from __future__ import annotations
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import numpy as np
import pandas as pd

from src.dimensionamiento.oe2._paths import (
    SOLAR_CANONICAL_CSV,
    CHARGERS_CANONICAL_CSV,
    MALL_DEMAND_CANONICAL_CSV,
)
from src.dimensionamiento.oe2.disenobess.bess import simulate_bess_arbitrage_hp_hfp


PEAK_SHAVING_THRESHOLD_KW = 1900.0
# Factores CO₂ variables Sistema Aislado Loreto (MINEM 2024 + estacionalidad Loreto)
# HP(18-23h): factor_mes×1.35 | HFP: factor_mes×0.908  — preserva promedio mensual
# Lluviosa(dic-may)=0.43, Seca(jun-nov)=0.47 kg CO₂/kWh base mensual
CO2_FACTOR_HP_KG_KWH  = 0.634   # 0.47 × 1.35 (peor caso seca + HP)
CO2_FACTOR_HFP_KG_KWH = 0.390   # 0.43 × 0.908 (mejor caso lluviosa + HFP)
CO2_FACTOR_KG_KWH     = 0.4521  # promedio anual MINEM (referencia histórica)
CAPEX_PER_KWH = 400.0   # USD/kWh (LFP commercial, 2024)
CAPEX_PER_KW  = 150.0   # USD/kW (inverter/BMS)
TARIFF_HP     = 0.45    # S/./kWh
TARIFF_HFP    = 0.28    # S/./kWh
LIFETIME_YEARS = 15


def load_data():
    solar = pd.read_csv(SOLAR_CANONICAL_CSV)
    pv_kwh = solar["energia_kwh"].values.astype(float)

    chargers = pd.read_csv(CHARGERS_CANONICAL_CSV)
    ev_col = "ev_energia_total_kwh"
    ev_kwh = chargers[ev_col].values.astype(float)

    mall = pd.read_csv(MALL_DEMAND_CANONICAL_CSV)
    mall_col = next(c for c in mall.columns if "kwh" in c.lower() or "demand" in c.lower())
    mall_kwh = mall[mall_col].values.astype(float)

    return pv_kwh, ev_kwh, mall_kwh


def evaluate_bess(pv_kwh, ev_kwh, mall_kwh, capacity_kwh, power_kw):
    df_sim, metrics = simulate_bess_arbitrage_hp_hfp(
        pv_kwh=pv_kwh,
        ev_kwh=ev_kwh,
        mall_kwh=mall_kwh,
        capacity_kwh=capacity_kwh,
        power_kw=power_kw,
    )

    # EV coverage
    total_ev = ev_kwh.sum()
    bess_to_ev = df_sim["bess_to_ev_kwh"].sum() if "bess_to_ev_kwh" in df_sim.columns else 0.0
    pv_to_ev = df_sim["pv_to_ev_kwh"].sum() if "pv_to_ev_kwh" in df_sim.columns else 0.0
    ev_coverage_pct = 100.0 * (pv_to_ev + bess_to_ev) / max(total_ev, 1.0)

    # Peak shaving
    mall_arr = df_sim["mall_kwh"].values if "mall_kwh" in df_sim.columns else mall_kwh
    bess_to_mall = df_sim["bess_to_mall_kwh"].values if "bess_to_mall_kwh" in df_sim.columns else np.zeros(len(mall_arr))
    net_mall = mall_arr - bess_to_mall
    hours_above_threshold_original = int((mall_arr > PEAK_SHAVING_THRESHOLD_KW).sum())
    hours_above_threshold_after = int((net_mall > PEAK_SHAVING_THRESHOLD_KW).sum())
    peak_reduction_pct = 100.0 * (1 - hours_above_threshold_after / max(hours_above_threshold_original, 1))
    peak_original = mall_arr.max()
    peak_after = net_mall.max()

    # CO₂ con factor horario variable (HP=peakers diesel, HFP=base load)
    if "co2_grid_kg" in df_sim.columns:
        co2_kg = float(df_sim["co2_grid_kg"].sum())
    else:
        # Fallback: calcular desde grid_import con factores HP/HFP
        grid_col = "grid_import_kwh" if "grid_import_kwh" in df_sim.columns else None
        if grid_col:
            hours_arr2 = np.arange(len(df_sim)) % 24
            is_hp_arr2 = (hours_arr2 >= 18) & (hours_arr2 < 23)
            co2_arr = df_sim[grid_col].values * np.where(is_hp_arr2, CO2_FACTOR_HP_KG_KWH, CO2_FACTOR_HFP_KG_KWH)
            co2_kg = float(co2_arr.sum())
        else:
            grid_import = df_sim["grid_to_ev_kwh"].sum() + df_sim["grid_to_mall_kwh"].sum()
            co2_kg = grid_import * CO2_FACTOR_KG_KWH

    # Cycles/day
    bess_discharge_total = df_sim["bess_discharge_kwh"].sum() if "bess_discharge_kwh" in df_sim.columns else 0.0
    cycles_per_day = bess_discharge_total / 365.0 / max(capacity_kwh, 1.0)

    # Economics: savings from peak shaving + EV arbitrage
    bess_to_mall_total = df_sim["bess_to_mall_kwh"].sum() if "bess_to_mall_kwh" in df_sim.columns else 0.0
    # During HP hours (18-23h), BESS→Mall saves HP tariff, paid at HFP
    hours_arr = np.arange(len(mall_arr)) % 24
    is_hp = (hours_arr >= 18) & (hours_arr < 23)
    bess_mall_arr = df_sim["bess_to_mall_kwh"].values if "bess_to_mall_kwh" in df_sim.columns else bess_to_mall
    bess_ev_arr = df_sim["bess_to_ev_kwh"].values if "bess_to_ev_kwh" in df_sim.columns else np.zeros(len(mall_arr))
    savings_soles = (
        (bess_mall_arr[is_hp] + bess_ev_arr[is_hp]).sum() * (TARIFF_HP - TARIFF_HFP)
    )

    # CAPEX
    capex_usd = capacity_kwh * CAPEX_PER_KWH + power_kw * CAPEX_PER_KW
    capex_soles = capex_usd * 3.75  # 1 USD ≈ 3.75 S/.
    annual_savings = savings_soles
    simple_payback_years = capex_soles / max(annual_savings, 1.0)
    roi_pct = 100.0 * annual_savings / max(capex_soles, 1.0)

    return {
        "capacity_kwh": capacity_kwh,
        "power_kw": power_kw,
        "ev_coverage_pct": round(ev_coverage_pct, 1),
        "peak_original_kw": round(peak_original, 0),
        "peak_after_kw": round(peak_after, 0),
        "peak_reduction_pct": round(peak_reduction_pct, 1),
        "hours_peak_original": hours_above_threshold_original,
        "hours_peak_after": hours_above_threshold_after,
        "co2_kg_year": round(co2_kg, 0),
        "cycles_per_day": round(cycles_per_day, 2),
        "savings_soles_year": round(annual_savings, 0),
        "capex_usd": round(capex_usd, 0),
        "payback_years": round(simple_payback_years, 1),
        "roi_pct": round(roi_pct, 1),
    }


def main():
    print("Cargando datos OE2...")
    pv_kwh, ev_kwh, mall_kwh = load_data()
    print(f"  PV: {pv_kwh.sum()/1e6:.2f} GWh/año | EV: {ev_kwh.sum():,.0f} kWh/año | Mall: {mall_kwh.sum()/1e6:.2f} GWh/año")
    print(f"  Mall pico máximo: {mall_kwh.max():.0f} kW | Umbral peak shaving: {PEAK_SHAVING_THRESHOLD_KW:.0f} kW")
    print()

    # Grid de configuraciones a evaluar
    capacidades_kwh = [500, 750, 1000, 1500, 2000, 2500, 3000]
    potencias_kw = [200, 300, 400, 500, 600]

    results = []
    total = len(capacidades_kwh) * len(potencias_kw)
    i = 0
    for cap in capacidades_kwh:
        for pot in potencias_kw:
            i += 1
            print(f"  Evaluando {i}/{total}: {cap} kWh / {pot} kW...", end="\r")
            r = evaluate_bess(pv_kwh, ev_kwh, mall_kwh, cap, pot)
            results.append(r)

    df = pd.DataFrame(results)
    print(f"\n  Evaluadas {len(df)} configuraciones.\n")

    # Filtrar configuraciones viables: EV >= 98%, peak_reduction >= 30%
    viable = df[(df["ev_coverage_pct"] >= 98.0) & (df["peak_reduction_pct"] >= 30.0)].copy()
    print(f"Configuraciones viables (EV>=98%, peak_shaving>=30%): {len(viable)}")

    if len(viable) == 0:
        print("[WARN] Ninguna config viable con umbral 30%. Mostrando todas.")
        viable = df.copy()

    # Ordenar por ROI descendente
    viable_sorted = viable.sort_values("roi_pct", ascending=False)

    print()
    print("=" * 110)
    print("TABLA: DIMENSIONAMIENTO ÓPTIMO BESS — DESPACHO DINÁMICO (peak shaving + EV prioritario)")
    print("=" * 110)
    cols = ["capacity_kwh", "power_kw", "ev_coverage_pct", "peak_after_kw",
            "peak_reduction_pct", "hours_peak_after", "co2_kg_year",
            "cycles_per_day", "capex_usd", "savings_soles_year", "payback_years", "roi_pct"]
    headers = ["Cap(kWh)", "Pot(kW)", "EV%", "Pico(kW)", "PS%", "h>1900",
               "CO2(kg/año)", "Ciclos/día", "CAPEX(USD)", "Ahorro(S/.)", "Payback(a)", "ROI%"]
    print("  ".join(f"{h:>10}" for h in headers))
    print("-" * 110)
    for _, row in viable_sorted.iterrows():
        vals = [str(int(row["capacity_kwh"])), str(int(row["power_kw"])),
                f"{row['ev_coverage_pct']:.1f}", f"{row['peak_after_kw']:.0f}",
                f"{row['peak_reduction_pct']:.1f}", str(int(row["hours_peak_after"])),
                f"{row['co2_kg_year']:,.0f}", f"{row['cycles_per_day']:.2f}",
                f"{row['capex_usd']:,.0f}", f"{row['savings_soles_year']:,.0f}",
                f"{row['payback_years']:.1f}", f"{row['roi_pct']:.1f}"]
        print("  ".join(f"{v:>10}" for v in vals))

    # Configuración óptima: mayor ROI entre las viables
    best = viable_sorted.iloc[0]
    print()
    print("=" * 110)
    print("CONFIGURACIÓN ÓPTIMA (mayor ROI con EV>=98% y peak shaving>=30%):")
    print(f"  Capacidad:       {int(best['capacity_kwh'])} kWh")
    print(f"  Potencia:        {int(best['power_kw'])} kW")
    print(f"  Cobertura EV:    {best['ev_coverage_pct']:.1f}%")
    print(f"  Pico mall neto:  {best['peak_after_kw']:.0f} kW (original: {best['peak_original_kw']:.0f} kW)")
    print(f"  Reducción picos: {best['peak_reduction_pct']:.1f}% horas con mall>1900 kW")
    print(f"  CO₂ anual:       {best['co2_kg_year']:,.0f} kg/año")
    print(f"  Ciclos/día:      {best['cycles_per_day']:.2f}")
    print(f"  CAPEX estimado:  {best['capex_usd']:,.0f} USD ({best['capex_usd']*3.75:,.0f} S/.)")
    print(f"  Ahorro anual:    {best['savings_soles_year']:,.0f} S/./año")
    print(f"  Payback simple:  {best['payback_years']:.1f} años")
    print(f"  ROI anual:       {best['roi_pct']:.1f}%")

    # Guardar
    out_path = _ROOT / "outputs" / "bess_sizing"
    out_path.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path / "bess_optimal_sizing_full.csv", index=False)
    viable_sorted.to_csv(out_path / "bess_optimal_sizing_viable.csv", index=False)
    print()
    print(f"[OK] Resultados guardados en: {out_path}")


if __name__ == "__main__":
    main()
